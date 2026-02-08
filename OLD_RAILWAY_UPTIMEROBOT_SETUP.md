# Railway + UptimeRobot Configuration Guide
## Configuration de Monitoring pour Discord Thugz Life RP Bot

---

## 🚀 Railway Configuration

### ✅ Déjà Configuré dans `railway.toml`

```toml
[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 300
healthcheckInterval = 60
port = 8000

[environments.production]
variables = { 
    HEALTH_PORT = "8000", 
    ENABLE_HEALTH_MONITOR = "true"
}
```

### 📍 Endpoints de Santé Disponibles

1. **`/health`** - Endpoint basique pour Railway et UptimeRobot
   - ✅ Status: "alive"
   - ✅ Timestamp
   - ✅ Uptime
   - ✅ Database status

2. **`/health/detailed`** - Monitoring détaillé
   - ✅ Métriques système (CPU, RAM, disque)
   - ✅ Status base de données avec détails
   - ✅ Statistiques du bot
   - ✅ Performance metrics

3. **`/health/resilience`** - Résilience de connexion (Phase 4C)
   - ✅ Status des reconnexions automatiques
   - ✅ Compteur d'échecs de connexion
   - ✅ Performance de récupération
   - ✅ Circuit breaker status

---

## 🔔 Configuration UptimeRobot

### Étape 1: Créer un Compte UptimeRobot
1. Aller sur https://uptimerobot.com/
2. Créer un compte gratuit (50 moniteurs max)
3. Vérifier l'email

### Étape 2: Configurer le Monitor Principal
```
Type de Monitor: HTTP(s)
URL: https://your-app.railway.app/health
Nom: Discord Bot - Health Check
Interval de Monitoring: 5 minutes (comme requis par TECH Brief)
Keyword Monitoring: "alive" (optionnel mais recommandé)
```

### Étape 3: Configurer Monitors Additionnels (Optionnel)
```
Monitor Détaillé:
URL: https://your-app.railway.app/health/detailed
Interval: 10 minutes

Monitor Résilience:
URL: https://your-app.railway.app/health/resilience  
Interval: 15 minutes
```

### Étape 4: Configuration des Alertes
```
Alert Contacts:
- Email: votre-email@domain.com
- Discord Webhook (optionnel): webhook-url
- Slack (optionnel): webhook-url

Alert Settings:
- Send when DOWN: ✅ Activé
- Send when UP: ✅ Activé
- Threshold: 2 minutes (attendre 2 min avant alerte)
```

### Étape 5: Obtenir l'URL Railway
```bash
# Déployer sur Railway et obtenir l'URL
railway login
railway link
railway deploy

# L'URL sera de la forme:
# https://your-app-name.railway.app
```

---

## 🧪 Tests de Validation

### Test Local (Développement)
```bash
# Démarrer le serveur de santé localement
python start.py

# Tester les endpoints
curl http://localhost:8000/health
curl http://localhost:8000/health/detailed
curl http://localhost:8000/health/resilience
```

### Test Railway (Production)
```bash
# Une fois déployé sur Railway
curl https://your-app.railway.app/health
curl https://your-app.railway.app/health/detailed
curl https://your-app.railway.app/health/resilience
```

---

## 📊 Réponses Attendues

### `/health` (Code 200)
```json
{
    "status": "alive",
    "timestamp": "2025-09-17T05:45:30.123456",
    "uptime_seconds": 3600,
    "database": "connected",
    "version": "4.0.0"
}
```

### `/health/detailed` (Code 200/503)
```json
{
    "overall_status": "healthy",
    "timestamp": "2025-09-17T05:45:30.123456",
    "system_metrics": {
        "uptime_hours": 1.5,
        "memory_usage_percent": 45.2,
        "cpu_usage_percent": 12.8
    },
    "database_health": {
        "status": "connected",
        "response_time_ms": 23.4,
        "connection_resilience": {
            "status": "healthy",
            "failures": 0
        }
    }
}
```

### `/health/resilience` (Code 200/503)
```json
{
    "connection_status": {
        "connected": true,
        "failures": 0,
        "status": "healthy"
    },
    "resilience_features": {
        "auto_retry_enabled": true,
        "max_retries": 3,
        "degraded_mode_available": true
    }
}
```

---

## ⚠️ Codes de Statut HTTP

- **200 OK**: Tout fonctionne normalement
- **503 Service Unavailable**: Service dégradé mais fonctionnel
- **500 Internal Server Error**: Erreur critique

UptimeRobot considère 200 et 503 comme "UP" si configuré correctement.

---

## 🔧 Configuration Railway - Variables d'Environnement

```bash
# Variables obligatoires
DISCORD_TOKEN=your_discord_bot_token
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key

# Variables de monitoring
HEALTH_PORT=8000
ENABLE_HEALTH_MONITOR=true
ENVIRONMENT=production
HEALTH_CHECK_INTERVAL=300

# Variables optionnelles pour Twitter
TWITTER_API_KEY=your_twitter_key
TWITTER_API_SECRET=your_twitter_secret
```

---

## 🎯 Checklist de Déploiement

### Phase 1: Préparation
- [ ] ✅ Code commit et push vers GitHub
- [ ] ✅ Variables d'environnement configurées
- [ ] ✅ `railway.toml` mis à jour

### Phase 2: Déploiement Railway
- [ ] `railway login`
- [ ] `railway link` (lier au projet)
- [ ] `railway deploy`
- [ ] Vérifier l'URL générée
- [ ] Tester `/health` endpoint

### Phase 3: Configuration UptimeRobot
- [ ] Créer compte UptimeRobot
- [ ] Ajouter monitor principal (`/health`)
- [ ] Configurer interval: 5 minutes
- [ ] Configurer alertes email
- [ ] Tester le monitoring

### Phase 4: Validation
- [ ] Monitors UptimeRobot actifs
- [ ] Alertes fonctionnelles
- [ ] Health checks répondent correctement
- [ ] Bot Discord fonctionnel

---

## 🚨 Troubleshooting

### Problème: Health check échoue
```bash
# Vérifier les logs Railway
railway logs

# Vérifier le port
echo $HEALTH_PORT

# Tester localement
python start.py
curl http://localhost:8000/health
```

### Problème: UptimeRobot n'arrive pas à atteindre l'endpoint
1. Vérifier que l'URL Railway est correcte
2. Vérifier que le port 8000 est bien exposé
3. Tester manuellement avec curl/browser
4. Vérifier les logs Railway pour erreurs

### Problème: Alertes trop fréquentes
1. Augmenter le threshold UptimeRobot (de 2 à 5 minutes)
2. Vérifier la stabilité du serveur Railway
3. Optimiser les timeouts dans `railway.toml`

---

## 📈 Monitoring Avancé (Optionnel)

### Intégration Discord Webhook
```python
# Dans UptimeRobot, ajouter webhook Discord
# URL: https://discord.com/api/webhooks/your-webhook-url
# Payload: {"content": "🔴 Bot DOWN: *monitorFriendlyName* - *alertDetails*"}
```

### Métriques Custom
```python
# Endpoint custom pour métriques business
@app.get("/metrics/business")
async def business_metrics():
    return {
        "active_users_24h": 150,
        "commands_executed_24h": 1250,
        "gang_wars_active": 3,
        "prisoners_count": 12
    }
```

Cette configuration assure un monitoring robuste et conforme aux exigences du TECH Brief ! 🚀
