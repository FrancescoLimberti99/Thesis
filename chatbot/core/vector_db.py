"""
Vector Database semplice per similarity search.
Memorizza embedding + metadata e trova opere più simili.
"""

import numpy as np
import pickle
from typing import List, Dict, Any, Optional


class VectorDB:
    """
    Database vettoriale per similarity search su embedding immagini
    """
    
    def __init__(self):
        """Inizializza database vuoto"""
        self.embeddings = []  # Lista di numpy arrays (512,)
        self.metadata = []    # Lista di dict con info opere
        print("NUOVO VectorDB inizializzato (vuoto)")
    
    def add(self, embedding: np.ndarray, metadata: Dict[str, Any]):
        """
        Aggiungi un embedding al database
        
        Args:
            embedding: Array numpy shape (768,) con embedding normalizzato
            metadata: Dict con info opera:
                - nome (str): Nome opera (es. "Colosseo")
                - filename (str): Nome file immagine
                - contesto (str): Testo descrittivo per chatbot
                - epoca (str, optional): Periodo storico
                - autore (str, optional): Chi l'ha realizzata
                - località (str, optional): Dove si trova
                - stile (str, optional): Stile artistico
        
        Raises:
            ValueError: Se embedding non ha shape corretta
        """
        # converti a numpy se necessario
        if not isinstance(embedding, np.ndarray):
            embedding = np.array(embedding)
        
        # verifica shape
        if len(embedding.shape) != 1:
            raise ValueError(f"Embedding deve essere 1D, ricevuto shape {embedding.shape}")
        
        # normalizza (per sicurezza, anche se dovrebbe essere già normalizzato)
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        # aggiungi
        self.embeddings.append(embedding)
        self.metadata.append(metadata)
    
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict]:
        """
        Cerca le opere più simili a query_embedding
        
        Args:
            query_embedding: Embedding immagine da cercare (768,)
            top_k: Numero di risultati da restituire (default 5)
        
        Returns:
            Lista di dict ordinati per similarity (più simile primo):
            [
                {
                    'similarity': float (0-1, 1=identico),
                    'metadata': dict con info opera,
                    'index': int (posizione in database)
                },
                ...
            ]
        
        Raises:
            ValueError: Se database vuoto
        """
        if len(self.embeddings) == 0:
            raise ValueError("Database vuoto! Carica o aggiungi opere prima.")
        
        # normalizza query
        query_embedding = np.array(query_embedding)
        query_norm = np.linalg.norm(query_embedding)
        if query_norm > 0:
            query_embedding = query_embedding / query_norm
        
        # calcola cosine similarity con tutti gli embedding
        # (dot product di vettori normalizzati = cosine similarity)
        similarities = []
        for emb in self.embeddings:
            sim = float(np.dot(query_embedding, emb))
            similarities.append(sim)
        
        # Trova top_k più simili
        # argsort restituisce indici ordinati (ascendente)
        # [::-1] inverte per avere discendente (più simile primo)
        # [:top_k] prende solo i primi K
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Costruisci risultati
        results = []
        for idx in top_indices:
            results.append({
                'similarity': similarities[idx],
                'metadata': self.metadata[idx],
                'index': int(idx)
            })
        
        return results
    
    def search_best_opera(self, 
                         query_embedding: np.ndarray, 
                         threshold: float = 0.75,
                         top_k: int = 10) -> Optional[Dict]:
        """
        Cerca la migliore opera gestendo multiple foto per opera.
        
        Se un'opera ha 3 foto diverse nel database, considera tutte e 3
        e restituisce quella con similarity massima.
        
        Args:
            query_embedding: Embedding immagine da cercare
            threshold: Soglia minima similarity (default 0.75 = 75%)
            top_k: Quanti risultati considerare (default 10)
        
        Returns:
            Dict con info opera migliore:
            {
                'nome': str,
                'similarity': float (max tra tutte le foto),
                'avg_similarity': float (media tra foto opera),
                'num_matches': int (quante foto opera matchano),
                'metadata': dict (metadata della foto più simile)
            }
            
            Oppure None se nessuna opera sopra threshold
        """
        # cerca top_k risultati
        results = self.search(query_embedding, top_k=top_k)
        
        # verifica soglia minima
        if not results or results[0]['similarity'] < threshold:
            return None
        
        # raggruppa per nome opera
        opere_scores = {}
        
        for result in results:
            nome = result['metadata']['nome']
            similarity = result['similarity']
            
            if nome not in opere_scores:
                opere_scores[nome] = {
                    'scores': [],
                    'metadatas': []
                }
            
            opere_scores[nome]['scores'].append(similarity)
            opere_scores[nome]['metadatas'].append(result['metadata'])
        
        # trova opera con similarity massima più alta
        best_opera = None
        best_max_score = 0
        
        for nome, data in opere_scores.items():
            scores = data['scores']
            max_score = max(scores)
            avg_score = np.mean(scores)
            
            if max_score > best_max_score:
                best_max_score = max_score
                
                # trova metadata della foto più simile
                best_idx = scores.index(max_score)
                best_metadata = data['metadatas'][best_idx]
                
                best_opera = {
                    'nome': nome,
                    'similarity': max_score,
                    'avg_similarity': avg_score,
                    'num_matches': len(scores),
                    'metadata': best_metadata
                }
        
        return best_opera
    
    def save(self, filepath: str):
        """
        Salva database su disco
        
        Args:
            filepath: Path file output (es: 'storage/vector_db.pkl')
        """
        data = {
            'embeddings': self.embeddings,
            'metadata': self.metadata,
            'version': '1.0'  # compatibilità futura
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        
        print(f"Vector DB salvato: {filepath}")
        print(f"   - {len(self.embeddings)} embeddings")
        print(f"   - {len(set(m['nome'] for m in self.metadata))} opere uniche")
    
    def load(self, filepath: str):
        """
        Carica database da disco
        
        Args:
            filepath: Path file input
        
        Raises:
            FileNotFoundError: Se file non esiste
        """
        # carica il vector db all'avvio
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
    
        self.embeddings = data['embeddings']
        self.metadata = data['metadata']
    
        print(f"Vector DB caricato: {filepath}")
        print(f"   - {len(self.embeddings)} embeddings")
        print(f"   - {len(set(m['nome'] for m in self.metadata))} opere uniche")
    
    def get_stats(self) -> Dict:
        """
        Statistiche del database
        
        Returns:
            Dict con:
            - total_embeddings: numero totale embedding
            - opere_uniche: numero opere diverse
            - opere_list: lista nomi opere
            - foto_per_opera: dict {nome: count}
        """
        opere_uniche = set(m['nome'] for m in self.metadata)
        
        foto_per_opera = {}
        for meta in self.metadata:
            nome = meta['nome']
            foto_per_opera[nome] = foto_per_opera.get(nome, 0) + 1
        
        return {
            'total_embeddings': len(self.embeddings),
            'opere_uniche': len(opere_uniche),
            'opere_list': sorted(list(opere_uniche)),
            'foto_per_opera': foto_per_opera
        }
    
    def find_by_name(self, opera_name: str) -> List[Dict]:
        """
        Trova tutti i metadata di un'opera per nome
        
        Args:
            opera_name: Nome opera da cercare
        
        Returns:
            Lista di metadata che matchano
        """
        matches = []
        for meta in self.metadata:
            if meta['nome'].lower() == opera_name.lower():
                matches.append(meta)
        return matches
    
    def get_all_opera_names(self) -> List[str]:
        """
        Restituisce lista di tutti i nomi opere nel database
        
        Returns:
            Lista nomi opere (ordinata, senza duplicati)
        """
        return sorted(list(set(m['nome'] for m in self.metadata)))
    
    def remove_by_name(self, opera_name: str) -> int:
        """
        Rimuove tutti gli embedding di un'opera dal database
    
        Args:
            opera_name: Nome opera da rimuovere
    
        Returns:
            int: Numero di embedding rimossi
        """
        indices_to_keep = [
            i for i, meta in enumerate(self.metadata)
            if meta['nome'].lower() != opera_name.lower()
        ]
    
        removed = len(self.embeddings) - len(indices_to_keep)
    
        self.embeddings = [self.embeddings[i] for i in indices_to_keep]
        self.metadata = [self.metadata[i] for i in indices_to_keep]
    
        return removed