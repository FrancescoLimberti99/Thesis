"""
Genera embedding delle immagini usando CLIP (modello open-source di OpenAI).
Trasforma immagini in vettori numerici (512 dimensioni) per similarity search.
"""

from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch
import numpy as np


class ImageEmbedding:
    """
    Classe per generare embedding dalle immagini usando CLIP
    """
    
    def __init__(self, model_name="openai/clip-vit-base-patch32"):
        """
        Inizializza il modello CLIP
        
        Args:
            model_name: Nome modello HuggingFace
                - "openai/clip-vit-base-patch32" (default): 512D, veloce, buona qualità
                - "openai/clip-vit-large-patch14": 768D, più lento, qualità migliore
        """
        print(f"Sto caricando il modello CLIP: {model_name}...")
        
        # carica modello e processore
        # primo avvio: scarica ~600MB, poi usa cache locale
        self.model = CLIPModel.from_pretrained(model_name)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        
        # imposta in modalità valutazione (no training)
        self.model.eval()
        
        print(f"MODELLO CLIP CARICATO!!")
    
    def generate_embedding(self, image_path):
        try:
            # carica immagine
            image = Image.open(image_path).convert('RGB')
        
            # preprocessa immagine per CLIP
            inputs = self.processor(
                images=image, 
                return_tensors="pt"
            )
        
            # genera embedding (no gradient per velocità)
            with torch.no_grad():
                outputs = self.model.vision_model(**inputs)
                image_features = outputs.pooler_output
        
            # normalizza
            image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
        
            # converti da tensor PyTorch a numpy array
            embedding = image_features.numpy().flatten()
        
            return embedding
        
        except FileNotFoundError:
            raise FileNotFoundError(f"Immagine non trovata: {image_path}")
        except Exception as e:
            raise Exception(f"Errore generazione embedding per {image_path}: {e}")
    
    def generate_batch_embeddings(self, image_paths):
        """
        Genera embedding per multiple immagini in batch (più veloce)
        
        Args:
            image_paths: Lista di path immagini
            
        Returns:
            list: Lista di embedding (numpy arrays)
        """
        embeddings = []
        
        for path in image_paths:
            try:
                emb = self.generate_embedding(path)
                embeddings.append(emb)
            except Exception as e:
                print(f"ERRORE {path}: {e}")
                embeddings.append(None)
        
        return embeddings


# FUNZIONE HELPER GLOBALE
# Per compatibilità con altri moduli

_embedding_model = None

def generate_embedding(image_path):
    """
    Funzione helper globale per generare embedding
    Inizializza modello automaticamente al primo uso (lazy loading)
    
    Args:
        image_path: Path dell'immagine
        
    Returns:
        numpy.ndarray: Embedding (512,)
    """
    global _embedding_model
    
    # lazy loading: carica modello solo quando serve
    if _embedding_model is None:
        _embedding_model = ImageEmbedding()
    
    return _embedding_model.generate_embedding(image_path)


if __name__ == "__main__":
    """
    Test del modulo (esegui con: python embeddings.py)
    """
    import time
    
    print("=" * 60)
    print("TEST EMBEDDINGS.PY")
    print("=" * 60)
    
    # Test 1: Inizializzazione
    print("\nTest 1: Inizializzazione modello")
    start = time.time()
    embedder = ImageEmbedding()
    print(f"   Tempo caricamento: {time.time()-start:.2f}s")
    
    # Test 2: Genera embedding singolo
    print("\nTest 2: Generazione embedding")
    
    # Usa un'immagine di esempio
    test_image = "../dataset/test1.jpg"
    
    try:
        start = time.time()
        embedding = embedder.generate_embedding(test_image)
        elapsed = time.time() - start
        
        print(f"   EMBEDDING GENERATO in {elapsed:.2f}s")
        print(f"   Shape: {embedding.shape}")
        print(f"   Tipo: {type(embedding)}")
        print(f"   Primi 5 valori: {embedding[:5]}")
        print(f"   Range valori: [{embedding.min():.3f}, {embedding.max():.3f}]")
        print(f"   Norma (dovrebbe essere ~1.0): {np.linalg.norm(embedding):.3f}")
        
    except FileNotFoundError:
        print(f"   FILE NON TROVATO: {test_image}")
        print(f"   Crea prima il dataset con foto per testare!")
    except Exception as e:
        print(f"   ERRORE: {e}")
    
    # Test 3: Funzione helper globale
    print("\nTest 3: Funzione helper globale")
    try:
        _embedding_model = embedder  # riusa istanza già caricata nel Test 1
        embedding2 = generate_embedding(test_image)
        print(f"   *** generate_embedding() FUNZIONA")
        print(f"   Shape: {embedding2.shape}")
    except Exception as e:
        print(f"   ERRORE: {e}")
    
    # Test 4: Similarity tra due immagini
    print("\nTest 4: Similarity tra immagini")
    
    test_image2 = "../dataset/test1.jpg"
    test_image3 = "../dataset/test1.jpg"
    
    try:
        emb1 = embedder.generate_embedding(test_image)
        emb2 = embedder.generate_embedding(test_image2)
        emb3 = embedder.generate_embedding(test_image3)
        
        # Cosine similarity (dot product di vettori normalizzati)
        sim_stesso_monumento = np.dot(emb1, emb2)
        sim_monumenti_diversi = np.dot(emb1, emb3)
        
        print(f"   Similarity Colosseo foto1 <-> foto2: {sim_stesso_monumento:.3f}")
        print(f"   Similarity Colosseo <-> Torre Pisa: {sim_monumenti_diversi:.3f}")
        
        if sim_stesso_monumento > sim_monumenti_diversi:
            print(f"   *** STESSO MONUMENTO è il più simile! (COME PREVISTO)")
        else:
            print(f"   *** ATTENZIONE: monumenti diversi sembrano più simili")
            
    except FileNotFoundError:
        print(f"   *** Servono almeno 3 foto nel dataset per test similarity")
    except Exception as e:
        print(f"   ERRORE: {e}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETATI")
    print("=" * 60)