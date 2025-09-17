#!/usr/bin/env python3
"""
Script de migration de discord.py vers nextcord
"""

import os
import re

def migrate_file_to_nextcord(filepath):
    """Migrate un fichier de discord vers nextcord"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remplacements nécessaires
        original_content = content
        
        # 1. Import principal
        content = re.sub(r'^import discord$', 'import nextcord as discord', content, flags=re.MULTILINE)
        
        # 2. From imports
        content = re.sub(r'^from discord', 'from nextcord', content, flags=re.MULTILINE)
        
        # 3. discord.ext imports
        content = re.sub(r'from discord\.ext', 'from nextcord.ext', content)
        
        # Si changements detectés
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Migration {filepath}")
            return True
        else:
            print(f"➖ Aucun changement {filepath}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur {filepath}: {e}")
        return False

# Fichiers à migrer
files_to_migrate = [
    "bot.py",
    "commands.py", 
    "point_system.py",
    "gang_events.py",
    "gang_commands.py",
    "health_monitoring.py"
]

print("🔄 MIGRATION DISCORD → NEXTCORD")
print("=" * 40)

migrated_count = 0
for filename in files_to_migrate:
    if os.path.exists(filename):
        if migrate_file_to_nextcord(filename):
            migrated_count += 1
    else:
        print(f"⚠️ Fichier non trouvé: {filename}")

print(f"\n🎯 Migration terminée: {migrated_count} fichiers modifiés")
print("✅ Tous les imports discord → nextcord complétés")
