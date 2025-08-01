"""
Module de logging avancé pour le système de paris Pinnacle
"""
import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path
from config.config import Config

class PinnacleLogger:
    """Gestionnaire de logging centralisé et avancé"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PinnacleLogger, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.setup_logging()
            self._initialized = True
    
    def setup_logging(self):
        """Configure le système de logging avec rotation et formatage avancé"""
        
        # Créer le répertoire de logs
        log_dir = Path(Config.LOG_FILE).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration du formateur
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Logger principal
        self.logger = logging.getLogger('pinnacle_betting')
        self.logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # Éviter la duplication des handlers
        if not self.logger.handlers:
            
            # Handler pour fichier avec rotation
            file_handler = logging.handlers.RotatingFileHandler(
                Config.LOG_FILE,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)
            
            # Handler console
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler.setLevel(getattr(logging, Config.LOG_LEVEL))
            
            # Handler pour erreurs critiques (email en production)
            error_handler = logging.handlers.RotatingFileHandler(
                str(log_dir / 'errors.log'),
                maxBytes=5*1024*1024,  # 5MB
                backupCount=3,
                encoding='utf-8'
            )
            error_handler.setFormatter(formatter)
            error_handler.setLevel(logging.ERROR)
            
            # Ajouter les handlers
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
            self.logger.addHandler(error_handler)
    
    def get_logger(self, name=None):
        """Retourne un logger configuré"""
        if name:
            return logging.getLogger(f'pinnacle_betting.{name}')
        return self.logger
    
    def log_api_call(self, endpoint, params=None, response_status=None, execution_time=None):
        """Log spécialisé pour les appels API"""
        logger = self.get_logger('api')
        
        message = f"API Call: {endpoint}"
        if params:
            message += f" | Params: {params}"
        if response_status:
            message += f" | Status: {response_status}"
        if execution_time:
            message += f" | Time: {execution_time:.3f}s"
        
        if response_status and response_status >= 400:
            logger.error(message)
        else:
            logger.info(message)
    
    def log_similarity_calculation(self, method, matches_found, execution_time, threshold):
        """Log spécialisé pour les calculs de similarité"""
        logger = self.get_logger('similarity')
        
        message = f"Similarity calculation: {method} | Found: {matches_found} matches | "
        message += f"Threshold: {threshold:.2f} | Time: {execution_time:.3f}s"
        
        logger.info(message)
    
    def log_database_operation(self, operation, table, records_affected=None, execution_time=None):
        """Log spécialisé pour les opérations de base de données"""
        logger = self.get_logger('database')
        
        message = f"DB Operation: {operation} on {table}"
        if records_affected is not None:
            message += f" | Records: {records_affected}"
        if execution_time:
            message += f" | Time: {execution_time:.3f}s"
        
        logger.info(message)
    
    def log_data_collection(self, source, events_processed, success_count, error_count, duration):
        """Log spécialisé pour la collecte de données"""
        logger = self.get_logger('collector')
        
        message = f"Data Collection: {source} | Processed: {events_processed} | "
        message += f"Success: {success_count} | Errors: {error_count} | Duration: {duration:.1f}s"
        
        success_rate = (success_count / events_processed * 100) if events_processed > 0 else 0
        message += f" | Success Rate: {success_rate:.1f}%"
        
        if error_count > events_processed * 0.1:  # Plus de 10% d'erreurs
            logger.warning(message)
        else:
            logger.info(message)
    
    def log_performance_metrics(self, component, metrics):
        """Log des métriques de performance"""
        logger = self.get_logger('performance')
        
        message = f"Performance [{component}]: "
        message += " | ".join([f"{k}: {v}" for k, v in metrics.items()])
        
        logger.info(message)
    
    def log_user_action(self, action, user_input=None, results=None):
        """Log des actions utilisateur dans l'interface"""
        logger = self.get_logger('user')
        
        message = f"User Action: {action}"
        if user_input:
            message += f" | Input: {user_input}"
        if results:
            message += f" | Results: {results}"
        
        logger.info(message)

# Instance singleton
pinnacle_logger = PinnacleLogger()

def get_logger(name=None):
    """Fonction helper pour obtenir un logger"""
    return pinnacle_logger.get_logger(name)