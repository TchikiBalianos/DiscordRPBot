# ⚡ Quick Start - Commandes Quotidiennes

## 🎯 Ce que tu dois faire chaque jour

### Matin : Vérifier l'état
```bash
python.exe bot_monitor.py --status
```

### Pendant le développement : Commit intelligent
```bash
# Chaque fois que tu finis une modification
.\commit_and_restart.ps1 -Message "fix: description courte"
```

### Avant de déployer : Tester
```bash
.\.venv\Scripts\python.exe test_commands_auto.py
```

---

## 🔄 Workflow Complet (5 minutes)

### 1️⃣ Vérifier l'état du bot
```bash
python.exe bot_monitor.py --check
```
Résultat attendu:
```
[STATUS] Bot: EN LIGNE [OK]
```

### 2️⃣ Faire ta modification
```
Édite un fichier (commands.py, point_system.py, etc.)
```

### 3️⃣ Tester automatiquement
```bash
.\.venv\Scripts\python.exe test_commands_auto.py
```
Vérifier que au moins 5/7 tests passent.

### 4️⃣ Commit et Push (avec auto-restart)
```bash
.\commit_and_restart.ps1 -Message "fix: description"
```

C'est fini! Le bot redémarrera automatiquement s'il s'était arrêté.

---

## 📊 Interpréter les Résultats

### Test Report
```bash
Get-Content test_report.json | ConvertFrom-Json
```

| Cas | Signification | Action |
|-----|---------------|--------|
| `"passed": 5` | ✅ Bon | Continue |
| `"passed": 3` | ⚠️ Problème | Vérifier `errors` |
| `"passed": 0` | ❌ Critique | Rollback |

### Bot Status
```bash
python.exe bot_monitor.py --status
```

| État | Signification | Action |
|------|---------------|--------|
| EN LIGNE | ✅ Bot fonctionne | Rien |
| HORS LIGNE | ⚠️ Bot crash | `python.exe bot_monitor.py --restart` |

### Logs
```bash
Get-Content logs/errors.log -Tail 20
```

---

## 🚨 Dépannage Rapide

### Le bot refuse de démarrer
```bash
# 1. Vérifier les erreurs
Get-Content logs/bot_monitor.log -Tail 50

# 2. Vérifier qu'il n'y a pas de conflits Python
Get-Process python

# 3. Tuer tous les Python et relancer
Get-Process python | Stop-Process -Force
python.exe bot_monitor.py --start
```

### Un test échoue
```bash
# 1. Lire le log du test
Get-Content test_report.log | Select-String "ERROR"

# 2. Voir le rapport JSON
Get-Content test_report.json | ConvertFrom-Json | ConvertTo-Json -Depth 5
```

### Le commit échoue
```bash
# Vérifier le statut git
git status

# Si conflits, les résoudre
git diff
```

---

## 💾 Sauvegarde Rapide

### Avant un gros changement
```bash
# Créer une branche
git checkout -b feature/mon-feature

# Faire tes changements...

# Merge quand c'est OK
git checkout main
git merge feature/mon-feature
git push
```

---

## 📈 Monitoring en Continu

Si tu fais du développement long (> 30 minutes):

```bash
# Terminal 1: Lance le monitoring
python.exe bot_monitor.py --monitor

# Terminal 2: Fais tes modifications...
# Edit code
# Commit avec .\commit_and_restart.ps1
# Monitoring détectera les problèmes
```

---

## 🎓 Exemples Réels

### Exemple 1: Fixer un bug simple
```bash
# 1. Vérifier état
python.exe bot_monitor.py --check
# [OK] Bot: EN LIGNE

# 2. Éditer commands.py
# ... corriger le bug ...

# 3. Commit
.\commit_and_restart.ps1 -Message "fix: Command parsing bug"
# Bot redémarrera automatiquement
```

### Exemple 2: Ajouter une nouvelle commande
```bash
# 1. Tester en local
.\.venv\Scripts\python.exe test_commands_auto.py
# [PASSED] 5/7

# 2. Ajouter la commande dans commands.py

# 3. Commit
.\commit_and_restart.ps1 -Message "feat: Add !steal command"

# 4. Tester en Discord
# /steal user
```

### Exemple 3: Gros refactor multi-fichiers
```bash
# 1. Créer une branche
git checkout -b refactor/point-system

# 2. Faire les modifications
# point_system.py
# database_supabase.py
# commands.py

# 3. Tester
.\.venv\Scripts\python.exe test_commands_auto.py

# 4. Commit multi-fichiers
.\commit_and_restart.ps1 `
  -Message "refactor: Reorganize point system" `
  -Files "point_system.py,database_supabase.py,commands.py"

# 5. Merge
git checkout main
git merge refactor/point-system
git push
```

---

## 📋 Checklist Quotidienne

- [ ] Vérifier le statut: `python.exe bot_monitor.py --status`
- [ ] Faire mes modifications
- [ ] Tester: `.\.venv\Scripts\python.exe test_commands_auto.py`
- [ ] Commit intelligent: `.\commit_and_restart.ps1 -Message "..."`
- [ ] Vérifier les logs: `Get-Content test_report.json`
- [ ] Tester en Discord (optionnel)

---

## 🔗 Ressources Complètes

- [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) - Vue d'ensemble complète
- [TESTING_MONITORING_GUIDE.md](TESTING_MONITORING_GUIDE.md) - Guide détaillé
- [BOT_MONITOR_GUIDE.md](BOT_MONITOR_GUIDE.md) - Guide monitoring
- [TESTING_SUMMARY.md](TESTING_SUMMARY.md) - Résumé testing

---

## ⚡ Pro Tips

1. **Alias PowerShell** - Créer des raccourcis
```powershell
# Ajouter dans le profil PowerShell
Set-Alias -Name car -Value '.\commit_and_restart.ps1'
Set-Alias -Name test-bot -Value '.\.venv\Scripts\python.exe test_commands_auto.py'
Set-Alias -Name check-bot -Value 'python.exe bot_monitor.py --check'

# Utilisation
car -Message "fix: bug"
test-bot
check-bot
```

2. **Monitoring dans l'arrière-plan**
```bash
# Lancer dans une fenêtre séparée
Start-Process powershell -ArgumentList "python.exe bot_monitor.py --monitor"
```

3. **Commit rapide**
```powershell
# Raccourci pour les commits répétitifs
function quick-commit {
    param([string]$msg)
    .\commit_and_restart.ps1 -Message $msg
}
```

---

**Note**: Tous les fichiers de logs et rapports sont automatiquement ignorés par git (.gitignore)

