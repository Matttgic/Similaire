import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config
from src.similarity_engine import OddsSimilarityEngine
from src.database_manager import DatabaseManager
from src.data_collector import PinnacleDataCollector
from src.utils import (
    format_odds, format_percentage, validate_odds_input,
    get_market_display_name, export_similar_matches_to_csv,
    calculate_implied_probability, calculate_betting_value
)

# Configuration de la page
st.set_page_config(
    page_title=Config.APP_TITLE,
    page_icon=Config.PAGE_ICON,
    layout=Config.LAYOUT,
    initial_sidebar_state="expanded"
)

def load_css():
    """Charge les styles CSS personnalisés"""
    st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .similarity-score {
        font-size: 1.2em;
        font-weight: bold;
        color: #1f77b4;
    }
    .match-result {
        font-weight: bold;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        color: white;
    }
    .result-H { background-color: #28a745; }
    .result-D { background-color: #ffc107; color: black; }
    .result-A { background-color: #dc3545; }
    </style>
    """, unsafe_allow_html=True)

def init_session_state():
    """Initialise les variables de session"""
    if 'similarity_engine' not in st.session_state:
        st.session_state.similarity_engine = OddsSimilarityEngine()
    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = DatabaseManager()
    if 'data_collector' not in st.session_state:
        st.session_state.data_collector = PinnacleDataCollector()

def display_header():
    """Affiche l'en-tête de l'application"""
    st.title(Config.APP_TITLE)
    st.markdown("""
    Cette application utilise la similarité des cotes pour prédire les résultats de matchs de football 
    basés sur l'historique des matchs avec des cotes similaires de Pinnacle.
    """)

def display_sidebar():
    """Affiche la barre latérale avec les paramètres"""
    st.sidebar.header("⚙️ Paramètres")
    
    # Méthode de similarité
    similarity_method = st.sidebar.selectbox(
        "Méthode de calcul",
        options=Config.SIMILARITY_METHODS,
        index=Config.SIMILARITY_METHODS.index(Config.DEFAULT_SIMILARITY_METHOD),
        help="Méthode utilisée pour calculer la similarité entre les cotes"
    )
    
    # Seuil de similarité
    similarity_threshold = st.sidebar.slider(
        "Seuil de similarité (%)",
        min_value=70,
        max_value=99,
        value=int(Config.SIMILARITY_THRESHOLD * 100),
        step=1,
        help="Pourcentage minimum de similarité requis"
    ) / 100
    
    # Nombre minimum de matchs
    min_matches = st.sidebar.number_input(
        "Nombre minimum de matchs",
        min_value=5,
        max_value=50,
        value=Config.MIN_SIMILAR_MATCHES,
        help="Nombre minimum de matchs similaires à analyser"
    )
    
    return similarity_method, similarity_threshold, min_matches

def display_database_stats():
    """Affiche les statistiques de la base de données"""
    with st.expander("📊 Statistiques de la base de données"):
        stats = st.session_state.db_manager.get_database_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total matchs", stats['total_matches'])
        with col2:
            st.metric("Avec cotes complètes", stats['matches_with_odds'])
        with col3:
            st.metric("Matchs terminés", stats['settled_matches'])
        with col4:
            st.metric("Ligues", stats['total_leagues'])
        
        if stats['date_range']['from'] and stats['date_range']['to']:
            st.info(f"Période couverte: {stats['date_range']['from'][:10]} à {stats['date_range']['to'][:10]}")

def odds_input_form():
    """Formulaire de saisie des cotes"""
    st.subheader("💰 Saisie des cotes")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Résultat du match (1X2)**")
        home_odds = st.number_input("Victoire Domicile", min_value=1.01, max_value=50.0, value=2.10, step=0.01)
        draw_odds = st.number_input("Match Nul", min_value=1.01, max_value=50.0, value=3.40, step=0.01)
        away_odds = st.number_input("Victoire Extérieur", min_value=1.01, max_value=50.0, value=3.20, step=0.01)
    
    with col2:
        st.markdown("**Total de buts (O/U 2.5)**")
        over_25_odds = st.number_input("Plus de 2.5 buts", min_value=1.01, max_value=10.0, value=1.85, step=0.01)
        under_25_odds = st.number_input("Moins de 2.5 buts", min_value=1.01, max_value=10.0, value=1.95, step=0.01)
    
    target_odds = {
        'home': home_odds,
        'draw': draw_odds,
        'away': away_odds,
        'over_25': over_25_odds,
        'under_25': under_25_odds
    }
    
    # Validation des cotes
    errors = validate_odds_input(target_odds)
    if errors:
        for error in errors:
            st.error(error)
        return None
    
    # Afficher les probabilités implicites
    with st.expander("🧮 Probabilités implicites"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Domicile", format_percentage(calculate_implied_probability(home_odds)))
        with col2:
            st.metric("Nul", format_percentage(calculate_implied_probability(draw_odds)))
        with col3:
            st.metric("Extérieur", format_percentage(calculate_implied_probability(away_odds)))
        
        col4, col5 = st.columns(2)
        with col4:
            st.metric("Plus 2.5", format_percentage(calculate_implied_probability(over_25_odds)))
        with col5:
            st.metric("Moins 2.5", format_percentage(calculate_implied_probability(under_25_odds)))
    
    return target_odds

def display_similar_matches(similar_matches):
    """Affiche les matchs similaires trouvés"""
    if not similar_matches:
        st.warning("Aucun match similaire trouvé")
        return
    
    st.subheader(f"🎯 {len(similar_matches)} matchs similaires trouvés")
    
    # Tableau des matchs
    matches_data = []
    for match in similar_matches:
        match_data = match['match_data']
        matches_data.append({
            'Similarité': f"{match['similarity']:.1%}",
            'Ligue': match_data.get('league_name', 'N/A'),
            'Domicile': match_data.get('home_team', 'N/A'),
            'Extérieur': match_data.get('away_team', 'N/A'),
            'Date': match_data.get('start_time', 'N/A')[:10] if match_data.get('start_time') else 'N/A',
            'Cotes 1': format_odds(match_data.get('home_odds')),
            'Cotes X': format_odds(match_data.get('draw_odds')),
            'Cotes 2': format_odds(match_data.get('away_odds')),
            'O 2.5': format_odds(match_data.get('over_25_odds')),
            'U 2.5': format_odds(match_data.get('under_25_odds')),
            'Résultat': match_data.get('result', 'N/A'),
            'Score': f"{match_data.get('home_score', 'N/A')}-{match_data.get('away_score', 'N/A')}"
        })
    
    df = pd.DataFrame(matches_data)
    st.dataframe(df, use_container_width=True)
    
    # Bouton d'export
    if st.button("📥 Exporter en CSV"):
        filename = export_similar_matches_to_csv(similar_matches)
        if filename:
            st.success(f"Fichier exporté: {filename}")

def display_analysis_results(analysis):
    """Affiche les résultats de l'analyse"""
    if 'error' in analysis:
        st.error(analysis['error'])
        return
    
    st.subheader("📈 Analyse des résultats")
    
    # Statistiques générales
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Matchs analysés", analysis['total_matches'])
    with col2:
        st.metric("Similarité moyenne", format_percentage(analysis['similarity_stats']['avg_similarity'] * 100))
    with col3:
        st.metric("Similarité médiane", format_percentage(analysis['similarity_stats']['median_similarity'] * 100))
    
    # Analyse des résultats 1X2
    if 'results_analysis' in analysis:
        st.markdown("### 🏆 Résultats des matchs (1X2)")
        
        results = analysis['results_analysis']
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Victoires Domicile", 
                f"{results['home_wins']['count']} matchs",
                delta=f"{results['home_wins']['percentage']:.1f}%"
            )
        with col2:
            st.metric(
                "Matchs Nuls", 
                f"{results['draws']['count']} matchs",
                delta=f"{results['draws']['percentage']:.1f}%"
            )
        with col3:
            st.metric(
                "Victoires Extérieur", 
                f"{results['away_wins']['count']} matchs",
                delta=f"{results['away_wins']['percentage']:.1f}%"
            )
        
        # Graphique en secteurs pour les résultats
        fig_results = go.Figure(data=[go.Pie(
            labels=['Domicile', 'Nul', 'Extérieur'],
            values=[
                results['home_wins']['percentage'],
                results['draws']['percentage'],
                results['away_wins']['percentage']
            ],
            hole=0.3,
            marker_colors=['#28a745', '#ffc107', '#dc3545']
        )])
        fig_results.update_layout(title="Répartition des résultats")
        st.plotly_chart(fig_results, use_container_width=True)
    
    # Analyse Over/Under
    if 'over_under_analysis' in analysis:
        st.markdown("### ⚽ Analyse Over/Under 2.5 buts")
        
        ou_analysis = analysis['over_under_analysis']
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Plus de 2.5 buts",
                f"{ou_analysis['over_25']['count']} matchs",
                delta=f"{ou_analysis['over_25']['percentage']:.1f}%"
            )
        with col2:
            st.metric(
                "Moins de 2.5 buts",
                f"{ou_analysis['under_25']['count']} matchs", 
                delta=f"{ou_analysis['under_25']['percentage']:.1f}%"
            )
    
    # Analyse BTTS
    if 'btts_analysis' in analysis:
        st.markdown("### 🥅 Analyse Both Teams To Score")
        
        btts_analysis = analysis['btts_analysis']
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "BTTS Oui",
                f"{btts_analysis['btts_yes']['count']} matchs",
                delta=f"{btts_analysis['btts_yes']['percentage']:.1f}%"
            )
        with col2:
            st.metric(
                "BTTS Non",
                f"{btts_analysis['btts_no']['count']} matchs",
                delta=f"{btts_analysis['btts_no']['percentage']:.1f}%"
            )

def display_data_management():
    """Section de gestion des données"""
    with st.expander("🔧 Gestion des données"):
        st.markdown("### Collecte de données")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📡 Collecter données actuelles"):
                with st.spinner("Collecte en cours..."):
                    st.session_state.data_collector.collect_current_markets()
                st.success("Données actuelles collectées!")
                st.rerun()
        
        with col2:
            max_events = st.number_input("Limite d'événements", min_value=100, max_value=5000, value=1000)
            if st.button("📚 Collecter données historiques"):
                with st.spinner("Collecte historique en cours... Cela peut prendre du temps"):
                    st.session_state.data_collector.collect_historical_data(max_events=max_events)
                st.success("Données historiques collectées!")
                st.rerun()
        
        st.markdown("### Maintenance")
        col3, col4 = st.columns(2)
        
        with col3:
            if st.button("🗑️ Vider le cache"):
                st.session_state.db_manager.clear_similarity_cache()
                st.success("Cache vidé!")
        
        with col4:
            if st.button("🔄 Actualiser les stats"):
                st.rerun()

def main():
    """Fonction principale de l'application"""
    load_css()
    init_session_state()
    display_header()
    
    # Barre latérale avec paramètres
    similarity_method, similarity_threshold, min_matches = display_sidebar()
    
    # Statistiques de la base
    display_database_stats()
    
    # Formulaire de saisie des cotes
    target_odds = odds_input_form()
    
    if target_odds is not None:
        if st.button("🔍 Analyser les matchs similaires", type="primary"):
            with st.spinner("Recherche de matchs similaires..."):
                # Trouver les matchs similaires
                similar_matches = st.session_state.similarity_engine.find_similar_matches(
                    target_odds,
                    method=similarity_method,
                    threshold=similarity_threshold,
                    min_matches=min_matches
                )
                
                # Analyser les résultats
                analysis = st.session_state.similarity_engine.analyze_similar_matches(similar_matches)
                
                # Stocker dans la session
                st.session_state.similar_matches = similar_matches
                st.session_state.analysis = analysis
        
        # Afficher les résultats s'ils existent
        if hasattr(st.session_state, 'similar_matches') and hasattr(st.session_state, 'analysis'):
            display_similar_matches(st.session_state.similar_matches)
            display_analysis_results(st.session_state.analysis)
    
    # Section de gestion des données
    display_data_management()

if __name__ == "__main__":
    main()
