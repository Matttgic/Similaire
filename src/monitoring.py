"""
Système de métriques et monitoring pour le système Pinnacle
"""
import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, asdict

from config.config import Config
from src.logger import get_logger, pinnacle_logger

@dataclass
class Metric:
    """Représentation d'une métrique"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = None
    unit: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'tags': self.tags or {},
            'unit': self.unit
        }

class MetricsCollector:
    """Collecteur de métriques système et application"""
    
    def __init__(self):
        self.logger = get_logger('metrics')
        self._metrics_buffer = deque(maxlen=10000)  # Buffer circulaire
        self._counters = defaultdict(int)
        self._gauges = defaultdict(float)
        self._histograms = defaultdict(list)
        self._timers = {}
        self._lock = threading.Lock()
        
        # Statistiques système
        self._system_stats = {
            'start_time': datetime.now(),
            'total_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def increment_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """Incrémente un compteur"""
        with self._lock:
            key = f"{name}:{str(sorted((tags or {}).items()))}"
            self._counters[key] += value
            
            metric = Metric(
                name=name,
                value=self._counters[key],
                timestamp=datetime.now(),
                tags=tags,
                unit="count"
            )
            self._metrics_buffer.append(metric)
    
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None, unit: str = ""):
        """Définit la valeur d'une jauge"""
        with self._lock:
            key = f"{name}:{str(sorted((tags or {}).items()))}"
            self._gauges[key] = value
            
            metric = Metric(
                name=name,
                value=value,
                timestamp=datetime.now(),
                tags=tags,
                unit=unit
            )
            self._metrics_buffer.append(metric)
    
    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None, unit: str = ""):
        """Enregistre une valeur dans un histogramme"""
        with self._lock:
            key = f"{name}:{str(sorted((tags or {}).items()))}"
            self._histograms[key].append(value)
            
            # Garder seulement les 1000 dernières valeurs
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-1000:]
            
            metric = Metric(
                name=name,
                value=value,
                timestamp=datetime.now(),
                tags=tags,
                unit=unit
            )
            self._metrics_buffer.append(metric)
    
    def start_timer(self, name: str, tags: Dict[str, str] = None) -> str:
        """Démarre un timer et retourne son ID"""
        timer_id = f"{name}:{str(sorted((tags or {}).items()))}:{time.time()}"
        self._timers[timer_id] = {
            'name': name,
            'start_time': time.time(),
            'tags': tags
        }
        return timer_id
    
    def stop_timer(self, timer_id: str) -> float:
        """Arrête un timer et enregistre la durée"""
        if timer_id not in self._timers:
            self.logger.warning(f"Timer {timer_id} not found")
            return 0.0
        
        timer_info = self._timers.pop(timer_id)
        duration = time.time() - timer_info['start_time']
        
        self.record_histogram(
            f"{timer_info['name']}.duration",
            duration,
            timer_info['tags'],
            "seconds"
        )
        
        return duration
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Collecte les métriques système"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('.')
            
            return {
                'cpu': {
                    'percent': cpu_percent,
                    'count': psutil.cpu_count()
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                },
                'uptime': (datetime.now() - self._system_stats['start_time']).total_seconds()
            }
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
            return {}
    
    def get_application_metrics(self) -> Dict[str, Any]:
        """Collecte les métriques de l'application"""
        with self._lock:
            # Calculer les statistiques des histogrammes
            histogram_stats = {}
            for key, values in self._histograms.items():
                if values:
                    import numpy as np
                    histogram_stats[key] = {
                        'count': len(values),
                        'mean': np.mean(values),
                        'median': np.median(values),
                        'p95': np.percentile(values, 95),
                        'p99': np.percentile(values, 99),
                        'min': min(values),
                        'max': max(values)
                    }
            
            return {
                'counters': dict(self._counters),
                'gauges': dict(self._gauges),
                'histograms': histogram_stats,
                'active_timers': len(self._timers),
                'metrics_buffer_size': len(self._metrics_buffer),
                'system_stats': self._system_stats.copy()
            }
    
    def get_recent_metrics(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Récupère les métriques récentes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self._lock:
            recent_metrics = [
                metric.to_dict() 
                for metric in self._metrics_buffer 
                if metric.timestamp >= cutoff_time
            ]
        
        return recent_metrics
    
    def clear_metrics(self):
        """Vide toutes les métriques"""
        with self._lock:
            self._metrics_buffer.clear()
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._timers.clear()
            self.logger.info("All metrics cleared")

class PerformanceMonitor:
    """Moniteur de performance pour les opérations critiques"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.logger = get_logger('performance')
        self._alerts = []
        self._thresholds = {
            'api_response_time': 5.0,  # secondes
            'database_query_time': 2.0,  # secondes
            'similarity_calculation_time': 10.0,  # secondes
            'memory_usage_percent': 85.0,  # pourcentage
            'cpu_usage_percent': 90.0,  # pourcentage
            'disk_usage_percent': 90.0,  # pourcentage
            'error_rate_percent': 10.0  # pourcentage
        }
    
    def monitor_function(self, operation_name: str, component: str = "unknown"):
        """Décorateur pour monitorer les performances d'une fonction"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Démarrer le timer
                timer_id = self.metrics.start_timer(
                    f"{operation_name}.execution_time",
                    tags={'component': component, 'function': func.__name__}
                )
                
                start_time = time.time()
                error_occurred = False
                
                try:
                    # Exécuter la fonction
                    result = func(*args, **kwargs)
                    
                    # Incrémenter le compteur de succès
                    self.metrics.increment_counter(
                        f"{operation_name}.success",
                        tags={'component': component}
                    )
                    
                    return result
                    
                except Exception as e:
                    error_occurred = True
                    
                    # Incrémenter le compteur d'erreurs
                    self.metrics.increment_counter(
                        f"{operation_name}.error",
                        tags={'component': component, 'error_type': type(e).__name__}
                    )
                    
                    raise
                    
                finally:
                    # Arrêter le timer
                    execution_time = self.metrics.stop_timer(timer_id)
                    
                    # Vérifier les seuils de performance
                    self._check_performance_thresholds(operation_name, execution_time)
                    
                    # Log de performance
                    pinnacle_logger.log_performance_metrics(component, {
                        'operation': operation_name,
                        'execution_time': execution_time,
                        'success': not error_occurred
                    })
            
            return wrapper
        return decorator
    
    def _check_performance_thresholds(self, operation_name: str, execution_time: float):
        """Vérifie si les seuils de performance sont dépassés"""
        threshold_key = f"{operation_name.lower()}_time"
        if threshold_key in self._thresholds:
            threshold = self._thresholds[threshold_key]
            if execution_time > threshold:
                alert = {
                    'type': 'performance_threshold_exceeded',
                    'operation': operation_name,
                    'execution_time': execution_time,
                    'threshold': threshold,
                    'timestamp': datetime.now(),
                    'severity': 'warning' if execution_time < threshold * 2 else 'critical'
                }
                self._alerts.append(alert)
                self.logger.warning(f"Performance threshold exceeded: {operation_name} took {execution_time:.3f}s (limit: {threshold}s)")
    
    def check_system_health(self) -> Dict[str, Any]:
        """Vérifie la santé générale du système"""
        health_status = {
            'status': 'healthy',
            'checks': {},
            'alerts': [],
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Métriques système
            system_metrics = self.metrics.get_system_metrics()
            
            # Vérifier l'utilisation de la mémoire
            if system_metrics.get('memory', {}).get('percent', 0) > self._thresholds['memory_usage_percent']:
                health_status['status'] = 'degraded'
                health_status['alerts'].append({
                    'type': 'high_memory_usage',
                    'value': system_metrics['memory']['percent'],
                    'threshold': self._thresholds['memory_usage_percent']
                })
            
            # Vérifier l'utilisation du CPU
            if system_metrics.get('cpu', {}).get('percent', 0) > self._thresholds['cpu_usage_percent']:
                health_status['status'] = 'degraded'
                health_status['alerts'].append({
                    'type': 'high_cpu_usage',
                    'value': system_metrics['cpu']['percent'],
                    'threshold': self._thresholds['cpu_usage_percent']
                })
            
            # Vérifier l'utilisation du disque
            if system_metrics.get('disk', {}).get('percent', 0) > self._thresholds['disk_usage_percent']:
                health_status['status'] = 'critical'
                health_status['alerts'].append({
                    'type': 'high_disk_usage',
                    'value': system_metrics['disk']['percent'],
                    'threshold': self._thresholds['disk_usage_percent']
                })
            
            # Vérifier le taux d'erreur
            app_metrics = self.metrics.get_application_metrics()
            total_requests = sum(v for k, v in app_metrics['counters'].items() if 'success' in k or 'error' in k)
            total_errors = sum(v for k, v in app_metrics['counters'].items() if 'error' in k)
            
            if total_requests > 0:
                error_rate = (total_errors / total_requests) * 100
                if error_rate > self._thresholds['error_rate_percent']:
                    health_status['status'] = 'degraded'
                    health_status['alerts'].append({
                        'type': 'high_error_rate',
                        'value': error_rate,
                        'threshold': self._thresholds['error_rate_percent']
                    })
            
            health_status['checks'] = {
                'memory_usage': system_metrics.get('memory', {}).get('percent', 0),
                'cpu_usage': system_metrics.get('cpu', {}).get('percent', 0),
                'disk_usage': system_metrics.get('disk', {}).get('percent', 0),
                'error_rate': error_rate if total_requests > 0 else 0,
                'uptime': system_metrics.get('uptime', 0)
            }
            
        except Exception as e:
            health_status['status'] = 'unknown'
            health_status['error'] = str(e)
            self.logger.error(f"Health check failed: {e}")
        
        return health_status
    
    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Génère un rapport de performance détaillé"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        report = {
            'period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'duration_hours': hours
            },
            'system_metrics': self.metrics.get_system_metrics(),
            'application_metrics': self.metrics.get_application_metrics(),
            'alerts': [alert for alert in self._alerts if alert['timestamp'] >= start_time],
            'health_status': self.check_system_health()
        }
        
        return report
    
    def set_threshold(self, metric_name: str, value: float):
        """Définit un seuil d'alerte pour une métrique"""
        self._thresholds[metric_name] = value
        self.logger.info(f"Threshold set: {metric_name} = {value}")
    
    def get_alerts(self, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Récupère les alertes, optionnellement filtrées par sévérité"""
        if severity:
            return [alert for alert in self._alerts if alert.get('severity') == severity]
        return self._alerts.copy()
    
    def clear_alerts(self):
        """Vide toutes les alertes"""
        self._alerts.clear()
        self.logger.info("All alerts cleared")

# Instances globales pour l'utilisation dans l'application
metrics_collector = MetricsCollector()
performance_monitor = PerformanceMonitor(metrics_collector)

def get_metrics_collector() -> MetricsCollector:
    """Retourne l'instance du collecteur de métriques"""
    return metrics_collector

def get_performance_monitor() -> PerformanceMonitor:
    """Retourne l'instance du moniteur de performance"""
    return performance_monitor