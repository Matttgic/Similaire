import unittest
import numpy as np
import sys
import os

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.similarity_engine import OddsSimilarityEngine
from config.config import Config

class TestSimilarityEngine(unittest.TestCase):
    
    def setUp(self):
        """Configuration des tests"""
        self.engine = OddsSimilarityEngine()
        
        # Données de test
        self.test_odds_1 = {
            'home': 2.10,
            'draw': 3.40,
            'away': 3.20,
            'over_25': 1.85,
            'under_25': 1.95
        }
        
        self.test_odds_2 = {
            'home': 2.05,
            'draw': 3.45,
            'away': 3.25,
            'over_25': 1.90,
            'under_25': 1.90
        }
        
        self.test_odds_different = {
            'home': 1.40,
            'draw': 4.50,
            'away': 7.00,
            'over_25': 2.20,
            'under_25': 1.65
        }
    
    def test_calculate_odds_vector(self):
        """Test du calcul du vecteur de cotes"""
        vector = self.engine.calculate_odds_vector(self.test_odds_1)
        
        expected = np.array([2.10, 3.40, 3.20, 1.85, 1.95])
        np.testing.assert_array_equal(vector, expected)
        
        # Test avec des données manquantes
        incomplete_odds = {'home': 2.10, 'draw': 3.40}
        with self.assertRaises(KeyError):
            self.engine.calculate_odds_vector(incomplete_odds)
    
    def test_similarity_cosine(self):
        """Test de la similarité cosinus"""
        vector1 = self.engine.calculate_odds_vector(self.test_odds_1)
        vector2 = self.engine.calculate_odds_vector(self.test_odds_2)
        vector3 = self.engine.calculate_odds_vector(self.test_odds_different)
        
        # Similarité entre cotes similaires
        sim_similar = self.engine.calculate_similarity_cosine(vector1, vector2)
        self.assertGreater(sim_similar, 0.95)
        
        # Similarité entre cotes différentes
        sim_different = self.engine.calculate_similarity_cosine(vector1, vector3)
        self.assertLess(sim_different, 0.90)
        
        # Similarité avec soi-même
        sim_identical = self.engine.calculate_similarity_cosine(vector1, vector1)
        self.assertAlmostEqual(sim_identical, 1.0, places=5)
    
    def test_similarity_euclidean(self):
        """Test de la similarité euclidienne"""
        vector1 = self.engine.calculate_odds_vector(self.test_odds_1)
vector2 = self.engine.calculate_odds_vector(self.test_odds_2)
        vector3 = self.engine.calculate_odds_vector(self.test_odds_different)
        
        # Similarité entre cotes similaires
        sim_similar = self.engine.calculate_similarity_euclidean(vector1, vector2)
        self.assertGreater(sim_similar, 0.90)
        
        # Similarité entre cotes différentes
        sim_different = self.engine.calculate_similarity_euclidean(vector1, vector3)
        self.assertLess(sim_different, 0.80)
        
        # Similarité avec soi-même
        sim_identical = self.engine.calculate_similarity_euclidean(vector1, vector1)
        self.assertAlmostEqual(sim_identical, 1.0, places=5)
    
    def test_similarity_percentage(self):
        """Test de la similarité par pourcentage"""
        vector1 = self.engine.calculate_odds_vector(self.test_odds_1)
        vector2 = self.engine.calculate_odds_vector(self.test_odds_2)
        
        sim = self.engine.calculate_similarity_percentage(vector1, vector2)
        self.assertGreater(sim, 0.0)
        self.assertLessEqual(sim, 1.0)
    
    def test_generate_odds_hash(self):
        """Test de génération du hash des cotes"""
        hash1 = self.engine.generate_odds_hash(self.test_odds_1)
        hash2 = self.engine.generate_odds_hash(self.test_odds_1)
        hash3 = self.engine.generate_odds_hash(self.test_odds_2)
        
        # Même cotes = même hash
        self.assertEqual(hash1, hash2)
        
        # Cotes différentes = hash différents
        self.assertNotEqual(hash1, hash3)
        
        # Format du hash
        self.assertEqual(len(hash1), 32)  # MD5 hash length
    
    def test_validate_odds_input(self):
        """Test de validation des cotes"""
        from src.utils import validate_odds_input
        
        # Cotes valides
        errors = validate_odds_input(self.test_odds_1)
        self.assertEqual(len(errors), 0)
        
        # Cotes invalides
        invalid_odds = {
            'home': 0.5,  # Trop faible
            'draw': 3.40,
            'away': 3.20,
            'over_25': 1.85,
            'under_25': None  # Manquante
        }
        errors = validate_odds_input(invalid_odds)
        self.assertGreater(len(errors), 0)

if __name__ == '__main__':
    unittest.main()
