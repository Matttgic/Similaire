import requests
import time
import json
from datetime import datetime, timedelta
from config.config import Config
from src.database_manager import DatabaseManager

class PinnacleDataCollector:
    def __init__(self):
        self.api_key = Config.RAPIDAPI_KEY
        self.base_url = Config.BASE_URL
        self.headers = {
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': Config.RAPIDAPI_HOST,
            'Content-Type': 'application/json'
        }
        self.db_manager = DatabaseManager()
        self.rate_limit_delay = Config.RATE_LIMIT_DELAY
    
    def get_sports(self):
        """Récupère la liste des sports disponibles"""
        try:
            response = requests.get(
                f"{self.base_url}/kit/v1/sports", 
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur lors de la récupération des sports: {e}")
            return None
    
    def get_markets(self, sport_id=None, since=None, event_type=None, is_have_odds=True):
        """Récupère la liste des marchés (matchs avec cotes)"""
        sport_id = sport_id or Config.FOOTBALL_SPORT_ID
        
        params = {
            'sport_id': sport_id,
            'is_have_odds': is_have_odds
        }
        
        if since:
            params['since'] = since
        if event_type:
            params['event_type'] = event_type
            
        try:
            response = requests.get(
                f"{self.base_url}/kit/v1/markets",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur lors de la récupération des marchés: {e}")
            return None
    
    def get_archive_events(self, sport_id=None, days_back=None):
        """Récupère les événements archivés"""
        sport_id = sport_id or Config.FOOTBALL_SPORT_ID
        days_back = days_back or (Config.HISTORICAL_YEARS * 365)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        params = {
            'sport_id': sport_id,
            'from': start_date.strftime('%Y-%m-%dT%H:%M:%S'),
            'to': end_date.strftime('%Y-%m-%dT%H:%M:%S')
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/kit/v1/archive",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur lors de la récupération de l'archive: {e}")
            return None
    
    def get_event_details(self, event_id):
        """Récupère les détails complets d'un événement"""
        try:
            response = requests.get(
                f"{self.base_url}/kit/v1/details/{event_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur pour l'événement {event_id}: {e}")
            return None
    
    def get_special_markets(self, sport_id=None):
        """Récupère les marchés spéciaux (BTTS, etc.)"""
        sport_id = sport_id or Config.FOOTBALL_SPORT_ID
        
        try:
            response = requests.get(
                f"{self.base_url}/kit/v1/specials",
                headers=self.headers,
                params={'sport_id': sport_id}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur lors de la récupération des marchés spéciaux: {e}")
            return None
    
    def extract_odds_from_event(self, event_data):
        """Extrait les cotes principales d'un événement"""
        match_data = {
            'event_id': event_data.get('event_id'),
            'sport_id': event_data.get('sport_id'),
            'league_id': event_data.get('league_id'),
            'league_name': event_data.get('league_name'),
            'home_team': event_data.get('home'),
            'away_team': event_data.get('away'),
            'start_time': event_data.get('starts'),
            'event_type': event_data.get('event_type')
        }
        
        # Récupérer les cotes de la période principale (num_0)
        periods = event_data.get('periods', {})
        main_period = periods.get('num_0', {})
        
        if not main_period:
            return match_data
        
        # Money Line (1X2)
        money_line = main_period.get('money_line', {})
        match_data.update({
            'home_odds': money_line.get('home'),
            'draw_odds': money_line.get('draw'),
            'away_odds': money_line.get('away')
        })
        
        # Totaux (chercher O/U 2.5)
        totals = main_period.get('totals', {})
        for points, total_data in totals.items():
            if float(points) == 2.5:
                match_data.update({
                    'over_25_odds': total_data.get('over'),
                    'under_25_odds': total_data.get('under')
                })
                break
        
        return match_data
    
    def collect_current_markets(self):
        """Collecte les marchés actuels (pour mise à jour)"""
        print("🔄 Collecte des marchés actuels...")
        
        markets_data = self.get_markets()
        if not markets_data:
            return
        
        events = markets_data.get('events', [])
        print(f"📊 {len(events)} événements trouvés")
        
        collected = 0
        for event in events:
            try:
                # Extraire les cotes
                match_data = self.extract_odds_from_event(event)
                
                # Sauvegarder
                self.db_manager.save_match(match_data)
                collected += 1
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
                
            except Exception as e:
                print(f"❌ Erreur pour l'événement {event.get('event_id', 'unknown')}: {e}")
                continue
        
        print(f"✅ {collected} matchs collectés")
    
    def collect_historical_data(self, max_events=None):
        """Collecte principale des données historiques"""
        print("🚀 Début de la collecte des données historiques...")
        
        # Option 1: Essayer l'archive
        archive_data = self.get_archive_events()
        if archive_data:
            events = archive_data.get('events', [])
        else:
            # Option 2: Utiliser les marchés actuels
            print("📡 Archive non disponible, utilisation des marchés actuels...")
            markets_data = self.get_markets()
            events = markets_data.get('events', []) if markets_data else []
        
        if not events:
            print("❌ Aucun événement trouvé")
            return
        
        if max_events:
            events = events[:max_events]
        
        print(f"📊 {len(events)} événements à traiter")
        
        collected_count = 0
        errors_count = 0
        
        for i, event in enumerate(events):
            try:
                # Afficher le progrès
                if i % 50 == 0:
                    print(f"📈 Progression: {i}/{len(events)} ({(i/len(events)*100):.1f}%)")
                
                # Si l'événement a déjà des cotes complètes, l'utiliser directement
                if self._has_complete_odds(event):
                    match_data = self.extract_odds_from_event(event)
                else:
                    # Sinon récupérer les détails complets
                    event_details = self.get_event_details(event['event_id'])
                    if not event_details:
                        continue
                    match_data = self.extract_odds_from_event(event_details)
                
                # Sauvegarder si on a des cotes complètes
                if self._has_complete_odds(match_data):
                    self.db_manager.save_match(match_data)
                    collected_count += 1
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
                
            except Exception as e:
                errors_count += 1
                print(f"❌ Erreur pour l'événement {event.get('event_id', 'unknown')}: {e}")
                continue
        
        print(f"🎉 Collecte terminée:")
        print(f"   ✅ {collected_count} matchs sauvegardés")
        print(f"   ❌ {errors_count} erreurs")
    
    def _has_complete_odds(self, event_data):
        """Vérifie si l'événement a des cotes complètes"""
        required_odds = ['home_odds', 'draw_odds', 'away_odds', 'over_25_odds', 'under_25_odds']
        
        if isinstance(event_data, dict):
            return all(event_data.get(field) is not None for field in required_odds)
        
        # Pour les événements bruts de l'API
        periods = event_data.get('periods', {})
        main_period = periods.get('num_0', {})
        
        if not main_period:
            return False
        
        # Vérifier money line
        money_line = main_period.get('money_line', {})
        if not all(money_line.get(field) for field in ['home', 'draw', 'away']):
            return False
        
        # Vérifier totaux 2.5
        totals = main_period.get('totals', {})
        has_25_total = any(
            float(points) == 2.5 and total_data.get('over') and total_data.get('under')
            for points, total_data in totals.items()
        )
        
        return has_25_total
    
    def update_results_from_api(self):
        """Met à jour les résultats des matchs terminés"""
        print("🔄 Mise à jour des résultats...")
        # Cette fonction nécessiterait une API de résultats
        # Pour l'instant, on peut la laisser vide ou utiliser une autre source
        pass
