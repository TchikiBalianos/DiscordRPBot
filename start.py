#!/usr/bin/env python3
"""
Script de démarrage simplifié pour Railway avec Health Monitoring
Phase 4A: Intégration du système de surveillance
"""

# PATCH AUDIOOP CRITIQUE - DOIT ÊTRE LE PREMIER IMPORT
import audioop_patch  # Python 3.13 compatibility patch

import os
import sys
import logging
import threading
import time
import warnings
from dotenv import load_dotenv

# Suppress tweepy SyntaxWarnings about invalid escape sequences (non-critical)
warnings.filterwarnings("ignore", category=SyntaxWarning, module="tweepy")

# Configuration logging pour Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger('Railway')

def start_health_monitor():
    """Démarrer le serveur de monitoring en arrière-plan"""
    try:
        from health_monitoring import run_health_server
        # Render utilise PORT, fallback sur HEALTH_PORT puis 8000
        port = int(os.getenv('PORT', os.getenv('HEALTH_PORT', 8000)))
        logger.info(f"🔍 Starting health monitor on port {port}")
        run_health_server(port)
    except Exception as e:
        logger.error(f"❌ Failed to start health monitor: {e}")

def main():
    """Main function with integrated health monitoring"""
    logger.info("🚀 Starting Discord bot with Health Monitoring on Railway...")
    
    # Charger les variables d'environnement
    load_dotenv()
    
    # Vérifier le token Discord
    if not os.getenv('DISCORD_TOKEN'):
        logger.error("❌ DISCORD_TOKEN not found!")
        sys.exit(1)
    
    logger.info("✅ Environment variables loaded")
    
    # Démarrer le serveur de monitoring dans un thread séparé
    if os.getenv('ENABLE_HEALTH_MONITOR', 'true').lower() == 'true':
        health_thread = threading.Thread(target=start_health_monitor, daemon=True)
        health_thread.start()
        logger.info("✅ Health monitoring thread started")
        
        # Attendre que le serveur de monitoring démarre
        time.sleep(2)
    
    # Importer et démarrer le bot
    try:
        from bot import main as bot_main
        import asyncio
        asyncio.run(bot_main())
    except Exception as e:
        logger.error(f"💥 Bot error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()