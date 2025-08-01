import json
import pandas as pd
from datetime import datetime, timedelta
import re

def format_odds(odds_value):
    """Formate une cote pour l'affichage"""
    if odds_value is None:
        return "N/A"
    return f"{odds_value:.2f}"

def format_percentage(value):
    """Formate un pourcentage pour l'affichage"""
    if value is None:
        return "N/A"
    return f"{value:.1f}%"

def parse_match_time(time_str):
    """Parse une chaîne de temps en datetime"""
    try:
        return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
    except:
        return None

def calculate_implied_probability(odds):
    """Calcule la probabilité implicite d'une cote"""
    if odds is None or odds <= 0:
        return None
    return (1 / odds) * 100

def validate_odds_input(odds_dict):
    """Valide les cotes saisies par l'utilisateur"""
    required_fields = ['home', 'draw', 'away', 'over_25', 'under_25']
    errors = []
    
    for field in required_fields:
        if field not in odds_dict:
            errors.append(f"Cote manquante: {field}")
        elif odds_dict[field] is None:
            errors.append(f"Cote invalide: {field}")
        elif odds_dict[field] <= 1.0:
            errors.append(f"Cote trop faible: {field} ({odds_dict[field]})")
        elif odds_dict[field] > 100:
            errors.append(f"Cote trop élevée: {field} ({odds_dict[field]})")
    
    return errors

def get_market_display_name(market_key):
    """Retourne le nom d'affichage d'un marché"""
    market_names = {
        'home': 'Victoire Domicile',
        'draw': 'Match Nul',
        'away': 'Victoire Extérieur',
        'over_25': 'Plus de 2.5 buts',
        'under_25': 'Moins de 2.5 buts',
        'btts_yes': 'BTTS Oui',
        'btts_no': 'BTTS Non'
    }
    return market_names.get(market_key, market_key)

def clean_team_name(team_name):
    """Nettoie le nom d'une équipe"""
    if not team_name:
        return ""
    
    # Supprimer les caractères spéciaux
    cleaned = re.sub(r'[^\w\s-]', '', team_name)
    # Normaliser les espaces
    cleaned = ' '.join(cleaned.split())
    return cleaned.title()

def export_similar_matches_to_csv(similar_matches, filename=None):
    """Exporte les matchs similaires vers un fichier CSV"""
    if not similar_matches:
        return None
    
    data = []
    for match in similar_matches:
        match_data = match['match_data']
        data.append({
            'Event_ID': match_data.get('event_id'),
            'League': match_data.get('league_name'),
            'Home_Team': match_data.get('home_team'),
            'Away_Team': match_data.get('away_team'),
            'Date': match_data.get('start_time'),
            'Similarity': f"{match['similarity']:.3f}",
            'Home_Odds': format_odds(match_data.get('home_odds')),
            'Draw_Odds': format_odds(match_data.get('draw_odds')),
            'Away_Odds': format_odds(match_data.get('away_odds')),
            'Over_2.5': format_odds(match_data.get('over_25_odds')),
            'Under_2.5': format_odds(match_data.get('under_25_odds')),
            'Result': match_data.get('result', 'N/A'),
            'Score': f"{match_data.get('home_score', 'N/A')}-{match_data.get('away_score', 'N/A')}"
        })
    
    df = pd.DataFrame(data)
    
    if filename is None:
        filename = f"similar_matches_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    df.to_csv(filename, index=False)
    return filename

def calculate_betting_value(odds, implied_prob, estimated_prob):
    """Calcule la valeur d'un pari (Kelly Criterion simplifié)"""
    if not all([odds, implied_prob, estimated_prob]):
        return None
    
    if estimated_prob <= implied_prob:
        return 0  # Pas de valeur
    
    # Formule de Kelly simplifiée
    edge = (estimated_prob / 100) - (1 / odds)
    kelly_fraction = edge / ((odds - 1) / odds)
    
    return max(0, kelly_fraction * 100)  # Retourner en pourcentage
