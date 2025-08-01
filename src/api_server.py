"""
API REST pour le système de paris Pinnacle
Permet l'intégration externe et l'accès programmatique aux fonctionnalités
"""
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
import uvicorn

from config.config import Config
from src.similarity_engine import OddsSimilarityEngine
from src.database_manager import DatabaseManager
from src.data_collector import PinnacleDataCollector
from src.logger import get_logger, pinnacle_logger
from src.error_handler import ValidationManager, PinnacleError
from src.monitoring import get_metrics_collector, get_performance_monitor

# Configuration FastAPI
app = FastAPI(
    title="Pinnacle Betting Similarity API",
    description="API pour l'analyse de similarité des cotes de paris sportifs",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Logger et composants
logger = get_logger('api')
similarity_engine = OddsSimilarityEngine()
db_manager = DatabaseManager()
data_collector = PinnacleDataCollector()
validator = ValidationManager()
metrics = get_metrics_collector()
monitor = get_performance_monitor()

# Modèles Pydantic
class OddsInput(BaseModel):
    """Modèle pour les cotes d'entrée"""
    home: float
    draw: float
    away: float
    over_25: float
    under_25: float
    
    @validator('*')
    def validate_odds(cls, v):
        if v <= 1.0 or v > 1000:
            raise ValueError('Odds must be between 1.01 and 1000')
        return v

class SimilarityRequest(BaseModel):
    """Modèle pour une requête de similarité"""
    odds: OddsInput
    method: Optional[str] = "cosine"
    threshold: Optional[float] = 0.90
    min_matches: Optional[int] = 10
    
    @validator('method')
    def validate_method(cls, v):
        if v not in ['cosine', 'euclidean', 'percentage']:
            raise ValueError('Method must be one of: cosine, euclidean, percentage')
        return v
    
    @validator('threshold')
    def validate_threshold(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Threshold must be between 0 and 1')
        return v
    
    @validator('min_matches')
    def validate_min_matches(cls, v):
        if v < 1 or v > 100:
            raise ValueError('min_matches must be between 1 and 100')
        return v

class DataCollectionRequest(BaseModel):
    """Modèle pour les requêtes de collecte de données"""
    max_events: Optional[int] = 1000
    source: Optional[str] = "current"  # current, historical
    
    @validator('max_events')
    def validate_max_events(cls, v):
        if v < 1 or v > 10000:
            raise ValueError('max_events must be between 1 and 10000')
        return v

# Décorateurs et middleware personnalisés
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware pour collecter les métriques des requêtes"""
    start_time = time.time()
    
    # Incrémenter le compteur de requêtes
    metrics.increment_counter(
        "api.requests.total",
        tags={"method": request.method, "endpoint": request.url.path}
    )
    
    try:
        response = await call_next(request)
        
        # Enregistrer la durée de traitement
        processing_time = time.time() - start_time
        metrics.record_histogram(
            "api.request.duration",
            processing_time,
            tags={"method": request.method, "endpoint": request.url.path, "status": str(response.status_code)},
            unit="seconds"
        )
        
        # Incrémenter le compteur de succès
        if response.status_code < 400:
            metrics.increment_counter(
                "api.requests.success",
                tags={"method": request.method, "endpoint": request.url.path}
            )
        else:
            metrics.increment_counter(
                "api.requests.error",
                tags={"method": request.method, "endpoint": request.url.path, "status": str(response.status_code)}
            )
        
        # Ajouter les headers de performance
        response.headers["X-Processing-Time"] = str(processing_time)
        return response
        
    except Exception as e:
        processing_time = time.time() - start_time
        
        # Incrémenter le compteur d'erreurs
        metrics.increment_counter(
            "api.requests.error",
            tags={"method": request.method, "endpoint": request.url.path, "error": type(e).__name__}
        )
        
        logger.error(f"API request failed: {request.method} {request.url.path} - {e}")
        raise

# Routes de l'API

@app.get("/api/health")
@monitor.monitor_function("health_check", "api")
async def health_check():
    """Vérification de l'état de santé de l'API"""
    health_status = monitor.check_system_health()
    
    return {
        "status": health_status["status"],
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "uptime": health_status["checks"].get("uptime", 0),
        "checks": health_status["checks"]
    }

@app.get("/api/metrics")
@monitor.monitor_function("get_metrics", "api")
async def get_metrics():
    """Récupère les métriques de l'application"""
    return {
        "system_metrics": metrics.get_system_metrics(),
        "application_metrics": metrics.get_application_metrics(),
        "recent_metrics": metrics.get_recent_metrics(60)  # Dernière heure
    }

@app.post("/api/similarity/analyze")
@monitor.monitor_function("similarity_analysis", "api")
async def analyze_similarity(request: SimilarityRequest):
    """Analyse la similarité pour des cotes données"""
    try:
        # Convertir le modèle Pydantic en dictionnaire
        odds_dict = {
            'home': request.odds.home,
            'draw': request.odds.draw,
            'away': request.odds.away,
            'over_25': request.odds.over_25,
            'under_25': request.odds.under_25
        }
        
        # Validation supplémentaire
        validation_errors = validator.validate_odds_input(odds_dict)
        if validation_errors:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid odds input",
                    "details": validation_errors
                }
            )
        
        # Trouver les matchs similaires
        similar_matches = similarity_engine.find_similar_matches(
            odds_dict,
            method=request.method,
            threshold=request.threshold,
            min_matches=request.min_matches
        )
        
        # Analyser les résultats
        analysis = similarity_engine.analyze_similar_matches(similar_matches)
        
        # Log de l'utilisation de l'API
        pinnacle_logger.log_user_action(
            "api_similarity_analysis",
            user_input=f"method={request.method}, threshold={request.threshold}",
            results=f"found {len(similar_matches)} matches"
        )
        
        return {
            "success": True,
            "request_params": {
                "method": request.method,
                "threshold": request.threshold,
                "min_matches": request.min_matches
            },
            "similar_matches": similar_matches[:50],  # Limiter la réponse
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }
        
    except PinnacleError as e:
        logger.error(f"Pinnacle error in similarity analysis: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in similarity analysis: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/similarity/methods")
@monitor.monitor_function("get_similarity_methods", "api")
async def get_similarity_methods():
    """Récupère la liste des méthodes de similarité disponibles"""
    return {
        "methods": Config.SIMILARITY_METHODS,
        "default_method": Config.DEFAULT_SIMILARITY_METHOD,
        "descriptions": {
            "cosine": "Mesure l'angle entre deux vecteurs de cotes",
            "euclidean": "Mesure la distance géométrique entre les cotes",
            "percentage": "Calcule la différence relative moyenne"
        }
    }

@app.post("/api/similarity/compare-methods")
@monitor.monitor_function("compare_methods", "api")
async def compare_methods(odds: OddsInput):
    """Compare les résultats selon différentes méthodes"""
    try:
        odds_dict = {
            'home': odds.home,
            'draw': odds.draw,
            'away': odds.away,
            'over_25': odds.over_25,
            'under_25': odds.under_25
        }
        
        comparison = similarity_engine.get_method_comparison(odds_dict)
        
        return {
            "success": True,
            "odds": odds_dict,
            "method_comparison": comparison,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in method comparison: {e}")
        raise HTTPException(status_code=500, detail="Method comparison failed")

@app.get("/api/database/stats")
@monitor.monitor_function("get_database_stats", "api")
async def get_database_stats():
    """Récupère les statistiques de la base de données"""
    try:
        stats = db_manager.get_database_stats()
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get database stats")

@app.post("/api/data/collect")
@monitor.monitor_function("data_collection", "api")
async def collect_data(request: DataCollectionRequest, background_tasks: BackgroundTasks):
    """Lance la collecte de données en arrière-plan"""
    try:
        if request.source == "current":
            background_tasks.add_task(
                data_collector.collect_current_markets
            )
            message = f"Current markets collection started (max {request.max_events} events)"
        elif request.source == "historical":
            background_tasks.add_task(
                data_collector.collect_historical_data,
                request.max_events
            )
            message = f"Historical data collection started (max {request.max_events} events)"
        else:
            raise HTTPException(status_code=400, detail="Invalid source. Must be 'current' or 'historical'")
        
        return {
            "success": True,
            "message": message,
            "source": request.source,
            "max_events": request.max_events,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error starting data collection: {e}")
        raise HTTPException(status_code=500, detail="Failed to start data collection")

@app.get("/api/data/collection-stats")
@monitor.monitor_function("get_collection_stats", "api")
async def get_collection_stats():
    """Récupère les statistiques de collecte de données"""
    try:
        stats = data_collector.get_collection_stats()
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting collection stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get collection stats")

@app.delete("/api/cache/similarity")
@monitor.monitor_function("clear_cache", "api")
async def clear_similarity_cache():
    """Vide le cache de similarité"""
    try:
        deleted_count = db_manager.clear_similarity_cache()
        similarity_engine.clear_cache()
        
        return {
            "success": True,
            "message": f"Cache cleared successfully. {deleted_count} entries deleted.",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")

@app.post("/api/database/optimize")
@monitor.monitor_function("optimize_database", "api")
async def optimize_database(background_tasks: BackgroundTasks):
    """Optimise la base de données en arrière-plan"""
    try:
        background_tasks.add_task(db_manager.optimize_database)
        
        return {
            "success": True,
            "message": "Database optimization started in background",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error starting database optimization: {e}")
        raise HTTPException(status_code=500, detail="Failed to start database optimization")

@app.get("/api/performance/report")
@monitor.monitor_function("get_performance_report", "api")
async def get_performance_report(hours: int = 24):
    """Génère un rapport de performance"""
    try:
        if hours < 1 or hours > 168:  # Max 1 semaine
            raise HTTPException(status_code=400, detail="Hours must be between 1 and 168")
        
        report = monitor.get_performance_report(hours)
        return {
            "success": True,
            "report": report,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating performance report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate performance report")

@app.get("/api/alerts")
@monitor.monitor_function("get_alerts", "api")
async def get_alerts(severity: Optional[str] = None):
    """Récupère les alertes système"""
    try:
        if severity and severity not in ['warning', 'critical']:
            raise HTTPException(status_code=400, detail="Severity must be 'warning' or 'critical'")
        
        alerts = monitor.get_alerts(severity)
        return {
            "success": True,
            "alerts": alerts,
            "count": len(alerts),
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alerts")

# Gestionnaire d'erreurs global
@app.exception_handler(PinnacleError)
async def pinnacle_error_handler(request: Request, exc: PinnacleError):
    """Gestionnaire pour les erreurs Pinnacle personnalisées"""
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": "PinnacleError",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Gestionnaire d'erreurs général"""
    logger.error(f"Unhandled exception in API: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "timestamp": datetime.now().isoformat()
        }
    )

# Event handlers
@app.on_event("startup")
async def startup_event():
    """Actions à effectuer au démarrage de l'API"""
    logger.info("Starting Pinnacle Betting Similarity API v2.0.0")
    
    # Vérifier la configuration
    try:
        Config.validate_config()
        logger.info("Configuration validation passed")
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise
    
    # Initialiser les métriques de base
    metrics.set_gauge("api.status", 1, tags={"status": "starting"})
    logger.info("API startup completed successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Actions à effectuer à l'arrêt de l'API"""
    logger.info("Shutting down Pinnacle Betting Similarity API")
    
    # Nettoyer les ressources si nécessaire
    metrics.set_gauge("api.status", 0, tags={"status": "shutdown"})
    logger.info("API shutdown completed")

# Point d'entrée pour le serveur de développement
if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=Config.DEBUG,
        log_level="info"
    )