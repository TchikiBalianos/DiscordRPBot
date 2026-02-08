#!/usr/bin/env python3
"""
Système de monitoring et auto-restart du bot Discord
Vérifie l'état du bot et le redémarre si nécessaire après un commit/push
"""

import subprocess
import time
import requests
import sys
import logging
from pathlib import Path
from datetime import datetime
import json
import os

# Configuration logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_DIR / 'bot_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('BotMonitor')

# Config
HEALTH_CHECK_URL = "http://localhost:8003/health"
BOT_SCRIPT = ".venv\\Scripts\\python.exe"
BOT_MAIN = "start.py"
VENV_PATH = ".venv\\Scripts\\python.exe"
CHECK_INTERVAL = 30  # Vérifier tous les 30 secondes
STATUS_FILE = Path("bot_status.json")

class BotMonitor:
    """Moniteur du bot Discord"""
    
    def __init__(self):
        self.bot_process = None
        self.is_running = False
        self.last_check = None
        self.restart_count = 0
        self.load_status()
    
    def load_status(self):
        """Charger le statut sauvegardé"""
        if STATUS_FILE.exists():
            try:
                with open(STATUS_FILE, 'r') as f:
                    data = json.load(f)
                    self.restart_count = data.get('restart_count', 0)
                    logger.info(f"Status chargé: {self.restart_count} redémarrages")
            except:
                pass
    
    def save_status(self):
        """Sauvegarder le statut"""
        with open(STATUS_FILE, 'w') as f:
            json.dump({
                'restart_count': self.restart_count,
                'last_restart': datetime.now().isoformat(),
                'timestamp': time.time()
            }, f)
    
    def is_bot_running(self) -> bool:
        """Vérifier si le bot tourne"""
        try:
            response = requests.get(HEALTH_CHECK_URL, timeout=5)
            self.is_running = response.status_code == 200
            return self.is_running
        except requests.exceptions.RequestException:
            self.is_running = False
            return False
    
    def get_bot_pid(self) -> int:
        """Obtenir le PID du bot s'il tourne"""
        try:
            # Vérifie si python.exe tourne start.py
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
                capture_output=True,
                text=True
            )
            if 'python.exe' in result.stdout:
                return True
        except:
            pass
        return False
    
    def start_bot(self) -> bool:
        """Lancer le bot"""
        try:
            logger.info("[START] Lancement du bot...")
            
            # Vérifier que les fichiers existent
            if not Path(VENV_PATH).exists():
                logger.error(f"Venv non trouvé: {VENV_PATH}")
                return False
            
            if not Path(BOT_MAIN).exists():
                logger.error(f"Bot script non trouvé: {BOT_MAIN}")
                return False
            
            # Lancer le bot en arrière-plan
            self.bot_process = subprocess.Popen(
                [VENV_PATH, BOT_MAIN],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            
            logger.info(f"[OK] Bot lancé avec PID {self.bot_process.pid}")
            
            # Attendre que le bot soit prêt
            time.sleep(5)
            
            if self.is_bot_running():
                logger.info("[OK] Bot est opérationnel!")
                self.restart_count += 1
                self.save_status()
                return True
            else:
                logger.warning("[WARNING] Bot lancé mais pas encore prêt...")
                return False
                
        except Exception as e:
            logger.error(f"[ERROR] Erreur au lancement du bot: {e}", exc_info=True)
            return False
    
    def stop_bot(self) -> bool:
        """Arrêter le bot"""
        try:
            logger.info("[STOP] Arrêt du bot...")
            
            # Tuer tous les processus python
            subprocess.run(
                ['taskkill', '/IM', 'python.exe', '/F'],
                capture_output=True
            )
            
            time.sleep(2)
            logger.info("[OK] Bot arrêté")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Erreur à l'arrêt: {e}")
            return False
    
    def restart_bot(self, reason: str = "unknown") -> bool:
        """Redémarrer le bot"""
        logger.info(f"[RESTART] Redémarrage du bot (raison: {reason})")
        
        self.stop_bot()
        time.sleep(3)
        
        return self.start_bot()
    
    def check_and_monitor(self):
        """Vérifier et monitorer le bot"""
        logger.info(f"[CHECK] Vérification de l'état du bot...")
        self.last_check = datetime.now()
        
        if self.is_bot_running():
            logger.info(f"[OK] Bot en cours d'exécution")
            return True
        else:
            logger.warning(f"[WARNING] Bot n'est pas opérationnel!")
            return False
    
    def run_monitor_loop(self):
        """Boucle de monitoring continu"""
        logger.info(f"[MONITOR] Démarrage du monitoring (intervalle: {CHECK_INTERVAL}s)")
        
        try:
            while True:
                self.check_and_monitor()
                
                if not self.is_running:
                    logger.warning("[ALERT] Bot détecté comme arrêté!")
                    self.restart_bot(reason="health_check_failed")
                
                time.sleep(CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("[SHUTDOWN] Arrêt du monitoring...")
            self.stop_bot()
            sys.exit(0)
        except Exception as e:
            logger.error(f"[CRITICAL] Erreur dans la boucle de monitoring: {e}", exc_info=True)
            sys.exit(1)


def main():
    """Fonction principale"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Moniteur et gestionnaire du bot Discord')
    parser.add_argument('--start', action='store_true', help='Lancer le bot')
    parser.add_argument('--stop', action='store_true', help='Arrêter le bot')
    parser.add_argument('--restart', action='store_true', help='Redémarrer le bot')
    parser.add_argument('--monitor', action='store_true', help='Activer monitoring continu')
    parser.add_argument('--check', action='store_true', help='Vérifier l\'état')
    parser.add_argument('--status', action='store_true', help='Afficher le statut')
    
    args = parser.parse_args()
    
    monitor = BotMonitor()
    
    # Par défaut: vérifier et afficher le statut
    if not any([args.start, args.stop, args.restart, args.monitor, args.check, args.status]):
        args.check = True
    
    if args.start:
        logger.info("===== LANCEMENT DU BOT =====")
        monitor.start_bot()
    
    elif args.stop:
        logger.info("===== ARRÊT DU BOT =====")
        monitor.stop_bot()
    
    elif args.restart:
        logger.info("===== REDÉMARRAGE DU BOT =====")
        monitor.restart_bot(reason="manual_restart")
    
    elif args.check:
        logger.info("===== VÉRIFICATION DE L'ÉTAT =====")
        if monitor.check_and_monitor():
            logger.info("[STATUS] Bot: EN LIGNE [OK]")
            sys.exit(0)
        else:
            logger.warning("[STATUS] Bot: HORS LIGNE [ERREUR]")
            sys.exit(1)
    
    elif args.status:
        logger.info("===== STATUT DU BOT =====")
        running = monitor.is_bot_running()
        status = "EN LIGNE" if running else "HORS LIGNE"
        logger.info(f"État: {status}")
        logger.info(f"Health Check URL: {HEALTH_CHECK_URL}")
        logger.info(f"Redémarrages: {monitor.restart_count}")
        if STATUS_FILE.exists():
            with open(STATUS_FILE, 'r') as f:
                data = json.load(f)
                logger.info(f"Dernier redémarrage: {data.get('last_restart', 'N/A')}")
    
    elif args.monitor:
        logger.info("===== MODE MONITORING CONTINU =====")
        logger.info("Appuie sur Ctrl+C pour arrêter")
        monitor.run_monitor_loop()


if __name__ == "__main__":
    main()
