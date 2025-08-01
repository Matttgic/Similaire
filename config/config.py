import os
import logging
from dotenv import load_dotenv
from pathlib import Path

# Charger le fichier .env s'il existe
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

class Config:
    # API Configuration - Sécurisée
    RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')
    if not RAPIDAPI_KEY:
        raise ValueError("RAPIDAPI_KEY environment variable is required. Please set it in .env file.")
    
    RAPIDAPI_HOST = 'pinnacle-odds.p.rapidapi.com'
    BASE_URL = 'https://pinnacle-odds.p.rapidapi.com'
    
    # Database Configuration
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/football_odds.db')
    
    # Similarity Engine Configuration
    SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', '0.90'))
    MIN_SIMILAR_MATCHES = int(os.getenv('MIN_SIMILAR_MATCHES', '10'))
    SIMILARITY_METHODS = ['cosine', 'euclidean', 'percentage']
    DEFAULT_SIMILARITY_METHOD = 'cosine'
    
    # Data Collection Configuration
    FOOTBALL_SPORT_ID = 1
    RATE_LIMIT_DELAY = float(os.getenv('RATE_LIMIT_DELAY', '0.1'))
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))
    HISTORICAL_YEARS = int(os.getenv('HISTORICAL_YEARS', '10'))
    MAX_CONCURRENT_REQUESTS = int(os.getenv('MAX_CONCURRENT_REQUESTS', '5'))
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    LOG_FILE = os.getenv('LOG_FILE', 'logs/pinnacle_betting.log')
    
    # Performance Configuration
    ENABLE_CACHE = os.getenv('ENABLE_CACHE', 'true').lower() == 'true'
    CACHE_TTL = int(os.getenv('CACHE_TTL', '3600'))
    
    # Security Configuration
    API_RATE_LIMIT = int(os.getenv('API_RATE_LIMIT', '100'))
    MAX_REQUEST_SIZE = int(os.getenv('MAX_REQUEST_SIZE', '1000000'))
    
    # Streamlit Configuration
    APP_TITLE = "⚽ Système de Paris Pinnacle - Similarité des Cotes"
    PAGE_ICON = "⚽"
    LAYOUT = "wide"
    STREAMLIT_SERVER_PORT = int(os.getenv('STREAMLIT_SERVER_PORT', '8501'))
    STREAMLIT_SERVER_ADDRESS = os.getenv('STREAMLIT_SERVER_ADDRESS', '0.0.0.0')
    STREAMLIT_SERVER_HEADLESS = os.getenv('STREAMLIT_SERVER_HEADLESS', 'true').lower() == 'true'
    
    # Development
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # Markets Configuration
    MARKETS = {
        'money_line': {'name': '1X2', 'fields': ['home', 'draw', 'away']},
        'totals': {'name': 'Plus/Moins 2.5', 'fields': ['over_25', 'under_25']},
        'btts': {'name': 'BTTS', 'fields': ['yes', 'no']}
    }
    
    @classmethod
    def setup_logging(cls):
        """Configure le système de logging"""
        # Créer le répertoire de logs s'il n'existe pas
        log_dir = Path(cls.LOG_FILE).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration du logging
        logging_config = {
            'level': getattr(logging, cls.LOG_LEVEL),
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'handlers': [
                logging.FileHandler(cls.LOG_FILE),
                logging.StreamHandler()
            ]
        }
        
        logging.basicConfig(**logging_config)
        return logging.getLogger(__name__)
    
    @classmethod
    def validate_config(cls):
        """Valide la configuration au démarrage"""
        errors = []
        
        # Validation des paramètres critiques
        if cls.SIMILARITY_THRESHOLD < 0 or cls.SIMILARITY_THRESHOLD > 1:
            errors.append("SIMILARITY_THRESHOLD must be between 0 and 1")
        
        if cls.MIN_SIMILAR_MATCHES < 1:
            errors.append("MIN_SIMILAR_MATCHES must be greater than 0")
        
        if cls.RATE_LIMIT_DELAY < 0:
            errors.append("RATE_LIMIT_DELAY must be non-negative")
        
        if cls.BATCH_SIZE < 1:
            errors.append("BATCH_SIZE must be greater than 0")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True
