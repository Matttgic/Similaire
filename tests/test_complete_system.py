#!/usr/bin/env python3
"""
Script de test complet pour le système Pinnacle amélioré
Tests unitaires, d'intégration et de performance
"""

import unittest
import tempfile
import os
import sys
import time
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config
from src.similarity_engine import OddsSimilarityEngine
from src.database_manager import DatabaseManager
from src.data_collector import PinnacleDataCollector
from src.error_handler import ValidationManager, ValidationError
from src.monitoring import MetricsCollector, PerformanceMonitor
from src.logger import get_logger, PinnacleLogger

class TestValidationManager(unittest.TestCase):
    """Tests pour le gestionnaire de validation"""
    
    def setUp(self):
        self.validator = ValidationManager()
    
    def test_valid_odds_input(self):
        """Test avec des cotes valides"""
        valid_odds = {
            'home': 2.10,
            'draw': 3.40,
            'away': 3.20,
            'over_25': 1.85,
            'under_25': 1.95
        }
        errors = self.validator.validate_odds_input(valid_odds)
        self.assertEqual(len(errors), 0)
    
    def test_invalid_odds_input(self):
        """Test avec des cotes invalides"""
        invalid_odds = {
            'home': 0.5,  # Trop faible
            'draw': 3.40,
            'away': 1001,  # Trop élevée
            'over_25': 1.85,
            'under_25': 1.95
        }
        errors = self.validator.validate_odds_input(invalid_odds)
        self.assertGreater(len(errors), 0)
    
    def test_missing_odds_fields(self):
        """Test avec des champs manquants"""
        incomplete_odds = {
            'home': 2.10,
            'draw': 3.40
            # Champs manquants
        }
        errors = self.validator.validate_odds_input(incomplete_odds)
        self.assertGreater(len(errors), 0)
    
    def test_odds_coherence(self):
        """Test de cohérence des cotes"""
        # Cotes incohérentes (probabilités totales trop élevées)
        incoherent_odds = {
            'home': 1.1,
            'draw': 1.1,
            'away': 1.1,
            'over_25': 1.1,
            'under_25': 1.1
        }
        errors = self.validator.validate_odds_input(incoherent_odds)
        self.assertGreater(len(errors), 0)

class TestDatabaseManager(unittest.TestCase):
    """Tests pour le gestionnaire de base de données"""
    
    def setUp(self):
        # Utiliser une base de données temporaire pour les tests
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_manager = DatabaseManager(self.temp_db.name)
    
    def tearDown(self):
        # Nettoyer la base temporaire
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_database_initialization(self):
        """Test d'initialisation de la base de données"""
        # La base devrait être créée et initialisée
        self.assertTrue(os.path.exists(self.temp_db.name))
        
        # Vérifier que les tables existent
        stats = self.db_manager.get_database_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('total_matches', stats)
    
    def test_save_match(self):
        """Test de sauvegarde de match"""
        test_match = {
            'event_id': 12345,
            'home_team': 'Team A',
            'away_team': 'Team B',
            'league_name': 'Test League',
            'home_odds': 2.10,
            'draw_odds': 3.40,
            'away_odds': 3.20,
            'over_25_odds': 1.85,
            'under_25_odds': 1.95
        }
        
        result = self.db_manager.save_match(test_match)
        self.assertTrue(result)
        
        # Vérifier que le match est bien sauvegardé
        stats = self.db_manager.get_database_stats()
        self.assertEqual(stats['total_matches'], 1)
    
    def test_get_matches_with_complete_odds(self):
        """Test de récupération des matchs avec cotes complètes"""
        # Sauvegarder un match de test
        test_match = {
            'event_id': 12345,
            'home_team': 'Team A',
            'away_team': 'Team B',
            'home_odds': 2.10,
            'draw_odds': 3.40,
            'away_odds': 3.20,
            'over_25_odds': 1.85,
            'under_25_odds': 1.95
        }
        self.db_manager.save_match(test_match)
        
        # Récupérer les matchs complets
        df = self.db_manager.get_matches_with_complete_odds()
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['event_id'], 12345)

class TestSimilarityEngine(unittest.TestCase):
    """Tests pour le moteur de similarité"""
    
    def setUp(self):
        # Utiliser une base temporaire
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Créer le moteur avec la base temporaire
        with patch('src.similarity_engine.Config.DATABASE_PATH', self.temp_db.name):
            self.engine = OddsSimilarityEngine()
        
        # Ajouter des données de test
        self._add_test_data()
    
    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def _add_test_data(self):
        """Ajouter des données de test à la base"""
        test_matches = [
            {
                'event_id': 1,
                'home_team': 'Team A',
                'away_team': 'Team B',
                'home_odds': 2.10,
                'draw_odds': 3.40,
                'away_odds': 3.20,
                'over_25_odds': 1.85,
                'under_25_odds': 1.95,
                'result': 'H'
            },
            {
                'event_id': 2,
                'home_team': 'Team C',
                'away_team': 'Team D',
                'home_odds': 2.15,
                'draw_odds': 3.35,
                'away_odds': 3.15,
                'over_25_odds': 1.90,
                'under_25_odds': 1.90,
                'result': 'A'
            }
        ]
        
        for match in test_matches:
            self.engine.db_manager.save_match(match)
    
    def test_calculate_odds_vector(self):
        """Test de calcul du vecteur de cotes"""
        odds_dict = {
            'home': 2.10,
            'draw': 3.40,
            'away': 3.20,
            'over_25': 1.85,
            'under_25': 1.95
        }
        
        vector = self.engine.calculate_odds_vector(odds_dict)
        self.assertEqual(len(vector), 5)
        self.assertEqual(vector[0], 2.10)
        self.assertEqual(vector[1], 3.40)
    
    def test_similarity_calculations(self):
        """Test des différentes méthodes de similarité"""
        vector1 = [2.10, 3.40, 3.20, 1.85, 1.95]
        vector2 = [2.15, 3.35, 3.15, 1.90, 1.90]
        
        # Test cosinus
        similarity_cosine = self.engine.calculate_similarity_cosine(vector1, vector2)
        self.assertGreater(similarity_cosine, 0.9)  # Vecteurs très similaires
        
        # Test euclidienne
        similarity_euclidean = self.engine.calculate_similarity_euclidean(vector1, vector2)
        self.assertGreater(similarity_euclidean, 0.9)
        
        # Test pourcentage
        similarity_percentage = self.engine.calculate_similarity_percentage(vector1, vector2)
        self.assertGreater(similarity_percentage, 0.9)
    
    def test_find_similar_matches(self):
        """Test de recherche de matchs similaires"""
        target_odds = {
            'home': 2.12,
            'draw': 3.38,
            'away': 3.18,
            'over_25': 1.87,
            'under_25': 1.93
        }
        
        similar_matches = self.engine.find_similar_matches(
            target_odds,
            method='cosine',
            threshold=0.8,
            min_matches=1
        )
        
        self.assertGreater(len(similar_matches), 0)
        self.assertIn('similarity', similar_matches[0])
        self.assertIn('match_data', similar_matches[0])
    
    def test_analyze_similar_matches(self):
        """Test d'analyse des matchs similaires"""
        # Simuler des matchs similaires
        similar_matches = [
            {
                'similarity': 0.95,
                'match_data': {
                    'event_id': 1,
                    'result': 'H',
                    'over_25_result': True,
                    'btts_result': False
                }
            },
            {
                'similarity': 0.92,
                'match_data': {
                    'event_id': 2,
                    'result': 'A',
                    'over_25_result': False,
                    'btts_result': True
                }
            }
        ]
        
        analysis = self.engine.analyze_similar_matches(similar_matches)
        
        self.assertIn('total_matches', analysis)
        self.assertEqual(analysis['total_matches'], 2)
        self.assertIn('similarity_stats', analysis)
        self.assertIn('results_analysis', analysis)

class TestMetricsCollector(unittest.TestCase):
    """Tests pour le collecteur de métriques"""
    
    def setUp(self):
        self.metrics = MetricsCollector()
    
    def test_increment_counter(self):
        """Test d'incrémentation de compteur"""
        self.metrics.increment_counter('test.counter', 5)
        self.metrics.increment_counter('test.counter', 3)
        
        app_metrics = self.metrics.get_application_metrics()
        # Le compteur devrait avoir une valeur de 8 (5+3)
        counter_keys = [k for k in app_metrics['counters'].keys() if 'test.counter' in k]
        self.assertGreater(len(counter_keys), 0)
    
    def test_set_gauge(self):
        """Test de définition de jauge"""
        self.metrics.set_gauge('test.gauge', 42.5, unit='percent')
        
        app_metrics = self.metrics.get_application_metrics()
        gauge_keys = [k for k in app_metrics['gauges'].keys() if 'test.gauge' in k]
        self.assertGreater(len(gauge_keys), 0)
    
    def test_record_histogram(self):
        """Test d'enregistrement d'histogramme"""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        for value in values:
            self.metrics.record_histogram('test.histogram', value)
        
        app_metrics = self.metrics.get_application_metrics()
        self.assertIn('histograms', app_metrics)
    
    def test_timer_functionality(self):
        """Test de la fonctionnalité de timer"""
        timer_id = self.metrics.start_timer('test.operation')
        time.sleep(0.1)  # Similer une opération
        duration = self.metrics.stop_timer(timer_id)
        
        self.assertGreaterEqual(duration, 0.1)
        
        # Vérifier que la durée a été enregistrée dans l'histogramme
        app_metrics = self.metrics.get_application_metrics()
        histogram_keys = [k for k in app_metrics['histograms'].keys() if 'duration' in k]
        self.assertGreater(len(histogram_keys), 0)

class TestPerformanceMonitor(unittest.TestCase):
    """Tests pour le moniteur de performance"""
    
    def setUp(self):
        self.metrics = MetricsCollector()
        self.monitor = PerformanceMonitor(self.metrics)
    
    def test_monitor_function_decorator(self):
        """Test du décorateur de monitoring de fonction"""
        @self.monitor.monitor_function("test_operation", "test_component")
        def test_function(x, y):
            time.sleep(0.1)
            return x + y
        
        result = test_function(2, 3)
        self.assertEqual(result, 5)
        
        # Vérifier que les métriques ont été collectées
        app_metrics = self.metrics.get_application_metrics()
        success_counters = [k for k in app_metrics['counters'].keys() if 'success' in k]
        self.assertGreater(len(success_counters), 0)
    
    def test_health_check(self):
        """Test de vérification de santé"""
        health_status = self.monitor.check_system_health()
        
        self.assertIn('status', health_status)
        self.assertIn('checks', health_status)
        self.assertIn('alerts', health_status)
    
    def test_performance_report(self):
        """Test de génération de rapport de performance"""
        # Générer quelques métriques
        self.metrics.increment_counter('test.requests', 10)
        self.metrics.set_gauge('test.memory', 75.5)
        
        report = self.monitor.get_performance_report(1)  # 1 heure
        
        self.assertIn('period', report)
        self.assertIn('system_metrics', report)
        self.assertIn('application_metrics', report)

class TestDataCollector(unittest.TestCase):
    """Tests pour le collecteur de données"""
    
    def setUp(self):
        # Mock de la configuration pour éviter les appels API réels
        self.mock_api_key = "test_api_key"
        
        with patch('src.data_collector.Config.RAPIDAPI_KEY', self.mock_api_key):
            self.collector = PinnacleDataCollector()
    
    @patch('src.data_collector.requests.get')
    def test_get_sports(self, mock_get):
        """Test de récupération des sports"""
        # Mock de la réponse API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'sports': [
                {'id': 1, 'name': 'Football'}
            ]
        }
        mock_get.return_value = mock_response
        
        result = self.collector.get_sports()
        
        self.assertIsNotNone(result)
        self.assertIn('sports', result)
        self.assertEqual(len(result['sports']), 1)
    
    def test_extract_odds_from_event(self):
        """Test d'extraction des cotes d'un événement"""
        test_event = {
            'event_id': 12345,
            'home': 'Team A',
            'away': 'Team B',
            'league_name': 'Test League',
            'periods': {
                'num_0': {
                    'money_line': {
                        'home': 2.10,
                        'draw': 3.40,
                        'away': 3.20
                    },
                    'totals': {
                        '2.5': {
                            'over': 1.85,
                            'under': 1.95
                        }
                    }
                }
            }
        }
        
        match_data = self.collector.extract_odds_from_event(test_event)
        
        self.assertEqual(match_data['event_id'], 12345)
        self.assertEqual(match_data['home_team'], 'Team A')
        self.assertEqual(match_data['home_odds'], 2.10)
        self.assertEqual(match_data['over_25_odds'], 1.85)
    
    def test_has_complete_odds(self):
        """Test de vérification des cotes complètes"""
        complete_match = {
            'home_odds': 2.10,
            'draw_odds': 3.40,
            'away_odds': 3.20,
            'over_25_odds': 1.85,
            'under_25_odds': 1.95
        }
        
        incomplete_match = {
            'home_odds': 2.10,
            'draw_odds': 3.40
            # Cotes manquantes
        }
        
        self.assertTrue(self.collector._has_complete_odds(complete_match))
        self.assertFalse(self.collector._has_complete_odds(incomplete_match))

class TestIntegration(unittest.TestCase):
    """Tests d'intégration entre les composants"""
    
    def setUp(self):
        # Configurer un environnement de test complet
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        with patch('src.similarity_engine.Config.DATABASE_PATH', self.temp_db.name):
            self.db_manager = DatabaseManager(self.temp_db.name)
            self.engine = OddsSimilarityEngine()
        
        self.validator = ValidationManager()
        self.metrics = MetricsCollector()
    
    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_end_to_end_similarity_analysis(self):
        """Test complet d'analyse de similarité"""
        # 1. Ajouter des données de test
        test_matches = [
            {
                'event_id': 1,
                'home_team': 'Arsenal',
                'away_team': 'Chelsea',
                'league_name': 'Premier League',
                'home_odds': 2.10,
                'draw_odds': 3.40,
                'away_odds': 3.20,
                'over_25_odds': 1.85,
                'under_25_odds': 1.95,
                'result': 'H'
            },
            {
                'event_id': 2,
                'home_team': 'Liverpool',
                'away_team': 'Manchester City',
                'league_name': 'Premier League',
                'home_odds': 2.05,
                'draw_odds': 3.45,
                'away_odds': 3.25,
                'over_25_odds': 1.80,
                'under_25_odds': 2.00,
                'result': 'A'
            }
        ]
        
        for match in test_matches:
            saved = self.db_manager.save_match(match)
            self.assertTrue(saved)
        
        # 2. Valider des cotes d'entrée
        target_odds = {
            'home': 2.08,
            'draw': 3.43,
            'away': 3.22,
            'over_25': 1.83,
            'under_25': 1.97
        }
        
        validation_errors = self.validator.validate_odds_input(target_odds)
        self.assertEqual(len(validation_errors), 0)
        
        # 3. Trouver des matchs similaires
        similar_matches = self.engine.find_similar_matches(
            target_odds,
            method='cosine',
            threshold=0.8,
            min_matches=1
        )
        
        self.assertGreater(len(similar_matches), 0)
        
        # 4. Analyser les résultats
        analysis = self.engine.analyze_similar_matches(similar_matches)
        
        self.assertIn('total_matches', analysis)
        self.assertIn('similarity_stats', analysis)
        self.assertIn('results_analysis', analysis)
        
        # 5. Vérifier les métriques
        self.assertIsInstance(analysis['similarity_stats']['avg_similarity'], float)
        self.assertGreater(analysis['similarity_stats']['avg_similarity'], 0)

def run_performance_tests():
    """Exécute des tests de performance"""
    print("\n" + "="*50)
    print("TESTS DE PERFORMANCE")
    print("="*50)
    
    # Test de base temporaire
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    try:
        with patch('src.similarity_engine.Config.DATABASE_PATH', temp_db.name):
            db_manager = DatabaseManager(temp_db.name)
            engine = OddsSimilarityEngine()
        
        # Ajouter des données de test en volume
        print("Ajout de 1000 matchs de test...")
        start_time = time.time()
        
        for i in range(1000):
            test_match = {
                'event_id': i,
                'home_team': f'Team A{i}',
                'away_team': f'Team B{i}',
                'league_name': 'Test League',
                'home_odds': 2.0 + (i % 20) * 0.1,
                'draw_odds': 3.0 + (i % 30) * 0.1,
                'away_odds': 3.0 + (i % 25) * 0.1,
                'over_25_odds': 1.8 + (i % 15) * 0.1,
                'under_25_odds': 1.9 + (i % 15) * 0.1,
                'result': ['H', 'D', 'A'][i % 3]
            }
            db_manager.save_match(test_match)
        
        insertion_time = time.time() - start_time
        print(f"Temps d'insertion: {insertion_time:.2f}s ({1000/insertion_time:.1f} matchs/s)")
        
        # Test de recherche de similarité
        print("Test de recherche de similarité...")
        target_odds = {
            'home': 2.10,
            'draw': 3.40,
            'away': 3.20,
            'over_25': 1.85,
            'under_25': 1.95
        }
        
        start_time = time.time()
        similar_matches = engine.find_similar_matches(
            target_odds,
            method='cosine',
            threshold=0.8,
            min_matches=10
        )
        search_time = time.time() - start_time
        
        print(f"Temps de recherche: {search_time:.3f}s")
        print(f"Matchs trouvés: {len(similar_matches)}")
        print(f"Performance: {1000/search_time:.1f} matchs analysés/s")
        
        # Test d'analyse
        start_time = time.time()
        analysis = engine.analyze_similar_matches(similar_matches)
        analysis_time = time.time() - start_time
        
        print(f"Temps d'analyse: {analysis_time:.3f}s")
        
        # Statistiques de la base
        stats = db_manager.get_database_stats()
        print(f"Statistiques finales: {stats['total_matches']} matchs, {stats['matches_with_odds']} avec cotes complètes")
        
    finally:
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)

def main():
    """Fonction principale de test"""
    print("="*60)
    print("TESTS AUTOMATISÉS - SYSTÈME PINNACLE AMÉLIORÉ")
    print("="*60)
    
    # Configuration du logger pour les tests 
    Config.setup_logging()
    
    # Exécuter les tests unitaires
    print("\nExécution des tests unitaires...")
    
    # Créer la suite de tests
    test_suite = unittest.TestSuite()
    
    # Ajouter les classes de test
    test_classes = [
        TestValidationManager,
        TestDatabaseManager,
        TestSimilarityEngine,
        TestMetricsCollector,
        TestPerformanceMonitor,
        TestDataCollector,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Exécuter les tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Afficher les résultats
    print(f"\nRÉSULTATS DES TESTS:")
    print(f"Tests exécutés: {result.testsRun}")
    print(f"Succès: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Échecs: {len(result.failures)}")
    print(f"Erreurs: {len(result.errors)}")
    
    if result.failures:
        print("\nÉCHECS:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERREURS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    # Tests de performance
    run_performance_tests()
    
    # Résumé final
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\n{'='*60}")
    print(f"TAUX DE SUCCÈS GLOBAL: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("✅ EXCELLENT - Le système est prêt pour la production")
    elif success_rate >= 75:
        print("⚠️  BON - Quelques améliorations nécessaires")
    else:
        print("❌ INSUFFISANT - Corrections importantes requises")
    
    print("="*60)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)