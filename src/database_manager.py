import sqlite3
import pandas as pd
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from contextlib import contextmanager

from config.config import Config
from src.logger import get_logger, pinnacle_logger
from src.error_handler import ErrorHandler, DatabaseError

class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = get_logger('database')
        self._lock = threading.Lock()
        
        # Créer le répertoire de la base si nécessaire
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.init_database()
        self._setup_connection_pool()
    
    def _setup_connection_pool(self):
        """Configure les paramètres de performance pour SQLite"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Optimisations SQLite
                cursor.execute('PRAGMA journal_mode=WAL')  # Write-Ahead Logging
                cursor.execute('PRAGMA synchronous=NORMAL')  # Balance performance/durability
                cursor.execute('PRAGMA temp_store=MEMORY')  # Temporary tables in memory
                cursor.execute('PRAGMA mmap_size=268435456')  # 256MB memory map
                cursor.execute('PRAGMA cache_size=10000')  # 10000 pages in cache
                cursor.execute('PRAGMA foreign_keys=ON')  # Enable foreign keys
                
                conn.commit()
                self.logger.info("Database performance optimizations applied")
                
        except Exception as e:
            self.logger.error(f"Failed to setup connection pool: {e}")
    
    @contextmanager 
    def get_connection(self):
        """Context manager pour les connexions à la base de données"""
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row  # Pour un accès par nom de colonne
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database connection error: {e}")
            raise DatabaseError(f"Database connection failed: {e}")
        finally:
            if conn:
                conn.close()
    
    @ErrorHandler.handle_database_error
    def init_database(self):
        """Initialise la base de données avec toutes les tables nécessaires et optimisations"""
        start_time = datetime.now()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Table principale des matchs avec contraintes améliorées
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS matches (
                    event_id INTEGER PRIMARY KEY,
                    sport_id INTEGER NOT NULL DEFAULT 1,
                    league_id INTEGER,
                    league_name TEXT,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    start_time TEXT,
                    event_type TEXT,
                    
                    -- Cotes Money Line (1X2)
                    home_odds REAL CHECK(home_odds > 1.0),
                    draw_odds REAL CHECK(draw_odds > 1.0),
                    away_odds REAL CHECK(away_odds > 1.0),
                    
                    -- Cotes Totaux (O/U 2.5)
                    over_25_odds REAL CHECK(over_25_odds > 1.0),
                    under_25_odds REAL CHECK(under_25_odds > 1.0),
                    
                    -- Cotes BTTS
                    btts_yes_odds REAL CHECK(btts_yes_odds > 1.0),
                    btts_no_odds REAL CHECK(btts_no_odds > 1.0),
                    
                    -- Résultats réels
                    home_score INTEGER CHECK(home_score >= 0),
                    away_score INTEGER CHECK(away_score >= 0),
                    result TEXT CHECK(result IN ('H', 'D', 'A')),
                    total_goals INTEGER CHECK(total_goals >= 0),
                    over_25_result BOOLEAN,
                    btts_result BOOLEAN,
                    
                    -- Métadonnées
                    is_settled BOOLEAN DEFAULT FALSE,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                    odds_vector TEXT, -- JSON pour recherche rapide
                    data_quality_score REAL DEFAULT 1.0,
                    
                    -- Contraintes
                    UNIQUE(event_id),
                    CHECK(home_team != away_team),
                    CHECK(start_time IS NOT NULL OR event_type = 'historical')
                )
            ''')
            
            # Table des ligues avec informations étendues
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leagues (
                    league_id INTEGER PRIMARY KEY,
                    league_name TEXT NOT NULL,
                    country TEXT,
                    sport_id INTEGER NOT NULL DEFAULT 1,
                    level INTEGER DEFAULT 1, -- Division level
                    is_active BOOLEAN DEFAULT TRUE,
                    total_matches INTEGER DEFAULT 0,
                    avg_odds_home REAL,
                    avg_odds_draw REAL,
                    avg_odds_away REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                    
                    UNIQUE(league_id)
                )
            ''')
            
            # Table des statistiques de similarité (cache) améliorée
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS similarity_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_odds_hash TEXT NOT NULL,
                    similar_matches TEXT NOT NULL, -- JSON
                    analysis_results TEXT, -- JSON
                    method TEXT NOT NULL CHECK(method IN ('cosine', 'euclidean', 'percentage')),
                    threshold REAL NOT NULL CHECK(threshold BETWEEN 0 AND 1),
                    matches_count INTEGER DEFAULT 0,
                    avg_similarity REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT DEFAULT CURRENT_TIMESTAMP,
                    
                    UNIQUE(target_odds_hash, method, threshold)
                )
            ''')
            
            # Table des logs de performance
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation TEXT NOT NULL,
                    component TEXT NOT NULL,
                    execution_time REAL NOT NULL,
                    records_affected INTEGER,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT -- JSON pour informations supplémentaires
                )
            ''')
            
            # Table de configuration dynamique
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT,
                    type TEXT DEFAULT 'string', -- string, int, float, bool, json
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Index pour optimiser les requêtes critiques
            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_matches_league_date ON matches(league_id, start_time)',
                'CREATE INDEX IF NOT EXISTS idx_matches_odds_complete ON matches(home_odds, draw_odds, away_odds, over_25_odds, under_25_odds) WHERE home_odds IS NOT NULL',
                'CREATE INDEX IF NOT EXISTS idx_matches_settled ON matches(is_settled)',
                'CREATE INDEX IF NOT EXISTS idx_matches_teams ON matches(home_team, away_team)',
                'CREATE INDEX IF NOT EXISTS idx_matches_sport_league ON matches(sport_id, league_id)',
                'CREATE INDEX IF NOT EXISTS idx_similarity_cache_hash ON similarity_cache(target_odds_hash)',
                'CREATE INDEX IF NOT EXISTS idx_similarity_cache_created ON similarity_cache(created_at)',
                'CREATE INDEX IF NOT EXISTS idx_leagues_active ON leagues(is_active, sport_id)',
                'CREATE INDEX IF NOT EXISTS idx_performance_logs_operation ON performance_logs(operation, timestamp)',
                'CREATE INDEX IF NOT EXISTS idx_matches_quality ON matches(data_quality_score) WHERE data_quality_score IS NOT NULL'
            ]
            
            for index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                except sqlite3.OperationalError as e:
                    if "already exists" not in str(e):
                        self.logger.warning(f"Failed to create index: {e}")
            
            # Vues pour les requêtes fréquentes
            cursor.execute('''
                CREATE VIEW IF NOT EXISTS complete_matches AS
                SELECT * FROM matches 
                WHERE home_odds IS NOT NULL 
                AND draw_odds IS NOT NULL 
                AND away_odds IS NOT NULL
                AND over_25_odds IS NOT NULL 
                AND under_25_odds IS NOT NULL
                AND data_quality_score >= 0.5
            ''')
            
            cursor.execute('''
                CREATE VIEW IF NOT EXISTS settled_matches AS
                SELECT * FROM complete_matches
                WHERE is_settled = TRUE
                AND result IS NOT NULL
            ''')
            
            conn.commit()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            pinnacle_logger.log_database_operation(
                'init_database', 
                'all_tables', 
                None, 
                execution_time
            )
            
            self.logger.info(f"Database initialized successfully in {execution_time:.3f}s")
    
    @ErrorHandler.handle_database_error
    def save_match(self, match_data: Dict[str, Any]) -> bool:
        """Sauvegarde un match en base avec validation et calcul de qualité"""
        start_time = datetime.now()
        
        try:
            # Calculer le score de qualité des données
            quality_score = self._calculate_data_quality_score(match_data)
            match_data['data_quality_score'] = quality_score
            
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
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Utiliser UPSERT pour éviter les doublons
                cursor.execute('''
                    INSERT INTO matches (
                        event_id, sport_id, league_id, league_name,
                        home_team, away_team, start_time, event_type,
                        home_odds, draw_odds, away_odds,
                        over_25_odds, under_25_odds,
                        btts_yes_odds, btts_no_odds,
                        home_score, away_score, result, total_goals,
                        over_25_result, btts_result, is_settled,
                        last_updated, odds_vector, data_quality_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(event_id) DO UPDATE SET
                        league_name = COALESCE(excluded.league_name, league_name),
                        home_odds = COALESCE(excluded.home_odds, home_odds),
                        draw_odds = COALESCE(excluded.draw_odds, draw_odds),
                        away_odds = COALESCE(excluded.away_odds, away_odds),
                        over_25_odds = COALESCE(excluded.over_25_odds, over_25_odds),
                        under_25_odds = COALESCE(excluded.under_25_odds, under_25_odds),
                        btts_yes_odds = COALESCE(excluded.btts_yes_odds, btts_yes_odds),
                        btts_no_odds = COALESCE(excluded.btts_no_odds, btts_no_odds),
                        home_score = COALESCE(excluded.home_score, home_score),
                        away_score = COALESCE(excluded.away_score, away_score),
                        result = COALESCE(excluded.result, result),
                        total_goals = COALESCE(excluded.total_goals, total_goals),
                        over_25_result = COALESCE(excluded.over_25_result, over_25_result),
                        btts_result = COALESCE(excluded.btts_result, btts_result),
                        is_settled = COALESCE(excluded.is_settled, is_settled),
                        last_updated = excluded.last_updated,
                        odds_vector = COALESCE(excluded.odds_vector, odds_vector),
                        data_quality_score = GREATEST(excluded.data_quality_score, data_quality_score)
                ''', (
                    match_data.get('event_id'),
                    match_data.get('sport_id', 1),
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
                    odds_vector,
                    quality_score
                ))
                
                conn.commit()
                affected_rows = cursor.rowcount
                
                # Mettre à jour les statistiques de la ligue si nécessaire
                if match_data.get('league_id'):
                    self._update_league_stats(cursor, match_data.get('league_id'), conn)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                pinnacle_logger.log_database_operation(
                    'save_match', 
                    'matches', 
                    affected_rows, 
                    execution_time
                )
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save match {match_data.get('event_id', 'unknown')}: {e}")
            return False
    
    def _calculate_data_quality_score(self, match_data: Dict[str, Any]) -> float:
        """Calcule un score de qualité des données (0-1)"""
        score = 0.0
        total_checks = 10
        
        # Vérifications de base
        if match_data.get('event_id'):
            score += 0.1
        if match_data.get('home_team') and match_data.get('away_team'):
            score += 0.1
        if match_data.get('league_name'):
            score += 0.1
        if match_data.get('start_time'):
            score += 0.1
        
        # Qualité des cotes
        odds_fields = ['home_odds', 'draw_odds', 'away_odds', 'over_25_odds', 'under_25_odds']
        valid_odds = sum(1 for field in odds_fields 
                        if match_data.get(field) and 1.0 < match_data[field] < 100.0)
        score += (valid_odds / len(odds_fields)) * 0.4
        
        # Cohérence des cotes 1X2
        if all(match_data.get(field) for field in ['home_odds', 'draw_odds', 'away_odds']):
            total_prob = sum(1/match_data[field] for field in ['home_odds', 'draw_odds', 'away_odds'])
            if 0.9 <= total_prob <= 1.2:  # Probabilités cohérentes
                score += 0.1
        
        # Présence de résultats
        if match_data.get('result'):
            score += 0.1
        
        return min(1.0, score)
    
    def _update_league_stats(self, cursor: sqlite3.Cursor, league_id: int, conn: sqlite3.Connection):
        """Met à jour les statistiques d'une ligue"""
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO leagues (league_id, league_name, sport_id)
                SELECT DISTINCT league_id, league_name, sport_id 
                FROM matches WHERE league_id = ?
            ''', (league_id,))
            
            cursor.execute('''
                UPDATE leagues SET
                    total_matches = (
                        SELECT COUNT(*) FROM matches WHERE league_id = ? AND data_quality_score >= 0.5
                    ),
                    avg_odds_home = (
                        SELECT AVG(home_odds) FROM matches 
                        WHERE league_id = ? AND home_odds IS NOT NULL
                    ),
                    avg_odds_draw = (
                        SELECT AVG(draw_odds) FROM matches 
                        WHERE league_id = ? AND draw_odds IS NOT NULL
                    ),
                    avg_odds_away = (
                        SELECT AVG(away_odds) FROM matches 
                        WHERE league_id = ? AND away_odds IS NOT NULL
                    ),
                    last_updated = ?
                WHERE league_id = ?
            ''', (league_id, league_id, league_id, league_id, datetime.now().isoformat(), league_id))
            
        except Exception as e:
            self.logger.debug(f"Failed to update league stats for {league_id}: {e}")
    
    @ErrorHandler.handle_database_error
    def get_matches_with_complete_odds(self, limit: Optional[int] = None, 
                                     min_quality_score: float = 0.5) -> pd.DataFrame:
        """Récupère tous les matchs avec cotes complètes"""
        start_time = datetime.now()
        
        try:
            query = '''
                SELECT * FROM complete_matches 
                WHERE data_quality_score >= ?
                ORDER BY start_time DESC
            '''
            params = [min_quality_score]
            
            if limit:
                query += ' LIMIT ?'
                params.append(limit)
            
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                pinnacle_logger.log_database_operation(
                    'get_matches_with_complete_odds', 
                    'matches', 
                    len(df), 
                    execution_time
                )
                
                return df
                
        except Exception as e:
            self.logger.error(f"Failed to get complete matches: {e}")
            return pd.DataFrame()
    
    @ErrorHandler.handle_database_error
    def get_database_stats(self) -> Dict[str, Any]:
        """Statistiques détaillées de la base de données"""
        start_time = datetime.now()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Statistiques de base
                cursor.execute('SELECT COUNT(*) FROM matches')
                stats['total_matches'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM complete_matches')
                stats['matches_with_odds'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM settled_matches')
                stats['settled_matches'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(DISTINCT league_id) FROM matches WHERE league_id IS NOT NULL')
                stats['total_leagues'] = cursor.fetchone()[0]
                
                # Plage de dates
                cursor.execute('SELECT MIN(start_time), MAX(start_time) FROM matches WHERE start_time IS NOT NULL')
                date_range = cursor.fetchone()
                stats['date_range'] = {
                    'from': date_range[0],
                    'to': date_range[1]
                }
                
                # Statistiques de qualité
                cursor.execute('SELECT AVG(data_quality_score) FROM matches WHERE data_quality_score IS NOT NULL')
                avg_quality = cursor.fetchone()[0]
                stats['avg_data_quality'] = round(avg_quality, 3) if avg_quality else None
                
                cursor.execute('''
                    SELECT 
                        COUNT(CASE WHEN data_quality_score >= 0.8 THEN 1 END) as high_quality,
                        COUNT(CASE WHEN data_quality_score >= 0.5 AND data_quality_score < 0.8 THEN 1 END) as medium_quality,
                        COUNT(CASE WHEN data_quality_score < 0.5 THEN 1 END) as low_quality
                    FROM matches WHERE data_quality_score IS NOT NULL
                ''')
                quality_dist = cursor.fetchone()
                stats['quality_distribution'] = {
                    'high_quality': quality_dist[0],
                    'medium_quality': quality_dist[1], 
                    'low_quality': quality_dist[2]
                }
                
                # Statistiques du cache
                cursor.execute('SELECT COUNT(*) FROM similarity_cache')
                stats['cache_entries'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT SUM(access_count) FROM similarity_cache')
                total_access = cursor.fetchone()[0]
                stats['cache_total_hits'] = total_access or 0
                
                # Top ligues par nombre de matchs
                cursor.execute('''
                    SELECT league_name, COUNT(*) as match_count
                    FROM matches 
                    WHERE league_name IS NOT NULL
                    GROUP BY league_name 
                    ORDER BY match_count DESC 
                    LIMIT 10
                ''')
                stats['top_leagues'] = [
                    {'name': row[0], 'matches': row[1]} 
                    for row in cursor.fetchall()
                ]
                
                # Taille de la base de données
                cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                db_size = cursor.fetchone()[0]
                stats['database_size_mb'] = round(db_size / (1024 * 1024), 2)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                pinnacle_logger.log_database_operation(
                    'get_database_stats', 
                    'multiple', 
                    None, 
                    execution_time
                )
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {e}")
            return {}
    
    @ErrorHandler.handle_database_error  
    def clear_similarity_cache(self, older_than_hours: int = 24) -> int:
        """Vide le cache de similarité avec option de nettoyage sélectif"""
        start_time = datetime.now()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if older_than_hours > 0:
                    cursor.execute('''
                        DELETE FROM similarity_cache 
                        WHERE datetime(created_at) < datetime('now', '-' || ? || ' hours')
                    ''', (older_than_hours,))
                else:
                    cursor.execute('DELETE FROM similarity_cache')
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                pinnacle_logger.log_database_operation(
                    'clear_similarity_cache', 
                    'similarity_cache', 
                    deleted_count, 
                    execution_time
                )
                
                self.logger.info(f"Cleared {deleted_count} cache entries")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Failed to clear similarity cache: {e}")
            return 0
    
    def optimize_database(self) -> Dict[str, Any]:
        """Optimise la base de données (VACUUM, ANALYZE, etc.)"""
        start_time = datetime.now()
        results = {}
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Analyser les statistiques des tables
                self.logger.info("Analyzing database statistics...")
                cursor.execute('ANALYZE')
                results['analyze'] = 'completed'
                
                # Récupérer les stats avant optimisation
                cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                size_before = cursor.fetchone()[0]
                
                # VACUUM pour réorganiser et compacter
                self.logger.info("Vacuuming database...")
                cursor.execute('VACUUM')
                results['vacuum'] = 'completed'
                
                # Stats après optimisation
                cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                size_after = cursor.fetchone()[0]
                
                space_saved = size_before - size_after
                results['space_saved_mb'] = round(space_saved / (1024 * 1024), 2)
                results['size_before_mb'] = round(size_before / (1024 * 1024), 2)
                results['size_after_mb'] = round(size_after / (1024 * 1024), 2)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                results['execution_time'] = execution_time
                
                self.logger.info(f"Database optimization completed in {execution_time:.2f}s")
                self.logger.info(f"Space saved: {results['space_saved_mb']} MB")
                
                return results
                
        except Exception as e:
            self.logger.error(f"Database optimization failed: {e}")
            return {'error': str(e)}
    
    def backup_database(self, backup_path: Optional[str] = None) -> str:
        """Crée une sauvegarde de la base de données"""
        if not backup_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{self.db_path}.backup_{timestamp}"
        
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            
            self.logger.info(f"Database backed up to: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            raise DatabaseError(f"Backup failed: {e}")
    
    def get_performance_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Récupère les métriques de performance de la base"""
        try:
            with self.get_connection() as conn:
                query = '''
                    SELECT 
                        operation,
                        component,
                        COUNT(*) as operation_count,
                        AVG(execution_time) as avg_time,
                        MAX(execution_time) as max_time,
                        MIN(execution_time) as min_time,
                        SUM(records_affected) as total_records
                    FROM performance_logs 
                    WHERE datetime(timestamp) > datetime('now', '-' || ? || ' hours')
                    GROUP BY operation, component
                    ORDER BY avg_time DESC
                '''
                
                df = pd.read_sql_query(query, conn, params=[hours])
                return df.to_dict('records')
                
        except Exception as e:
            self.logger.error(f"Failed to get performance metrics: {e}")
            return []