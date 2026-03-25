"""
Costruisce il vector database dalle opere nel database Django.

ESEGUIRE dopo aver aggiunto le opere tramite il pannello curatore.

Un'opera aggiunta viene successivamente aggiunta anche nel vector database

Processo:
1. Legge le opere da Django (modello Artwork + ArtworkImage)
2. Per ogni immagine genera embedding con CLIP
3. Salva tutto in storage/vector_db.pkl

Usage:
    python manage.py shell < chatbot/core/build_dataset.py
    oppure
    .\venv\Scripts\python.exe chatbot/core/build_dataset.py
"""

import os
import sys
import time
import django
from pathlib import Path

# setup Django
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from chatbot.models import Artwork, ArtworkImage
from chatbot.core.embeddings import generate_embedding, generate_embedding_with_crops
from chatbot.core.vector_db import VectorDB


def build_dataset(output_path=None):
    if output_path is None:
        output_path = BASE_DIR / 'storage' / 'vector_db.pkl'

    print("=" * 70)
    print("COSTRUZIONE VECTOR DATABASE - CHATBOT BENI CULTURALI")
    print("=" * 70)

    # legge opere dal database Django
    print("\nSto leggendo le opere dal database Django...")
    artworks = Artwork.objects.prefetch_related('images').all()

    if not artworks.exists():
        print("Nessuna opera nel database. Aggiungile dal pannello curatore.")
        return None

    print(f"Opere trovate: {artworks.count()}")

    # crea Vector DB vuoto
    print("\nSto creando il Vector Database...")
    db = VectorDB()

    # processa ogni immagine
    print("\nSto processando le immagini...")
    print("=" * 70)

    success_count = 0
    error_count = 0
    start_time = time.time()

    for artwork in artworks:
        images = artwork.images.all()

        if not images.exists():
            print(f"Nessuna immagine per: {artwork.name} - SALTATA")
            continue

        print(f"\nProcessando: {artwork.name} ({images.count()} immagini)")

        for artwork_image in images:
            image_path = BASE_DIR / 'media' / str(artwork_image.image)

            if not image_path.exists():
                print(f"  File non trovato: {image_path} - SALTATO")
                error_count += 1
                continue

            try:
                # genera embedding immagine intera + crop per riconoscimento dettagli
                embeddings = generate_embedding_with_crops(str(image_path))

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
                    db.add(emb, metadata)
                success_count += 1
                print(f"  OK: {artwork_image.image} ({len(embeddings)} embeddings)")

            except Exception as e:
                print(f"  ERRORE: {artwork_image.image} - {e}")
                error_count += 1

    elapsed_time = time.time() - start_time

    # salva il database
    print(f"\nSto salvando il database...")
    Path(output_path).parent.mkdir(exist_ok=True, parents=True)

    try:
        db.save(str(output_path))
    except Exception as e:
        print(f"ERRORE salvataggio: {e}")
        return None

    # statistiche finali
    print("\n" + "=" * 70)
    print("COSTRUZIONE COMPLETATA!")
    print("=" * 70)

    stats = db.get_stats()
    print(f"\nSTATISTICHE:")
    print(f"  Immagini processate: {success_count}")
    print(f"  Errori: {error_count}")
    print(f"  Embeddings totali: {stats['total_embeddings']}")
    print(f"  Opere uniche: {stats['opere_uniche']}")
    print(f"  Tempo: {elapsed_time:.2f}s")

    print(f"\nDETTAGLIO OPERE:")
    for opera, count in sorted(stats['foto_per_opera'].items()):
        print(f"  {opera}: {count} foto")

    print(f"\nDATABASE SALVATO IN: {output_path}")
    print("=" * 70)

    return db


if __name__ == "__main__":
    db = build_dataset()
    if db is None:
        sys.exit(1)
    else:
        sys.exit(0)