#!/bin/bash

# Script de démarrage pour le système Pinnacle amélioré
# Ce script lance les différents composants du système

set -e

echo "🚀 Démarrage du système Pinnacle Betting - Version 2.0"
echo "=================================================="

# Fonction d'affichage coloré
print_status() {
    echo -e "\033[1;32m[INFO]\033[0m $1"
}

print_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

print_warning() {
    echo -e "\033[1;33m[WARN]\033[0m $1"
}

# Vérifier les prérequis
print_status "Vérification des prérequis..."

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 n'est pas installé"
    exit 1
fi

# Vérifier pip
if ! command -v pip &> /dev/null; then
    print_error "pip n'est pas installé"
    exit 1
fi

# Créer les répertoires nécessaires
print_status "Création des répertoires nécessaires..."
mkdir -p data
mkdir -p logs
mkdir -p backups

# Installer les dépendances si nécessaire
if [ ! -f ".dependencies_installed" ]; then
    print_status "Installation des dépendances..."
    pip install -r requirements.txt
    touch .dependencies_installed
else
    print_status "Dépendances déjà installées"
fi

# Vérifier le fichier .env
if [ ! -f ".env" ]; then
    print_warning "Fichier .env manquant, copie depuis .env.example"
    cp .env.example .env
    print_warning "⚠️  N'oubliez pas de configurer votre clé API dans le fichier .env"
fi

# Fonction pour tester la configuration
test_config() {
    print_status "Test de la configuration..."
    python3 -c "
from config.config import Config
try:
    Config.validate_config()
    print('✅ Configuration valide')
except Exception as e:
    print(f'❌ Erreur de configuration: {e}')
    exit(1)
"
}

# Fonction pour lancer les tests
run_tests() {
    print_status "Exécution des tests automatisés..."
    if python3 tests/test_complete_system.py; then
        print_status "✅ Tous les tests sont passés"
    else
        print_error "❌ Certains tests ont échoué"
        read -p "Continuer malgré les échecs de tests? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Fonction pour lancer l'application Streamlit
start_streamlit() {
    print_status "Démarrage de l'interface Streamlit..."
    export PYTHONPATH="/app:$PYTHONPATH"
    
    # Démarrer en arrière-plan
    nohup streamlit run app/streamlit_app.py \
        --server.port 8501 \
        --server.address 0.0.0.0 \
        --server.headless true \
        --server.fileWatcherType none \
        > logs/streamlit.log 2>&1 &
    
    STREAMLIT_PID=$!
    echo $STREAMLIT_PID > logs/streamlit.pid
    
    print_status "Interface Streamlit démarrée (PID: $STREAMLIT_PID)"
    print_status "Accessible sur http://localhost:8501"
}

# Fonction pour lancer l'API REST
start_api() {
    print_status "Démarrage de l'API REST..."
    export PYTHONPATH="/app:$PYTHONPATH"
    
    # Démarrer en arrière-plan
    nohup python3 -m uvicorn src.api_server:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 1 \
        --access-log \
        > logs/api.log 2>&1 &
    
    API_PID=$!
    echo $API_PID > logs/api.pid
    
    print_status "API REST démarrée (PID: $API_PID)"
    print_status "Documentation accessible sur http://localhost:8000/api/docs"
}

# Fonction pour arrêter les services
stop_services() {
    print_status "Arrêt des services..."
    
    # Arrêter Streamlit
    if [ -f "logs/streamlit.pid" ]; then
        STREAMLIT_PID=$(cat logs/streamlit.pid)
        if kill -0 $STREAMLIT_PID 2>/dev/null; then
            kill $STREAMLIT_PID
            print_status "Interface Streamlit arrêtée"
        fi
        rm -f logs/streamlit.pid
    fi
    
    # Arrêter l'API
    if [ -f "logs/api.pid" ]; then
        API_PID=$(cat logs/api.pid)
        if kill -0 $API_PID 2>/dev/null; then
            kill $API_PID
            print_status "API REST arrêtée"
        fi
        rm -f logs/api.pid
    fi
}

# Fonction pour afficher le statut
show_status() {
    echo "Status des services:"
    echo "==================="
    
    # Vérifier Streamlit
    if [ -f "logs/streamlit.pid" ]; then
        STREAMLIT_PID=$(cat logs/streamlit.pid)
        if kill -0 $STREAMLIT_PID 2>/dev/null; then
            echo "✅ Interface Streamlit: Running (PID: $STREAMLIT_PID)"
        else
            echo "❌ Interface Streamlit: Stopped"
        fi
    else
        echo "❌ Interface Streamlit: Not started"
    fi
    
    # Vérifier l'API
    if [ -f "logs/api.pid" ]; then
        API_PID=$(cat logs/api.pid)
        if kill -0 $API_PID 2>/dev/null; then
            echo "✅ API REST: Running (PID: $API_PID)"
        else
            echo "❌ API REST: Stopped"
        fi
    else
        echo "❌ API REST: Not started"
    fi
    
    echo ""
    echo "Liens utiles:"
    echo "- Interface web: http://localhost:8501"
    echo "- API Documentation: http://localhost:8000/api/docs"
    echo "- Logs: tail -f logs/*.log"
}

# Fonction pour collecter des données de test
collect_sample_data() {
    print_status "Collecte de données d'exemple..."
    export PYTHONPATH="/app:$PYTHONPATH"
    
    python3 -c "
from src.data_collector import PinnacleDataCollector
from src.database_manager import DatabaseManager

collector = PinnacleDataCollector()
print('Collecte de données de test en cours...')

try:
    result = collector.collect_current_markets()
    print(f'✅ {result[\"collected\"]} matchs collectés, {result[\"errors\"]} erreurs')
except Exception as e:
    print(f'❌ Erreur lors de la collecte: {e}')
    print('ℹ️  Ceci est normal si vous n\\'avez pas de clé API valide')
    
    # Créer des données de test fictives
    db = DatabaseManager()
    import random
    
    print('Création de données de test fictives...')
    for i in range(50):
        test_match = {
            'event_id': 1000 + i,
            'home_team': f'Équipe Domicile {i+1}',
            'away_team': f'Équipe Extérieur {i+1}',
            'league_name': ['Premier League', 'La Liga', 'Serie A', 'Bundesliga'][i % 4],
            'home_odds': round(1.5 + random.random() * 3, 2),
            'draw_odds': round(2.8 + random.random() * 1.5, 2),
            'away_odds': round(1.5 + random.random() * 3, 2),
            'over_25_odds': round(1.6 + random.random() * 0.8, 2),
            'under_25_odds': round(1.6 + random.random() * 0.8, 2),
            'result': ['H', 'D', 'A'][i % 3] if i % 3 == 0 else None
        }
        db.save_match(test_match)
    
    print('✅ 50 matchs de test créés')
"
}

# Traitement des arguments de ligne de commande
case "${1:-help}" in
    "start")
        test_config
        start_streamlit
        start_api
        sleep 3
        show_status
        print_status "🎉 Système démarré avec succès!"
        print_status "Utilisez './start.sh status' pour vérifier l'état"
        print_status "Utilisez './start.sh stop' pour arrêter les services"
        ;;
    
    "stop")
        stop_services
        print_status "✅ Tous les services ont été arrêtés"
        ;;
    
    "restart")
        stop_services
        sleep 2
        test_config
        start_streamlit
        start_api
        sleep 3
        show_status
        print_status "🔄 Système redémarré avec succès!"
        ;;
    
    "status")
        show_status
        ;;
    
    "test")
        test_config
        run_tests
        ;;
    
    "setup")
        test_config
        collect_sample_data
        print_status "✅ Configuration initiale terminée"
        ;;
    
    "logs")
        if [ -n "$2" ]; then
            tail -f logs/$2.log
        else
            echo "Logs disponibles:"
            ls -la logs/*.log 2>/dev/null || echo "Aucun fichier de log trouvé"
            echo ""
            echo "Usage: ./start.sh logs [streamlit|api]"
        fi
        ;;
    
    "help"|*)
        echo "Système Pinnacle Betting - Version 2.0"
        echo "Usage: $0 {start|stop|restart|status|test|setup|logs|help}"
        echo ""
        echo "Commandes:"
        echo "  start     - Démarre tous les services"
        echo "  stop      - Arrête tous les services"
        echo "  restart   - Redémarre tous les services"
        echo "  status    - Affiche l'état des services"
        echo "  test      - Lance les tests automatisés"
        echo "  setup     - Configuration initiale avec données d'exemple"
        echo "  logs      - Affiche les logs (spécifier streamlit ou api)"
        echo "  help      - Affiche cette aide"
        echo ""
        echo "Exemples:"
        echo "  $0 start              # Démarre le système"
        echo "  $0 status             # Vérifie l'état"
        echo "  $0 logs streamlit     # Suit les logs Streamlit"
        echo "  $0 setup              # Configuration initiale"
        ;;
esac