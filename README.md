# ⚽ Système de Paris Pinnacle - Similarité des Cotes

Un système intelligent d'analyse de paris sportifs basé sur la similarité des cotes historiques de Pinnacle.

## 🎯 Fonctionnalités

- **Collecte automatique** des données historiques Pinnacle (10 ans)
- **Algorithmes de similarité** avancés (cosinus, euclidienne, pourcentage)
- **Interface Streamlit** intuitive pour l'analyse
- **Base de données SQLite** optimisée
- **Analyse statistique** complète des résultats
- **Export CSV** des résultats

## 📦 Installation

1. **Cloner le repository**
```bash
git clone https://github.com/votre-username/pinnacle-betting-system.git
cd pinnacle-betting-systemInstaller les dépendancespip install -r requirements.txtConfigurationcp .env.example .env
# Éditer .env avec votre clé APICréer les répertoiresmkdir data🚀 Utilisation1. Collecte des données historiquespython scripts/collect_historical_data.py --max-events 50002. Lancer l'applicationstreamlit run app/streamlit_app.py3. Utiliser l'interfaceSaisir les cotes d'un match à venirAjuster les paramètres de similaritéAnalyser les résultats basés sur l'historique🔧 ConfigurationVariables d'environnement (.env)RAPIDAPI_KEY=votre_cle_api_ici
DATABASE_PATH=data/football_odds.db
SIMILARITY_THRESHOLD=0.90
MIN_SIMILAR_MATCHES=10Paramètres principauxSeuil de similarité: 90% par défautNombre min de matchs: 10 par défautMéthodes de similarité: cosinus, euclidienne, pourcentage📊 Structure des donnéesMarchés analysés1X2: Victoire domicile/nul/extérieurO/U 2.5: Plus/moins de 2.5 butsBTTS: Both Teams To Score (futur)Base de donnéesmatches: Données des matchs avec cotes et résultats
- **leagues**: Informations sur les ligues
- **similarity_cache**: Cache des résultats de similarité

### Format des cotes
```json
{
  "home": 2.10,
  "draw": 3.40, 
  "away": 3.20,
  "over_25": 1.85,
  "under_25": 1.95
}🧮 Algorithmes de similarité1. Similarité CosinusMesure l'angle entre deux vecteurs de cotesValeurs: 0 (différent) à 1 (identique)Recommandé pour la plupart des cas2. Distance EuclidienneMesure la distance géométrique entre les cotesNormalisée entre 0 et 1Sensible aux écarts absolus3. Pourcentage de différenceCalcule la différence relative moyenneBon pour identifier des cotes proportionnellement similaires📈 Métriques d'analyseRésultats 1X2Pourcentage de victoires domicile/nul/extérieurBasé sur les matchs avec résultats connusOver/Under 2.5 butsPourcentage de matchs avec plus/moins de 2.5 butsAnalyse de la productivité offensiveBTTS (Both Teams To Score)Pourcentage de matchs où les deux équipes marquentIndicateur de défenses perméables🔍 Exemple d'utilisationfrom src.similarity_engine import OddsSimilarityEngine

# Initialiser le moteur
engine = OddsSimilarityEngine()

# Cotes d'un match à venir
target_odds = {
    'home': 2.10,
    'draw': 3.40,
    'away': 3.20,
    'over_25': 1.85,
    'under_25': 1.95
}

# Trouver les matchs similaires
similar_matches = engine.find_similar_matches(target_odds)

# Analyser les résultats
analysis = engine.analyze_similar_matches(similar_matches)

print(f"Basé sur {analysis['total_matches']} matchs similaires:")
print(f"Victoires domicile: {analysis['results_analysis']['home_wins']['percentage']:.1f}%")🛠️ DéveloppementStructure du projetpinnacle-betting-system/
├── config/           # Configuration
├── src/             # Code source principal
├── app/             # Interface Streamlit
├── scripts/         # Scripts utilitaires
├── tests/           # Tests unitaires
└── data/            # Base de donnéesAjouter un nouveau marchéModifier config/config.py (section MARKETS)Mettre à jour database_manager.py (schéma DB)Adapter data_collector.py (extraction API)Modifier similarity_engine.py (calculs)Testspython -m pytest tests/📚 API PinnacleEndpoints utilisésGET /kit/v1/sports - Liste des sportsGET /kit/v1/markets - Marchés avec cotesGET /kit/v1/archive - Événements archivésGET /kit/v1/details/{event_id} - Détails d'un événementRate LimitingDélai de 0.1s entre les appelsGestion automatique des erreursCache pour éviter les appels répétés⚠️ LimitationsDonnéesQualité dépendante de l'API PinnacleRésultats parfois manquantsCouverture variable selon les liguesAlgorithmesBasé uniquement sur les cotes (pas de form, blessures, etc.)Hypothèse que les cotes similaires = contextes similairesPerformance dépendante du volume de données historiquesTechniqueSQLite pour le prototypage (migrer vers PostgreSQL pour la production)Pas de mise à jour temps réelCache simple (améliorer avec Redis)📋 RoadmapVersion 1.1[ ] Intégration résultats automatique[ ] Marchés BTTS et Handicaps[ ] Filtrages par ligue/période[ ] Notifications par emailVersion 1.2[ ] Machine Learning (Random Forest, XGBoost)[ ] API REST pour intégrations externes[ ] Dashboard avancé avec Plotly Dash[ ] Backtesting automatiséVersion 2.0[ ] Multi-bookmakers (Bet365, William Hill)[ ] Streaming temps réel[ ] Mobile app (React Native)[ ] Algorithmes de portfolio optimization🤝 ContributionFork le projetCréer une branche feature (git checkout -b feature/amazing-feature)Commit vos changements (git commit -m 'Add amazing feature')Push vers la branche (git push origin feature/amazing-feature)Ouvrir une Pull RequestGuidelinesCode en anglais, commentaires en françaisTests unitaires obligatoiresDocumentation des nouvelles fonctionnalitésRespect PEP 8📄 LicenseCe projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.⚡ SupportIssues: GitHub IssuesDiscussions: GitHub DiscussionsEmail: votre-email@example.com🙏 RemerciementsPinnacle Sports pour l'API de qualitéStreamlit pour l'interface utilisateurScikit-learn pour les algorithmes de similaritéLa communauté open-source⚠️ Avertissement: Ce système est à des fins éducatives et de recherche. Les paris sportifs comportent des risques. Pariez de manière responsable
