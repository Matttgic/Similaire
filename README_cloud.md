# ⚽ Système de Paris Pinnacle - Version Streamlit Cloud

## 🚀 Application de Similarité des Cotes Sportives

Cette application analyse la similarité entre les cotes sportives actuelles et les données historiques pour fournir des insights précieux sur les paris sportifs.

### ✨ Fonctionnalités

- **🔍 Analyse de Similarité** : 3 algorithmes (cosinus, euclidienne, pourcentage)
- **📊 Statistiques Avancées** : Analyse des résultats historiques
- **📈 Visualisations** : Graphiques interactifs avec Plotly
- **🎯 Presets de Cotes** : Configurations prédéfinies
- **💡 Validation Intelligente** : Contrôle de cohérence des cotes
- **🏆 Analyse de Résultats** : Prédictions basées sur l'historique

### 🛠️ Technologies Utilisées

- **Frontend** : Streamlit
- **Calculs** : NumPy, Pandas, Scikit-learn
- **Visualisations** : Plotly
- **Base de données** : SQLite (embarquée)
- **API** : Intégration Pinnacle Sports

### 📱 Utilisation

1. **Saisir les cotes** du match à analyser
2. **Choisir la méthode** de calcul de similarité
3. **Ajuster les paramètres** (seuil, nombre de matchs)
4. **Lancer l'analyse** pour obtenir les résultats
5. **Explorer les résultats** dans les différents onglets

### ⚙️ Configuration

L'application utilise les **Streamlit Secrets** pour la configuration :

```toml
# .streamlit/secrets.toml
RAPIDAPI_KEY = "your_pinnacle_api_key_here"
```

### 🎯 Métriques d'Analyse

- **Similarité moyenne** : Score de ressemblance global
- **Distribution des résultats** : Statistiques 1X2 historiques  
- **Analyse par ligue** : Répartition des matchs similaires
- **Scores de confiance** : Niveau de fiabilité des prédictions

### 📊 Algorithmes de Similarité

1. **Cosinus** : Mesure l'angle entre les vecteurs de cotes
2. **Euclidienne** : Calcule la distance géométrique
3. **Pourcentage** : Analyse les différences relatives

### 🔧 Développement Local

Pour tester localement :

```bash
pip install -r requirements_cloud.txt
streamlit run streamlit_cloud_app.py
```

---

**Version Cloud** - Optimisée pour Streamlit Community Cloud