#!/usr/bin/env python3
"""
Script de mise à jour des résultats des matchs
Ce script peut être lancé périodiquement pour mettre à jour les résultats
"""

import sys
import os
import argparse
import requests
from datetime import datetime, timedelta

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database_manager import DatabaseManager
from config.config import Config

class ResultsUpdater:
    def __init__(self):
        self.db_manager = DatabaseManager()
        # Pour l'exemple, on utilise une API de résultats sportifs
        # Vous devrez adapter selon votre source de résultats
        self.results_api_key = os.getenv('FOOTBALL_API_KEY', '')
        self.results_base_url = 'https://api.football-data.org/v4'
        
    def get_unsettled_matches(self, days_back=7):
        """Récupère les matchs non réglés des derniers jours"""
        import sqlite3
        conn = sqlite3.connect(self.db_manager.db_path)
        
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        query = '''
            SELECT * FROM matches 
            WHERE is_settled = FALSE 
            AND start_time > ?
            AND start_time < datetime('now')
            ORDER BY start_time DESC
        '''
        
        cursor = conn.cursor()
        cursor.execute(query, (cutoff_date,))
        
        matches = []
        for row in cursor.fetchall():
            match_dict = dict(zip([col[0] for col in cursor.description], row))
            matches.append(match_dict)
        
        conn.close()
        return matches
    
    def search_match_result(self, home_team, away_team, match_date):
        """
        Recherche le résultat d'un match via une API externe
        Cette fonction doit être adaptée selon votre source de données
        """
        # Exemple avec une API générique (à adapter)
        try:
            # Nettoyer les noms d'équipes
            home_clean = self.clean_team_name(home_team)
            away_clean = self.clean_team_name(away_team)
            
            # Simuler une recherche de résultat
            # Dans la réalité, vous feriez un appel API ici
            result = self.mock_result_lookup(home_clean, away_clean, match_date)
            
            return result
            
        except Exception as e:
            print(f"❌ Erreur recherche résultat pour {home_team} vs {away_team}: {e}")
            return None
    
    def clean_team_name(self, team_name):
        """Nettoie le nom d'une équipe pour la recherche"""
        import re
        if not team_name:
            return ""
        
        # Supprimer les caractères spéciaux et normaliser
        cleaned = re.sub(r'[^\w\s]', '', team_name)
        cleaned = ' '.join(cleaned.split())
        return cleaned.lower()
    
    def mock_result_lookup(self, home_team, away_team, match_date):
        """
        Mock de recherche de résultat (pour les tests)
        À remplacer par une vraie recherche API
        """
        import random
        
        # Simuler des résultats aléatoires pour les tests
        home_score = random.randint(0, 4)
        away_score = random.randint(0, 4)
        
        result = 'H' if home_score > away_score else 'A' if away_score > home_score else 'D'
        total_goals = home_score + away_score
        over_25 = total_goals > 2.5
        btts = home_score > 0 and away_score > 0
        
        return {
            'home_score': home_score,
            'away_score': away_score,
            'result': result,
            'total_goals': total_goals,
            'over_25_result': over_25,
            'btts_result': btts
        }
    
    def update_match_result(self, event_id, result_data):
        """Met à jour le résultat d'un match en base"""
        import sqlite3
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE matches SET
                home_score = ?,
                away_score = ?,
                result = ?,
                total_goals = ?,
                over_25_result = ?,
                btts_result = ?,
                is_settled = TRUE,
                last_updated = ?
            WHERE event_id = ?
        ''', (
            result_data['home_score'],
            result_data['away_score'],
            result_data['result'],
            result_data['total_goals'],
            result_data['over_25_result'],
            result_data['btts_result'],
            datetime.now().isoformat(),
            event_id
        ))
        
        conn.commit()
        conn.close()
    
    def update_all_results(self, days_back=7, max_updates=100):
        """Met à jour tous les résultats manquants"""
        print(f"🔄 Mise à jour des résultats (derniers {days_back} jours)")
        
        unsettled_matches = self.get_unsettled_matches(days_back)
        print(f"📊 {len(unsettled_matches)} matchs à vérifier")
        
        if not unsettled_matches:
            print("✅ Aucun match à mettre à jour")
            return
        
        updated_count = 0
        error_count = 0
        
        for match in unsettled_matches[:max_updates]:
            try:
                print(f"🔍 Recherche: {match['home_team']} vs {match['away_team']}")
                
                result_data = self.search_match_result(
                    match['home_team'],
                    match['away_team'],
                    match['start_time']
                )
                
                if result_data:
                    self.update_match_result(match['event_id'], result_data)
                    updated_count += 1
                    print(f"✅ Résultat mis à jour: {result_data['home_score']}-{result_data['away_score']}")
                else:
                    print("⚠️ Résultat non trouvé")
                
                # Rate limiting
                import time
                time.sleep(0.5)
                
            except Exception as e:
                error_count += 1
                print(f"❌ Erreur pour le match {match['event_id']}: {e}")
                continue
        
        print(f"\n🎉 Mise à jour terminée:")
        print(f"   ✅ {updated_count} résultats mis à jour")
        print(f"   ❌ {error_count} erreurs")
        
        # Vider le cache de similarité après mise à jour
        if updated_count > 0:
            self.db_manager.clear_similarity_cache()
            print("🗑️ Cache de similarité vidé")

def main():
    parser = argparse.ArgumentParser(description='Mise à jour des résultats de matchs')
    parser.add_argument('--days-back', type=int, default=7,
                       help='Nombre de jours en arrière à vérifier')
    parser.add_argument('--max-updates', type=int, default=100,
                       help='Nombre maximum de mises à jour')
    parser.add_argument('--dry-run', action='store_true',
                       help='Simulation sans mise à jour réelle')
    
    args = parser.parse_args()
    
    print("🚀 Démarrage de la mise à jour des résultats")
    print(f"📊 Paramètres: {args.days_back} jours, max {args.max_updates} mises à jour")
    
    if args.dry_run:
        print("🔍 Mode simulation activé")
    
    updater = ResultsUpdater()
    
    if not args.dry_run:
        updater.update_all_results(args.days_back, args.max_updates)
    else:
        # Mode simulation
        unsettled = updater.get_unsettled_matches(args.days_back)
        print(f"📊 {len(unsettled)} matchs seraient vérifiés")
        for match in unsettled[:5]:  # Afficher les 5 premiers
            print(f"   - {match['home_team']} vs {match['away_team']} ({match['start_time'][:10]})")

if __name__ == "__main__":
    main()
