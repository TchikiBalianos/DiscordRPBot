# 🔄 Système de Monitoring et Auto-Restart

## Vue d'ensemble

Deux outils pour gérer automatiquement le cycle de vie du bot :

1. **bot_monitor.py** - Moniteur du bot avec health check
2. **commit_and_restart.ps1** - Commit intelligent avec auto-restart

---

## A) bot_monitor.py - Moniteur du Bot

### Commandes Disponibles

```bash
# Vérifier l'état du bot
python.exe bot_monitor.py --check

# Afficher le statut détaillé
python.exe bot_monitor.py --status

# Lancer le bot
python.exe bot_monitor.py --start

# Arrêter le bot
python.exe bot_monitor.py --stop

# Redémarrer le bot
python.exe bot_monitor.py --restart

# Monitoring continu (vérifie chaque 30s)
python.exe bot_monitor.py --monitor
```

### Fichiers Générés

- `bot_status.json` - Statut du bot (PID, nombre de redémarrages, etc.)
- `logs/bot_monitor.log` - Logs du monitoring

### Exemple de Sortie

```
[CHECK] Vérification de l'état du bot...
[OK] Bot en cours d'exécution
[STATUS] Bot: EN LIGNE [OK]
```

---

## B) commit_and_restart.ps1 - Commit Intelligent

### Commandes Disponibles

```powershell
# Commit automatique avec message
.\commit_and_restart.ps1 -Message "fix: Correction bug DB"

# Commit uniquement certains fichiers
.\commit_and_restart.ps1 -Message "feat: New feature" -Files "commands.py,point_system.py"

# Commit avec message par défaut
.\commit_and_restart.ps1
```

### Workflow Automatique

Le script :
1. ✅ Vérifie si le bot était EN LIGNE avant le commit
2. ✅ Stage les fichiers (ou les fichiers spécifiés)
3. ✅ Commit avec le message fourni
4. ✅ Push vers GitHub
5. ✅ Vérifie si le bot est toujours EN LIGNE
6. ✅ Redémarre le bot s'il s'est arrêté

### Exemple d'Exécution

```
[INFO] ============================================
[INFO] COMMIT INTELLIGENT AVEC AUTO-RESTART
[INFO] ============================================
[INFO] Vérification du statut initial du bot...
[OK] Bot détecté comme EN LIGNE
[INFO] Stage des fichiers...
[INFO] Ajout de tous les fichiers modifiés...
[INFO] Commit: 'fix: Remove asyncio deadlock'
[OK] Commit réussi
[INFO] Push vers GitHub...
[OK] Push réussi
[INFO] Bot était EN LIGNE, vérification post-push...
[OK] Bot toujours EN LIGNE, aucune action nécessaire
[INFO] ============================================
[OK] WORKFLOW TERMINÉ
[INFO] ============================================
```

---

## Workflow Recommandé

### 1. Pendant le développement (bot EN LIGNE)

```bash
# Modifie ton code
# Puis utilise le script de commit automatique
.\commit_and_restart.ps1 -Message "fix: Description de la correction"

# Le script:
# ✓ Vérifie que le bot était EN LIGNE
# ✓ Commit et push
# ✓ Redémarre le bot s'il s'est arrêté
```

### 2. Vérification Rapide

```bash
# Vérifier l'état sans intervenir
python.exe bot_monitor.py --check

# Afficher le statut détaillé
python.exe bot_monitor.py --status
```

### 3. Monitoring Continu

```bash
# Dans une fenêtre terminal séparée, activer le monitoring
python.exe bot_monitor.py --monitor

# Le bot sera automatiquement redémarré s'il s'arrête
```

### 4. Redémarrage Manuel

```bash
# Si tu veux redémarrer le bot manuellement
python.exe bot_monitor.py --restart
```

---

## Cas d'Usage

### Cas 1: Modifier du code et push

```bash
# 1. Modifie commands.py
# 2. Commit et push avec auto-restart
.\commit_and_restart.ps1 -Message "fix: Command parsing issue"

# Résultat:
# ✅ Changements committé
# ✅ Changements pushés
# ✅ Bot redémarré si nécessaire
```

### Cas 2: Modifier plusieurs fichiers

```bash
# Commit uniquement les fichiers importants
.\commit_and_restart.ps1 `
  -Message "feat: Add new point system" `
  -Files "point_system.py,commands.py"

# Les fichiers .log et __pycache__ sont ignorés automatiquement
```

### Cas 3: Debugging continu

```powershell
# Fenêtre 1: Lance le monitoring
python.exe bot_monitor.py --monitor

# Fenêtre 2: Fais tes modifications
# Modifie commands.py
# Commit et push
.\commit_and_restart.ps1 -Message "fix: Command bug"

# Le monitoring détecte le changement et redémarre si besoin
```

---

## Fichiers Générés

```
bot_status.json
{
  "restart_count": 5,
  "last_restart": "2026-02-08T19:45:32.123456",
  "timestamp": 1707425132.123456
}

logs/bot_monitor.log
[2026-02-08 19:45:32] INFO     [CHECK] Vérification de l'état du bot...
[2026-02-08 19:45:32] INFO     [OK] Bot en cours d'exécution
...
```

---

## Health Check

Le monitoring utilise l'endpoint health check du bot :

```
URL: http://localhost:8003/health
Méthode: GET
Timeout: 5 secondes
```

Si le health check échoue (timeout, erreur 500, etc.), le bot est considéré comme HORS LIGNE.

---

## Troubleshooting

### "Bot détecté comme arrêté mais il est en ligne"
- Le health check peut échouer temporairement
- Vérifier que le port 8003 est correct dans `.env`
- Vérifier que la health monitoring est bien lancée

### Le script de commit échoue
- Vérifier que tu es dans le bon répertoire
- Vérifier que git est configuré
- Vérifier qu'il n'y a pas de conflits

### Le bot ne redémarre pas
- Vérifier qu'il n'y a pas d'erreurs dans `start.py`
- Consulter les logs: `Get-Content logs/bot_monitor.log -Tail 50`
- Vérifier que le bot peut bien se lancer manuellement

---

## Variables d'Environnement

```python
HEALTH_CHECK_URL = "http://localhost:8003/health"  # À mettre à jour si port change
CHECK_INTERVAL = 30  # Vérification tous les 30 secondes
```

---

## Intégration CI/CD Future

Ces scripts peuvent être intégrés dans un workflow GitHub Actions :

```yaml
# .github/workflows/auto-restart.yml
name: Auto-Restart Bot
on: [push]
jobs:
  restart:
    runs-on: ubuntu-latest
    steps:
      - name: Check Bot Status
        run: python bot_monitor.py --check
      - name: Restart if needed
        run: python bot_monitor.py --restart
```

