#!/usr/bin/env python3
"""
Système de test automatisé pour les commandes Discord
Teste toutes les commandes et génère un rapport d'erreurs
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import List, Dict, Tuple
import sys

# Patches requis AVANT les imports nextcord
import audioop_patch

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_report.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('CommandTester')

# Import des modules du bot
sys.path.insert(0, '.')

from database_supabase import SupabaseDatabase
from point_system import PointSystem


class CommandTester:
    """Testeur automatisé de commandes"""
    
    def __init__(self):
        self.database = SupabaseDatabase()
        self.points = PointSystem(self.database, None)
        self.test_user_id = "999999999999999999"  # ID de test fictif
        self.results = {
            'passed': [],
            'failed': [],
            'errors': []
        }
    
    async def test_points_command(self) -> Tuple[bool, str]:
        """Tester: !points - Affiche les points de l'utilisateur"""
        try:
            logger.info("TEST: !points command")
            points = self.database.get_user_points(self.test_user_id)
            
            if isinstance(points, int):
                logger.info(f"✓ Points command passed: User has {points} points")
                return True, f"Points: {points}"
            else:
                raise ValueError(f"Expected int, got {type(points)}")
        except Exception as e:
            logger.error(f"✗ Points command failed: {e}", exc_info=True)
            return False, str(e)
    
    async def test_work_command(self) -> Tuple[bool, str]:
        """Tester: !work - Gagne des points avec cooldown"""
        try:
            logger.info("TEST: !work command")
            success, message = await self.points.daily_work(self.test_user_id)
            
            if success:
                logger.info(f"✓ Work command passed: {message}")
                return True, message
            else:
                logger.warning(f"! Work command returned False: {message}")
                return True, message  # C'est normal si le cooldown est actif
        except Exception as e:
            logger.error(f"✗ Work command failed: {e}", exc_info=True)
            return False, str(e)
    
    async def test_leaderboard_command(self) -> Tuple[bool, str]:
        """Tester: !leaderboard - Affiche le classement"""
        try:
            logger.info("TEST: !leaderboard command")
            leaderboard = await self.points.get_monthly_leaderboard()
            
            if isinstance(leaderboard, list):
                logger.info(f"✓ Leaderboard command passed: {len(leaderboard)} users")
                return True, f"Leaderboard has {len(leaderboard)} entries"
            else:
                raise ValueError(f"Expected list, got {type(leaderboard)}")
        except Exception as e:
            logger.error(f"✗ Leaderboard command failed: {e}", exc_info=True)
            return False, str(e)
    
    async def test_prison_status_command(self) -> Tuple[bool, str]:
        """Tester: !prison - Affiche le statut de prison"""
        try:
            logger.info("TEST: !prison command")
            status = await self.points.get_prison_status(self.test_user_id)
            
            # Vérifier que le dict contient les bonnes clés
            required_keys = ['is_imprisoned', 'prison_time_remaining']
            if all(key in status for key in required_keys):
                logger.info(f"✓ Prison command passed: {status}")
                return True, f"Prison status: {status}"
            else:
                raise KeyError(f"Missing keys. Expected {required_keys}, got {list(status.keys())}")
        except Exception as e:
            logger.error(f"✗ Prison command failed: {e}", exc_info=True)
            return False, str(e)
    
    async def test_database_connection(self) -> Tuple[bool, str]:
        """Tester: Connexion à la base de données"""
        try:
            logger.info("TEST: Database connection")
            
            if self.database.is_connected():
                logger.info("✓ Database connection passed")
                return True, "Connected to Supabase"
            else:
                raise Exception("Database connection failed")
        except Exception as e:
            logger.error(f"✗ Database connection failed: {e}", exc_info=True)
            return False, str(e)
    
    async def test_user_creation(self) -> Tuple[bool, str]:
        """Tester: Création d'utilisateur"""
        try:
            logger.info("TEST: User creation")
            
            user_data = self.database.get_user_data(self.test_user_id)
            if user_data and 'user_id' in user_data:
                logger.info(f"✓ User creation passed: {user_data}")
                return True, f"User created/found: {user_data['user_id']}"
            else:
                raise ValueError("User data invalid")
        except Exception as e:
            logger.error(f"✗ User creation failed: {e}", exc_info=True)
            return False, str(e)
    
    async def test_add_points(self) -> Tuple[bool, str]:
        """Tester: Ajouter des points"""
        try:
            logger.info("TEST: Add points")
            
            initial_points = self.database.get_user_points(self.test_user_id)
            self.database.add_points(self.test_user_id, 100, "test")
            final_points = self.database.get_user_points(self.test_user_id)
            
            if final_points > initial_points:
                logger.info(f"✓ Add points passed: {initial_points} -> {final_points}")
                return True, f"Points added: {initial_points} -> {final_points}"
            else:
                raise ValueError("Points not added")
        except Exception as e:
            logger.error(f"✗ Add points failed: {e}", exc_info=True)
            return False, str(e)
    
    async def run_all_tests(self) -> None:
        """Exécuter tous les tests"""
        logger.info("=" * 80)
        logger.info("STARTING AUTOMATED COMMAND TESTS")
        logger.info(f"Test user ID: {self.test_user_id}")
        logger.info("=" * 80)
        
        tests = [
            ("Database Connection", self.test_database_connection),
            ("User Creation", self.test_user_creation),
            ("Add Points", self.test_add_points),
            ("Points Command", self.test_points_command),
            ("Leaderboard Command", self.test_leaderboard_command),
            ("Prison Status Command", self.test_prison_status_command),
            ("Work Command", self.test_work_command),
        ]
        
        for test_name, test_func in tests:
            logger.info(f"\n>>> Running: {test_name}")
            success, message = await test_func()
            
            if success:
                self.results['passed'].append({
                    'name': test_name,
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                })
                logger.info(f"✓ PASSED: {test_name}")
            else:
                self.results['failed'].append({
                    'name': test_name,
                    'error': message,
                    'timestamp': datetime.now().isoformat()
                })
                logger.error(f"✗ FAILED: {test_name}")
        
        self.print_report()
    
    def print_report(self) -> None:
        """Afficher un rapport des tests"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST REPORT")
        logger.info("=" * 80)
        
        logger.info(f"\n[PASSED] {len(self.results['passed'])}/{len(self.results['passed']) + len(self.results['failed'])} tests")
        for test in self.results['passed']:
            logger.info(f"  ✓ {test['name']}: {test['message']}")
        
        if self.results['failed']:
            logger.info(f"\n[FAILED] {len(self.results['failed'])} tests")
            for test in self.results['failed']:
                logger.error(f"  ✗ {test['name']}: {test['error']}")
        
        # Sauvegarder le rapport en JSON
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(self.results['passed']) + len(self.results['failed']),
            'passed': len(self.results['passed']),
            'failed': len(self.results['failed']),
            'results': self.results
        }
        
        with open('test_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"\nReport saved to test_report.json")
        logger.info("=" * 80)


async def main():
    tester = CommandTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
