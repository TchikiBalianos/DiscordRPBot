# Outils de Testing et Monitoring Automatisé

## A) Script de Test Automatisé

### Description
**test_commands_auto.py** - Testeur autonome de toutes les commandes du bot sans avoir besoin de Discord.

### Utilisation

```bash
cd DiscordTwitterBOT-main
.\.venv\Scripts\python.exe test_commands_auto.py
```

### Résultats Produits

Le script génère 2 fichiers :

1. **test_report.json** - Rapport structuré en JSON
   ```json
   {
     "timestamp": "2026-02-08T19:27:06...",
     "total_tests": 7,
     "passed": 5,
     "failed": 2,
     "results": { ... }
   }
   ```

2. **test_report.log** - Logs détaillés en texte

### Tests Inclus

| Test | Description | Statut |
|------|-------------|--------|
| Database Connection | Vérifie connexion Supabase | [OK] |
| User Creation | Crée/récupère utilisateur test | [OK] |
| Add Points | Ajoute des points (100) | [FAIL] |
| Points Command | Récupère points utilisateur | [OK] |
| Leaderboard Command | Récupère classement mensuel | [OK] |
| Prison Status Command | Récupère statut de prison | [OK] |
| Work Command | Simule commande !work | [OK] |

### Résultats Actuels

✅ **5/7 tests PASSENT** :
- User Creation ✓
- Points Command ✓
- Leaderboard Command ✓
- Prison Status Command ✓
- Work Command ✓

❌ **2/7 tests ÉCHOUENT** :
- Database Connection (is_connected() non implémentée)
- Add Points (points non ajoutés)

### Comment Utiliser les Résultats

1. **Après chaque modification de code**, exécute le script :
   ```bash
   .\.venv\Scripts\python.exe test_commands_auto.py
   ```

2. **Analyse les résultats** dans `test_report.json`

3. **Si un test échoue** :
   - Lis les logs dans `test_report.log`
   - Corrige le code problématique
   - Réexécute le test
   - Git commit et push

### Extension du Script

Tu peux ajouter de nouveaux tests en ajoutant des méthodes `async def test_*`:

```python
async def test_new_feature(self) -> Tuple[bool, str]:
    """Tester: Description de la nouvelle fonctionnalité"""
    try:
        logger.info("TEST: New feature")
        # Ton code de test ici
        return True, "Success message"
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False, str(e)
```

---

## B) Système de Logging Avancé

### Description
**advanced_logging.py** - Logger structuré qui capture TOUS les événements du bot.

### Structure des Logs

```
logs/
├── all.log                    # Tous les logs (DEBUG et plus)
├── errors.log                 # Uniquement les erreurs
└── events.jsonl              # Événements au format JSON (1 ligne = 1 événement)
```

### Utilisation dans le Code

```python
from advanced_logging import bot_logger, database_logger, commands_logger

# Logs simples
bot_logger.info("Bot started successfully")
database_logger.error("Connection failed", exception=db_error)
commands_logger.debug("Command executed", user_id=123, command="work")

# Logs structurés
commands_logger.command_executed(
    command_name="work",
    user_id="123456789",
    success=True,
    duration_ms=45.3,
    error=None
)

database_logger.database_operation(
    operation="select_user",
    success=True,
    duration_ms=12.5,
    error=None,
    user_id="123456789"
)

api_logger.api_call(
    service="supabase",
    endpoint="/rest/v1/users",
    status_code=200,
    duration_ms=150.5,
    error=None
)
```

### Types de Logs Disponibles

#### 1. Info/Warning/Error/Debug
```python
bot_logger.info("Message", key1="value1", key2="value2")
bot_logger.warning("Warning message")
bot_logger.error("Error occurred", exception=e)
bot_logger.debug("Debug details")
```

#### 2. Logs de Commande
```python
commands_logger.command_executed(
    command_name="work",
    user_id="user_123",
    success=True,
    duration_ms=45.3
)
```

#### 3. Logs de Base de Données
```python
database_logger.database_operation(
    operation="update_points",
    success=True,
    duration_ms=12.5,
    user_id="user_123",
    points_added=100
)
```

#### 4. Logs d'API
```python
api_logger.api_call(
    service="supabase",
    endpoint="/rest/v1/users",
    status_code=200,
    duration_ms=150.5
)
```

#### 5. Logs JSON
```python
bot_logger.log_json({
    'type': 'custom_event',
    'event_name': 'gang_created',
    'gang_id': 'gang_123',
    'timestamp': datetime.now().isoformat()
})
```

### Analyse des Logs

#### Récupérer les dernières erreurs
```bash
tail logs/errors.log
```

#### Voir tous les logs
```bash
tail -f logs/all.log
```

#### Analyser les événements JSON
```bash
Get-Content logs/events.jsonl | ConvertFrom-Json -AsHashtable | Format-Table
```

### Intégration Recommandée

1. **Dans commands.py** - Logger chaque exécution de commande
2. **Dans database_supabase.py** - Logger opérations DB
3. **Dans point_system.py** - Logger modifications de points
4. **Dans bot.py** - Logger événements de bot

---

## Workflow Recommandé

### Phase 1 : Développement Local
```bash
# 1. Exécute les tests
.\.venv\Scripts\python.exe test_commands_auto.py

# 2. Vérifie les résultats
Get-Content test_report.json

# 3. Si test échoue, corrige le code
# 4. Commit et push
git add .; git commit -m "fix: ..."; git push
```

### Phase 2 : Testing en Discord
```bash
# 1. Lance le bot
.\.venv\Scripts\python.exe start.py

# 2. Teste manuellement les commandes
# !ping, !work, !points, etc.

# 3. Vérifie les logs
Get-Content logs/all.log -Tail 50
```

### Phase 3 : Production (Render)
```bash
# 1. Les logs sont disponibles sur Render dashboard
# 2. Monitoring en temps réel via health check
# 3. Redéploiement automatique si erreurs
```

---

## Troubleshooting

### Le test s'arrête avec erreur encoding
**Cause**: Windows cp1252 encoding + emojis
**Solution**: Le script a déjà du code pour gérer ça

### Le test "Database Connection" échoue
**Cause**: `is_connected()` n'est pas implémentée
**Vérifier**: `database_supabase.py` ligne ~950

### Points ne s'ajoutent pas
**Cause**: Possible problème asyncio ou transaction
**Vérifier**: Logs dans `test_report.log` ou `logs/errors.log`

---

## Prochaines Étapes

1. ✅ Intégrer `advanced_logging` dans tous les modules
2. ✅ Exécuter `test_commands_auto.py` avant chaque commit
3. ✅ Analyser les fichiers de logs pour trouver bugs
4. ✅ Auto-corriger les bugs détectés
5. ✅ Déployer sur Render avec les logs activés

---

## Notes Importantes

- Le script de test ne nécessite PAS d'être connecté à Discord
- Les logs sont stockés localement dans le dossier `logs/`
- Les rapports sont générés en JSON pour faciliter l'analyse
- Tous les tests peuvent tourner en parallèle
- Les logs incluent le traceback complet en cas d'erreur

