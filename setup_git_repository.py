#!/usr/bin/env python3
"""
Setup Git Repository - TchikiBalianos/DiscordRPBot
Configure le repository local pour pousser vers le nouveau GitHub
"""

import os
import subprocess
import sys

def run_command(command, description):
    """Exécuter une commande git"""
    print(f"🔧 {description}")
    print(f"   Command: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"   ✅ Success")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
        else:
            print(f"   ❌ Error: {result.stderr.strip()}")
            return False
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False
    
    return True

def setup_git_repository():
    """Configurer le repository Git"""
    print("🔄 GIT REPOSITORY SETUP")
    print("=" * 60)
    print("Target: https://github.com/TchikiBalianos/DiscordRPBot")
    print("=" * 60)
    
    commands = [
        ("git init", "Initialiser repository Git"),
        ("git remote remove origin", "Supprimer ancien remote (peut échouer)"),
        ("git remote add origin https://github.com/TchikiBalianos/DiscordRPBot.git", "Ajouter nouveau remote"),
        ("git branch -M main", "Configurer branche main"),
        ("git add .", "Ajouter tous les fichiers"),
        ("git commit -m \"Initial commit - Bot Discord Thugz Life RP ready for production\"", "Commit initial"),
    ]
    
    success_count = 0
    
    for command, description in commands:
        if run_command(command, description):
            success_count += 1
        elif "remove origin" not in command:  # Ignore l'erreur de remove origin
            print(f"   ⚠️ Command failed but continuing...")
        print()
    
    # Push vers GitHub
    print("🚀 PUSHING TO GITHUB")
    print("-" * 40)
    
    push_success = run_command(
        "git push -u origin main", 
        "Push vers GitHub (peut demander authentification)"
    )
    
    if push_success:
        print("\n✅ REPOSITORY SETUP COMPLETE!")
        print(f"🔗 GitHub: https://github.com/TchikiBalianos/DiscordRPBot")
        print("📋 Ready for deployment on Render/Railway/Heroku")
    else:
        print("\n⚠️ PUSH FAILED")
        print("Manual steps required:")
        print("1. Create repository on GitHub: TchikiBalianos/DiscordRPBot")
        print("2. git push -u origin main")
    
    return push_success

def create_gitignore():
    """Créer .gitignore approprié"""
    gitignore_content = """# Environment variables
.env
.env.local
.env.production

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
pip-log.txt
pip-delete-this-directory.txt

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Logs
*.log
logs/
bot.log

# Database
*.db
*.sqlite

# OS
.DS_Store
Thumbs.db

# Backup files
*.backup
data.json.backup

# Test files
test_*.py
*_test.py

# Temporary files
temp/
tmp/
"""
    
    try:
        with open(".gitignore", "w", encoding="utf-8") as f:
            f.write(gitignore_content)
        print("✅ .gitignore created")
        return True
    except Exception as e:
        print(f"❌ Error creating .gitignore: {e}")
        return False

def check_repository_status():
    """Vérifier le statut du repository"""
    print("\n📊 REPOSITORY STATUS")
    print("-" * 40)
    
    status_commands = [
        ("git status --porcelain", "Files to commit"),
        ("git remote -v", "Remote repositories"),
        ("git branch", "Current branch")
    ]
    
    for command, description in status_commands:
        run_command(command, description)
        print()

def main():
    """Setup complet du repository"""
    print("🔧 GIT REPOSITORY CONFIGURATION")
    print("=" * 70)
    print("Repository: TchikiBalianos/DiscordRPBot")
    print("Purpose: Discord RP Bot - Production Ready")
    print("=" * 70)
    
    # Vérifier si on est dans le bon dossier
    if not os.path.exists("bot.py"):
        print("❌ Error: bot.py not found")
        print("Make sure you're in the bot directory")
        return False
    
    # Créer .gitignore
    gitignore_created = create_gitignore()
    
    # Vérifier statut initial
    check_repository_status()
    
    # Configurer repository
    repo_setup = setup_git_repository()
    
    print("\n" + "=" * 70)
    print("📋 SETUP SUMMARY")
    print("=" * 70)
    
    if repo_setup:
        print("✅ Git repository configured successfully")
        print("✅ Code pushed to GitHub")
        print("🚀 Ready for deployment on:")
        print("   - Render.com (recommended)")
        print("   - Railway")
        print("   - Heroku")
        
        print(f"\n🔗 Repository URL:")
        print(f"   https://github.com/TchikiBalianos/DiscordRPBot")
        
    else:
        print("⚠️ Repository setup incomplete")
        print("Manual steps may be required")
    
    return repo_setup

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
