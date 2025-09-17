# 🌐 DÉPLOIEMENT RENDER.COM - GUIDE COMPLET
# Bot Discord Thugz Life RP - Plan Gratuit

## ✅ AVANTAGES RENDER GRATUIT
- **750 heures/mois gratuites** (suffisant pour bot 24/7)
- **Déploiement automatique depuis GitHub**
- **SSL gratuit et domaine fourni**
- **Health checks intégrés**
- **Logs en temps réel**
- **Variables d'environnement sécurisées**

---

## 🚀 ÉTAPES DE DÉPLOIEMENT

### 1. Préparation du Repository GitHub

**Vérifier que le repo est à jour** :
```bash
cd "c:\Users\Okaze\Desktop\Julian\Thugz Labs\BOT Discord\DiscordTwitterBOT-main"
git status
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

### 2. Création du Service Render

1. **Aller sur https://render.com**
2. **Sign Up / Login** (connecter avec GitHub recommandé)
3. **Cliquer "New +"** dans le dashboard
4. **Choisir "Web Service"**
5. **Connecter le repository** : `TchikiBalianos/DiscordRPBot`

### 3. Configuration du Service

**Settings de base** :
```
Name: discord-bot-thugz
Region: Oregon (US West) - Gratuit
Branch: main
Runtime: Python 3
```

**Build & Deploy** :
```
Build Command: pip install -r requirements.txt
Start Command: python start.py
```

### 4. Variables d'Environnement

**Variables OBLIGATOIRES** :
```
DISCORD_TOKEN=votre_token_discord_bot
DISCORD_GUILD_ID=votre_server_id
SUPABASE_URL=votre_url_supabase
SUPABASE_KEY=votre_cle_supabase
```

**Variables RECOMMANDÉES** :
```
ENABLE_HEALTH_MONITOR=true
PORT=10000
PYTHON_VERSION=3.12.0
```

**Variables OPTIONNELLES** :
```
TWITTER_CONSUMER_KEY=votre_cle
TWITTER_CONSUMER_SECRET=votre_secret
TWITTER_ACCESS_TOKEN=votre_token
TWITTER_ACCESS_TOKEN_SECRET=votre_token_secret
```

### 5. Configuration Avancée

**Health Check** :
- Render vérifiera automatiquement le port 10000
- Notre health monitoring FastAPI répondra sur ce port
- Path: `/health` (automatiquement détecté)

**Auto-Deploy** :
- ✅ Activé par défaut
- Déploie automatiquement lors des push sur `main`

---

## 🔧 OPTIMISATIONS RENDER

### Modification pour Render (Port dynamique)

Render assigne automatiquement un port via la variable `PORT`. Notre `start.py` est déjà configuré pour ça :

```python
# Dans start.py - déjà configuré
health_port = int(os.getenv('PORT', os.getenv('HEALTH_PORT', 8000)))
```

### Render.yaml (Optionnel - Configuration avancée)

Si vous voulez une configuration plus précise, on peut créer un `render.yaml` :

```yaml
services:
- type: web
  name: discord-bot-thugz
  env: python
  buildCommand: pip install -r requirements.txt
  startCommand: python start.py
  envVars:
  - key: ENABLE_HEALTH_MONITOR
    value: true
  - key: PYTHON_VERSION  
    value: 3.12.0
```

---

## 🧪 TESTS POST-DÉPLOIEMENT

### 1. Vérification Santé

Après déploiement, votre bot sera accessible sur :
```
https://discord-bot-thugz.onrender.com
```

**Test des endpoints** :
```bash
# Health check principal
curl https://discord-bot-thugz.onrender.com/health

# Health détaillé
curl https://discord-bot-thugz.onrender.com/health/detailed

# Métriques
curl https://discord-bot-thugz.onrender.com/metrics
```

### 2. Validation Discord

- Le bot doit apparaître en ligne sur Discord
- Tester quelques commandes de base
- Vérifier les logs dans Render dashboard

### 3. UptimeRobot Setup

Configurer UptimeRobot avec :
```
URL: https://discord-bot-thugz.onrender.com/health
Keyword: alive
Interval: 5 minutes
```

---

## 📊 LIMITATIONS PLAN GRATUIT

### Render Free Tier :
- **750 heures/mois** (31 jours × 24h = 744h - parfait!)
- **Sleep après 15min d'inactivité** (health check évite ça)
- **Build time : 15 minutes max** (notre bot build en <2min)
- **1 service web gratuit**

### Solutions aux limitations :
- **Sleep Mode** : Notre health monitoring empêche le sleep
- **Cold Start** : Premier ping peut prendre 30s (normal)
- **Bandwidth** : Largement suffisant pour bot Discord

---

## 🔍 MONITORING RENDER

### Dashboard Render :
- **Metrics** : CPU, Memory, Network
- **Logs** : En temps réel, filtrage possible  
- **Events** : Déploiements, redémarrages
- **Settings** : Variables, configuration

### Health Checks automatiques :
- Render ping automatiquement votre service
- Si pas de réponse → redémarrage automatique
- Notre FastAPI health endpoint répond toujours

---

## 🛠️ TROUBLESHOOTING

### Problème : Build Failed
```bash
# Vérifier requirements.txt
cat requirements.txt

# Tester build localement
pip install -r requirements.txt
```

### Problème : Bot Offline Discord
1. Vérifier `DISCORD_TOKEN` dans Render
2. Consulter logs Render pour erreurs
3. Vérifier permissions bot Discord

### Problème : Health Check Failed
1. Vérifier que `ENABLE_HEALTH_MONITOR=true`
2. Tester endpoint : `/health`
3. Vérifier port configuration

### Commandes Debug :
```bash
# Logs en temps réel
# Via Render dashboard → Logs tab

# Variables d'environnement
# Via Render dashboard → Environment tab

# Redémarrage manuel
# Via Render dashboard → Manual Deploy
```

---

## 🎯 CHECKLIST DÉPLOIEMENT

### Pré-déploiement :
- [ ] Repository GitHub à jour
- [ ] Variables d'environnement préparées
- [ ] Tokens Discord et Supabase valides

### Déploiement :
- [ ] Service Render créé
- [ ] Repository connecté
- [ ] Variables configurées
- [ ] Build réussi

### Post-déploiement :
- [ ] Bot en ligne sur Discord
- [ ] Health endpoint accessible
- [ ] Commandes bot fonctionnelles
- [ ] UptimeRobot configuré

### Validation 24h :
- [ ] Uptime stable >99%
- [ ] Aucun cold start inattendu
- [ ] Logs sans erreurs
- [ ] Performance acceptable

---

## 🚀 PROCHAINES ÉTAPES

1. **Aller sur https://render.com**
2. **Créer compte / Se connecter**
3. **New Web Service**
4. **Connecter repo TchikiBalianos/DiscordRPBot**
5. **Configurer selon ce guide**
6. **Deploy!**

**✅ Render.com est parfait pour notre bot Discord !**
**Plan gratuit largement suffisant avec 750h/mois**
**Health monitoring déjà configuré pour éviter le sleep**

---

*Guide créé pour déploiement Render.com - Plan gratuit optimisé*
