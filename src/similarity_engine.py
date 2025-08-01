import numpy as np
import pandas as pd
import json
import hashlib
from sklearn.metrics.pairwise import cosine_similarity
from scipy.spatial.distance import euclidean
from config.config import Config
from src.database_manager import DatabaseManager

class OddsSimilarityEngine:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.similarity_threshold = Config.SIMILARITY_THRESHOLD
        self.min_matches = Config.MIN_SIMILAR_MATCHES
        self.default_method = Config.DEFAULT_SIMILARITY_METHOD
    
    def calculate_odds_vector(self, odds_data):
        """Convertit les cotes en vecteur numérique pour comparaison"""
        if isinstance(odds_data, pd.Series):
            return np.array([
                odds_data['home_odds'],
                odds_data['draw_odds'],
                odds_data['away_odds'],
                odds_data['over_25_odds'],
                odds_data['under_25_odds']
            ])
        elif isinstance(odds_data, dict):
            return np.array([
                odds_data.get('home', odds_data.get('home_odds')),
                odds_data.get('draw', odds_data.get('draw_odds')),
                odds_data.get('away', odds_data.get('away_odds')),
                odds_data.get('over_25', odds_data.get('over_25_odds')),
                odds_data.get('under_25', odds_data.get('under_25_odds'))
            ])
        else:
            raise ValueError("Format de données non supporté")
    
    def calculate_similarity_cosine(self, vector1, vector2):
        """Calcule la similarité cosinus entre deux vecteurs"""
        similarity = cosine_similarity([vector1], [vector2])[0][0]
        return max(0, similarity)  # S'assurer que c'est positif
    
    def calculate_similarity_euclidean(self, vector1, vector2):
        """Calcule la similarité basée sur la distance euclidienne"""
        distance = euclidean(vector1, vector2)
        # Normaliser: plus la distance est faible, plus la similarité est élevée
        max_possible_distance = np.sqrt(np.sum((vector1 + vector2) ** 2))
        if max_possible_distance == 0:
            return 1.0
        similarity = 1 - (distance / max_possible_distance)
        return max(0, similarity)
    
    def calculate_similarity_percentage(self, vector1, vector2):
        """Calcule la similarité basée sur les pourcentages de différence"""
        # Éviter la division par zéro
        vector1_safe = np.where(vector1 == 0, 0.001, vector1)
        differences = np.abs(vector1 - vector2) / vector1_safe
        avg_difference = np.mean(differences)
        similarity = 1 - avg_difference
        return max(0, similarity)
    
    def calculate_similarity(self, vector1, vector2, method='cosine'):
        """Calcule la similarité selon la méthode choisie"""
        if method == 'cosine':
            return self.calculate_similarity_cosine(vector1, vector2)
        elif method == 'euclidean':
            return self.calculate_similarity_euclidean(vector1, vector2)
        elif method == 'percentage':
            return self.calculate_similarity_percentage(vector1, vector2)
        else:
            raise ValueError(f"Méthode non supportée: {method}")
    
    def generate_odds_hash(self, target_odds):
        """Génère un hash unique pour les cotes (pour le cache)"""
        odds_str = json.dumps(target_odds, sort_keys=True)
        return hashlib.md5(odds_str.encode()).hexdigest()
    
    def find_similar_matches(self, target_odds, method=None, threshold=None, min_matches=None):
        """
        Trouve les matchs similaires aux cotes données
        
        Args:
            target_odds: dict avec les cotes cibles
            method: méthode de calcul de similarité
            threshold: seuil de similarité minimum
            min_matches: nombre minimum de matchs à retourner
        
        Returns:
            list: matchs similaires avec leurs scores de similarité
        """
        method = method or self.default_method
        threshold = threshold or self.similarity_threshold
        min_matches = min_matches or self.min_matches
        
        # Vérifier le cache
        odds_hash = self.generate_odds_hash(target_odds)
        cached_result = self._get_cached_similarity(odds_hash, method, threshold)
        if cached_result:
            return cached_result
        
        # Charger les données historiques
        historical_df = self.db_manager.get_matches_with_complete_odds()
        
        if historical_df.empty:
            print("❌ Aucune donnée historique disponible")
            return []
        
        print(f"📊 Analyse de {len(historical_df)} matchs historiques...")
        
        # Convertir les cotes cibles en vecteur
        target_vector = self.calculate_odds_vector(target_odds)
        
        # Calculer les similarités
        similarities = []
        
        for idx, row in historical_df.iterrows():
            try:
                historical_vector = self.calculate_odds_vector(row)
                
                # Vérifier que le vecteur est valide
                if np.any(np.isnan(historical_vector)) or np.any(historical_vector <= 0):
                    continue
                
                similarity_score = self.calculate_similarity(
                    target_vector, historical_vector, method
                )
                
                similarities.append({
                    'event_id': row['event_id'],
                    'similarity': similarity_score,
                    'match_data': row.to_dict(),
                    'odds_vector': historical_vector.tolist()
                })
                
            except Exception as e:
                continue  # Ignorer les erreurs de calcul
        
        # Trier par similarité décroissante
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Appliquer le seuil
        high_similarity_matches = [
            match for match in similarities 
            if match['similarity'] >= threshold
        ]
        
        # S'assurer d'avoir le minimum requis
        if len(high_similarity_matches) < min_matches:
            result_matches = similarities[:min_matches]
            actual_above_threshold = len(high_similarity_matches)
            print(f"⚠️ Seulement {actual_above_threshold} matchs au-dessus de {threshold*100:.1f}%")
            print(f"📊 Retour des {len(result_matches)} matchs les plus similaires")
        else:
            result_matches = high_similarity_matches
        
        # Mettre en cache
        self._cache_similarity_result(odds_hash, result_matches, method, threshold)
        
        return result_matches
    
    def analyze_similar_matches(self, similar_matches):
        """Analyse les résultats des matchs similaires"""
        if not similar_matches:
            return {
                'error': 'Aucun match similaire trouvé',
                'total_matches': 0
            }
        
        total_matches = len(similar_matches)
        analysis = {
            'total_matches': total_matches,
            'similarity_stats': {
                'avg_similarity': np.mean([m['similarity'] for m in similar_matches]),
                'min_similarity': min([m['similarity'] for m in similar_matches]),
                'max_similarity': max([m['similarity'] for m in similar_matches]),
                'median_similarity': np.median([m['similarity'] for m in similar_matches])
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
                    'btts_
'count': btts_yes_count,
                        'percentage': btts_yes_count / total_btts * 100
                    },
                    'btts_no': {
                        'count': total_btts - btts_yes_count,
                        'percentage': (total_btts - btts_yes_count) / total_btts * 100
                    }
                }
        
        return analysis
    
    def _get_cached_similarity(self, odds_hash, method, threshold):
        """Récupère un résultat de similarité depuis le cache"""
        import sqlite3
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT similar_matches FROM similarity_cache 
            WHERE target_odds_hash = ? AND method = ? AND threshold = ?
            AND datetime(created_at) > datetime('now', '-1 hour')
        ''', (odds_hash, method, threshold))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        return None
    
    def _cache_similarity_result(self, odds_hash, similar_matches, method, threshold):
        """Met en cache un résultat de similarité"""
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
    
    def get_method_comparison(self, target_odds):
        """Compare les résultats selon différentes méthodes"""
        methods = Config.SIMILARITY_METHODS
        comparison = {}
        
        for method in methods:
            similar_matches = self.find_similar_matches(
                target_odds, 
                method=method,
                threshold=0.8  # Seuil plus bas pour comparaison
            )
            analysis = self.analyze_similar_matches(similar_matches)
            comparison[method] = analysis
        
        return comparison
