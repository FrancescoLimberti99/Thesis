"""
Rileva nome opera nelle domande testuali degli utenti.

Quando l'utente scrive "Dimmi della Gioconda", questo modulo:
1. Rileva "Gioconda" nel testo
2. Recupera il contesto dal vector_db
3. Permette al chatbot di rispondere usando quel contesto

Gestisce anche:
- Alias/sinonimi definiti dal curatore (es. "Mona Lisa" → "Gioconda")
- Fuzzy matching per errori di battitura
- Rilevamento multiplo per paragoni tra opere
"""

import os
import sys
import re
from difflib import get_close_matches
from typing import Optional, List, Dict, Tuple


class OperaDetector:
    """
    Rileva nome opera nelle domande testuali degli utenti.
    Gli alias vengono letti dal database Django.
    """

    def __init__(self, vector_db):
        self.vector_db = vector_db
        self.opere_names = self.vector_db.get_all_opera_names()
        self.aliases = self._load_aliases()

        print(f"OperaDetector inizializzato")
        print(f"   - {len(self.opere_names)} opere nel database")
        print(f"   - {len(self.aliases)} opere con alias configurati")

    def _load_aliases(self) -> Dict[str, List[str]]:
        """
        Carica gli alias dal database Django.

        Returns:
            Dict {nome_opera_lower: [alias1, alias2, ...]}
        """
        aliases = {}

        try:
            import django
            from django.apps import apps
            Artwork = apps.get_model('chatbot', 'Artwork')

            for artwork in Artwork.objects.all():
                if artwork.aliases:
                    alias_list = [
                        a.strip().lower()
                        for a in artwork.aliases.split(',')
                        if a.strip()
                    ]
                    if alias_list:
                        aliases[artwork.name.lower()] = alias_list
        except Exception as e:
            print(f"   Impossibile caricare alias dal database: {e}")

        return aliases
    
    def _load_metadata(self) -> List[Dict]:
        """
        Carica i metadati di tutte le opere dal database Django.
        Usato per il rilevamento per metadati come fallback.

        Returns:
            Lista di dict con campi: nome, autore, epoca, stile, localita
        """
        metadata = []
        try:
            from django.apps import apps
            Artwork = apps.get_model('chatbot', 'Artwork')
            for artwork in Artwork.objects.all():
                metadata.append({
                    'nome': artwork.name,
                    'autore': (artwork.author or '').lower(),
                    'epoca': (artwork.period or '').lower(),
                    'stile': (artwork.style or '').lower(),
                    'localita': (artwork.location or '').lower(),
                })
        except Exception as e:
            print(f"   Impossibile caricare metadata dal database: {e}")
        return metadata

    def reload(self):
        """
        Ricarica nomi opere e alias dal database.
        Da chiamare dopo aggiunta/rimozione opere.
        """
        self.opere_names = self.vector_db.get_all_opera_names()
        self.aliases = self._load_aliases()

    def detect_opera(self, user_message: str) -> Optional[str]:
        """
        Rileva la prima opera nel messaggio utente (retrocompatibilità).
        Per rilevamento multiplo usa detect_multiple().

        Args:
            user_message: Testo scritto dall'utente

        Returns:
            Nome opera trovato o None
        """
        results = self.detect_multiple(user_message)
        return results[0] if results else None

    def detect_multiple(self, user_message: str) -> List[str]:
        """
        Rileva TUTTE le opere citate nel messaggio utente.
        Utile per paragoni (es. "confronta la Gioconda con l'Urlo").

        Args:
            user_message: Testo scritto dall'utente

        Returns:
            Lista ordinata di nomi opere trovate (senza duplicati)
        """
        message_lower = user_message.lower()
        found = []

        # CHECK 1: Match esatto con nomi opere nel database
        for opera in self.opere_names:
            if opera.lower() in message_lower and opera not in found:
                found.append(opera)

        # CHECK 2: Match con alias dal database
        for opera_name, alias_list in self.aliases.items():
            for alias in alias_list:
                if alias in message_lower:
                    for opera in self.opere_names:
                        if opera.lower() == opera_name and opera not in found:
                            found.append(opera)

        # CHECK 3: Fuzzy matching per errori di battitura
        for match in self._fuzzy_match_all(message_lower, exclude=found):
            if match not in found:
                found.append(match)

        return found

    def _fuzzy_match_all(self, message_lower: str, cutoff: float = 0.75, exclude: List[str] = []) -> List[str]:
        all_words_raw = re.findall(r'\b\w+\b', message_lower)

        # singole parole, coppie, triplette
        candidates = []
        candidates.extend([w for w in all_words_raw if len(w) >= 4])
        candidates.extend([f"{all_words_raw[i]} {all_words_raw[i+1]}"
                        for i in range(len(all_words_raw)-1)])
        candidates.extend([f"{all_words_raw[i]} {all_words_raw[i+1]} {all_words_raw[i+2]}"
                        for i in range(len(all_words_raw)-2)])

        found = []
        opere_remaining = [o for o in self.opere_names if o not in exclude]

        for candidate in candidates:
            # confronta con nomi opere
            matches = get_close_matches(candidate, [o.lower() for o in opere_remaining], n=1, cutoff=cutoff)
            if matches:
                for opera in opere_remaining:
                    if opera.lower() == matches[0] and opera not in found:
                        found.append(opera)

            # confronta con alias
            all_aliases = [a for al in self.aliases.values() for a in al]
            matches = get_close_matches(candidate, all_aliases, n=1, cutoff=cutoff)
            if matches:
                for opera_name, alias_list in self.aliases.items():
                    if matches[0] in alias_list:
                        for opera in opere_remaining:
                            if opera.lower() == opera_name and opera not in found:
                                found.append(opera)

        return found

    def _fuzzy_match(self, message_lower: str, cutoff: float = 0.75) -> Optional[str]:
        words = re.findall(r'\b\w{4,}\b', message_lower)
        all_words_raw = re.findall(r'\b\w+\b', message_lower)

        # singole parole, coppie, triplette
        candidates = []
        candidates.extend([w for w in words if len(w) >= 4])
        candidates.extend([f"{all_words_raw[i]} {all_words_raw[i+1]}"
                        for i in range(len(all_words_raw)-1)])
        candidates.extend([f"{all_words_raw[i]} {all_words_raw[i+1]} {all_words_raw[i+2]}"
                        for i in range(len(all_words_raw)-2)])

        for candidate in candidates:
            # confronta con nomi opere
            matches = get_close_matches(candidate,[o.lower() for o in self.opere_names],n=1,cutoff=cutoff)
            if matches:
                for opera in self.opere_names:
                    if opera.lower() == matches[0]:
                        return opera

            # confronta con alias
            all_aliases = []
            for alias_list in self.aliases.values():
                all_aliases.extend(alias_list)

            matches = get_close_matches(candidate, all_aliases, n=1, cutoff=cutoff)
            if matches:
                for opera_name, alias_list in self.aliases.items():
                    if matches[0] in alias_list:
                        for opera in self.opere_names:
                            if opera.lower() == opera_name:
                                return opera

        return None

    def detect_with_confidence(self, user_message: str) -> Tuple[Optional[str], str]:
        """
        Rileva opera con livello di confidenza.

        Returns:
            Tuple (nome_opera, confidenza)
            confidenza: 'high', 'medium', 'low', 'none'
        """
        message_lower = user_message.lower()

        for opera in self.opere_names:
            if opera.lower() in message_lower:
                return opera, 'high'

        for opera_name, alias_list in self.aliases.items():
            for alias in alias_list:
                if alias in message_lower:
                    for opera in self.opere_names:
                        if opera.lower() == opera_name:
                            return opera, 'medium'

        fuzzy = self._fuzzy_match(message_lower)
        if fuzzy:
            return fuzzy, 'low'

        return None, 'none'

    def get_context(self, opera_name: str) -> Optional[Dict]:
        """
        Recupera contesto e metadata di un'opera dal vector_db.
        """
        entries = self.vector_db.find_by_name(opera_name)
        if entries:
            return entries[0]
        return None
    
    def detect_by_metadata(self, user_message: str) -> Dict:
        """
        Fallback: cerca opere per metadati chiamato solo se non vengono trovati titoli/alias.

        Priorità dei campi: autore > epoca > stile > località
        Usa match esatto su sottostringhe + fuzzy matching.

        Args:
            user_message: Testo scritto dall'utente

        Returns:
            Dict con:
            - 'opere': lista di nomi opere trovate
            - 'campo': il campo che ha fatto match ('autore','epoca','stile','localita')
            - 'valore': il valore del campo trovato nel messaggio
            oppure dict vuoto {} se nessun match
        """
        message_lower = user_message.lower()
        artworks_meta = self._load_metadata()

        # ordine di priorità dei campi
        campi_priorita = ['autore', 'epoca', 'stile', 'localita']

        # --- STEP 1: match esatto su sottostringhe e per token ---
        for campo in campi_priorita:
            valori_unici = list({
                m[campo] for m in artworks_meta if m[campo]
            })
            for valore in valori_unici:
                if not valore:
                    continue
                # match 1a: la stringa intera è contenuta nel messaggio
                match_intero = valore in message_lower

                # match 1b: ogni token del valore è contenuto nel messaggio
                token_valore = [t for t in valore.split() if len(t) >= 4]
                match_token = token_valore and all(t in message_lower for t in token_valore)

                if match_intero or match_token:
                    opere_trovate = [
                        m['nome'] for m in artworks_meta
                        if m[campo] == valore
                    ]
                    if opere_trovate:
                        return {
                            'opere': opere_trovate,
                            'campo': campo,
                            'valore': valore,
                        }

        # --- STEP 2: fuzzy matching su parole, bigram, trigram ---
        all_words_raw = re.findall(r'\b\w+\b', message_lower)
        candidates = [w for w in all_words_raw if len(w) >= 4]
        candidates += [
            f"{all_words_raw[i]} {all_words_raw[i+1]}"
            for i in range(len(all_words_raw) - 1)
        ]
        candidates += [
            f"{all_words_raw[i]} {all_words_raw[i+1]} {all_words_raw[i+2]}"
            for i in range(len(all_words_raw) - 2)
        ]

        for campo in campi_priorita:
            valori_unici = list({
                m[campo] for m in artworks_meta if m[campo]
            })
            if not valori_unici:
                continue
            for candidate in candidates:
                matches = get_close_matches(candidate, valori_unici, n=1, cutoff=0.80)
                if matches:
                    valore_matched = matches[0]
                    opere_trovate = [
                        m['nome'] for m in artworks_meta
                        if m[campo] == valore_matched
                    ]
                    if opere_trovate:
                        return {
                            'opere': opere_trovate,
                            'campo': campo,
                            'valore': valore_matched,
                        }

        return {}