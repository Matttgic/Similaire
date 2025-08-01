"""
Module de gestion d'erreurs et validations pour le système Pinnacle
"""
import re
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
from src.logger import get_logger

logger = get_logger('validation')

class PinnacleError(Exception):
    """Exception de base pour les erreurs du système Pinnacle"""
    pass

class APIError(PinnacleError):
    """Erreur liée aux appels API"""
    def __init__(self, message, status_code=None, endpoint=None):
        super().__init__(message)
        self.status_code = status_code
        self.endpoint = endpoint

class ValidationError(PinnacleError):
    """Erreur de validation des données"""
    pass

class DatabaseError(PinnacleError):
    """Erreur liée à la base de données"""
    pass

class SimilarityError(PinnacleError):
    """Erreur liée aux calculs de similarité"""
    pass

class ValidationManager:
    """Gestionnaire centralisé des validations"""
    
    @staticmethod
    def validate_odds_input(odds_dict: Dict[str, float]) -> List[str]:
        """Valide les cotes saisies par l'utilisateur avec vérifications avancées"""
        required_fields = ['home', 'draw', 'away', 'over_25', 'under_25']
        errors = []
        
        # Vérifier la présence des champs requis
        for field in required_fields:
            if field not in odds_dict:
                errors.append(f"Cote manquante: {field}")
                continue
                
            value = odds_dict[field]
            
            # Vérifier le type
            if not isinstance(value, (int, float)):
                errors.append(f"Type invalide pour {field}: doit être un nombre")
                continue
            
            # Vérifier les valeurs
            if value is None:
                errors.append(f"Cote invalide: {field} ne peut pas être None")
            elif value <= 1.0:
                errors.append(f"Cote trop faible: {field} ({value}) - minimum 1.01")
            elif value > 1000:
                errors.append(f"Cote trop élevée: {field} ({value}) - maximum 1000")
        
        # Vérifications de cohérence si toutes les cotes sont valides
        if not errors and len(odds_dict) >= 5:
            # Vérifier la cohérence des cotes 1X2
            total_probability = (1/odds_dict['home'] + 1/odds_dict['draw'] + 1/odds_dict['away'])
            if total_probability < 0.85 or total_probability > 1.25:
                errors.append(f"Cotes 1X2 incohérentes (probabilité totale: {total_probability:.3f})")
            
            # Vérifier la cohérence Over/Under
            ou_probability = (1/odds_dict['over_25'] + 1/odds_dict['under_25'])
            if ou_probability < 0.85 or ou_probability > 1.25:
                errors.append(f"Cotes O/U incohérentes (probabilité totale: {ou_probability:.3f})")
        
        if errors:
            logger.warning(f"Validation errors for odds input: {errors}")
        
        return errors
    
    @staticmethod
    def validate_api_response(response: requests.Response, expected_fields: List[str] = None) -> Dict[str, Any]:
        """Valide et nettoie une réponse API"""
        
        # Vérifier le statut HTTP
        if response.status_code != 200:
            raise APIError(
                f"API error: {response.status_code} - {response.text}",
                status_code=response.status_code,
                endpoint=response.url
            )
        
        try:
            data = response.json()
        except ValueError as e:
            raise APIError(f"Invalid JSON response: {e}")
        
        # Vérifier la structure de base
        if not isinstance(data, dict):
            raise APIError("Response must be a JSON object")
        
        # Vérifier les champs attendus
        if expected_fields:
            missing_fields = [field for field in expected_fields if field not in data]
            if missing_fields:
                logger.warning(f"Missing fields in API response: {missing_fields}")
        
        return data
    
    @staticmethod
    def validate_match_data(match_data: Dict[str, Any]) -> Dict[str, Any]:
        """Valide et nettoie les données d'un match"""
        validated = {}
        
        # Champs requis
        required_fields = {
            'event_id': int,
            'home_team': str,
            'away_team': str
        }
        
        # Champs optionnels avec types
        optional_fields = {
            'sport_id': int,
            'league_id': int,
            'league_name': str,
            'start_time': str,
            'event_type': str,
            'home_odds': float,
            'draw_odds': float,
            'away_odds': float,
            'over_25_odds': float,
            'under_25_odds': float,
            'btts_yes_odds': float,
            'btts_no_odds': float,
            'home_score': int,
            'away_score': int,
            'result': str,
            'total_goals': int,
            'over_25_result': bool,
            'btts_result': bool
        }
        
        # Valider les champs requis
        for field, expected_type in required_fields.items():
            if field not in match_data:
                raise ValidationError(f"Required field missing: {field}")
            
            try:
                validated[field] = expected_type(match_data[field])
            except (ValueError, TypeError):
                raise ValidationError(f"Invalid type for {field}: expected {expected_type.__name__}")
        
        # Valider les champs optionnels
        for field, expected_type in optional_fields.items():
            if field in match_data and match_data[field] is not None:
                try:
                    validated[field] = expected_type(match_data[field])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid type for optional field {field}, skipping")
        
        # Validations spécifiques
        if 'start_time' in validated:
            validated['start_time'] = ValidationManager._validate_datetime_string(validated['start_time'])
        
        if 'home_team' in validated:
            validated['home_team'] = ValidationManager._clean_team_name(validated['home_team'])
        
        if 'away_team' in validated:
            validated['away_team'] = ValidationManager._clean_team_name(validated['away_team'])
        
        # Valider les cotes si présentes
        odds_fields = ['home_odds', 'draw_odds', 'away_odds', 'over_25_odds', 'under_25_odds']
        odds_present = {field: validated.get(field) for field in odds_fields if field in validated}
        
        if odds_present:
            for field, value in odds_present.items():
                if value is not None and (value <= 1.0 or value > 1000):
                    logger.warning(f"Suspicious odds value for {field}: {value}")
        
        return validated
    
    @staticmethod
    def validate_similarity_parameters(method: str, threshold: float, min_matches: int) -> bool:
        """Valide les paramètres de calcul de similarité"""
        
        valid_methods = ['cosine', 'euclidean', 'percentage']
        if method not in valid_methods:
            raise ValidationError(f"Invalid similarity method: {method}. Must be one of {valid_methods}")
        
        if not 0 <= threshold <= 1:
            raise ValidationError(f"Threshold must be between 0 and 1, got: {threshold}")
        
        if min_matches < 1:
            raise ValidationError(f"min_matches must be at least 1, got: {min_matches}")
        
        return True
    
    @staticmethod
    def _validate_datetime_string(dt_string: str) -> str:
        """Valide et normalise une chaîne de datetime"""
        try:
            # Essayer de parser la date pour validation
            if 'T' in dt_string:
                # Format ISO avec T
                datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
            else:
                # Format simple
                datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')
            return dt_string
        except ValueError:
            logger.warning(f"Invalid datetime format: {dt_string}")
            return None
    
    @staticmethod
    def _clean_team_name(team_name: str) -> str:
        """Nettoie et normalise le nom d'une équipe"""
        if not team_name:
            return ""
        
        # Supprimer les caractères spéciaux dangereux
        cleaned = re.sub(r'[<>"\']', '', team_name)
        # Normaliser les espaces
        cleaned = ' '.join(cleaned.split())
        # Limiter la longueur
        if len(cleaned) > 100:
            cleaned = cleaned[:100]
            logger.warning(f"Team name truncated: {team_name}")
        
        return cleaned.strip()

class ErrorHandler:
    """Gestionnaire centralisé des erreurs"""
    
    @staticmethod
    def handle_api_error(func):
        """Décorateur pour gérer les erreurs API"""
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.RequestException as e:
                logger.error(f"API request failed in {func.__name__}: {e}")
                raise APIError(f"Network error: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {e}")
                raise
        return wrapper
    
    @staticmethod
    def handle_database_error(func):
        """Décorateur pour gérer les erreurs de base de données"""
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Database error in {func.__name__}: {e}")
                raise DatabaseError(f"Database operation failed: {e}")
        return wrapper
    
    @staticmethod
    def log_and_return_none(func):
        """Décorateur qui log les erreurs et retourne None"""
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                return None
        return wrapper

# Instances pour utilisation globale
validator = ValidationManager()
error_handler = ErrorHandler()