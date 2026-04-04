from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from .models import Artwork, ArtworkImage, Conversation
from .serializers import ArtworkSerializer, ConversationSerializer
from .core.embeddings import generate_embedding, generate_embedding_with_crops
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
            "content": [
                {
                    "type": "image",
                    "image": f"data:image/jpeg;base64,{image_base64}"
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ] if image_base64 else prompt
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
    history = json.loads(request.data.get('history', '[]'))

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
        if similarity_score < 0.8:
            return Response({'response': "Opera non riconosciuta. Prova con un'altra immagine."})
        artwork_name = results[0]['metadata']['nome']
        # rileva eventuali altre opere citate nel testo
        all_detected = detector.detect_multiple(input_text) if input_text else []
        extra_artworks = [o for o in all_detected if o != artwork_name]
    # casistica: solo testo
    elif input_text:
        all_detected = detector.detect_multiple(input_text)
        if not all_detected and current_artwork:
            all_detected = [current_artwork]
        if not all_detected:
            # fallback: ricerca per metadati (autore, epoca, stile, località)
            meta_result = detector.detect_by_metadata(input_text)
            if meta_result:
                campo_label = {
                    'autore': "dell'autore",
                    'epoca': "dell'epoca",
                    'stile': "dello stile",
                    'localita': "della località",
                }.get(meta_result['campo'], 'del campo')
                return Response({
                    'metadata_match': True,
                    'opere': meta_result['opere'],
                    'campo': meta_result['campo'],
                    'valore': meta_result['valore'],
                    'campo_label': campo_label,
                })
            return Response({'response': 'Opera non riconosciuta nel testo. Prova a scrivere il titolo correttamente.'})
        artwork_name = all_detected[0]
        extra_artworks = all_detected[1:]
        similarity_score = 1.0

    # recupera contesto opera principale
    try:
        artwork = Artwork.objects.get(name=artwork_name)
        context = artwork.context
    except Artwork.DoesNotExist:
        context = ""

    # recupera contesti opere extra per risposte comparative
    extra_context = ""
    for opera in extra_artworks:
        try:
            a = Artwork.objects.get(name=opera)
            extra_context += f"\nContesto {opera}: {a.context}"
        except Artwork.DoesNotExist:
            extra_context += f"\n{opera}: usa la tua conoscenza generale."

    # converti immagine in base64 se presente
    image_base64 = None
    if input_image:
        import base64
        input_image.seek(0)
        image_base64 = base64.b64encode(input_image.read()).decode('utf-8')

    # cronologia per il prompt
    history_text = ""
    if history:
        history_text = "\nCronologia conversazione:\n"
        for msg in history[-6:]:
            role = "Utente" if msg['role'] == 'user' else "Assistente"
            history_text += f"{role}: {msg['content']}\n"

    # costruisci prompt
    domanda = input_text if input_text else f"Descrivi l'opera '{artwork_name}' in modo dettagliato e coinvolgente."

    if extra_artworks:
        quoted_artworks = ', '.join([artwork_name] + extra_artworks)
        prompt = (
            f"Opere citate: {quoted_artworks}\n"
            f"Autore: {artwork.author}\n"
            f"Epoca: {artwork.period}\n"
            f"Stile: {artwork.style}\n"
            f"Località: {artwork.location}\n"
            f"Contesto {artwork_name}: {context}{extra_context}\n"
            f"{history_text}\n"
            f"{'Immagine: vedi immagine allegata.\n' if input_image else ''}"
            f"Domanda: {domanda}\n\n"
            f"Rispondi alla domanda usando i contesti forniti e la tua conoscenza generale. /no_think"
        )
    else:
        prompt = (
            f"Opera: {artwork_name}\n"
            f"Autore: {artwork.author}\n"
            f"Epoca: {artwork.period}\n"
            f"Stile: {artwork.style}\n"
            f"Località: {artwork.location}\n"
            f"Contesto storico: {context}\n"
            f"{history_text}\n"
            f"{'Immagine: vedi immagine allegata.\n' if input_image else ''}"
            f"Domanda: {domanda}\n\n"
            f"Fornisci una risposta dettagliata basandoti sul contesto fornito. /no_think"
        )

    try:
        print("PROMPT:", prompt)
        print("input_text:", input_text)
        print("artwork_name:", artwork_name)
        print("context:", context)
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

    return Response({
        'artwork': artwork_name,
        'extra_artworks': extra_artworks,
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
                    embeddings = generate_embedding_with_crops(image_path)
                    metadata = {
                        'nome': artwork.name,
                        'filename': str(artwork_image.image),
                        'contesto': artwork.context,
                        'autore': artwork.author,
                        'epoca': artwork.period,
                        'localita': artwork.location,
                        'stile': artwork.style,
                    }
                    for emb in embeddings:
                        vector_db.add(emb, metadata)
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
                        embeddings = generate_embedding_with_crops(image_path)
                        metadata = {
                            'nome': artwork.name,
                            'filename': str(artwork_image.image),
                            'contesto': artwork.context,
                            'autore': artwork.author,
                            'epoca': artwork.period,
                            'localita': artwork.location,
                            'stile': artwork.style,
                        }
                        for emb in embeddings:
                            vector_db.add(emb, metadata)
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