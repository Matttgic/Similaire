import unittest
import tempfile
import os
import sys

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database_manager import DatabaseManager

class TestDatabaseManager(unittest.TestCase):
    
    def setUp(self):
        """Configuration des tests avec base temporaire"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_manager = DatabaseManager(self.temp_db.name)
        
        # Données de test
        self.test_match = {
            'event_id': 123456,
            'sport_id': 1,
            'league_id': 100,
            'league_name': 'Test League',
            'home_team': 'Team A',
            'away_team': 'Team B',
            'start_time': '2024-01-01T15:00:00',
            'event_type': 'prematch',
            'home_odds': 2.10,
            'draw_odds': 3.40,
            'away_odds': 3.20,
            'over_25_odds': 1.85,
            'under_25_odds': 1.95,
            'home_score': 2,
            'away_score': 1,
            'result': 'H',
            'total_goals': 3,
            'over_25_result': True,
            'btts_result': True,
            'is_settled': True
        }
    
    def tearDown(self):
        """Nettoyage après les tests"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_database_initialization(self):
        """Test de l'initialisation de la base"""
        # Vérifier que les tables existent
        import sqlite3
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['matches', 'leagues', 'similarity_cache']
        for table in expected_tables:
            self.assertIn(table, tables)
        
        conn.close()
    
    def test_save_match(self):
        """Test de sauvegarde d'un match"""
        # Sauvegarder le match de test
        self.db_manager.save_match(self.test_match)
        
        # Vérifier qu'il a été sauvegardé
        matches_df = self.db_manager.get_matches_with_complete_odds()
        self.assertEqual(len(matches_df), 1)
        
        # Vérifier les données
        saved_match = matches_df.iloc[0]
        self.assertEqual(saved_match['event_id'], self.test_match['event_id'])
        self.assertEqual(saved_match['home_team'], self.test_match['home_team'])
        self.assertAlmostEqual(saved_match['home_odds'], self.test_match['home_odds'])
    
    def test_get_matches_with_complete_odds(self):
        """Test de récupération des matchs avec cotes complètes"""
        # Match avec toutes les cotes
        complete_match = self.test_match.copy()
        self.db_manager.save_match(complete_match)
        
        # Match avec cotes incomplètes
        incomplete_match = self.test_match.copy()
        incomplete_match['event_id'] = 789
        incomplete_match['over_25_odds'] = None
        self.db_manager.save_match(incomplete_match)
        
        # Récupérer seulement les matchs complets
        complete_matches = self.db_manager.get_matches_with_complete_odds()
        self.assertEqual(len(complete_matches), 1)
        self.assertEqual(complete_matches.iloc[0]['event_id'], complete_match['event_id'])
    
    def test_database_stats(self):
        """Test des statistiques de la base"""
        # Base vide
        stats = self.db_manager.get_database_stats()
        self.assertEqual(stats['total_matches'], 0)
        
        # Ajouter des matchs
        for i in range(5):
            match = self.test_match.copy()
            match['event_id'] = 100 + i
            match['league_id'] = 200 + (i % 2)  # 2 ligues différentes
            self.db_manager.save_match(match)
        
        # Vérifier les stats
        stats = self.db_manager.get_database_stats()
        self.assertEqual(stats['total_matches'], 5)
        self.assertEqual(stats['matches_with_odds'], 5)
        self.assertEqual(stats['settled_matches'], 5)
        self.assertEqual(stats['total_leagues'], 2)
    
    def test_clear_similarity_cache(self):
        """Test du nettoyage du cache"""
        # Ajouter une entrée dans le cache (simulation)
        import sqlite3
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO similarity_cache (target_odds_hash, similar_matches, method, threshold)
            VALUES (?, ?, ?, ?)
        ''', ('test_hash', '[]', 'cosine', 0.9))
        conn.commit()
        
        # Vérifier qu'elle existe
        cursor.execute('SELECT COUNT(*) FROM similarity_cache')
        count_before = cursor.fetchone()[0]
        self.assertEqual(count_before, 1)
        conn.close()
        
        # Vider le cache
        self.db_manager.clear_similarity_cache()
        
        # Vérifier qu'il est vide
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM similarity_cache')
        count_after = cursor.fetchone()[0]
        self.assertEqual(count_after, 0)
        conn.close()

if __name__ == '__main__':
    unittest.main()
