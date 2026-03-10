"""
Rileva nome opera nelle domande testuali degli utenti.

Quando l'utente scrive "Dimmi della Gioconda", questo modulo:
1. Rileva "Gioconda" nel testo
2. Recupera il contesto dal vector_db
3. Permette al chatbot di rispondere usando quel contesto

Gestisce anche:
- Alias/sinonimi definiti dal curatore (es. "Mona Lisa" → "Gioconda")
- Fuzzy matching per errori di battitura
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

    def reload(self):
        """
        Ricarica nomi opere e alias dal database.
        Da chiamare dopo aggiunta/rimozione opere.
        """
        self.opere_names = self.vector_db.get_all_opera_names()
        self.aliases = self._load_aliases()

    def detect_opera(self, user_message: str) -> Optional[str]:
        """
        Rileva nome opera nel messaggio utente.

        Args:
            user_message: Testo scritto dall'utente

        Returns:
            Nome opera trovato o None
        """
        message_lower = user_message.lower()

        # CHECK 1: Match esatto con nomi opere nel database
        for opera in self.opere_names:
            if opera.lower() in message_lower:
                return opera

        # CHECK 2: Match con alias dal database
        for opera_name, alias_list in self.aliases.items():
            for alias in alias_list:
                if alias in message_lower:
                    for opera in self.opere_names:
                        if opera.lower() == opera_name:
                            return opera

        # CHECK 3: Fuzzy matching per errori di battitura
        fuzzy_match = self._fuzzy_match(message_lower)
        if fuzzy_match:
            return fuzzy_match

        return None

    def _fuzzy_match(self, message_lower: str, cutoff: float = 0.75) -> Optional[str]:
        """
        Cerca match approssimativo per gestire errori di battitura.
        """
        words = re.findall(r'\b\w{4,}\b', message_lower)

        for word in words:
            matches = get_close_matches(
                word,
                [o.lower() for o in self.opere_names],
                n=1,
                cutoff=cutoff
            )
            if matches:
                for opera in self.opere_names:
                    if opera.lower() == matches[0]:
                        return opera

            # cerca anche negli alias
            all_aliases = []
            for alias_list in self.aliases.values():
                all_aliases.extend(alias_list)

            matches = get_close_matches(word, all_aliases, n=1, cutoff=cutoff)
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

    def get_contesto(self, opera_name: str) -> Optional[Dict]:
        """
        Recupera contesto e metadata di un'opera dal vector_db.
        """
        entries = self.vector_db.find_by_name(opera_name)
        if entries:
            return entries[0]
        return None