#!/usr/bin/env python3
"""
Script de migration des données JSON vers Supabase
Exécutez ce script avant le premier déploiement
"""

import os
import sys
from dotenv import load_dotenv
from database_supabase import SupabaseDatabase

def main():
    """Migration des données"""
    print("🔄 Début de la migration des données...")
    
    # Charger les variables d'environnement
    load_dotenv()
    
    # Vérifier les credentials Supabase
    if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_ANON_KEY'):
        print("❌ Variables d'environnement Supabase manquantes!")
        sys.exit(1)
    
    # Initialiser la base de données
    db = SupabaseDatabase()
    
    if not db.is_connected():
        print("❌ Impossible de se connecter à Supabase!")
        sys.exit(1)
    
    print("✅ Connexion à Supabase réussie")
    
    # Migrer les données
    if os.path.exists('data.json'):
        print("📦 Migration des données depuis data.json...")
        db.migrate_from_json('data.json')
        print("✅ Migration terminée!")
        
        # Créer une sauvegarde
        import shutil
        shutil.copy('data.json', 'data.json.backup')
        print("💾 Sauvegarde créée: data.json.backup")
    else:
        print("ℹ️ Aucun fichier data.json trouvé")
    
    print("🎉 Migration terminée avec succès!")

if __name__ == "__main__":
    main()