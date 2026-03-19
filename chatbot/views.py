from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from .models import Artwork, ArtworkImage, Conversation
from .serializers import ArtworkSerializer, ConversationSerializer
from .core.embeddings import generate_embedding
from .core.vector_db import VectorDB
from .core.opera_detection import OperaDetector
import json
import os
from django.conf import settings

import requests
from dotenv import load_dotenv
load_dotenv()

# carica il vector db all'avvio
VECTOR_DB_PATH = os.path.join(settings.BASE_DIR, 'storage', 'vector_db.pkl')
vector_db = VectorDB()
vector_db.load(VECTOR_DB_PATH)

# istanzia opera detector all'avvio
detector = OperaDetector(vector_db)

def call_runpod(prompt, image_base64=None):
    import time
    api_key = os.getenv('RUNPOD_API_KEY')
    endpoint_id = os.getenv('RUNPOD_ENDPOINT_ID')
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = [
        {
            "role": "system",
            "content": "Sei una guida museale esperta. Rispondi SEMPRE e SOLO in italiano. Vai direttamente alla risposta senza preamboli. Non usare markdown, asterischi, grassetto o corsivo. Scrivi in testo semplice."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    payload = {
        "input": {
            "messages": messages,
            "sampling_params": {
                "max_tokens": 4096,
                "temperature": 0.7
            }
        }
    }

    # invia il job asincrono
    response = requests.post(
        f"https://api.runpod.ai/v2/{endpoint_id}/run",
        headers=headers,
        json=payload,
        timeout=30
    )
    result = response.json()
    job_id = result.get('id')
    print("JOB AVVIATO:", job_id)

    if not job_id:
        raise Exception(f"RunPod non ha restituito un job ID: {result}")

    # polling finché il job non è completato
    for attempt in range(120):
        time.sleep(2)
        status_response = requests.get(
            f"https://api.runpod.ai/v2/{endpoint_id}/status/{job_id}",
            headers=headers,
            timeout=30
        )
        status_result = status_response.json()
        job_status = status_result.get('status')
        print(f"Polling #{attempt + 1} — status: {job_status}")

        if job_status == 'COMPLETED':
            output = status_result.get('output')
            print("OUTPUT COMPLETO:", output)
            if isinstance(output, list):
                choices = output[0].get('choices', [])
            else:
                choices = output.get('choices', [])
            choice = choices[0]
            if 'text' in choice:
                return choice['text'].strip()
            elif 'message' in choice:
                return choice['message']['content'].strip()
            elif 'tokens' in choice:
                return ''.join(choice['tokens']).strip()
            else:
                raise Exception(f"Formato output non riconosciuto: {choice}")

        elif job_status == 'FAILED':
            raise Exception(f"Job RunPod fallito: {status_result.get('error')}")

    raise Exception("Timeout: RunPod non ha completato il job entro il tempo massimo.")

@api_view(['POST'])
@permission_classes([AllowAny])
def chat(request):
    input_text = request.data.get('text', None)
    input_image = request.FILES.get('image', None)
    current_artwork = request.data.get('current_artwork', None)
    previous_artwork = request.data.get('previous_artwork', None)
    history = json.loads(request.data.get('history', '[]'))  # ← aggiungi

    if not input_text and not input_image:
        return Response(
            {'error': 'Provide text or image'},
            status=status.HTTP_400_BAD_REQUEST
        )

# casistica: immagine (ha priorità sul testo)
    if input_image:
        embedding = generate_embedding(input_image)
        results = vector_db.search(embedding, top_k=1)
        similarity_score = results[0]['similarity']
        if similarity_score < 0.7:
            return Response({'response': 'Opera non riconosciuta. Prova con un\'immagine più chiara.'})
        artwork_name = results[0]['metadata']['nome']
        # rileva eventuali opere aggiuntive citate nel testo
        extra_artworks = detector.detect_multiple(input_text) if input_text else []
        extra_artworks = [o for o in extra_artworks if o != artwork_name]
    # casistica: solo testo (nessuna immagine allegata)
    elif input_text:
        detected_artworks = detector.detect_multiple(input_text)
        if not detected_artworks and current_artwork:
            detected_artworks = [current_artwork]
        if not detected_artworks:
            return Response({'response': 'Opera non riconosciuta nel testo.'})
        artwork_name = detected_artworks[0]
        extra_artworks = detected_artworks[1:]
        similarity_score = 1.0

    # recupera contesto opera principale dal db
    try:
        artwork = Artwork.objects.get(name=artwork_name)
        main_context = f'Contesto {artwork_name}: {artwork.context}'
    except Artwork.DoesNotExist:
        main_context = f'{artwork_name}: opera non presente nel database.'

    # recupera contesti opere aggiuntive (es. paragoni)
    extra_context = ''
    for opera in extra_artworks:
        try:
            a = Artwork.objects.get(name=opera)
            extra_context += f'\nContesto {opera}: {a.context}'
        except Artwork.DoesNotExist:
            extra_context += f'\n{opera}: opera non presente nella galleria.'

    # recupera contesto opera precedente se disponibile
    previous_context = ''
    if previous_artwork and previous_artwork != artwork_name:
        try:
            prev = Artwork.objects.get(name=previous_artwork)
            previous_context = f'\nContesto opera precedente {previous_artwork}: {prev.context}'
        except Artwork.DoesNotExist:
            previous_context = f'\n{previous_artwork}: opera precedente non presente nel database.'

    # riepilogo esplicito di tutte le opere discusse nella sessione
    opere_sessione = [artwork_name]
    if previous_artwork and previous_artwork not in opere_sessione:
        opere_sessione.append(previous_artwork)
    for o in extra_artworks:
        if o not in opere_sessione:
            opere_sessione.append(o)
    riepilogo_opere = ', '.join(opere_sessione)

    # cronologia per il prompt
    history_text = ''
    if history:
        history_text = '\nCronologia conversazione:\n'
        for msg in history[-6:]:
            role = 'Utente' if msg['role'] == 'user' else 'Assistente'
            history_text += f"{role}: {msg['content']}\n"
    # nota esplicita sulle opere della sessione in coda alla history
    history_text += f'\nOpere discusse in questa sessione: {riepilogo_opere}\n'

    # costruisci prompt
    domanda = input_text if input_text else f"Descrivi l'opera '{artwork_name}' in modo dettagliato e coinvolgente."

    # specifica chiaramente la fonte di riconoscimento di ogni opera
    if input_image:
        image_label = f'Opera riconosciuta dalla IMMAGINE caricata: {artwork_name}'
        text_labels = '\n'.join([f'Opera citata nel TESTO: {o}' for o in extra_artworks])
        source_info = image_label + ('\n' + text_labels if text_labels else '')
    else:
        source_info = '\n'.join([f'Opera citata nel testo: {o}' for o in ([artwork_name] + extra_artworks)])

    prompt = (
        f'{source_info}\n'
        f'    {main_context}{extra_context}{previous_context}\n'
        f'    {history_text}\n'
        f'    Domanda: {domanda}\n\n'
        f'Rispondi usando il contesto fornito per le opere presenti nel database. '
        f'Per le opere non presenti o per informazioni mancanti, usa la tua conoscenza generale. '
        f'Se viene chiesto di identificare l\'opera nell\'immagine, rispondi basandoti SOLO sull\'opera riconosciuta dalla immagine, ignorando quelle citate nel testo. /no_think'
    )

    # converti immagine in base64 se presente
    image_base64 = None
    if input_image:
        import base64
        input_image.seek(0)
        image_base64 = base64.b64encode(input_image.read()).decode('utf-8')

    try:
        print("PROMPT:", prompt)
        print("input_text:", input_text)
        print("artwork_name:", artwork_name)
        print("context:", main_context)
        model_response = call_runpod(prompt, image_base64)
    except Exception as e:
        model_response = f"Errore del modello: {str(e)}"

    # salva la conversazione
    Conversation.objects.create(
        input_text=input_text,
        input_image=input_image,
        recognized_artwork=artwork_name,
        similarity_score=similarity_score,
        model_response=model_response
    )

    all_artworks = [artwork_name] + extra_artworks
    return Response({
        'artwork': artwork_name,
        'artworks': all_artworks,
        'response': model_response
    })


@api_view(['GET', 'POST'])
def artwork_list(request):
    if request.method == 'GET':
        artworks = Artwork.objects.all()
        serializer = ArtworkSerializer(artworks, many=True)
        return Response(serializer.data)

    if not request.user.is_authenticated:
        return Response(status=status.HTTP_401_UNAUTHORIZED)

    if request.method == 'POST':
        serializer = ArtworkSerializer(data=request.data)
        if serializer.is_valid():
            artwork = serializer.save()
            images = request.FILES.getlist('images')
            for image in images:
                artwork_image = ArtworkImage.objects.create(artwork=artwork, image=image)
                image_path = os.path.join(settings.MEDIA_ROOT, str(artwork_image.image))
                try:
                    embedding = generate_embedding(image_path)
                    metadata = {
                        'nome': artwork.name,
                        'filename': str(artwork_image.image),
                        'contesto': artwork.context,
                        'autore': artwork.author,
                        'epoca': artwork.period,
                        'localita': artwork.location,
                        'stile': artwork.style,
                    }
                    vector_db.add(embedding, metadata)
                except Exception as e:
                    print(f"Errore embedding {image_path}: {e}")
            vector_db.save(VECTOR_DB_PATH)
            detector.reload()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def artwork_detail(request, pk):
    try:
        artwork = Artwork.objects.get(pk=pk)
    except Artwork.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ArtworkSerializer(artwork)
        return Response(serializer.data)

    if request.method == 'PUT':
        old_name = artwork.name
        serializer = ArtworkSerializer(artwork, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            # se ci sono nuove immagini, aggiorna gli embedding 
            new_images = request.FILES.getlist('images')
            if new_images:
                # rimuove vecchi embedding e vecchie immagini dal db, poi aggiunge i nuovi dati
                
                vector_db.remove_by_name(old_name)
                artwork.images.all().delete()
                
                for image in new_images:
                    artwork_image = ArtworkImage.objects.create(artwork=artwork, image=image)
                    image_path = os.path.join(settings.MEDIA_ROOT, str(artwork_image.image))
                    try:
                        embedding = generate_embedding(image_path)
                        metadata = {
                            'nome': artwork.name,
                            'filename': str(artwork_image.image),
                            'contesto': artwork.context,
                            'autore': artwork.author,
                            'epoca': artwork.period,
                            'localita': artwork.location,
                            'stile': artwork.style,
                        }
                        vector_db.add(embedding, metadata)
                    except Exception as e:
                        print(f"Errore embedding {image_path}: {e}")
                vector_db.save(VECTOR_DB_PATH)
                detector.reload()

            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        name = artwork.name
        artwork.delete()
        removed = vector_db.remove_by_name(name)
        vector_db.save(VECTOR_DB_PATH)
        detector.reload()
        print(f"Rimossi {removed} embedding per: {name}")
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_list(request):
    conversations = Conversation.objects.all().order_by('-timestamp')
    serializer = ConversationSerializer(conversations, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    data = json.loads(request.body)
    username = data.get('username')
    password = data.get('password')

    user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user)
        return Response({'message': 'Login successful'})
    else:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def logout_view(request):
    logout(request)
    return Response({'message': 'Logout successful'})