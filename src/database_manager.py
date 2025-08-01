import sqlite3
import pandas as pd
import json
from datetime import datetime
from config.config import Config

class DatabaseManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.init_database()
    
    def init_database(self):
        """Initialise la base de données avec toutes les tables nécessaires"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table principale des matchs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                event_id INTEGER PRIMARY KEY,
                sport_id INTEGER,
                league_id INTEGER,
                league_name TEXT,
                home_team TEXT,
                away_team TEXT,
                start_time TEXT,
                event_type TEXT,
                
                -- Cotes Money Line (1X2)
                home_odds REAL,
                draw_odds REAL,
                away_odds REAL,
                
                -- Cotes Totaux (O/U 2.5)
                over_25_odds REAL,
                under_25_odds REAL,
                
                -- Cotes BTTS
                btts_yes_odds REAL,
                btts_no_odds REAL,
                
                -- Résultats réels
                home_score INTEGER,
                away_score INTEGER,
                result TEXT, -- 'H', 'D', 'A'
                total_goals INTEGER,
                over_25_result BOOLEAN,
                btts_result BOOLEAN,
                
                -- Métadonnées
                is_settled BOOLEAN DEFAULT FALSE,
                last_updated TEXT,
                odds_vector TEXT, -- JSON pour recherche rapide
                
                -- Contraintes
                UNIQUE(event_id)
            )
        ''')
        
        # Table des ligues
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leagues (
                league_id INTEGER PRIMARY KEY,
                league_name TEXT,
                country TEXT,
                sport_id INTEGER,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table des statistiques de similarité (cache)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS similarity_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_odds_hash TEXT,
                similar_matches TEXT, -- JSON
                analysis_results TEXT, -- JSON
                method TEXT,
                threshold REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE(target_odds_hash, method, threshold)
            )
        ''')
        
        # Index pour optimiser les requêtes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_league_date ON matches(league_id, start_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_odds_complete ON matches(home_odds, draw_odds, away_odds, over_25_odds, under_25_odds)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_settled ON matches(is_settled)')
        
        conn.commit()
        conn.close()
        print("✅ Base de données initialisée")
    
    def save_match(self, match_data):
        """Sauvegarde un match en base"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculer le vecteur des cotes pour recherche rapide
        odds_vector = None
        if all(match_data.get(field) for field in ['home_odds', 'draw_odds', 'away_odds', 'over_25_odds', 'under_25_odds']):
            odds_vector = json.dumps([
                match_data['home_odds'],
                match_data['draw_odds'],
                match_data['away_odds'],
                match_data['over_25_odds'],
                match_data['under_25_odds']
            ])
        
        cursor.execute('''
            INSERT OR REPLACE INTO matches (
                event_id, sport_id, league_id, league_name,
                home_team, away_team, start_time, event_type,
                home_odds, draw_odds, away_odds,
                over_25_odds, under_25_odds,
                btts_yes_odds, btts_no_odds,
                home_score, away_score, result, total_goals,
                over_25_result, btts_result, is_settled,
                last_updated, odds_vector
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            match_data.get('event_id'),
            match_data.get('sport_id'),
            match_data.get('league_id'),
            match_data.get('league_name'),
            match_data.get('home_team'),
            match_data.get('away_team'),
            match_data.get('start_time'),
            match_data.get('event_type'),
            match_data.get('home_odds'),
            match_data.get('draw_odds'),
            match_data.get('away_odds'),
            match_data.get('over_25_odds'),
            match_data.get('under_25_odds'),
            match_data.get('btts_yes_odds'),
            match_data.get('btts_no_odds'),
            match_data.get('home_score'),
            match_data.get('away_score'),
            match_data.get('result'),
            match_data.get('total_goals'),
            match_data.get('over_25_result'),
            match_data.get('btts_result'),
            match_data.get('is_settled', False),
            datetime.now().isoformat(),
            odds_vector
        ))
        
        conn.commit()
        conn.close()
    
    def get_matches_with_complete_odds(self):
        """Récupère tous les matchs avec cotes complètes"""
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT * FROM matches 
            WHERE home_odds IS NOT NULL 
            AND draw_odds IS NOT NULL 
            AND away_odds IS NOT NULL
            AND over_25_odds IS NOT NULL 
            AND under_25_odds IS NOT NULL
            ORDER BY start_time DESC
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def get_database_stats(self):
        """Statistiques de la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Nombre total de matchs
        cursor.execute('SELECT COUNT(*) FROM matches')
        stats['total_matches'] = cursor.fetchone()[0]
        
        # Matchs avec cotes complètes
        cursor.execute('''
            SELECT COUNT(*) FROM matches 
            WHERE odds_vector IS NOT NULL
        ''')
        stats['matches_with_odds'] = cursor.fetchone()[0]
        
        # Matchs avec résultats
        cursor.execute('SELECT COUNT(*) FROM matches WHERE is_settled = TRUE')
        stats['settled_matches'] = cursor.fetchone()[0]
        
        # Ligues uniques
        cursor.execute('SELECT COUNT(DISTINCT league_id) FROM matches')
        stats['total_leagues'] = cursor.fetchone()[0]
        
        # Plage de dates
        cursor.execute('SELECT MIN(start_time), MAX(start_time) FROM matches')
        date_range = cursor.fetchone()
        stats['date_range'] = {
            'from': date_range[0],
            'to': date_range[1]
        }
        
        conn.close()
        return stats
    
    def clear_similarity_cache(self):
        """Vide le cache de similarité"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM similarity_cache')
        conn.commit()
        conn.close()
