#!/usr/bin/env python3
"""
Script de démarrage simplifié pour Railway
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Configuration logging pour Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger('Railway')

def main():
    """Main function"""
    logger.info("🚀 Starting Discord bot on Railway...")
    
    # Charger les variables d'environnement
    load_dotenv()
    
    # Vérifier le token Discord
    if not os.getenv('DISCORD_TOKEN'):
        logger.error("❌ DISCORD_TOKEN not found!")
        sys.exit(1)
    
    logger.info("✅ Environment variables loaded")
    
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