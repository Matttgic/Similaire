import numpy as np
import pandas as pd
import json
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from sklearn.metrics.pairwise import cosine_similarity
from scipy.spatial.distance import euclidean
from concurrent.futures import ThreadPoolExecutor, as_completed

from config.config import Config
from src.database_manager import DatabaseManager
from src.logger import get_logger, pinnacle_logger
from src.error_handler import ValidationManager, ErrorHandler, SimilarityError

class OddsSimilarityEngine:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.similarity_threshold = Config.SIMILARITY_THRESHOLD
        self.min_matches = Config.MIN_SIMILAR_MATCHES
        self.default_method = Config.DEFAULT_SIMILARITY_METHOD
        self.logger = get_logger('similarity')
        self.validator = ValidationManager()
        
        # Cache en mémoire pour les calculs répétés
        self._calculation_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
    
    def calculate_odds_vector(self, odds_data: Any) -> np.ndarray:
        """Convertit les cotes en vecteur numérique pour comparaison avec validation"""
        try:
            if isinstance(odds_data, pd.Series):
                vector = np.array([
                    odds_data['home_odds'],
                    odds_data['draw_odds'],
                    odds_data['away_odds'],
                    odds_data['over_25_odds'],
                    odds_data['under_25_odds']
                ])
            elif isinstance(odds_data, dict):
                vector = np.array([
                    odds_data.get('home', odds_data.get('home_odds')),
                    odds_data.get('draw', odds_data.get('draw_odds')),
                    odds_data.get('away', odds_data.get('away_odds')),
                    odds_data.get('over_25', odds_data.get('over_25_odds')),
                    odds_data.get('under_25', odds_data.get('under_25_odds'))
                ])
            else:
                raise SimilarityError(f"Unsupported data format: {type(odds_data)}")
            
            # Validation du vecteur résultant
            if np.any(np.isnan(vector)) or np.any(vector <= 0):
                raise SimilarityError("Invalid odds vector: contains NaN or non-positive values")
            
            return vector
            
        except Exception as e:
            self.logger.error(f"Error creating odds vector: {e}")
            raise SimilarityError(f"Failed to create odds vector: {e}")
    
    def calculate_similarity_cosine(self, vector1: np.ndarray, vector2: np.ndarray) -> float:
        """Calcule la similarité cosinus entre deux vecteurs"""
        try:
            # Vérification des entrées
            if len(vector1) != len(vector2):
                raise SimilarityError("Vectors must have the same length")
            
            similarity = cosine_similarity([vector1], [vector2])[0][0]
            
            # S'assurer que le résultat est dans [0, 1]
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            self.logger.error(f"Error in cosine similarity calculation: {e}")
            return 0.0
    
    def calculate_similarity_euclidean(self, vector1: np.ndarray, vector2: np.ndarray) -> float:
        """Calcule la similarité basée sur la distance euclidienne normalisée"""
        try:
            if len(vector1) != len(vector2):
                raise SimilarityError("Vectors must have the same length")
            
            distance = euclidean(vector1, vector2)
            
            # Normalisation améliorée
            max_possible_distance = np.sqrt(np.sum((np.maximum(vector1, vector2)) ** 2))
            
            if max_possible_distance == 0:
                return 1.0
            
            similarity = 1 - (distance / max_possible_distance)
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            self.logger.error(f"Error in euclidean similarity calculation: {e}")
            return 0.0
    
    def calculate_similarity_percentage(self, vector1: np.ndarray, vector2: np.ndarray) -> float:
        """Calcule la similarité basée sur les pourcentages de différence"""
        try:
            if len(vector1) != len(vector2):
                raise SimilarityError("Vectors must have the same length")
            
            # Éviter la division par zéro avec une valeur minimale plus réaliste
            vector1_safe = np.where(vector1 == 0, 0.01, vector1)
            differences = np.abs(vector1 - vector2) / vector1_safe
            
            # Utiliser la médiane plutôt que la moyenne pour être moins sensible aux outliers
            median_difference = np.median(differences)
            similarity = 1 - median_difference
            
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            self.logger.error(f"Error in percentage similarity calculation: {e}")
            return 0.0
    
    def calculate_similarity(self, vector1: np.ndarray, vector2: np.ndarray, method: str = 'cosine') -> float:
        """Calcule la similarité selon la méthode choisie avec cache"""
        # Vérifier le cache
        cache_key = (tuple(vector1), tuple(vector2), method)
        if cache_key in self._calculation_cache:
            self._cache_hits += 1
            return self._calculation_cache[cache_key]
        
        self._cache_misses += 1
        
        # Valider les paramètres
        self.validator.validate_similarity_parameters(method, 0.5, 1)  # Validation de base
        
        if method == 'cosine':
            similarity = self.calculate_similarity_cosine(vector1, vector2)
        elif method == 'euclidean':
            similarity = self.calculate_similarity_euclidean(vector1, vector2)
        elif method == 'percentage':
            similarity = self.calculate_similarity_percentage(vector1, vector2)
        else:
            raise SimilarityError(f"Unsupported similarity method: {method}")
        
        # Mettre en cache si le cache n'est pas trop grand
        if len(self._calculation_cache) < 10000:  # Limiter la taille du cache
            self._calculation_cache[cache_key] = similarity
        
        return similarity
    
    def generate_odds_hash(self, target_odds: Dict[str, float]) -> str:
        """Génère un hash unique pour les cotes (pour le cache)"""
        try:
            # Normaliser les clés et valeurs pour un hash cohérent
            normalized_odds = {k: round(v, 3) for k, v in sorted(target_odds.items())}
            odds_str = json.dumps(normalized_odds, sort_keys=True)
            return hashlib.md5(odds_str.encode()).hexdigest()
        except Exception as e:
            self.logger.error(f"Error generating odds hash: {e}")
            return hashlib.md5(str(target_odds).encode()).hexdigest()
    
    def find_similar_matches(self, target_odds: Dict[str, float], method: Optional[str] = None, 
                           threshold: Optional[float] = None, min_matches: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Trouve les matchs similaires aux cotes données avec performance optimisée
        
        Args:
            target_odds: dict avec les cotes cibles
            method: méthode de calcul de similarité
            threshold: seuil de similarité minimum
            min_matches: nombre minimum de matchs à retourner
        
        Returns:
            list: matchs similaires avec leurs scores de similarité
        """
        start_time = time.time()
        
        # Paramètres par défaut
        method = method or self.default_method
        threshold = threshold or self.similarity_threshold
        min_matches = min_matches or self.min_matches
        
        # Validation des paramètres
        try:
            self.validator.validate_similarity_parameters(method, threshold, min_matches)
            # Validation des cotes d'entrée
            validation_errors = self.validator.validate_odds_input(target_odds)
            if validation_errors:
                raise SimilarityError(f"Invalid target odds: {'; '.join(validation_errors)}")
        except Exception as e:
            self.logger.error(f"Parameter validation failed: {e}")
            return []
        
        # Vérifier le cache
        odds_hash = self.generate_odds_hash(target_odds)
        cached_result = self._get_cached_similarity(odds_hash, method, threshold)
        if cached_result and Config.ENABLE_CACHE:
            self.logger.debug(f"Cache hit for odds hash {odds_hash[:8]}")
            return cached_result
        
        # Charger les données historiques
        try:
            historical_df = self.db_manager.get_matches_with_complete_odds()
        except Exception as e:
            self.logger.error(f"Failed to load historical data: {e}")
            return []
        
        if historical_df.empty:
            self.logger.warning("No historical data available for similarity calculation")
            return []
        
        self.logger.info(f"Analyzing {len(historical_df)} historical matches using {method} method")
        
        # Convertir les cotes cibles en vecteur
        try:
            target_vector = self.calculate_odds_vector(target_odds)
        except Exception as e:
            self.logger.error(f"Failed to create target vector: {e}")
            return []
        
        # Calculer les similarités avec traitement parallèle pour de gros datasets
        similarities = []
        
        if len(historical_df) > 1000:  # Traitement parallèle pour les gros datasets
            similarities = self._calculate_similarities_parallel(historical_df, target_vector, method)
        else:
            similarities = self._calculate_similarities_sequential(historical_df, target_vector, method)
        
        if not similarities:
            self.logger.warning("No similarities calculated")
            return []
        
        # Trier par similarité décroissante
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Appliquer le seuil et les limites
        high_similarity_matches = [
            match for match in similarities 
            if match['similarity'] >= threshold
        ]
        
        # S'assurer d'avoir le minimum requis
        if len(high_similarity_matches) < min_matches:
            result_matches = similarities[:min_matches]
            actual_above_threshold = len(high_similarity_matches)
            self.logger.info(f"Only {actual_above_threshold} matches above {threshold*100:.1f}% threshold")
            self.logger.info(f"Returning top {len(result_matches)} most similar matches")
        else:
            result_matches = high_similarity_matches
            self.logger.info(f"Found {len(result_matches)} matches above {threshold*100:.1f}% threshold")
        
        # Mettre en cache si activé
        if Config.ENABLE_CACHE:
            self._cache_similarity_result(odds_hash, result_matches, method, threshold)
        
        # Log des métriques de performance
        execution_time = time.time() - start_time
        pinnacle_logger.log_similarity_calculation(method, len(result_matches), execution_time, threshold)
        
        # Métriques détaillées
        pinnacle_logger.log_performance_metrics('similarity_calculation', {
            'method': method,
            'historical_matches': len(historical_df),
            'matches_found': len(result_matches),
            'cache_hit_rate': self._cache_hits / (self._cache_hits + self._cache_misses) * 100 if (self._cache_hits + self._cache_misses) > 0 else 0,
            'avg_similarity': np.mean([m['similarity'] for m in result_matches]) if result_matches else 0,
            'execution_time': execution_time
        })
        
        return result_matches
    
    def _calculate_similarities_sequential(self, historical_df: pd.DataFrame, 
                                         target_vector: np.ndarray, method: str) -> List[Dict[str, Any]]:
        """Calcul séquentiel des similarités"""
        similarities = []
        
        for idx, row in historical_df.iterrows():
            try:
                historical_vector = self.calculate_odds_vector(row)
                
                # Vérifier que le vecteur est valide
                if np.any(np.isnan(historical_vector)) or np.any(historical_vector <= 0):
                    continue
                
                similarity_score = self.calculate_similarity(target_vector, historical_vector, method)
                
                if similarity_score > 0:  # Ignorer les similarités nulles
                    similarities.append({
                        'event_id': row['event_id'],
                        'similarity': similarity_score,
                        'match_data': row.to_dict(),
                        'odds_vector': historical_vector.tolist()
                    })
                
            except Exception as e:
                self.logger.debug(f"Error calculating similarity for event {row.get('event_id', 'unknown')}: {e}")
                continue
        
        return similarities
    
    def _calculate_similarities_parallel(self, historical_df: pd.DataFrame, 
                                       target_vector: np.ndarray, method: str) -> List[Dict[str, Any]]:
        """Calcul parallèle des similarités pour de gros datasets"""
        similarities = []
        
        # Diviser le DataFrame en chunks
        chunk_size = max(100, len(historical_df) // 4)  # 4 threads par défaut
        chunks = [historical_df[i:i + chunk_size] for i in range(0, len(historical_df), chunk_size)]
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for chunk in chunks:
                future = executor.submit(self._process_chunk, chunk, target_vector, method)
                futures.append(future)
            
            for future in as_completed(futures):
                try:
                    chunk_similarities = future.result(timeout=30)
                    similarities.extend(chunk_similarities)
                except Exception as e:
                    self.logger.error(f"Error in parallel similarity calculation: {e}")
        
        return similarities
    
    def _process_chunk(self, chunk: pd.DataFrame, target_vector: np.ndarray, method: str) -> List[Dict[str, Any]]:
        """Traite un chunk de données pour le calcul parallèle"""
        similarities = []
        
        for idx, row in chunk.iterrows():
            try:
                historical_vector = self.calculate_odds_vector(row)
                
                if np.any(np.isnan(historical_vector)) or np.any(historical_vector <= 0):
                    continue
                
                similarity_score = self.calculate_similarity(target_vector, historical_vector, method)
                
                if similarity_score > 0:
                    similarities.append({
                        'event_id': row['event_id'],
                        'similarity': similarity_score,
                        'match_data': row.to_dict(),
                        'odds_vector': historical_vector.tolist()
                    })
                
            except Exception:
                continue
        
        return similarities
    
    def analyze_similar_matches(self, similar_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyse les résultats des matchs similaires avec statistiques avancées"""
        if not similar_matches:
            return {
                'error': 'Aucun match similaire trouvé',
                'total_matches': 0
            }
        
        total_matches = len(similar_matches)
        
        # Statistiques de similarité
        similarities = [m['similarity'] for m in similar_matches]
        analysis = {
            'total_matches': total_matches,
            'similarity_stats': {
                'avg_similarity': np.mean(similarities),
                'min_similarity': min(similarities),
                'max_similarity': max(similarities),
                'median_similarity': np.median(similarities),
                'std_similarity': np.std(similarities),
                'percentile_90': np.percentile(similarities, 90),
                'percentile_75': np.percentile(similarities, 75),
                'percentile_25': np.percentile(similarities, 25)
            }
        }
        
        # Analyser les résultats (si disponibles)
        matches_with_results = [
            m for m in similar_matches 
            if m['match_data'].get('result') is not None
        ]
        
        if matches_with_results:
            results = [m['match_data']['result'] for m in matches_with_results]
            total_with_results = len(results)
            
            analysis['results_analysis'] = {
                'matches_with_results': total_with_results,
                'coverage': total_with_results / total_matches * 100,
                'home_wins': {
                    'count': results.count('H'),
                    'percentage': results.count('H') / total_with_results * 100
                },
                'draws': {
                    'count': results.count('D'),
                    'percentage': results.count('D') / total_with_results * 100
                },
                'away_wins': {
                    'count': results.count('A'),
                    'percentage': results.count('A') / total_with_results * 100
                }
            }
            
            # Analyse de confiance basée sur le nombre et la similarité
            avg_similarity = analysis['similarity_stats']['avg_similarity']
            confidence_score = min(100, (total_with_results / 10) * 20 + avg_similarity * 50)
            analysis['results_analysis']['confidence_score'] = confidence_score
            
            # Analyse Over/Under 2.5
            over_results = [
                m['match_data'].get('over_25_result') for m in matches_with_results
                if m['match_data'].get('over_25_result') is not None
            ]
            
            if over_results:
                over_count = sum(over_results)
                total_over = len(over_results)
                analysis['over_under_analysis'] = {
                    'matches_with_ou_results': total_over,
                    'coverage': total_over / total_matches * 100,
                    'over_25': {
                        'count': over_count,
                        'percentage': over_count / total_over * 100
                    },
                    'under_25': {
                        'count': total_over - over_count,
                        'percentage': (total_over - over_count) / total_over * 100
                    }
                }
            
            # Analyse BTTS
            btts_results = [
                m['match_data'].get('btts_result') for m in matches_with_results
                if m['match_data'].get('btts_result') is not None
            ]
            
            if btts_results:
                btts_yes_count = sum(btts_results)
                total_btts = len(btts_results)
                analysis['btts_analysis'] = {
                    'matches_with_btts_results': total_btts,
                    'coverage': total_btts / total_matches * 100,
                    'btts_yes': {
                        'count': btts_yes_count,
                        'percentage': btts_yes_count / total_btts * 100
                    },
                    'btts_no': {
                        'count': total_btts - btts_yes_count,
                        'percentage': (total_btts - btts_yes_count) / total_btts * 100
                    }
                }
        
        return analysis
    
    def _get_cached_similarity(self, odds_hash: str, method: str, threshold: float) -> Optional[List[Dict[str, Any]]]:
        """Récupère un résultat de similarité depuis le cache"""
        if not Config.ENABLE_CACHE:
            return None
            
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT similar_matches FROM similarity_cache 
                WHERE target_odds_hash = ? AND method = ? AND threshold = ?
                AND datetime(created_at) > datetime('now', '-' || ? || ' seconds')
            ''', (odds_hash, method, threshold, Config.CACHE_TTL))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return json.loads(result[0])
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving from cache: {e}")
            return None
    
    def _cache_similarity_result(self, odds_hash: str, similar_matches: List[Dict[str, Any]], 
                               method: str, threshold: float) -> None:
        """Met en cache un résultat de similarité"""
        if not Config.ENABLE_CACHE:
            return
            
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO similarity_cache 
                (target_odds_hash, similar_matches, method, threshold, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                odds_hash,
                json.dumps(similar_matches, default=str),
                method,
                threshold,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error caching similarity result: {e}")
    
    def get_method_comparison(self, target_odds: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """Compare les résultats selon différentes méthodes"""
        methods = Config.SIMILARITY_METHODS
        comparison = {}
        
        for method in methods:
            try:
                similar_matches = self.find_similar_matches(
                    target_odds, 
                    method=method,
                    threshold=0.8  # Seuil plus bas pour comparaison
                )
                analysis = self.analyze_similar_matches(similar_matches)
                comparison[method] = analysis
            except Exception as e:
                self.logger.error(f"Error in method comparison for {method}: {e}")
                comparison[method] = {'error': str(e)}
        
        return comparison
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du moteur de similarité"""
        return {
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_hit_rate': self._cache_hits / (self._cache_hits + self._cache_misses) * 100 
                             if (self._cache_hits + self._cache_misses) > 0 else 0,
            'cache_size': len(self._calculation_cache),
            'similarity_threshold': self.similarity_threshold,
            'min_matches': self.min_matches,
            'default_method': self.default_method
        }
    
    def clear_cache(self) -> None:
        """Vide les caches en mémoire et en base"""
        self._calculation_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        
        try:
            self.db_manager.clear_similarity_cache()
            self.logger.info("All caches cleared successfully")
        except Exception as e:
            self.logger.error(f"Error clearing database cache: {e}")