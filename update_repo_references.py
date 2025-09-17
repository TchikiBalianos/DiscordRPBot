#!/usr/bin/env python3
"""
Mise à jour Repository References
Change toutes les références de YEVANAFARO/DiscordTweeterBT vers TchikiBalianos/DiscordRPBot
"""

import os
import glob

def update_repository_references():
    """Met à jour toutes les références au repository"""
    print("🔄 UPDATING REPOSITORY REFERENCES")
    print("=" * 60)
    
    # Fichiers à mettre à jour
    files_to_update = [
        "GUIDE_DEPLOYMENT_ALTERNATIVES.md",
        "RENDER_DEPLOYMENT_GUIDE.md", 
        "DEPLOY_RENDER_QUICK_GUIDE.md",
        "test_render_deployment.py",
        "GUIDE_DEPLOYMENT_PRODUCTION.md",
        "RAILWAY_UPTIMEROBOT_SETUP.md",
        "RAPPORT_FINAL_TECH_BRIEF.md",
        "README.md"
    ]
    
    old_repo = "YEVANAFARO/DiscordTweeterBT"
    new_repo = "TchikiBalianos/DiscordRPBot"
    
    old_url = "https://github.com/YEVANAFARO/DiscordTweeterBT"
    new_url = "https://github.com/TchikiBalianos/DiscordRPBot"
    
    updated_files = []
    
    for filename in files_to_update:
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Remplacer les références
                content = content.replace(old_repo, new_repo)
                content = content.replace(old_url, new_url)
                content = content.replace("YEVANAFARO", "TchikiBalianos")
                content = content.replace("DiscordTweeterBT", "DiscordRPBot")
                
                if content != original_content:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"✅ Updated: {filename}")
                    updated_files.append(filename)
                else:
                    print(f"⚪ No changes: {filename}")
                    
            except Exception as e:
                print(f"❌ Error updating {filename}: {e}")
        else:
            print(f"⚠️ File not found: {filename}")
    
    return updated_files

def create_new_readme():
    """Créer un README.md mis à jour"""
    readme_content = """# 🤖 Discord RP Bot - Thugz Life
# Bot Discord complet pour serveur Roleplay

## 📋 Repository
**GitHub**: https://github.com/TchikiBalianos/DiscordRPBot

## 🎯 Fonctionnalités
- ✅ **51 commandes** Discord opérationnelles
- ✅ **Système de gangs** complet avec guerres automatisées
- ✅ **Justice RP** (arrestations, amendes, tribunaux)
- ✅ **Administration** avancée (ban, mute, warn)
- ✅ **Health monitoring** intégré pour production
- ✅ **Résilience connexion** avec circuit breaker
- ✅ **Interface français** complète

## 🚀 Déploiement
**Prêt pour production** sur:
- **Render.com** (gratuit) - Guide: `DEPLOY_RENDER_QUICK_GUIDE.md`
- **Railway** - Guide: `GUIDE_DEPLOYMENT_PRODUCTION.md`
- **Heroku** - Guide: `GUIDE_DEPLOYMENT_ALTERNATIVES.md`

## 🔧 Configuration
1. **Variables d'environnement** (voir `.env.example`)
2. **Base de données**: Supabase PostgreSQL
3. **Health monitoring**: FastAPI intégré
4. **UptimeRobot**: Monitoring 24/7

## 📊 TECH Brief Compliance
**96% conforme** aux spécifications techniques

## 📁 Structure
```
├── bot.py                 # Bot Discord principal
├── start.py               # Script démarrage avec health monitoring
├── health_monitoring.py   # Endpoints de santé FastAPI
├── gang_system.py         # Système de gangs complet
├── gang_wars.py          # Guerres automatisées
├── commands.py           # Commandes de base
├── database_supabase.py  # Couche base de données avec résilience
├── config.py             # Configuration centralisée
├── railway.toml          # Configuration Railway
├── requirements.txt      # Dépendances Python
└── guides/               # Documentation complète
```

## 🧪 Tests
- `test_render_deployment.py` - Tests préparation Render
- `test_deployment_simple.py` - Tests généraux
- `test_production_endpoints.py` - Tests production

## 📖 Documentation
- `DEPLOY_RENDER_QUICK_GUIDE.md` - Déploiement Render.com
- `GUIDE_DEPLOYMENT_PRODUCTION.md` - Guide complet Railway
- `RAPPORT_FINAL_TECH_BRIEF.md` - Rapport technique final

---

**✅ Bot Discord Thugz Life RP - Ready for Production!**
"""
    
    try:
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(readme_content)
        print("✅ Created new README.md")
        return True
    except Exception as e:
        print(f"❌ Error creating README.md: {e}")
        return False

def main():
    """Exécuter mise à jour des références"""
    print("🔄 REPOSITORY REFERENCE UPDATE")
    print("=" * 50)
    print("Old: YEVANAFARO/DiscordTweeterBT")
    print("New: TchikiBalianos/DiscordRPBot")
    print("=" * 50)
    
    # Mettre à jour les fichiers
    updated_files = update_repository_references()
    
    # Créer nouveau README
    readme_created = create_new_readme()
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"Files updated: {len(updated_files)}")
    for file in updated_files:
        print(f"  ✅ {file}")
    
    if readme_created:
        print(f"  ✅ README.md")
    
    print(f"\n✅ Repository references updated!")
    print(f"🔗 New repository: https://github.com/TchikiBalianos/DiscordRPBot")
    
    return True

if __name__ == "__main__":
    main()
