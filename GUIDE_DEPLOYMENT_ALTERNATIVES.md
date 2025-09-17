# 🚀 GUIDE DÉPLOIEMENT - Options Alternatives
# Bot Discord Thugz Life RP

## ⚠️ STATUT RAILWAY
- Railway CLI installé ✅
- Authentifié comme Tchiki ✅  
- **Problème**: Période d'essai expirée
- **Solution**: Choisir un plan sur railway.app

---

## 🛤️ OPTION 1: RAILWAY (RECOMMANDÉ)

### Étapes pour continuer avec Railway:

1. **Aller sur https://railway.app**
2. **Se connecter avec le compte Tchiki**
3. **Choisir un plan**:
   - **Hobby Plan**: $5/mois - 500h compute, 1GB RAM
   - **Pro Plan**: $20/mois - Illimité
   - Ou continuer avec les limitations du plan gratuit

4. **Créer projet via interface web**:
   - New Project → Deploy from GitHub
   - Connecter le repo `TchikiBalianos/DiscordRPBot`
   - Railway détectera automatiquement le `railway.toml`

5. **Configurer variables d'environnement**:
   ```
   DISCORD_TOKEN=your_bot_token
   DISCORD_GUILD_ID=your_server_id
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   ENABLE_HEALTH_MONITOR=true
   HEALTH_PORT=8000
   ```

6. **Déployer automatiquement**

### Puis retour CLI:
```bash
cd "c:\\Users\\Okaze\\Desktop\\Julian\\Thugz Labs\\BOT Discord\\DiscordTwitterBOT-main"
railway link  # Lier au projet créé
railway status  # Vérifier le déploiement
```

---

## 🐳 OPTION 2: HEROKU (ALTERNATIVE)

### Installation Heroku CLI:
```bash
# Via npm
npm install -g heroku

# Authentification
heroku login
```

### Déploiement Heroku:
```bash
# Créer Procfile pour Heroku
echo "worker: python start.py" > Procfile

# Initialiser git si nécessaire
git init
git add .
git commit -m "Deploy to Heroku"

# Créer app Heroku
heroku create your-bot-name

# Configurer variables
heroku config:set DISCORD_TOKEN=your_token
heroku config:set SUPABASE_URL=your_url
heroku config:set SUPABASE_KEY=your_key
heroku config:set ENABLE_HEALTH_MONITOR=true

# Déployer
git push heroku main
```

---

## ☁️ OPTION 3: RENDER (GRATUIT)

### Déploiement Render:

1. **Aller sur https://render.com**
2. **Connecter GitHub repo**
3. **Créer Web Service**:
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python start.py`

4. **Variables d'environnement**:
   ```
   DISCORD_TOKEN=your_token
   SUPABASE_URL=your_url  
   SUPABASE_KEY=your_key
   ENABLE_HEALTH_MONITOR=true
   PORT=8000
   ```

---

## 🏠 OPTION 4: DÉPLOIEMENT LOCAL PERSISTANT

### Windows Service avec NSSM:

1. **Télécharger NSSM**: https://nssm.cc/download
2. **Installer le service**:
   ```bash
   # Ouvrir cmd en tant qu'administrateur
   nssm install DiscordBot
   ```

3. **Configuration NSSM**:
   - Path: `C:\Python312\python.exe`
   - Startup directory: `c:\Users\Okaze\Desktop\Julian\Thugz Labs\BOT Discord\DiscordTwitterBOT-main`
   - Arguments: `start.py`

4. **Variables d'environnement dans NSSM**
5. **Démarrer le service**: `nssm start DiscordBot`

---

## 🔧 CONFIGURATION COMMUNE

### Fichiers déjà prêts:
- ✅ `railway.toml` - Configuration Railway
- ✅ `requirements.txt` - Dépendances
- ✅ `runtime.txt` - Python 3.12
- ✅ `start.py` - Script de démarrage avec health monitoring

### Variables d'environnement requises:
```env
# Discord (OBLIGATOIRE)
DISCORD_TOKEN=your_discord_bot_token
DISCORD_GUILD_ID=your_server_id

# Supabase (OBLIGATOIRE)  
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key

# Health Monitoring (RECOMMANDÉ)
ENABLE_HEALTH_MONITOR=true
HEALTH_PORT=8000

# Twitter (OPTIONNEL)
TWITTER_CONSUMER_KEY=your_key
TWITTER_CONSUMER_SECRET=your_secret
TWITTER_ACCESS_TOKEN=your_token
TWITTER_ACCESS_TOKEN_SECRET=your_token_secret
```

---

## 🎯 RECOMMANDATION

**Railway reste la meilleure option** car:
- Configuration `railway.toml` déjà optimisée
- Health checks automatiques configurés
- Compatible UptimeRobot monitoring
- Scaling automatique
- Logs centralisés

**Prochaines étapes**:
1. Choisir un plan Railway sur https://railway.app
2. Créer le projet via interface web
3. Configurer variables d'environnement
4. Déployer automatiquement

**Alternative immédiate**: Render (gratuit) ou Heroku si Railway n'est pas possible.

---

**🚀 Le bot est 100% prêt pour déploiement sur n'importe quelle plateforme !**
