.PHONY: install run test clean backup collect-data docker-build docker-run

# Installation des dépendances
install:
	pip install -r requirements.txt
	mkdir -p data

# Lancer l'application Streamlit
run:
	streamlit run app/streamlit_app.py

# Lancer les tests
test:
	python -m pytest tests/ -v

# Collecter les données historiques
collect-data:
	python scripts/collect_historical_data.py --max-events 5000

# Mise à jour des résultats
update-results:
	python scripts/update_results.py --days-back 7

# Sauvegarde de la base
backup:
	python scripts/backup_database.py backup

# Nettoyage des fichiers temporaires
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.log" -delete

# Construction de l'image Docker
docker-build:
docker build -t pinnacle-betting-system .

# Lancer avec Docker
docker-run:
	docker-compose up -d

# Arrêter Docker
docker-stop:
	docker-compose down

# Développement avec rechargement automatique
dev:
	streamlit run app/streamlit_app.py --server.runOnSave true

# Initialisation complète du projet
setup: install
	cp .env.example .env
	@echo "⚠️  N'oubliez pas de configurer votre clé API dans le fichier .env"
	python scripts/collect_historical_data.py --max-events 1000
	@echo "✅ Projet initialisé avec succès!"

# Maintenance quotidienne
daily-maintenance:
	python scripts/update_results.py --days-back 2
	python scripts/backup_database.py backup
	python scripts/backup_database.py cleanup --keep-days 30

# Afficher l'aide
help:
	@echo "📋 Commandes disponibles:"
	@echo "  make install          - Installer les dépendances"
	@echo "  make run             - Lancer l'application Streamlit"
	@echo "  make test            - Lancer les tests"
	@echo "  make collect-data    - Collecter les données historiques"
	@echo "  make update-results  - Mettre à jour les résultats"
	@echo "  make backup          - Sauvegarder la base de données"
	@echo "  make clean           - Nettoyer les fichiers temporaires"
	@echo "  make docker-build    - Construire l'image Docker"
	@echo "  make docker-run      - Lancer avec Docker Compose"
	@echo "  make setup           - Configuration initiale complète"
	@echo "  make daily-maintenance - Maintenance quotidienne"
	@echo "  make help            - Afficher cette aide"
