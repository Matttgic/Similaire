import streamlit as st
from src.utils import validate_odds_input, calculate_implied_probability, format_percentage

def render_odds_input():
    """Composant de saisie des cotes"""
    st.subheader("💰 Saisie des cotes")
    
    # Possibilité de charger des cotes prédéfinies
    preset_odds = st.selectbox(
        "Charger des cotes d'exemple",
        options=[
            "Personnalisé",
            "Match équilibré",
            "Favori domicile",
            "Favori extérieur",
            "Match défensif",
            "Match offensif"
        ]
    )
    
    # Définir les cotes selon le preset
    if preset_odds == "Match équilibré":
        default_odds = {'home': 2.50, 'draw': 3.20, 'away': 2.80, 'over_25': 1.90, 'under_25': 1.90}
    elif preset_odds == "Favori domicile":
        default_odds = {'home': 1.40, 'draw': 4.50, 'away': 7.00, 'over_25': 1.75, 'under_25': 2.10}
    elif preset_odds == "Favori extérieur":
        default_odds = {'home': 6.50, 'draw': 4.20, 'away': 1.50, 'over_25': 1.80, 'under_25': 2.00}
    elif preset_odds == "Match défensif":
        default_odds = {'home': 2.20, 'draw': 2.90, 'away': 3.40, 'over_25': 2.40, 'under_25': 1.55}
    elif preset_odds == "Match offensif":
        default_odds = {'home': 2.80, 'draw': 3.60, 'away': 2.40, 'over_25': 1.45, 'under_25': 2.75}
    else:
        default_odds = {'home': 2.10, 'draw': 3.40, 'away': 3.20, 'over_25': 1.85, 'under_25': 1.95}
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🏆 Résultat du match (1X2)**")
        home_odds = st.number_input(
            "Victoire Domicile", 
            min_value=1.01, 
            max_value=50.0, 
            value=default_odds['home'], 
            step=0.01,
            key="home_odds_input"
        )
        draw_odds = st.number_input(
            "Match Nul", 
            min_value=1.01, 
            max_value=50.0, 
            value=default_odds['draw'], 
            step=0.01,
            key="draw_odds_input"
        )
        away_odds = st.number_input(
            "Victoire Extérieur", 
            min_value=1.01, 
            max_value=50.0, 
            value=default_odds['away'], 
            step=0.01,
            key="away_odds_input"
        )
    
    with col2:
        st.markdown("**⚽ Total de buts (O/U 2.5)**")
        over_25_odds = st.number_input(
            "Plus de 2.5 buts", 
            min_value=1.01, 
            max_value=10.0, 
            value=default_odds['over_25'], 
            step=0.01,
            key="over_25_odds_input"
        )
        under_25_odds = st.number_input(
            "Moins de 2.5 buts", 
            min_value=1.01, 
            max_value=10.0, 
            value=default_odds['under_25'], 
            step=0.01,
            key="under_25_odds_input"
        )
    
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
    
    # Vérification de la marge du bookmaker
    total_prob_1x2 = (1/home_odds + 1/draw_odds + 1/away_odds) * 100
    total_prob_ou = (1/over_25_odds + 1/under_25_odds) * 100
    margin_1x2 = total_prob_1x2 - 100
    margin_ou = total_prob_ou - 100
    
    # Afficher les probabilités implicites et marges
    with st.expander("🧮 Analyse des cotes"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Prob. Domicile", format_percentage(calculate_implied_probability(home_odds)))
        with col2:
            st.metric("Prob. Nul", format_percentage(calculate_implied_probability(draw_odds)))
        with col3:
            st.metric("Prob. Extérieur", format_percentage(calculate_implied_probability(away_odds)))
        
        col4, col5 = st.columns(2)
        with col4:
            st.metric("Prob. Plus 2.5", format_percentage(calculate_implied_probability(over_25_odds)))
        with col5:
            st.metric("Prob. Moins 2.5", format_percentage(calculate_implied_probability(under_25_odds)))
        
        st.markdown("**Marges du bookmaker:**")
        col6, col7 = st.columns(2)
        with col6:
            color = "red" if margin_1x2 > 8 else "orange" if margin_1x2 > 5 else "green"
            st.markdown(f"1X2: <span style='color:{color}'>{margin_1x2:.2f}%</span>", unsafe_allow_html=True)
        with col7:
            color = "red" if margin_ou > 8 else "orange" if margin_ou > 5 else "green"
            st.markdown(f"O/U: <span style='color:{color}'>{margin_ou:.2f}%</span>", unsafe_allow_html=True)
    
    return target_odds
