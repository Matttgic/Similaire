import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os
import time
import json
import sqlite3
import numpy as np
from typing import Dict, List, Any, Optional
import requests
from sklearn.metrics.pairwise import cosine_similarity
from scipy.spatial.distance import euclidean
import hashlib
import threading
from pathlib import Path
import warnings

# Supprimer les warnings pour un affichage plus propre
warnings.filterwarnings('ignore')

# Configuration de la page
st.set_page_config(
    page_title="⚽ Système de Paris Pinnacle - Similarité des Cotes",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration simplifiée pour Streamlit Cloud
class Config:
    # API Configuration - utilise les secrets Streamlit
    try:
        RAPIDAPI_KEY = st.secrets.get("RAPIDAPI_KEY", "demo_key") if hasattr(st, 'secrets') and st.secrets else "demo_key"
    except:
        RAPIDAPI_KEY = "demo_key"
        
    RAPIDAPI_HOST = 'pinnacle-odds.p.rapidapi.com'
    BASE_URL = 'https://pinnacle-odds.p.rapidapi.com'
    
    # Configuration locale pour Streamlit Cloud
    DATABASE_PATH = 'football_odds.db'
    SIMILARITY_THRESHOLD = 0.90
    MIN_SIMILAR_MATCHES = 10
    SIMILARITY_METHODS = ['cosine', 'euclidean', 'percentage']
    DEFAULT_SIMILARITY_METHOD = 'cosine'
    
    # Paramètres optimisés pour le cloud
    RATE_LIMIT_DELAY = 0.5
    BATCH_SIZE = 50
    MAX_CONCURRENT_REQUESTS = 2
    
    APP_TITLE = "⚽ Système de Paris Pinnacle - Similarité des Cotes"
    PAGE_ICON = "⚽"
    LAYOUT = "wide"

# Classes simplifiées pour Streamlit Cloud
class ValidationManager:
    """Gestionnaire de validation simplifié"""
    
    @staticmethod
    def validate_odds_input(odds_dict: Dict[str, float]) -> List[str]:
        """Valide les cotes saisies par l'utilisateur"""
        required_fields = ['home', 'draw', 'away', 'over_25', 'under_25']
        errors = []
        
        for field in required_fields:
            if field not in odds_dict:
                errors.append(f"Cote manquante: {field}")
                continue
                
            value = odds_dict[field]
            
            if not isinstance(value, (int, float)):
                errors.append(f"Type invalide pour {field}: doit être un nombre")
                continue
            
            if value is None:
                errors.append(f"Cote invalide: {field} ne peut pas être None")
            elif value <= 1.0:
                errors.append(f"Cote trop faible: {field} ({value}) - minimum 1.01")
            elif value > 1000:
                errors.append(f"Cote trop élevée: {field} ({value}) - maximum 1000")
        
        # Vérifications de cohérence
        if not errors and len(odds_dict) >= 5:
            total_probability = (1/odds_dict['home'] + 1/odds_dict['draw'] + 1/odds_dict['away'])
            if total_probability < 0.85 or total_probability > 1.25:
                errors.append(f"Cotes 1X2 incohérentes (probabilité totale: {total_probability:.3f})")
            
            ou_probability = (1/odds_dict['over_25'] + 1/odds_dict['under_25'])
            if ou_probability < 0.85 or ou_probability > 1.25:
                errors.append(f"Cotes O/U incohérentes (probabilité totale: {ou_probability:.3f})")
        
        return errors

class DatabaseManager:
    """Gestionnaire de base de données simplifié pour Streamlit Cloud"""
    
    def __init__(self, db_path: str = Config.DATABASE_PATH):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialise la base de données"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS matches (
                    event_id INTEGER PRIMARY KEY,
                    sport_id INTEGER DEFAULT 1,
                    league_id INTEGER,
                    league_name TEXT,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    start_time TEXT,
                    
                    home_odds REAL CHECK(home_odds > 1.0),
                    draw_odds REAL CHECK(draw_odds > 1.0),
                    away_odds REAL CHECK(away_odds > 1.0),
                    over_25_odds REAL CHECK(over_25_odds > 1.0),
                    under_25_odds REAL CHECK(under_25_odds > 1.0),
                    
                    home_score INTEGER,
                    away_score INTEGER,
                    result TEXT CHECK(result IN ('H', 'D', 'A')),
                    total_goals INTEGER,
                    over_25_result BOOLEAN,
                    
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                    data_quality_score REAL DEFAULT 1.0
                )
            ''')
            
            # Créer des index
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_odds ON matches(home_odds, draw_odds, away_odds, over_25_odds, under_25_odds)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_league ON matches(league_name)')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            st.error(f"Erreur d'initialisation de la base: {e}")
    
    def save_match(self, match_data: Dict[str, Any]) -> bool:
        """Sauvegarde un match"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO matches (
                    event_id, league_name, home_team, away_team, start_time,
                    home_odds, draw_odds, away_odds, over_25_odds, under_25_odds,
                    result, last_updated, data_quality_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                match_data.get('event_id'),
                match_data.get('league_name'),
                match_data.get('home_team'),
                match_data.get('away_team'),
                match_data.get('start_time'),
                match_data.get('home_odds'),
                match_data.get('draw_odds'),
                match_data.get('away_odds'),
                match_data.get('over_25_odds'),
                match_data.get('under_25_odds'),
                match_data.get('result'),
                datetime.now().isoformat(),
                1.0
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            st.error(f"Erreur de sauvegarde: {e}")
            return False
    
    def get_matches_with_complete_odds(self, limit: Optional[int] = None) -> pd.DataFrame:
        """Récupère les matchs avec cotes complètes"""
        try:
            query = '''
                SELECT * FROM matches 
                WHERE home_odds IS NOT NULL 
                AND draw_odds IS NOT NULL 
                AND away_odds IS NOT NULL
                AND over_25_odds IS NOT NULL 
                AND under_25_odds IS NOT NULL
                ORDER BY last_updated DESC
            '''
            
            if limit:
                query += f' LIMIT {limit}'
            
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            return df
            
        except Exception as e:
            st.error(f"Erreur de récupération: {e}")
            return pd.DataFrame()
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Statistiques de la base"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM matches')
            total_matches = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM matches 
                WHERE home_odds IS NOT NULL AND draw_odds IS NOT NULL 
                AND away_odds IS NOT NULL AND over_25_odds IS NOT NULL 
                AND under_25_odds IS NOT NULL
            ''')
            matches_with_odds = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM matches WHERE result IS NOT NULL')
            settled_matches = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT league_name) FROM matches WHERE league_name IS NOT NULL')
            total_leagues = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_matches': total_matches,
                'matches_with_odds': matches_with_odds,
                'settled_matches': settled_matches,
                'total_leagues': total_leagues
            }
            
        except Exception as e:
            st.error(f"Erreur stats: {e}")
            return {}

class OddsSimilarityEngine:
    """Moteur de similarité simplifié pour Streamlit Cloud"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.similarity_threshold = Config.SIMILARITY_THRESHOLD
        self.min_matches = Config.MIN_SIMILAR_MATCHES
    
    def calculate_odds_vector(self, odds_data) -> np.ndarray:
        """Convertit les cotes en vecteur"""
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
            raise ValueError(f"Format non supporté: {type(odds_data)}")
    
    def calculate_similarity_cosine(self, vector1: np.ndarray, vector2: np.ndarray) -> float:
        """Similarité cosinus"""
        try:
            similarity = cosine_similarity([vector1], [vector2])[0][0]
            return max(0.0, min(1.0, similarity))
        except:
            return 0.0
    
    def calculate_similarity_euclidean(self, vector1: np.ndarray, vector2: np.ndarray) -> float:
        """Similarité euclidienne"""
        try:
            distance = euclidean(vector1, vector2)
            max_distance = np.sqrt(np.sum((np.maximum(vector1, vector2)) ** 2))
            if max_distance == 0:
                return 1.0
            similarity = 1 - (distance / max_distance)
            return max(0.0, min(1.0, similarity))
        except:
            return 0.0
    
    def calculate_similarity_percentage(self, vector1: np.ndarray, vector2: np.ndarray) -> float:
        """Similarité par pourcentage"""
        try:
            vector1_safe = np.where(vector1 == 0, 0.01, vector1)
            differences = np.abs(vector1 - vector2) / vector1_safe
            median_diff = np.median(differences)
            similarity = 1 - median_diff
            return max(0.0, min(1.0, similarity))
        except:
            return 0.0
    
    def calculate_similarity(self, vector1: np.ndarray, vector2: np.ndarray, method: str = 'cosine') -> float:
        """Calcule la similarité selon la méthode"""
        if method == 'cosine':
            return self.calculate_similarity_cosine(vector1, vector2)
        elif method == 'euclidean':
            return self.calculate_similarity_euclidean(vector1, vector2)
        elif method == 'percentage':
            return self.calculate_similarity_percentage(vector1, vector2)
        else:
            return 0.0
    
    def find_similar_matches(self, target_odds: Dict[str, float], method: str = 'cosine', 
                           threshold: float = None, min_matches: int = None) -> List[Dict[str, Any]]:
        """Trouve les matchs similaires"""
        threshold = threshold or self.similarity_threshold
        min_matches = min_matches or self.min_matches
        
        # Charger les données historiques
        historical_df = self.db_manager.get_matches_with_complete_odds()
        
        if historical_df.empty:
            return []
        
        # Convertir les cotes cibles
        target_vector = self.calculate_odds_vector(target_odds)
        
        # Calculer les similarités
        similarities = []
        
        for idx, row in historical_df.iterrows():
            try:
                historical_vector = self.calculate_odds_vector(row)
                
                if np.any(np.isnan(historical_vector)) or np.any(historical_vector <= 0):
                    continue
                
                similarity_score = self.calculate_similarity(target_vector, historical_vector, method)
                
                if similarity_score > 0:
                    similarities.append({
                        'event_id': row['event_id'],
                        'similarity': similarity_score,
                        'match_data': row.to_dict()
                    })
                    
            except Exception:
                continue
        
        # Trier et filtrer
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        high_similarity = [m for m in similarities if m['similarity'] >= threshold]
        
        if len(high_similarity) < min_matches:
            return similarities[:min_matches]
        else:
            return high_similarity
    
    def analyze_similar_matches(self, similar_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyse les matchs similaires"""
        if not similar_matches:
            return {'error': 'Aucun match similaire trouvé', 'total_matches': 0}
        
        total_matches = len(similar_matches)
        similarities = [m['similarity'] for m in similar_matches]
        
        analysis = {
            'total_matches': total_matches,
            'similarity_stats': {
                'avg_similarity': np.mean(similarities),
                'min_similarity': min(similarities),
                'max_similarity': max(similarities),
                'median_similarity': np.median(similarities)
            }
        }
        
        # Analyser les résultats
        matches_with_results = [m for m in similar_matches if m['match_data'].get('result')]
        
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
        
        return analysis

# Fonctions utilitaires
def format_odds(odds):
    """Formate les cotes"""
    return f"{odds:.2f}" if odds else "-"

def calculate_implied_probability(odds):
    """Calcule la probabilité implicite"""
    return (1 / odds) * 100 if odds and odds > 0 else 0

def load_css():
    """Charge les styles CSS"""
    st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #f0f2f6 0%, #e8eaf0 100%);
        padding: 1.2rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border: 1px solid #ddd;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .similarity-score {
        font-size: 1.3em;
        font-weight: bold;
        color: #1f77b4;
    }
    .match-result {
        font-weight: bold;
        padding: 0.3rem 0.7rem;
        border-radius: 15px;
        color: white;
        display: inline-block;
        margin: 2px;
    }
    .result-H { background: linear-gradient(135deg, #28a745, #20c997); }
    .result-D { background: linear-gradient(135deg, #ffc107, #fd7e14); color: black; }
    .result-A { background: linear-gradient(135deg, #dc3545, #e83e8c); }
    </style>
    """, unsafe_allow_html=True)

# Initialisation de l'application
@st.cache_resource
def init_app():
    """Initialise l'application avec cache"""
    db_manager = DatabaseManager()
    similarity_engine = OddsSimilarityEngine(db_manager)
    validator = ValidationManager()
    
    # Créer des données de test si la base est vide
    stats = db_manager.get_database_stats()
    if stats.get('total_matches', 0) == 0:
        create_sample_data(db_manager)
    
    return db_manager, similarity_engine, validator

def create_sample_data(db_manager: DatabaseManager):
    """Crée des données d'exemple"""
    import random
    
    leagues = ['Premier League', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1']
    teams = [
        ['Arsenal', 'Chelsea', 'Liverpool', 'Man City', 'Man United', 'Tottenham'],
        ['Barcelona', 'Real Madrid', 'Atletico', 'Valencia', 'Sevilla', 'Betis'],
        ['Juventus', 'Milan', 'Inter', 'Napoli', 'Roma', 'Lazio'],
        ['Bayern', 'Dortmund', 'Leipzig', 'Leverkusen', 'Frankfurt', 'Wolfsburg'],
        ['PSG', 'Lyon', 'Marseille', 'Monaco', 'Nice', 'Rennes']
    ]
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(200):
        league_idx = i % len(leagues)
        league_teams = teams[league_idx]
        
        home_team = random.choice(league_teams)
        away_team = random.choice([t for t in league_teams if t != home_team])
        
        match_data = {
            'event_id': 10000 + i,
            'league_name': leagues[league_idx],
            'home_team': home_team,
            'away_team': away_team,
            'start_time': (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat(),
            'home_odds': round(1.5 + random.random() * 3, 2),
            'draw_odds': round(2.8 + random.random() * 1.5, 2),
            'away_odds': round(1.5 + random.random() * 3, 2),
            'over_25_odds': round(1.6 + random.random() * 0.8, 2),
            'under_25_odds': round(1.6 + random.random() * 0.8, 2),
            'result': random.choice(['H', 'D', 'A']) if random.random() > 0.3 else None
        }
        
        db_manager.save_match(match_data)
        
        # Mise à jour de la barre de progression
        progress_bar.progress((i + 1) / 200)
        status_text.text(f'Création des données d\'exemple: {i + 1}/200')
    
    progress_bar.empty()
    status_text.empty()

def main():
    """Fonction principale"""
    load_css()
    
    # Titre principal
    st.title("⚽ Système de Paris Pinnacle - Version Cloud")
    st.markdown("**Analyse intelligente de similarité des cotes sportives**")
    
    # Initialisation
    db_manager, similarity_engine, validator = init_app()
    
    # Sidebar avec paramètres
    st.sidebar.header("⚙️ Paramètres")
    
    similarity_method = st.sidebar.selectbox(
        "Méthode de similarité",
        options=['cosine', 'euclidean', 'percentage'],
        index=0,
        help="Algorithme pour calculer la similarité"
    )
    
    similarity_threshold = st.sidebar.slider(
        "Seuil de similarité (%)",
        min_value=70, max_value=99, value=90, step=1
    ) / 100
    
    min_matches = st.sidebar.number_input(
        "Nombre minimum de matchs",
        min_value=5, max_value=50, value=10
    )
    
    # Statistiques de la base
    with st.sidebar.expander("📊 Statistiques", expanded=False):
        stats = db_manager.get_database_stats()
        st.metric("Total matchs", stats.get('total_matches', 0))
        st.metric("Avec cotes complètes", stats.get('matches_with_odds', 0))
        st.metric("Matchs terminés", stats.get('settled_matches', 0))
        st.metric("Ligues", stats.get('total_leagues', 0))
    
    # Formulaire de saisie des cotes
    st.header("💰 Saisie des Cotes")
    
    # Presets
    presets = {
        "Match équilibré": {"home": 2.10, "draw": 3.40, "away": 3.20, "over_25": 1.85, "under_25": 1.95},
        "Favori domicile": {"home": 1.50, "draw": 4.20, "away": 6.50, "over_25": 1.75, "under_25": 2.05},
        "Match serré": {"home": 1.95, "draw": 3.20, "away": 4.10, "over_25": 2.10, "under_25": 1.75}
    }
    
    preset_choice = st.selectbox("🎯 Utiliser un preset", ["Personnalisé"] + list(presets.keys()))
    
    if preset_choice != "Personnalisé":
        preset_odds = presets[preset_choice]
        st.info(f"Cotes {preset_choice.lower()} chargées")
    else:
        preset_odds = {}
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🏠 Résultat du match (1X2)**")
        home_odds = st.number_input("Victoire Domicile", min_value=1.01, max_value=50.0, 
                                   value=preset_odds.get("home", 2.10), step=0.01)
        draw_odds = st.number_input("Match Nul", min_value=1.01, max_value=50.0, 
                                   value=preset_odds.get("draw", 3.40), step=0.01)
        away_odds = st.number_input("Victoire Extérieur", min_value=1.01, max_value=50.0, 
                                   value=preset_odds.get("away", 3.20), step=0.01)
    
    with col2:
        st.markdown("**⚽ Total de buts (O/U 2.5)**")
        over_25_odds = st.number_input("Plus de 2.5 buts", min_value=1.01, max_value=10.0, 
                                      value=preset_odds.get("over_25", 1.85), step=0.01)
        under_25_odds = st.number_input("Moins de 2.5 buts", min_value=1.01, max_value=10.0, 
                                       value=preset_odds.get("under_25", 1.95), step=0.01)
    
    target_odds = {
        'home': home_odds,
        'draw': draw_odds,
        'away': away_odds,
        'over_25': over_25_odds,
        'under_25': under_25_odds
    }
    
    # Validation
    errors = validator.validate_odds_input(target_odds)
    if errors:
        for error in errors:
            st.error(f"⚠️ {error}")
        return
    
    # Analyse des cotes
    with st.expander("🧮 Analyse des Cotes", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Probabilités 1X2**")
            home_prob = calculate_implied_probability(home_odds)
            draw_prob = calculate_implied_probability(draw_odds)
            away_prob = calculate_implied_probability(away_odds)
            
            st.metric("Domicile", f"{home_prob:.1f}%")
            st.metric("Nul", f"{draw_prob:.1f}%")
            st.metric("Extérieur", f"{away_prob:.1f}%")
        
        with col2:
            st.markdown("**Probabilités O/U 2.5**")
            over_prob = calculate_implied_probability(over_25_odds)
            under_prob = calculate_implied_probability(under_25_odds)
            
            st.metric("Plus 2.5", f"{over_prob:.1f}%")
            st.metric("Moins 2.5", f"{under_prob:.1f}%")
        
        with col3:
            st.markdown("**Cohérence**")
            total_1x2 = home_prob + draw_prob + away_prob
            total_ou = over_prob + under_prob
            
            coherence_1x2 = "✅ Cohérent" if 95 <= total_1x2 <= 125 else "⚠️ Suspect"
            coherence_ou = "✅ Cohérent" if 95 <= total_ou <= 125 else "⚠️ Suspect"
            
            st.metric("1X2", coherence_1x2)
            st.metric("O/U", coherence_ou)
    
    # Bouton d'analyse
    if st.button("🔍 Analyser les matchs similaires", type="primary", use_container_width=True):
        
        with st.spinner("Recherche de matchs similaires..."):
            # Trouver les matchs similaires
            similar_matches = similarity_engine.find_similar_matches(
                target_odds,
                method=similarity_method,
                threshold=similarity_threshold,
                min_matches=min_matches
            )
            
            # Analyser les résultats
            analysis = similarity_engine.analyze_similar_matches(similar_matches)
            
            # Stocker dans session state
            st.session_state.similar_matches = similar_matches
            st.session_state.analysis = analysis
            
            st.success(f"✅ Analyse terminée ! {len(similar_matches)} matchs trouvés")
    
    # Afficher les résultats
    if 'similar_matches' in st.session_state and 'analysis' in st.session_state:
        
        similar_matches = st.session_state.similar_matches
        analysis = st.session_state.analysis
        
        if similar_matches:
            st.header(f"🎯 Résultats de l'Analyse")
            
            # Métriques principales
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📊 Matchs analysés", analysis['total_matches'])
            with col2:
                avg_sim = analysis['similarity_stats']['avg_similarity']
                st.metric("📈 Similarité moyenne", f"{avg_sim:.1%}")
            with col3:
                med_sim = analysis['similarity_stats']['median_similarity']
                st.metric("📊 Similarité médiane", f"{med_sim:.1%}")
            with col4:
                max_sim = analysis['similarity_stats']['max_similarity']
                st.metric("🎯 Similarité max", f"{max_sim:.1%}")
            
            # Onglets pour les résultats
            tab1, tab2, tab3 = st.tabs(["📋 Matchs Similaires", "📊 Analyse Statistique", "📈 Visualisations"])
            
            with tab1:
                # Filtres
                col1, col2 = st.columns(2)
                with col1:
                    min_similarity_filter = st.slider("Similarité minimum", 0.0, 1.0, 0.8, 0.01)
                with col2:
                    show_results_only = st.checkbox("Seulement avec résultats", False)
                
                # Filtrer les matchs
                filtered_matches = [
                    m for m in similar_matches 
                    if m['similarity'] >= min_similarity_filter
                ]
                
                if show_results_only:
                    filtered_matches = [
                        m for m in filtered_matches 
                        if m['match_data'].get('result')
                    ]
                
                # Tableau des matchs
                if filtered_matches:
                    matches_data = []
                    for i, match in enumerate(filtered_matches[:30]):
                        match_data = match['match_data']
                        matches_data.append({
                            '#': i + 1,
                            'Similarité': f"{match['similarity']:.1%}",
                            'Ligue': match_data.get('league_name', 'N/A')[:20],
                            'Domicile': match_data.get('home_team', 'N/A')[:15],
                            'Extérieur': match_data.get('away_team', 'N/A')[:15],
                            '1': format_odds(match_data.get('home_odds')),
                            'X': format_odds(match_data.get('draw_odds')),
                            '2': format_odds(match_data.get('away_odds')),
                            'O2.5': format_odds(match_data.get('over_25_odds')),
                            'U2.5': format_odds(match_data.get('under_25_odds')),
                            'Résultat': match_data.get('result', '-')
                        })
                    
                    df = pd.DataFrame(matches_data)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("Aucun match ne correspond aux filtres")
            
            with tab2:
                # Analyse des résultats
                if 'results_analysis' in analysis:
                    results = analysis['results_analysis']
                    
                    st.markdown("### 🏆 Analyse des Résultats (1X2)")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("🏠 Victoires Domicile", 
                                f"{results['home_wins']['count']} matchs",
                                delta=f"{results['home_wins']['percentage']:.1f}%")
                    with col2:
                        st.metric("🤝 Matchs Nuls", 
                                f"{results['draws']['count']} matchs",
                                delta=f"{results['draws']['percentage']:.1f}%")
                    with col3:
                        st.metric("✈️ Victoires Extérieur", 
                                f"{results['away_wins']['count']} matchs",
                                delta=f"{results['away_wins']['percentage']:.1f}%")
                    
                    # Graphique en secteurs
                    fig = go.Figure(data=[go.Pie(
                        labels=['Domicile', 'Nul', 'Extérieur'],
                        values=[
                            results['home_wins']['percentage'],
                            results['draws']['percentage'],
                            results['away_wins']['percentage']
                        ],
                        hole=0.4,
                        marker_colors=['#28a745', '#ffc107', '#dc3545']
                    )])
                    fig.update_layout(title="Distribution des Résultats", height=400)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Pas de résultats disponibles pour l'analyse")
            
            with tab3:
                # Visualisations
                similarities = [m['similarity'] for m in similar_matches]
                
                # Distribution des similarités
                fig_dist = px.histogram(
                    x=similarities,
                    nbins=15,
                    title="Distribution des Scores de Similarité",
                    labels={'x': 'Score de Similarité', 'y': 'Nombre de Matchs'}
                )
                st.plotly_chart(fig_dist, use_container_width=True)
                
                # Analyse par ligue
                if len(similar_matches) > 5:
                    league_counts = {}
                    for match in similar_matches:
                        league = match['match_data'].get('league_name', 'Inconnue')
                        league_counts[league] = league_counts.get(league, 0) + 1
                    
                    if league_counts:
                        fig_leagues = px.bar(
                            x=list(league_counts.keys()),
                            y=list(league_counts.values()),
                            title="Répartition par Ligue",
                            labels={'x': 'Ligue', 'y': 'Nombre de Matchs'}
                        )
                        st.plotly_chart(fig_leagues, use_container_width=True)
        else:
            st.warning("❌ Aucun match similaire trouvé")
    
    # Footer
    st.markdown("---")
    st.markdown("**Système Pinnacle Betting** - Version Cloud Streamlit - Analyse intelligente des cotes sportives")

if __name__ == "__main__":
    main()