import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.utils import format_odds, format_percentage, export_similar_matches_to_csv

def render_similar_matches_table(similar_matches):
    """Affiche le tableau des matchs similaires"""
    if not similar_matches:
        st.warning("Aucun match similaire trouvé")
        return
    
    st.subheader(f"🎯 {len(similar_matches)} matchs similaires trouvés")
    
    # Options d'affichage
    col1, col2, col3 = st.columns(3)
    with col1:
        show_detailed = st.checkbox("Affichage détaillé", value=True)
    with col2:
        max_display = st.selectbox("Nombre à afficher", [10, 25, 50, 100], index=1)
    with col3:
        sort_by = st.selectbox("Trier par", ["Similarité", "Date", "Ligue"])
    
    # Préparer les données
    matches_data = []
    display_matches = similar_matches[:max_display]
    
    for match in display_matches:
        match_data = match['match_data']
        row = {
            'Similarité': f"{match['similarity']:.1%}",
            'Ligue': match_data.get('league_name', 'N/A')[:30] + "..." if len(match_data.get('league_name', '')) > 30 else match_data.get('league_name', 'N/A'),
            'Domicile': match_data.get('home_team', 'N/A'),
            'Extérieur': match_data.get('away_team', 'N/A'),
            'Date': match_data.get('start_time', 'N/A')[:10] if match_data.get('start_time') else 'N/A',
        }
        
        if show_detailed:
            row.update({
                'Cotes 1': format_odds(match_data.get('home_odds')),
                'Cotes X': format_odds(match_data.get('draw_odds')),
                'Cotes 2': format_odds(match_data.get('away_odds')),
                'O 2.5': format_odds(match_data.get('over_25_odds')),
                'U 2.5': format_odds(match_data.get('under_25_odds')),
            })
        
        # Résultats si disponibles
        result = match_data.get('result', 'N/A')
        if result != 'N/A':
            row['Résultat'] = result
            score_home = match_data.get('home_score', 'N/A')
            score_away = match_data.get('away_score', 'N/A')
            row['Score'] = f"{score_home}-{score_away}"
        
        matches_data.append(row)
    
    # Trier selon le choix
    if sort_by == "Date":
        matches_data.sort(key=lambda x: x['Date'], reverse=True)
    elif sort_by == "Ligue":
        matches_data.sort(key=lambda x: x['Ligue'])
    # "Similarité" est déjà trié par défaut
    
    df = pd.DataFrame(matches_data)
    
    # Colorer selon la similarité
    def color_similarity(val):
        if '%' in val:
            percent = float(val.replace('%', ''))
            if percent >= 95:
                return 'background-color: #d4edda'
            elif percent >= 90:
                return 'background-color: #fff3cd'
            else:
                return 'background-color: #f8d7da'
        return ''
    
    # Afficher le tableau avec style
    styled_df = df.style.applymap(color_similarity, subset=['Similarité'])
    st.dataframe(styled_df, use_container_width=True)
    
    # Boutons d'action
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📥 Exporter en CSV"):
            filename = export_similar_matches_to_csv(similar_matches)
            if filename:
                st.success(f"Fichier exporté: {filename}")
    
    with col2:
        if st.button("📊 Graphiques détaillés"):
            st.session_state.show_detailed_charts = True
    
    with col3:
        if st.button("🔄 Actualiser"):
            st.rerun()

def render_analysis_summary(analysis):
    """Affiche le résumé de l'analyse"""
    if 'error' in analysis:
        st.error(analysis['error'])
        return
    
    st.subheader("📈 Résumé de l'analyse")
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Matchs analysés", 
            analysis['total_matches'],
            help="Nombre total de matchs similaires trouvés"
        )
    
    with col2:
        avg_sim = analysis['similarity_stats']['avg_similarity'] * 100
        st.metric(
            "Similarité moyenne", 
            f"{avg_sim:.1f}%",
            help="Score de similarité moyen des matchs retenus"
        )
    
    with col3:
        if 'results_analysis' in analysis:
            matches_with_results = analysis['results_analysis']['matches_with_results']
            total_matches = analysis['total_matches']
            coverage = (matches_with_results / total_matches) * 100
            st.metric(
                "Couverture résultats", 
                f"{coverage:.0f}%",
                help="Pourcentage de matchs avec résultats connus"
            )
        else:
            st.metric("Couverture résultats", "0%")
    
    with col4:
        median_sim = analysis['similarity_stats']['median_similarity'] * 100
        st.metric(
            "Similarité médiane", 
            f"{median_sim:.1f}%",
            help="Score de similarité médian"
        )

def render_results_analysis(analysis):
    """Affiche l'analyse détaillée des résultats"""
    if 'results_analysis' not in analysis:
        st.info("Aucun résultat disponible pour l'analyse")
        return
    
    results = analysis['results_analysis']
    
    st.markdown("### 🏆 Analyse des résultats (1X2)")
    
    # Métriques des résultats
    col1, col2, col3 = st.columns(3)
    
    with col1:
        home_pct = results['home_wins']['percentage']
        st.metric(
            "🏠 Victoires Domicile", 
            f"{results['home_wins']['count']} matchs",
            delta=f"{home_pct:.1f}%",
            delta_color="normal"
        )
    
    with col2:
        draw_pct = results['draws']['percentage']
        st.metric(
            "🤝 Matchs Nuls", 
            f"{results['draws']['count']} matchs",
            delta=f"{draw_pct:.1f}%",
            delta_color="normal"
        )
    
    with col3:
        away_pct = results['away_wins']['percentage']
        st.metric(
            "✈️ Victoires Extérieur", 
            f"{results['away_wins']['count']} matchs",
            delta=f"{away_pct:.1f}%",
            delta_color="normal"
        )
    
    # Graphique en secteurs pour les résultats
    fig_results = go.Figure(data=[go.Pie(
        labels=['Domicile', 'Nul', 'Extérieur'],
        values=[home_pct, draw_pct, away_pct],
        hole=0.4,
        marker_colors=['#28a745', '#ffc107', '#dc3545'],
        textinfo='label+percent',
        textposition='auto'
    )])
    
    fig_results.update_layout(
        title="Répartition des résultats 1X2",
        showlegend=True,
        height=400
    )
    
    st.plotly_chart(fig_results, use_container_width=True)
    
    # Recommandations basées sur les résultats
    st.markdown("#### 💡 Recommandations")
    
    max_result = max(
        ('Domicile', home_pct),
        ('Nul', draw_pct), 
        ('Extérieur', away_pct),
        key=lambda x: x[1]
    )
    
    if max_result[1] > 50:
        st.success(f"**Forte tendance**: {max_result[0]} ({max_result[1]:.1f}%) - Considérer ce marché")
    elif max_result[1] > 40:
        st.info(f"**Tendance modérée**: {max_result[0]} ({max_result[1]:.1f}%) - À surveiller")
    else:
        st.warning("**Résultats équilibrés** - Marché difficile à prédire")

def render_over_under_analysis(analysis):
    """Affiche l'analyse Over/Under"""
    if 'over_under_analysis' not in analysis:
        return
    
    ou_analysis = analysis['over_under_analysis']
    
    st.markdown("### ⚽ Analyse Over/Under 2.5 buts")
    
    col1, col2 = st.columns(2)
    
    with col1:
        over_pct = ou_analysis['over_25']['percentage']
        st.metric(
            "📈 Plus de 2.5 buts",
            f"{ou_analysis['over_25']['count']} matchs",
            delta=f"{over_pct:.1f}%"
        )
    
    with col2:
        under_pct = ou_analysis['under_25']['percentage']
        st.metric(
            "📉 Moins de 2.5 buts",
            f"{ou_analysis['under_25']['count']} matchs", 
            delta=f"{under_pct:.1f}%"
        )
    
    # Graphique en barres
    fig_ou = go.Figure(data=[
        go.Bar(
            x=['Plus de 2.5', 'Moins de 2.5'],
            y=[over_pct, under_pct],
            marker_color=['#ff6b6b', '#4ecdc4'],
            text=[f'{over_pct:.1f}%', f'{under_pct:.1f}%'],
            textposition='auto'
        )
    ])
    
    fig_ou.update_layout(
        title="Répartition Over/Under 2.5 buts",
        yaxis_title="Pourcentage",
        showlegend=False,
        height=400
    )
    
    st.plotly_chart(fig_ou, use_container_width=True)
    
    # Recommandation O/U
    if over_pct > 60:
        st.success(f"**Tendance offensive** ({over_pct:.1f}%) - Favoriser Over 2.5")
    elif under_pct > 60:
        st.success(f"**Tendance défensive** ({under_pct:.1f}%) - Favoriser Under 2.5")
    else:
        st.info("**Équilibre O/U** - Marché imprévisible")

def render_btts_analysis(analysis):
    """Affiche l'analyse BTTS si disponible"""
    if 'btts_analysis' not in analysis:
        return
    
    btts_analysis = analysis['btts_analysis']
    
    st.markdown("### 🥅 Analyse Both Teams To Score")
    
    col1, col2 = st.columns(2)
    
    with col1:
        btts_yes_pct = btts_analysis['btts_yes']['percentage']
        st.metric(
            "✅ BTTS Oui",
            f"{btts_analysis['btts_yes']['count']} matchs",
            delta=f"{btts_yes_pct:.1f}%"
        )
    
    with col2:
        btts_no_pct = btts_analysis['btts_no']['percentage']
        st.metric(
            "❌ BTTS Non",
            f"{btts_analysis['btts_no']['count']} matchs",
            delta=f"{btts_no_pct:.1f}%"
        )

def render_detailed_charts(similar_matches):
    """Affiche des graphiques détaillés si demandé"""
    if not hasattr(st.session_state, 'show_detailed_charts') or not st.session_state.show_detailed_charts:
        return
    
    st.markdown("### 📊 Graphiques détaillés")
    
    # Graphique de distribution des similarités
    similarities = [match['similarity'] for match in similar_matches]
    
    fig_sim_dist = px.histogram(
        x=similarities,
        nbins=20,
        title="Distribution des scores de similarité",
        labels={'x': 'Score de similarité', 'y': 'Nombre de matchs'}
    )
    fig_sim_dist.update_layout(showlegend=False)
    st.plotly_chart(fig_sim_dist, use_container_width=True)
    
    # Graphique des cotes vs similarité
    if len(similar_matches) > 5:
        match_data = []
        for match in similar_matches[:50]:  # Limiter pour la lisibilité
            data = match['match_data']
            match_data.append({
                'Similarité': match['similarity'],
                'Cote Domicile': data.get('home_odds'),
                'Cote Nul': data.get('draw_odds'),
                'Cote Extérieur': data.get('away_odds'),
                'Ligue': data.get('league_name', 'N/A')[:20]
            })
        
        df_scatter = pd.DataFrame(match_data)
        
        fig_scatter = px.scatter(
            df_scatter,
            x='Similarité',
            y='Cote Domicile',
            color='Ligue',
            title="Relation Similarité vs Cotes Domicile",
            hover_data=['Cote Nul', 'Cote Extérieur']
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    # Bouton pour masquer les graphiques détaillés
    if st.button("Masquer les graphiques détaillés"):
        st.session_state.show_detailed_charts = False
        st.rerun()
