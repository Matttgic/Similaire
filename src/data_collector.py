import requests
import time
import json
import asyncio
import aiohttp
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from config.config import Config
from src.database_manager import DatabaseManager
from src.logger import get_logger, pinnacle_logger
from src.error_handler import ValidationManager, ErrorHandler, APIError

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
        self.logger = get_logger('collector')
        self.validator = ValidationManager()
        
        # Statistiques de collecte
        self.stats = {
            'requests_made': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'matches_processed': 0,
            'matches_saved': 0,
            'start_time': None
        }
    
    @ErrorHandler.handle_api_error
    def get_sports(self) -> Optional[Dict[str, Any]]:
        """Récupère la liste des sports disponibles"""
        start_time = time.time()
        
        try:
            self.stats['requests_made'] += 1
            response = requests.get(
                f"{self.base_url}/kit/v1/sports", 
                headers=self.headers,
                timeout=30
            )
            
            execution_time = time.time() - start_time
            
            # Valider la réponse
            data = self.validator.validate_api_response(response, ['sports'])
            
            self.stats['successful_requests'] += 1
            pinnacle_logger.log_api_call(
                'get_sports', 
                response_status=response.status_code,
                execution_time=execution_time
            )
            
            self.logger.info(f"Retrieved {len(data.get('sports', []))} sports")
            return data
            
        except Exception as e:
            self.stats['failed_requests'] += 1
            self.logger.error(f"Failed to get sports: {e}")
            return None
    
    @ErrorHandler.handle_api_error
    def get_markets(self, sport_id: Optional[int] = None, since: Optional[str] = None, 
                   event_type: Optional[str] = None, is_have_odds: bool = True) -> Optional[Dict[str, Any]]:
        """Récupère la liste des marchés (matchs avec cotes)"""
        sport_id = sport_id or Config.FOOTBALL_SPORT_ID
        start_time = time.time()
        
        params = {
            'sport_id': sport_id,
            'is_have_odds': is_have_odds
        }
        
        if since:
            params['since'] = since
        if event_type:
            params['event_type'] = event_type
            
        try:
            self.stats['requests_made'] += 1
            response = requests.get(
                f"{self.base_url}/kit/v1/markets",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            execution_time = time.time() - start_time
            
            # Valider la réponse
            data = self.validator.validate_api_response(response, ['events'])
            
            self.stats['successful_requests'] += 1
            pinnacle_logger.log_api_call(
                'get_markets',
                params=params,
                response_status=response.status_code,
                execution_time=execution_time
            )
            
            events_count = len(data.get('events', []))
            self.logger.info(f"Retrieved {events_count} market events")
            return data
            
        except Exception as e:
            self.stats['failed_requests'] += 1
            self.logger.error(f"Failed to get markets: {e}")
            return None
    
    @ErrorHandler.handle_api_error
    def get_archive_events(self, sport_id: Optional[int] = None, 
                          days_back: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Récupère les événements archivés"""
        sport_id = sport_id or Config.FOOTBALL_SPORT_ID
        days_back = days_back or (Config.HISTORICAL_YEARS * 365)
        start_time = time.time()
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        params = {
            'sport_id': sport_id,
            'from': start_date.strftime('%Y-%m-%dT%H:%M:%S'),
            'to': end_date.strftime('%Y-%m-%dT%H:%M:%S')
        }
        
        try:
            self.stats['requests_made'] += 1
            response = requests.get(
                f"{self.base_url}/kit/v1/archive",
                headers=self.headers,
                params=params,
                timeout=60  # Plus de temps pour l'archive
            )
            
            execution_time = time.time() - start_time
            
            # Valider la réponse
            data = self.validator.validate_api_response(response, ['events'])
            
            self.stats['successful_requests'] += 1
            pinnacle_logger.log_api_call(
                'get_archive_events',
                params=params,
                response_status=response.status_code,
                execution_time=execution_time
            )
            
            events_count = len(data.get('events', []))
            self.logger.info(f"Retrieved {events_count} archived events")
            return data
            
        except Exception as e:
            self.stats['failed_requests'] += 1
            self.logger.error(f"Failed to get archive events: {e}")
            return None
    
    @ErrorHandler.handle_api_error
    def get_event_details(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Récupère les détails complets d'un événement"""
        start_time = time.time()
        
        try:
            self.stats['requests_made'] += 1
            response = requests.get(
                f"{self.base_url}/kit/v1/details/{event_id}",
                headers=self.headers,
                timeout=30
            )
            
            execution_time = time.time() - start_time
            
            # Valider la réponse
            data = self.validator.validate_api_response(response)
            
            self.stats['successful_requests'] += 1
            pinnacle_logger.log_api_call(
                f'get_event_details/{event_id}',
                response_status=response.status_code,
                execution_time=execution_time
            )
            
            return data
            
        except Exception as e:
            self.stats['failed_requests'] += 1
            self.logger.error(f"Failed to get event details for {event_id}: {e}")
            return None
    
    def extract_odds_from_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extrait les cotes principales d'un événement avec validation"""
        try:
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
                self.logger.debug(f"No main period found for event {event_data.get('event_id')}")
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
                try:
                    if float(points) == 2.5:
                        match_data.update({
                            'over_25_odds': total_data.get('over'),
                            'under_25_odds': total_data.get('under')
                        })
                        break
                except (ValueError, TypeError):
                    continue
            
            # Valider les données extraites
            validated_data = self.validator.validate_match_data(match_data)
            return validated_data
            
        except Exception as e:
            self.logger.error(f"Error extracting odds from event {event_data.get('event_id', 'unknown')}: {e}")
            return {}
    
    def collect_current_markets(self) -> Dict[str, int]:
        """Collecte les marchés actuels (pour mise à jour)"""
        self.logger.info("Starting current markets collection...")
        self.stats['start_time'] = time.time()
        
        markets_data = self.get_markets()
        if not markets_data:
            self.logger.error("No markets data received")
            return {'collected': 0, 'errors': 0}
        
        events = markets_data.get('events', [])
        self.logger.info(f"Processing {len(events)} current events")
        
        collected = 0
        errors = 0
        
        for event in events:
            try:
                self.stats['matches_processed'] += 1
                
                # Extraire les cotes
                match_data = self.extract_odds_from_event(event)
                
                if match_data and self._has_complete_odds(match_data):
                    # Sauvegarder
                    self.db_manager.save_match(match_data)
                    collected += 1
                    self.stats['matches_saved'] += 1
                    
                    # Log détaillé pour les premiers matchs
                    if collected <= 5:
                        self.logger.debug(f"Saved match: {match_data.get('home_team')} vs {match_data.get('away_team')}")
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
                
            except Exception as e:
                errors += 1
                self.stats['failed_requests'] += 1
                self.logger.error(f"Error processing event {event.get('event_id', 'unknown')}: {e}")
                continue
        
        # Log final avec statistiques
        duration = time.time() - self.stats['start_time']
        pinnacle_logger.log_data_collection(
            'current_markets', 
            len(events), 
            collected, 
            errors, 
            duration
        )
        
        self.logger.info(f"Current markets collection completed: {collected} saved, {errors} errors")
        return {'collected': collected, 'errors': errors}
    
    def collect_historical_data(self, max_events: Optional[int] = None) -> Dict[str, int]:
        """Collecte principale des données historiques avec traitement parallèle"""
        self.logger.info("Starting historical data collection...")
        self.stats['start_time'] = time.time()
        
        # Option 1: Essayer l'archive
        archive_data = self.get_archive_events()
        if archive_data:
            events = archive_data.get('events', [])
            source = "archive"
        else:
            # Option 2: Utiliser les marchés actuels
            self.logger.info("Archive unavailable, using current markets...")
            markets_data = self.get_markets()
            events = markets_data.get('events', []) if markets_data else []
            source = "current_markets"
        
        if not events:
            self.logger.error("No events found for historical collection")
            return {'collected': 0, 'errors': 0}
        
        if max_events:
            events = events[:max_events]
        
        self.logger.info(f"Processing {len(events)} historical events from {source}")
        
        # Traitement avec pool de threads pour améliorer les performances
        collected_count = 0
        errors_count = 0
        
        with ThreadPoolExecutor(max_workers=Config.MAX_CONCURRENT_REQUESTS) as executor:
            # Soumettre les tâches par batches
            batch_size = Config.BATCH_SIZE
            for i in range(0, len(events), batch_size):
                batch = events[i:i + batch_size]
                
                # Soumettre le batch
                futures = []
                for event in batch:
                    future = executor.submit(self._process_historical_event, event)
                    futures.append(future)
                
                # Traiter les résultats du batch
                for future in as_completed(futures):
                    try:
                        result = future.result(timeout=60)  # 60s timeout par event
                        if result:
                            collected_count += 1
                            self.stats['matches_saved'] += 1
                        else:
                            errors_count += 1
                    except Exception as e:
                        errors_count += 1
                        self.logger.error(f"Thread execution error: {e}")
                
                # Afficher le progrès
                progress = (i + len(batch)) / len(events) * 100
                self.logger.info(f"Progress: {progress:.1f}% ({collected_count} saved, {errors_count} errors)")
                
                # Rate limiting entre les batches
                time.sleep(self.rate_limit_delay * len(batch))
        
        # Log final avec statistiques détaillées  
        duration = time.time() - self.stats['start_time']
        pinnacle_logger.log_data_collection(
            f'historical_{source}',
            len(events),
            collected_count,
            errors_count,
            duration
        )
        
        # Métriques de performance
        pinnacle_logger.log_performance_metrics('historical_collection', {
            'events_per_second': len(events) / duration if duration > 0 else 0,
            'success_rate': collected_count / len(events) * 100 if events else 0,
            'avg_processing_time': duration / len(events) if events else 0
        })
        
        self.logger.info(f"Historical collection completed: {collected_count} saved, {errors_count} errors")
        return {'collected': collected_count, 'errors': errors_count}
    
    def _process_historical_event(self, event: Dict[str, Any]) -> bool:
        """Traite un événement historique (pour le traitement parallèle)"""
        try:
            self.stats['matches_processed'] += 1
            
            # Si l'événement a déjà des cotes complètes, l'utiliser directement
            if self._has_complete_odds(event):
                match_data = self.extract_odds_from_event(event)
            else:
                # Sinon récupérer les détails complets
                event_details = self.get_event_details(event['event_id'])
                if not event_details:
                    return False
                match_data = self.extract_odds_from_event(event_details)
            
            # Sauvegarder si on a des cotes complètes
            if match_data and self._has_complete_odds(match_data):
                self.db_manager.save_match(match_data)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error processing historical event {event.get('event_id', 'unknown')}: {e}")
            return False
    
    def _has_complete_odds(self, event_data: Dict[str, Any]) -> bool:
        """Vérifie si l'événement a des cotes complètes"""
        try:
            required_odds = ['home_odds', 'draw_odds', 'away_odds', 'over_25_odds', 'under_25_odds']
            
            if isinstance(event_data, dict):
                # Vérifier si toutes les cotes requises sont présentes et valides
                for field in required_odds:
                    value = event_data.get(field)
                    if value is None or not isinstance(value, (int, float)) or value <= 1.0:
                        return False
                return True
            
            # Pour les événements bruts de l'API
            periods = event_data.get('periods', {})
            main_period = periods.get('num_0', {})
            
            if not main_period:
                return False
            
            # Vérifier money line
            money_line = main_period.get('money_line', {})
            if not all(money_line.get(field) and money_line.get(field) > 1.0 
                      for field in ['home', 'draw', 'away']):
                return False
            
            # Vérifier totaux 2.5
            totals = main_period.get('totals', {})
            has_25_total = any(
                float(points) == 2.5 and 
                total_data.get('over') and total_data.get('over') > 1.0 and
                total_data.get('under') and total_data.get('under') > 1.0
                for points, total_data in totals.items()
                if isinstance(points, (str, int, float))
            )
            
            return has_25_total
            
        except Exception as e:
            self.logger.debug(f"Error checking complete odds: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de collecte"""
        duration = time.time() - self.stats['start_time'] if self.stats['start_time'] else 0
        
        return {
            **self.stats,
            'duration': duration,
            'success_rate': (self.stats['successful_requests'] / self.stats['requests_made'] * 100) 
                           if self.stats['requests_made'] > 0 else 0,
            'processing_rate': (self.stats['matches_processed'] / duration) if duration > 0 else 0
        }
    
    def update_results_from_api(self):
        """Met à jour les résultats des matchs terminés"""
        self.logger.info("Starting results update...")
        # Cette fonction nécessiterait une API de résultats
        # Pour l'instant, on peut la laisser vide ou utiliser une autre source
        # TODO: Implémenter avec une source de résultats fiable
        self.logger.info("Results update completed (not implemented yet)")