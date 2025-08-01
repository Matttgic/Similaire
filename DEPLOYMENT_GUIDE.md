# 🚀 Guide de Déploiement sur Streamlit Cloud

## 📋 Prérequis

1. **Compte GitHub** avec le repository
2. **Compte Streamlit Cloud** (gratuit sur [share.streamlit.io](https://share.streamlit.io))
3. **Clé API Pinnacle** (optionnelle, l'app fonctionne avec des données de test)

## 🔧 Étapes de Déploiement

### 1. Préparer le Repository

**Fichiers nécessaires dans votre repository :**

```
votre-repo/
├── streamlit_cloud_app.py      # Application principale
├── requirements_cloud.txt      # Dépendances Python
├── README_cloud.md            # Documentation
├── .streamlit/
│   ├── config.toml           # Configuration Streamlit
│   └── secrets.toml.example  # Exemple de secrets
```

### 2. Configuration des Fichiers

**requirements_cloud.txt** (déjà créé) :
```
streamlit==1.29.0
pandas==2.0.3
numpy==1.24.3
requests==2.31.0
scikit-learn==1.3.0
plotly==5.17.0
python-dotenv==1.0.0
scipy==1.11.4
psutil==5.9.8
```

**streamlit_cloud_app.py** (fichier principal - déjà créé)

### 3. Déploiement sur Streamlit Cloud

1. **Se connecter** à [share.streamlit.io](https://share.streamlit.io)

2. **Cliquer sur "New app"**

3. **Configuration du déploiement :**
   - **Repository** : `votre-username/votre-repo`
   - **Branch** : `main` (ou la branche de votre choix)
   - **Main file path** : `streamlit_cloud_app.py`
   - **App URL** : `votre-app-name` (sera accessible sur `votre-app-name.streamlit.app`)

### 4. Configuration des Secrets (Optionnel)

Dans l'interface Streamlit Cloud :

1. **Aller dans "Advanced settings"**
2. **Ajouter les secrets** dans la section "Secrets" :

```toml
RAPIDAPI_KEY = "votre_cle_api_pinnacle_ici"
```

**⚠️ Important :** Les secrets sont optionnels. L'application fonctionne sans clé API en créant des données de test.

### 5. Déploiement Automatique

Une fois configuré, Streamlit Cloud :
- ✅ Clone automatiquement votre repository
- ✅ Installe les dépendances
- ✅ Lance l'application
- ✅ Fournit une URL publique

## 🎯 URLs d'Accès

Une fois déployée, votre application sera accessible sur :
- **URL principale** : `https://votre-app-name.streamlit.app`
- **URL de partage** : Partageable publiquement

## 🔍 Fonctionnalités de l'App Cloud

### ✨ Interface Simplifiée
- **Saisie de cotes** avec presets et validation
- **3 méthodes de similarité** (cosinus, euclidienne, pourcentage)
- **Analyse statistique** des matchs similaires
- **Visualisations interactives** avec Plotly

### 📊 Données Automatiques
- **200 matchs de test** créés automatiquement au premier lancement
- **5 ligues européennes** simulées
- **Données réalistes** avec résultats et cotes cohérentes

### 🎛️ Paramètres Configurables
- **Seuil de similarité** (70% à 99%)
- **Nombre minimum de matchs** (5 à 50)
- **Filtres avancés** par ligue et résultats

## 🛠️ Maintenance et Mises à Jour

### Mise à Jour Automatique
- **Push sur GitHub** → Redéploiement automatique
- **Temps de build** : ~2-3 minutes
- **Zéro downtime** pendant les mises à jour

### Monitoring
- **Logs en temps réel** dans l'interface Streamlit Cloud
- **Métriques d'usage** disponibles
- **Alertes automatiques** en cas d'erreur

## 🚨 Résolution des Problèmes

### Erreurs Communes

**1. Erreur de dépendances**
```
Solution : Vérifier requirements_cloud.txt
```

**2. Erreur de mémoire**
```
Solution : Optimiser les données en cache (@st.cache_resource)
```

**3. Erreur de secrets**
```
Solution : L'app fonctionne sans secrets (mode démo)
```

### Support et Debug

1. **Logs Streamlit Cloud** : Interface web → onglet "Logs"
2. **GitHub Issues** : Pour les bugs du code
3. **Streamlit Community** : [discuss.streamlit.io](https://discuss.streamlit.io)

## 📱 Test de Fonctionnement

### Vérifications Post-Déploiement

✅ **L'application se charge** sans erreur  
✅ **Données de test créées** (200 matchs)  
✅ **Saisie de cotes** fonctionnelle  
✅ **Calcul de similarité** opérationnel  
✅ **Visualisations** affichées correctement  
✅ **Interface responsive** sur mobile  

### Cas de Test

1. **Test basique** :
   - Utiliser preset "Match équilibré"
   - Lancer l'analyse
   - Vérifier résultats > 0

2. **Test avancé** :
   - Saisir cotes personnalisées
   - Modifier les paramètres
   - Explorer tous les onglets

## 🎨 Personnalisation

### Thème et Style
Modifier `.streamlit/config.toml` :

```toml
[theme]
primaryColor = "#1f77b4"        # Couleur principale
backgroundColor = "#ffffff"      # Arrière-plan
secondaryBackgroundColor = "#f0f2f6"  # Arrière-plan secondaire
textColor = "#262730"           # Couleur du texte
```

### Fonctionnalités Additionnelles
- Ajouter de nouveaux presets
- Intégrer d'autres sports
- Créer des alertes personnalisées
- Ajouter des exports de données

## 🔐 Sécurité et Limites

### Limites Streamlit Cloud (Plan Gratuit)
- **1 CPU** par application
- **800 MB RAM** maximum
- **1 GB stockage** pour les fichiers
- **Pas d'accès SSH/FTP**

### Bonnes Pratiques
- ✅ Utiliser `@st.cache_resource` pour les données lourdes
- ✅ Limiter les requêtes API externes
- ✅ Optimiser les calculs numpy/pandas
- ✅ Nettoyer les données en cache régulièrement

## 🎉 Application Déployée !

Une fois toutes ces étapes complétées, votre **Système de Paris Pinnacle** sera accessible mondialement sur **Streamlit Cloud** avec :

- ⚡ **Performance optimisée** pour le cloud
- 🔒 **Configuration sécurisée** avec secrets
- 📱 **Interface responsive** mobile/desktop
- 🚀 **Déploiement automatique** à chaque commit
- 📊 **Données de démonstration** intégrées

**URL d'exemple** : `https://pinnacle-betting-system.streamlit.app`

---

**🏆 Prêt pour la production sur Streamlit Cloud !**