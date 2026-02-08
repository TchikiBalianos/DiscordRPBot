#!/usr/bin/env powershell
# Script: Commit intelligent avec auto-restart du bot
# Usage: .\commit_and_restart.ps1 -Message "fix: descriptif" [-Files "file1.py,file2.py"]

param(
    [string]$Message = "refactor: auto-commit",
    [string]$Files = ""
)

# Couleurs
$Green = [System.ConsoleColor]::Green
$Red = [System.ConsoleColor]::Red
$Yellow = [System.ConsoleColor]::Yellow
$Cyan = [System.ConsoleColor]::Cyan

function Write-Status {
    param([string]$Text, [string]$Status = "INFO")
    
    switch($Status) {
        "OK" { Write-Host "[$Status] $Text" -ForegroundColor $Green }
        "ERROR" { Write-Host "[$Status] $Text" -ForegroundColor $Red }
        "WARNING" { Write-Host "[$Status] $Text" -ForegroundColor $Yellow }
        "INFO" { Write-Host "[$Status] $Text" -ForegroundColor $Cyan }
        default { Write-Host "[$Status] $Text" }
    }
}

function Test-BotStatus {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8003/health" -TimeoutSec 3 -ErrorAction Stop
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

# === MAIN WORKFLOW ===

Write-Status "============================================" "INFO"
Write-Status "COMMIT INTELLIGENT AVEC AUTO-RESTART" "INFO"
Write-Status "============================================" "INFO"

# 1. Vérifier le statut initial du bot
Write-Status "Vérification du statut initial du bot..." "INFO"
$bot_was_running = Test-BotStatus

if ($bot_was_running) {
    Write-Status "Bot détecté comme EN LIGNE" "OK"
} else {
    Write-Status "Bot détecté comme HORS LIGNE" "WARNING"
}

# 2. Stage les fichiers
Write-Status "Stage des fichiers..." "INFO"

if ($Files) {
    # Stage les fichiers spécifiés
    $file_list = $Files -split ','
    foreach ($file in $file_list) {
        $file = $file.Trim()
        Write-Status "Ajout: $file" "INFO"
        git add $file
    }
} else {
    # Stage tous les fichiers modifiés (sauf cache et logs)
    Write-Status "Ajout de tous les fichiers modifiés..." "INFO"
    git add -A
    git reset __pycache__ 2>$null
    git reset *.log 2>$null
}

# 3. Vérifier s'il y a quelque chose à commiter
$status = git status --porcelain
if ([string]::IsNullOrWhiteSpace($status)) {
    Write-Status "Aucun changement à commiter" "WARNING"
    exit 0
}

# 4. Commit
Write-Status "Commit: '$Message'" "INFO"
git commit -m $Message

if ($LASTEXITCODE -eq 0) {
    Write-Status "Commit réussi" "OK"
} else {
    Write-Status "Erreur lors du commit" "ERROR"
    exit 1
}

# 5. Push
Write-Status "Push vers GitHub..." "INFO"
git push

if ($LASTEXITCODE -eq 0) {
    Write-Status "Push réussi" "OK"
} else {
    Write-Status "Erreur lors du push" "ERROR"
    exit 1
}

# 6. Attendre 2 secondes après push
Start-Sleep -Seconds 2

# 7. Vérifier si bot était en cours d'exécution
if ($bot_was_running) {
    Write-Status "Bot était EN LIGNE, vérification post-push..." "INFO"
    
    # Vérifier si le bot est toujours en ligne
    $bot_still_running = Test-BotStatus
    
    if ($bot_still_running) {
        Write-Status "Bot toujours EN LIGNE, aucune action nécessaire" "OK"
    } else {
        Write-Status "Bot est passé HORS LIGNE suite au push!" "WARNING"
        Write-Status "Redémarrage du bot en cours..." "INFO"
        
        # Appeler le script de monitoring pour redémarrer
        python.exe bot_monitor.py --restart
        
        Start-Sleep -Seconds 3
        
        # Vérifier que le bot a redémarré
        if (Test-BotStatus) {
            Write-Status "Bot redémarré avec succès" "OK"
        } else {
            Write-Status "Impossible de redémarrer le bot" "ERROR"
        }
    }
} else {
    Write-Status "Bot était HORS LIGNE avant le commit" "WARNING"
    Write-Status "Aucun redémarrage nécessaire" "INFO"
}

Write-Status "============================================" "INFO"
Write-Status "WORKFLOW TERMINÉ" "OK"
Write-Status "============================================" "INFO"
