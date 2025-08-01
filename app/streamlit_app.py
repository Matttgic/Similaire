import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os
import time
import json

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config
from src.similarity_engine import OddsSimilarityEngine
from src.database_manager import DatabaseManager
from src.data_collector import PinnacleDataCollector
from src.logger import get_logger, PinnacleLogger
from src.error_handler import ValidationManager
from src.monitoring import get_metrics_collector, get_performance_monitor
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

# Initialiser le système de logging
logger = get_logger('streamlit')
validator = ValidationManager()
metrics = get_metrics_collector()
monitor = get_performance_monitor()

def load_css():
    """Charge les styles CSS personnalisés améliorés"""
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
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
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
    .stats-container {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .quality-badge {
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: bold;
    }
    .quality-high { background: #d4edda; color: #155724; }
    .quality-medium { background: #fff3cd; color: #856404; }
    .quality-low { background: #f8d7da; color: #721c24; }
    .alert-warning {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .alert-success {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .performance-metric {
        background: white;
        border-radius: 8px;
        padding: 0.8rem;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }
    </style>
    """, unsafe_allow_html=True)

def init_session_state():
    """Initialise les variables de session avec gestion d'erreurs"""
    try:
        if 'similarity_engine' not in st.session_state:
            st.session_state.similarity_engine = OddsSimilarityEngine()
            logger.info("Similarity engine initialized")
        
        if 'db_manager' not in st.session_state:
            st.session_state.db_manager = DatabaseManager()
            logger.info("Database manager initialized")
        
        if 'data_collector' not in st.session_state:
            st.session_state.data_collector = PinnacleDataCollector()
            logger.info("Data collector initialized")
        
        if 'validator' not in st.session_state:
            st.session_state.validator = validator
        
        if 'last_analysis_time' not in st.session_state:
            st.session_state.last_analysis_time = None
        
        return True
        
    except Exception as e:
        st.error(f"Erreur d'initialisation: {e}")
        logger.error(f"Session state initialization failed: {e}")
        return False

def display_header():
    """Affiche l'en-tête amélioré de l'application"""
    col1, col2, col3 = st.columns([2, 3, 1])
    
    with col1:
        st.title(Config.APP_TITLE)
    
    with col2:
        st.markdown("""
        **Version 2.0** - Système intelligent d'analyse de paris sportifs basé sur la similarité 
        des cotes historiques de Pinnacle avec ML avancé et monitoring en temps réel.
        """)
    
    with col3:
        # Badge de statut système
        health_status = monitor.check_system_health()
        status_color = {
            'healthy': '🟢',
            'degraded': '🟡', 
            'critical': '🔴',
            'unknown': '⚪'
        }.get(health_status['status'], '⚪')
        
        st.markdown(f"**Statut:** {status_color} {health_status['status'].title()}")

def display_sidebar():
    """Affiche la barre latérale avec paramètres avancés"""
    st.sidebar.header("⚙️ Paramètres d'Analyse")
    
    # Méthode de similarité avec descriptions
    method_descriptions = {
        'cosine': 'Cosinus - Mesure l\'angle entre vecteurs',
        'euclidean': 'Euclidienne - Distance géométrique',
        'percentage': 'Pourcentage - Différence relative'
    }
    
    similarity_method = st.sidebar.selectbox(
        "Méthode de calcul",
        options=list(method_descriptions.keys()),
        index=list(method_descriptions.keys()).index(Config.DEFAULT_SIMILARITY_METHOD),
        format_func=lambda x: method_descriptions[x],
        help="Algorithme utilisé pour calculer la similarité entre les cotes"
    )
    
    # Paramètres avancés dans un expander
    with st.sidebar.expander("🔧 Paramètres Avancés", expanded=False):
        similarity_threshold = st.slider(
            "Seuil de similarité (%)",
            min_value=70,
            max_value=99,
            value=int(Config.SIMILARITY_THRESHOLD * 100),
            step=1,
            help="Pourcentage minimum de similarité requis"
        ) / 100
        
        min_matches = st.number_input(
            "Nombre minimum de matchs",
            min_value=5,
            max_value=100,
            value=Config.MIN_SIMILAR_MATCHES,
            help="Nombre minimum de matchs similaires à analyser"
        )
        
        quality_threshold = st.slider(
            "Seuil de qualité des données",
            min_value=0.1,
            max_value=1.0,
            value=0.5,
            step=0.1,
            help="Score minimum de qualité des données (0-1)"
        )
    
    # Section monitoring
    st.sidebar.header("📊 Monitoring")
    
    if st.sidebar.button("🔄 Actualiser Métriques"):
        st.session_state.refresh_metrics = True
    
    # Afficher métriques système basiques
    try:
        system_metrics = metrics.get_system_metrics()
        if system_metrics:
            st.sidebar.metric("CPU", f"{system_metrics.get('cpu', {}).get('percent', 0):.1f}%")
            st.sidebar.metric("Mémoire", f"{system_metrics.get('memory', {}).get('percent', 0):.1f}%")
    except Exception as e:
        logger.debug(f"Could not display system metrics: {e}")
    
    return similarity_method, similarity_threshold, min_matches, quality_threshold

def display_database_stats():
    """Affiche les statistiques détaillées de la base de données"""
    with st.expander("📊 Statistiques de la Base de Données", expanded=False):
        try:
            stats = st.session_state.db_manager.get_database_stats()
            
            # Métriques principales
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total matchs", stats.get('total_matches', 0))
            with col2:
                st.metric("Avec cotes complètes", stats.get('matches_with_odds', 0))
            with col3:
                st.metric("Matchs terminés", stats.get('settled_matches', 0))
            with col4:
                st.metric("Ligues", stats.get('total_leagues', 0))
            
            # Qualité des données
            if 'quality_distribution' in stats:
                st.markdown("### 📈 Distribution de la Qualité des Données")
                quality_data = stats['quality_distribution']
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(
                        f'<div class="quality-badge quality-high">Haute: {quality_data.get("high_quality", 0)}</div>',
                        unsafe_allow_html=True
                    )
                with col2:
                    st.markdown(
                        f'<div class="quality-badge quality-medium">Moyenne: {quality_data.get("medium_quality", 0)}</div>',
                        unsafe_allow_html=True
                    )
                with col3:
                    st.markdown(
                        f'<div class="quality-badge quality-low">Faible: {quality_data.get("low_quality", 0)}</div>',
                        unsafe_allow_html=True
                    )
            
            # Période couverte
            date_range = stats.get('date_range', {})
            if date_range.get('from') and date_range.get('to'):
                st.info(f"📅 Période: {date_range['from'][:10]} → {date_range['to'][:10]}")
            
            # Top ligues
            if 'top_leagues' in stats and stats['top_leagues']:
                st.markdown("### 🏆 Top Ligues")
                top_leagues_df = pd.DataFrame(stats['top_leagues'])
                st.dataframe(top_leagues_df, use_container_width=True)
                
        except Exception as e:
            st.error(f"Erreur lors du chargement des statistiques: {e}")
            logger.error(f"Failed to load database stats: {e}")

def odds_input_form():
    """Formulaire de saisie des cotes avec validation en temps réel"""
    st.subheader("💰 Saisie des Cotes")
    
    # Options prédéfinies
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
        home_odds = st.number_input(
            "Victoire Domicile", 
            min_value=1.01, 
            max_value=50.0, 
            value=preset_odds.get("home", 2.10), 
            step=0.01,
            help="Cote pour la victoire de l'équipe à domicile"
        )
        draw_odds = st.number_input(
            "Match Nul", 
            min_value=1.01, 
            max_value=50.0, 
            value=preset_odds.get("draw", 3.40), 
            step=0.01,
            help="Cote pour le match nul"
        )
        away_odds = st.number_input(
            "Victoire Extérieur", 
            min_value=1.01, 
            max_value=50.0, 
            value=preset_odds.get("away", 3.20), 
            step=0.01,
            help="Cote pour la victoire de l'équipe à l'extérieur"
        )
    
    with col2:
        st.markdown("**⚽ Total de buts (O/U 2.5)**")
        over_25_odds = st.number_input(
            "Plus de 2.5 buts", 
            min_value=1.01, 
            max_value=10.0, 
            value=preset_odds.get("over_25", 1.85), 
            step=0.01,
            help="Cote pour plus de 2.5 buts dans le match"
        )
        under_25_odds = st.number_input(
            "Moins de 2.5 buts", 
            min_value=1.01, 
            max_value=10.0, 
            value=preset_odds.get("under_25", 1.95), 
            step=0.01,
            help="Cote pour moins de 2.5 buts dans le match"
        )
    
    target_odds = {
        'home': home_odds,
        'draw': draw_odds,
        'away': away_odds,
        'over_25': over_25_odds,
        'under_25': under_25_odds
    }
    
    # Validation en temps réel
    errors = st.session_state.validator.validate_odds_input(target_odds)
    if errors:
        for error in errors:
            st.error(f"⚠️ {error}")
        return None
    
    # Afficher les probabilités implicites et analyses
    with st.expander("🧮 Analyse des Cotes", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        # Probabilités 1X2
        home_prob = calculate_implied_probability(home_odds)
        draw_prob = calculate_implied_probability(draw_odds)
        away_prob = calculate_implied_probability(away_odds)
        total_prob_1x2 = home_prob + draw_prob + away_prob
        
        with col1:
            st.markdown("**Probabilités 1X2**")
            st.metric("Domicile", f"{home_prob:.1f}%")
            st.metric("Nul", f"{draw_prob:.1f}%")
            st.metric("Extérieur", f"{away_prob:.1f}%")
            
            # Marge du bookmaker
            margin_1x2 = total_prob_1x2 - 100
            st.metric("Marge bookmaker", f"{margin_1x2:.1f}%")
        
        # Probabilités O/U
        over_prob = calculate_implied_probability(over_25_odds)
        under_prob = calculate_implied_probability(under_25_odds)
        total_prob_ou = over_prob + under_prob
        
        with col2:
            st.markdown("**Probabilités O/U 2.5**")
            st.metric("Plus 2.5", f"{over_prob:.1f}%")
            st.metric("Moins 2.5", f"{under_prob:.1f}%")
            
            margin_ou = total_prob_ou - 100
            st.metric("Marge bookmaker", f"{margin_ou:.1f}%")
        
        # Analyse de cohérence
        with col3:
            st.markdown("**Analyse de Cohérence**")
            
            coherence_1x2 = "✅ Cohérent" if 95 <= total_prob_1x2 <= 125 else "⚠️ Suspect"
            coherence_ou = "✅ Cohérent" if 95 <= total_prob_ou <= 125 else "⚠️ Suspect"
            
            st.metric("1X2", coherence_1x2)
            st.metric("O/U", coherence_ou)
            
            # Score de qualité global
            quality_score = 100 - (abs(margin_1x2) + abs(margin_ou)) / 2
            st.metric("Score qualité", f"{max(0, quality_score):.0f}/100")
    
    return target_odds

def display_similar_matches(similar_matches, analysis):
    """Affiche les matchs similaires avec analyse avancée"""
    if not similar_matches:
        st.warning("❌ Aucun match similaire trouvé")
        return
    
    st.subheader(f"🎯 {len(similar_matches)} matchs similaires trouvés")
    
    # Onglets pour différentes vues
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Matchs", "📊 Analyse", "📈 Visualisations", "⚡ Actions"])
    
    with tab1:
        # Filtres
        col1, col2, col3 = st.columns(3)
        with col1:
            min_similarity = st.slider("Similarité minimum", 0.0, 1.0, 0.8, 0.01)
        with col2:
            league_filter = st.selectbox(
                "Filtrer par ligue",
                ["Toutes"] + list(set([m['match_data'].get('league_name', 'N/A') for m in similar_matches]))
            )
        with col3:
            show_results_only = st.checkbox("Seulement les matchs avec résultats", False)
        
        # Filtrer les matchs
        filtered_matches = similar_matches
        if min_similarity > 0:
            filtered_matches = [m for m in filtered_matches if m['similarity'] >= min_similarity]
        if league_filter != "Toutes":
            filtered_matches = [m for m in filtered_matches if m['match_data'].get('league_name') == league_filter]
        if show_results_only:
            filtered_matches = [m for m in filtered_matches if m['match_data'].get('result')]
        
        # Tableau des matchs
        matches_data = []
        for i, match in enumerate(filtered_matches[:50]):  # Limiter à 50 pour les performances
            match_data = match['match_data']
            matches_data.append({
                '#': i + 1,
                'Similarité': f"{match['similarity']:.1%}",
                'Ligue': match_data.get('league_name', 'N/A')[:30],
                'Domicile': match_data.get('home_team', 'N/A')[:20],
                'Extérieur': match_data.get('away_team', 'N/A')[:20],
                'Date': match_data.get('start_time', 'N/A')[:10] if match_data.get('start_time') else 'N/A',
                '1': format_odds(match_data.get('home_odds')),
                'X': format_odds(match_data.get('draw_odds')),
                '2': format_odds(match_data.get('away_odds')),
                'O2.5': format_odds(match_data.get('over_25_odds')),
                'U2.5': format_odds(match_data.get('under_25_odds')),
                'Résultat': match_data.get('result', '-'),
                'Score': f"{match_data.get('home_score', '-')}-{match_data.get('away_score', '-')}" if match_data.get('home_score') is not None else '-'
            })
        
        if matches_data:
            df = pd.DataFrame(matches_data)
            st.dataframe(df, use_container_width=True)
            st.caption(f"Affichage de {len(matches_data)} matchs sur {len(similar_matches)} trouvés")
        else:
            st.info("Aucun match ne correspond aux filtres sélectionnés")
    
    with tab2:
        display_analysis_results(analysis)
    
    with tab3:
        display_analysis_visualizations(similar_matches, analysis)
    
    with tab4:
        # Actions sur les données
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Exporter en CSV"):
                try:
                    filename = export_similar_matches_to_csv(filtered_matches)
                    if filename:
                        st.success(f"✅ Fichier exporté: {filename}")
                        logger.info(f"CSV export successful: {filename}")
                except Exception as e:
                    st.error(f"❌ Erreur d'export: {e}")
                    logger.error(f"CSV export failed: {e}")
        
        with col2:
            if st.button("🔄 Rafraîchir l'analyse"):
                st.session_state.refresh_analysis = True
                st.experimental_rerun()
        
        with col3:
            if st.button("📊 Comparer les méthodes"):
                st.session_state.show_method_comparison = True

def display_analysis_results(analysis):
    """Affiche les résultats d'analyse avec métriques avancées"""
    if 'error' in analysis:
        st.error(f"❌ {analysis['error']}")
        return
    
    # Statistiques générales
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Matchs analysés", analysis['total_matches'])
    with col2:
        avg_sim = analysis['similarity_stats']['avg_similarity']
        st.metric("📈 Similarité moyenne", f"{avg_sim:.1%}")
    with col3:
        med_sim = analysis['similarity_stats']['median_similarity']
        st.metric("📊 Similarité médiane", f"{med_sim:.1%}")
    
    # Analyse des résultats 1X2
    if 'results_analysis' in analysis:
        st.markdown("### 🏆 Analyse des Résultats (1X2)")
        
        results = analysis['results_analysis']
        coverage = results.get('coverage', 0)
        
        if coverage > 0:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "🏠 Victoires Domicile", 
                    f"{results['home_wins']['count']} matchs",
                    delta=f"{results['home_wins']['percentage']:.1f}%"
                )
            with col2:
                st.metric(
                    "🤝 Matchs Nuls", 
                    f"{results['draws']['count']} matchs",
                    delta=f"{results['draws']['percentage']:.1f}%"
                )
            with col3:
                st.metric(
                    "✈️ Victoires Extérieur", 
                    f"{results['away_wins']['count']} matchs",
                    delta=f"{results['away_wins']['percentage']:.1f}%"
                )
            with col4:
                confidence = results.get('confidence_score', 0)
                confidence_level = "Élevé" if confidence > 80 else "Moyen" if confidence > 50 else "Faible"
                st.metric("🎯 Confiance", f"{confidence:.0f}%", delta=confidence_level)
            
            # Graphique en secteurs
            fig_results = go.Figure(data=[go.Pie(
                labels=['Domicile', 'Nul', 'Extérieur'],
                values=[
                    results['home_wins']['percentage'],
                    results['draws']['percentage'],
                    results['away_wins']['percentage']
                ],
                hole=0.4,
                marker_colors=['#28a745', '#ffc107', '#dc3545'],
                textinfo='label+percent',
                textfont_size=12
            )])
            fig_results.update_layout(
                title="Distribution des Résultats",
                font=dict(size=14),
                height=400
            )
            st.plotly_chart(fig_results, use_container_width=True)
        else:
            st.info("ℹ️ Pas de résultats disponibles pour l'analyse 1X2")
    
    # Analyse Over/Under
    if 'over_under_analysis' in analysis:
        st.markdown("### ⚽ Analyse Over/Under 2.5 buts")
        
        ou_analysis = analysis['over_under_analysis']
        coverage = ou_analysis.get('coverage', 0)
        
        if coverage > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "📈 Plus de 2.5 buts",
                    f"{ou_analysis['over_25']['count']} matchs",
                    delta=f"{ou_analysis['over_25']['percentage']:.1f}%"
                )
            with col2:
                st.metric(
                    "📉 Moins de 2.5 buts",
                    f"{ou_analysis['under_25']['count']} matchs", 
                    delta=f"{ou_analysis['under_25']['percentage']:.1f}%"
                )
        else:
            st.info("ℹ️ Pas de données Over/Under disponibles")
    
    # Analyse BTTS
    if 'btts_analysis' in analysis:
        st.markdown("### 🥅 Analyse Both Teams To Score")
        
        btts_analysis = analysis['btts_analysis']
        coverage = btts_analysis.get('coverage', 0)
        
        if coverage > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "✅ BTTS Oui",
                    f"{btts_analysis['btts_yes']['count']} matchs",
                    delta=f"{btts_analysis['btts_yes']['percentage']:.1f}%"
                )
            with col2:
                st.metric(
                    "❌ BTTS Non",
                    f"{btts_analysis['btts_no']['count']} matchs",
                    delta=f"{btts_analysis['btts_no']['percentage']:.1f}%"
                )
        else:
            st.info("ℹ️ Pas de données BTTS disponibles")

def display_analysis_visualizations(similar_matches, analysis):
    """Affiche des visualisations avancées des résultats"""
    
    # Distribution de similarité
    similarities = [m['similarity'] for m in similar_matches]
    
    fig_dist = px.histogram(
        x=similarities,
        nbins=20,
        title="Distribution des Scores de Similarité",
        labels={'x': 'Score de Similarité', 'y': 'Nombre de Matchs'},
        color_discrete_sequence=['#1f77b4']
    )
    fig_dist.update_layout(height=400)
    st.plotly_chart(fig_dist, use_container_width=True)
    
    # Timeline des matchs similaires
    if similar_matches:
        matches_with_dates = [
            m for m in similar_matches 
            if m['match_data'].get('start_time')
        ]
        
        if matches_with_dates:
            dates = []
            similarities = []
            teams = []
            
            for match in matches_with_dates[:50]:  # Limiter pour les performances
                try:
                    date_str = match['match_data']['start_time'][:10]
                    dates.append(date_str)
                    similarities.append(match['similarity'])
                    home = match['match_data'].get('home_team', 'N/A')[:15]
                    away = match['match_data'].get('away_team', 'N/A')[:15]
                    teams.append(f"{home} vs {away}")
                except Exception:
                    continue
            
            if dates:
                fig_timeline = px.scatter(
                    x=dates,
                    y=similarities,
                    title="Timeline des Matchs Similaires",
                    labels={'x': 'Date', 'y': 'Similarité'},
                    hover_data={'text': teams} if teams else None
                )
                fig_timeline.update_layout(height=400)
                st.plotly_chart(fig_timeline, use_container_width=True)
    
    # Analyse par ligue
    if len(similar_matches) > 5:
        league_data = {}
        for match in similar_matches:
            league = match['match_data'].get('league_name', 'Inconnue')
            if league not in league_data:
                league_data[league] = {'count': 0, 'avg_similarity': 0, 'similarities': []}
            league_data[league]['count'] += 1
            league_data[league]['similarities'].append(match['similarity'])
        
        # Calculer les moyennes
        for league in league_data:
            league_data[league]['avg_similarity'] = sum(league_data[league]['similarities']) / len(league_data[league]['similarities'])
        
        # Créer le graphique
        leagues = list(league_data.keys())[:10]  # Top 10
        counts = [league_data[l]['count'] for l in leagues]
        avg_sims = [league_data[l]['avg_similarity'] for l in leagues]
        
        fig_leagues = go.Figure()
        fig_leagues.add_trace(go.Bar(
            x=leagues,
            y=counts,
            name='Nombre de matchs',
            yaxis='y',
            marker_color='lightblue'
        ))
        fig_leagues.add_trace(go.Scatter(
            x=leagues,
            y=avg_sims,
            mode='lines+markers',
            name='Similarité moyenne',
            yaxis='y2',
            line=dict(color='red', width=3)
        ))
        
        fig_leagues.update_layout(
            title="Analyse par Ligue",
            xaxis_title="Ligue",
            yaxis=dict(title="Nombre de matchs", side="left"),
            yaxis2=dict(title="Similarité moyenne", side="right", overlaying="y"),
            height=400
        )
        st.plotly_chart(fig_leagues, use_container_width=True)

def display_performance_monitoring():
    """Affiche les métriques de performance et monitoring"""
    with st.expander("🔧 Monitoring & Performance", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Métriques Système")
            try:
                system_metrics = metrics.get_system_metrics()
                if system_metrics:
                    # CPU
                    cpu_percent = system_metrics.get('cpu', {}).get('percent', 0)
                    st.metric("CPU", f"{cpu_percent:.1f}%")
                    
                    # Mémoire
                    memory = system_metrics.get('memory', {})
                    memory_percent = memory.get('percent', 0)
                    memory_used_gb = memory.get('used', 0) / (1024**3)
                    st.metric("Mémoire", f"{memory_percent:.1f}%", delta=f"{memory_used_gb:.1f} GB")
                    
                    # Uptime
                    uptime = system_metrics.get('uptime', 0)
                    uptime_hours = uptime / 3600
                    st.metric("Uptime", f"{uptime_hours:.1f}h")
            except Exception as e:
                st.error(f"Erreur métriques système: {e}")
        
        with col2:
            st.markdown("#### ⚡ Métriques Application")
            try:
                app_metrics = metrics.get_application_metrics()
                
                # Cache hit rate
                cache_stats = st.session_state.similarity_engine.get_engine_stats()
                hit_rate = cache_stats.get('cache_hit_rate', 0)
                st.metric("Cache Hit Rate", f"{hit_rate:.1f}%")
                
                # Taille du buffer de métriques
                buffer_size = app_metrics.get('metrics_buffer_size', 0)
                st.metric("Buffer Métriques", buffer_size)
                
                # Timers actifs
                active_timers = app_metrics.get('active_timers', 0)
                st.metric("Timers Actifs", active_timers)
                
            except Exception as e:
                st.error(f"Erreur métriques app: {e}")
        
        # Alertes système
        try:
            health_status = monitor.check_system_health()
            if health_status.get('alerts'):
                st.markdown("#### 🚨 Alertes")
                for alert in health_status['alerts'][:5]:  # Top 5
                    alert_type = alert.get('type', 'Unknown')
                    alert_value = alert.get('value', 'N/A')
                    st.warning(f"⚠️ {alert_type}: {alert_value}")
        except Exception as e:
            logger.debug(f"Could not display alerts: {e}")

def display_data_management():
    """Section de gestion des données améliorée"""
    with st.expander("🔧 Gestion des Données", expanded=False):
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📡 Collecte de Données")
            
            if st.button("📊 Collecter données actuelles", use_container_width=True):
                with st.spinner("Collecte en cours..."):
                    try:
                        result = st.session_state.data_collector.collect_current_markets()
                        if result:
                            st.success(f"✅ {result.get('collected', 0)} matchs collectés, {result.get('errors', 0)} erreurs")
                        else:
                            st.warning("⚠️ Aucune donnée collectée")
                    except Exception as e:
                        st.error(f"❌ Erreur de collecte: {e}")
                        logger.error(f"Current market collection failed: {e}")
            
            max_events = st.number_input("Limite d'événements", min_value=100, max_value=5000, value=1000)
            if st.button("📚 Collecter données historiques", use_container_width=True):
                with st.spinner("Collecte historique... Cela peut prendre du temps"):
                    try:
                        result = st.session_state.data_collector.collect_historical_data(max_events=max_events)
                        if result:
                            st.success(f"✅ {result.get('collected', 0)} matchs collectés, {result.get('errors', 0)} erreurs")
                        else:
                            st.warning("⚠️ Aucune donnée collectée")
                    except Exception as e:
                        st.error(f"❌ Erreur de collecte historique: {e}")
                        logger.error(f"Historical data collection failed: {e}")
        
        with col2:
            st.markdown("#### 🛠️ Maintenance")
            
            if st.button("🗑️ Vider le cache", use_container_width=True):
                try:
                    deleted_count = st.session_state.db_manager.clear_similarity_cache()
                    st.session_state.similarity_engine.clear_cache()
                    st.success(f"✅ Cache vidé! {deleted_count} entrées supprimées")
                except Exception as e:
                    st.error(f"❌ Erreur: {e}")
            
            if st.button("⚡ Optimiser la base", use_container_width=True):
                with st.spinner("Optimisation en cours..."):
                    try:
                        result = st.session_state.db_manager.optimize_database()
                        if 'error' not in result:
                            space_saved = result.get('space_saved_mb', 0)
                            st.success(f"✅ Optimisation terminée! {space_saved:.1f} MB économisés")
                        else:
                            st.error(f"❌ Erreur: {result['error']}")
                    except Exception as e:
                        st.error(f"❌ Erreur d'optimisation: {e}")
            
            if st.button("🔄 Actualiser les stats", use_container_width=True):
                st.experimental_rerun()

def main():
    """Fonction principale de l'application améliorée"""
    # Initialiser le CSS
    load_css()
    
    # Initialiser les composants
    if not init_session_state():
        st.stop()
    
    # En-tête
    display_header()
    
    # Monitoring en arrière-plan
    metrics.set_gauge("streamlit.active_users", 1)
    
    # Barre latérale avec paramètres
    similarity_method, similarity_threshold, min_matches, quality_threshold = display_sidebar()
    
    # Monitoring des performances
    display_performance_monitoring()
    
    # Statistiques de la base
    display_database_stats()
    
    # Formulaire de saisie des cotes
    target_odds = odds_input_form()
    
    if target_odds is not None:
        # Bouton d'analyse principal
        if st.button("🔍 Analyser les matchs similaires", type="primary", use_container_width=True):
            
            # Métriques de performance
            analysis_start_time = time.time()
            
            with st.spinner("Recherche de matchs similaires..."):
                try:
                    # Log de l'action utilisateur
                    logger.info(f"Starting similarity analysis with method={similarity_method}, threshold={similarity_threshold}")
                    
                    # Trouver les matchs similaires
                    similar_matches = st.session_state.similarity_engine.find_similar_matches(
                        target_odds,
                        method=similarity_method,
                        threshold=similarity_threshold,
                        min_matches=min_matches
                    )
                    
                    # Analyser les résultats
                    analysis = st.session_state.similarity_engine.analyze_similar_matches(similar_matches)
                    
                    # Enregistrer les métriques
                    analysis_time = time.time() - analysis_start_time
                    metrics.record_histogram("analysis.duration", analysis_time, unit="seconds")
                    metrics.increment_counter("analysis.completed")
                    
                    # Stocker dans la session
                    st.session_state.similar_matches = similar_matches
                    st.session_state.analysis = analysis
                    st.session_state.last_analysis_time = datetime.now()
                    
                    st.success(f"✅ Analyse terminée en {analysis_time:.2f}s")
                    
                except Exception as e:
                    metrics.increment_counter("analysis.failed")
                    st.error(f"❌ Erreur lors de l'analyse: {e}")
                    logger.error(f"Similarity analysis failed: {e}")
        
        # Afficher les résultats s'ils existent
        if hasattr(st.session_state, 'similar_matches') and hasattr(st.session_state, 'analysis'):
            # Afficher le timestamp de la dernière analyse
            if st.session_state.last_analysis_time:
                st.caption(f"Dernière analyse: {st.session_state.last_analysis_time.strftime('%H:%M:%S')}")
            
            display_similar_matches(st.session_state.similar_matches, st.session_state.analysis)
        
        # Comparaison de méthodes si demandée
        if getattr(st.session_state, 'show_method_comparison', False):
            with st.expander("🔬 Comparaison des Méthodes", expanded=True):
                with st.spinner("Comparaison des méthodes en cours..."):
                    try:
                        comparison = st.session_state.similarity_engine.get_method_comparison(target_odds)
                        
                        for method, result in comparison.items():
                            if 'error' not in result:
                                st.markdown(f"**{method.title()}**")
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Matchs trouvés", result.get('total_matches', 0))
                                with col2:
                                    avg_sim = result.get('similarity_stats', {}).get('avg_similarity', 0)
                                    st.metric("Similarité moy.", f"{avg_sim:.1%}")
                                with col3:
                                    if 'results_analysis' in result:
                                        confidence = result['results_analysis'].get('confidence_score', 0)
                                        st.metric("Confiance", f"{confidence:.0f}%")
                        
                        st.session_state.show_method_comparison = False
                        
                    except Exception as e:
                        st.error(f"❌ Erreur de comparaison: {e}")
    
    # Section de gestion des données
    display_data_management()
    
    # Footer avec informations
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Version 2.0** - Système avancé avec ML et monitoring")
    with col2:
        if hasattr(st.session_state, 'db_manager'):
            try:
                stats = st.session_state.db_manager.get_database_stats()
                st.markdown(f"**Base:** {stats.get('total_matches', 0)} matchs")
            except:
                pass
    with col3:
        st.markdown(f"**Uptime:** {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()