#!/usr/bin/env python3
"""
Script de collecte des données historiques
Lancez ce script une fois pour initialiser votre base de données
"""

import sys
import os
import argparse
from datetime import datetime

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_collector import PinnacleDataCollector
from src.database_manager import DatabaseManager

def main():
    parser = argparse.ArgumentParser(description='Collecte des données historiques Pinnacle')
    parser.add_argument('--max-events', type=int, default=5000, 
                       help='Nombre maximum d\'événements à collecter')
    parser.add_argument('--sport-id', type=int, default=1,
                       help='ID du sport (1 = Football)')
    parser.add_argument('--days-back', type=int, default=3650,
                       help='Nombre de jours dans le passé à récupérer')
    
    args = parser.parse_args()
    
    print("🚀 Début de la collecte des données historiques Pinnacle")
    print(f"📊 Paramètres:")
    print(f"   - Max événements: {args.max_events}")
    print(f"   - Sport ID: {args.sport_id}")
    print(f"   - Jours en arrière: {args.days_back}")
    print(f"   - Début: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialiser le collecteur
    collector = PinnacleDataCollector()
    
    # Lancer la collecte
    try:
        collector.collect_historical_data(max_events=args.max_events)
        
        # Afficher les statistiques finales
        db_manager = DatabaseManager()
        stats = db_manager.get_database_stats()
        
        print("\n🎉 Collecte terminée avec succès!")
        print(f"📈 Statistiques finales:")
        print(f"   - Total matchs: {stats['total_matches']}")
        print(f"   - Avec cotes complètes: {stats['matches_with_odds']}")
        print(f"   - Ligues couvertes: {stats['total_leagues']}")
        
    except Exception as e:
        print(f"❌ Erreur lors de la collecte: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
