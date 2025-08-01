import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Configuration
    RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY', 'e1e76b8e3emsh2445ffb97db0128p158afdjsnb3175ce8d916')
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
    RATE_LIMIT_DELAY = 0.1  # seconds between API calls
    BATCH_SIZE = 100
    HISTORICAL_YEARS = 10
    
    # Streamlit Configuration
    APP_TITLE = "⚽ Système de Paris Pinnacle - Similarité des Cotes"
    PAGE_ICON = "⚽"
    LAYOUT = "wide"
    
    # Markets Configuration
    MARKETS = {
        'money_line': {'name': '1X2', 'fields': ['home', 'draw', 'away']},
        'totals': {'name': 'Plus/Moins 2.5', 'fields': ['over_25', 'under_25']},
        'btts': {'name': 'BTTS', 'fields': ['yes', 'no']}
    }
