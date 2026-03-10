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
    api_key = os.getenv('RUNPOD_API_KEY')
    endpoint_id = os.getenv('RUNPOD_ENDPOINT_ID')
    
    messages = []
    
    if image_base64:
        messages.append({
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                {"type": "text", "text": prompt}
            ]
        })
    else:
        messages.append({
            "role": "user",
            "content": prompt
        })
    
    payload = {
        "input": {
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.7
        }
    }
    
    response = requests.post(
        f"https://api.runpod.ai/v2/{endpoint_id}/runsync",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=120
    )
    
    # DEBUG — guarda questi print nel terminale Django
    print("STATUS CODE:", response.status_code)
    print("RAW RESPONSE:", response.text)
    
    result = response.json()
    print("PARSED JSON:", result)
    return result['output'][0]['choices'][0]['tokens'][0]

@api_view(['POST'])
@permission_classes([AllowAny])
def chat(request):
    input_text = request.data.get('text', None)
    input_image = request.FILES.get('image', None)

    if not input_text and not input_image:
        return Response(
            {'error': 'Provide text or image'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # casistica : immagine
    if input_image:
        embedding = generate_embedding(input_image)
        results = vector_db.search(embedding, top_k=1)
        artwork_name = results[0]['metadata']['nome']
        similarity_score = results[0]['similarity']

    # casistica : testo
    if input_text:
        artwork_name = detector.detect_opera(input_text)
        similarity_score = 1.0
        if not artwork_name:
            return Response({'response': 'Opera non riconosciuta nel testo.'})

    # recupera contesto dal db
    try:
        artwork = Artwork.objects.get(name=artwork_name)
        context = artwork.context
    except Artwork.DoesNotExist:
        context = ""

    # costruisci prompt con contesto opera - TODO : correggi per risposta troncata
    prompt = f"""Sei una guida esperta di beni culturali. Rispondi in massimo 3 frasi.
    Opera riconosciuta: {artwork_name}
    Contesto: {context}

    Domanda dell'utente: {input_text or 'Descrivi questa opera'}

    Rispondi in italiano in modo chiaro e coinvolgente."""

    # converti immagine in base64 se presente
    image_base64 = None
    if input_image:
        import base64
        input_image.seek(0)
        image_base64 = base64.b64encode(input_image.read()).decode('utf-8')

    try:
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
        'response': model_response
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def artwork_list(request):
    if request.method == 'GET':
        artworks = Artwork.objects.all()
        serializer = ArtworkSerializer(artworks, many=True)
        return Response(serializer.data)

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