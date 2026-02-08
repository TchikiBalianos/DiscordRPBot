import nextcord as discord
from nextcord.ext import commands
import logging
import time
import random
from typing import Optional, Dict, List, Tuple
from datetime import datetime, date

logger = logging.getLogger('EngagementBot')

class PointSystem:
    """Système de points adapté pour Supabase"""
    
    def __init__(self, database, bot):
        self.database = database  # Utiliser database au lieu de db
        self.bot = bot
        
        # Alias pour compatibilité avec l'ancien code
        self.db = database
    
    def get_user_data(self, user_id: str) -> Dict:
        """Récupérer les données utilisateur"""
        try:
            return self.database.get_user_data(user_id)
        except Exception as e:
            logger.error(f"Error getting user data: {e}", exc_info=True)
            return {'user_id': user_id, 'points': 0}
    
    def add_points(self, user_id: str, points: int, reason: str = ""):
        """Ajouter des points à un utilisateur"""
        try:
            self.database.add_points(user_id, points)
            if reason:
                logger.info(f"Added {points} points to {user_id}: {reason}")
        except Exception as e:
            logger.error(f"Error adding points: {e}", exc_info=True)
    
    def remove_points(self, user_id: str, points: int) -> bool:
        """Retirer des points à un utilisateur"""
        try:
            return self.database.remove_points(user_id, points)
        except Exception as e:
            logger.error(f"Error removing points: {e}", exc_info=True)
            return False
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Récupérer le classement"""
        try:
            return self.database.get_leaderboard(limit)
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}", exc_info=True)
            return []
    
    def is_on_cooldown(self, command: str, user_id: str, cooldown_duration: int) -> Tuple[bool, Optional[int]]:
        """Vérifier si l'utilisateur est en cooldown"""
        try:
            last_used = self.database.get_cooldown(command, user_id)
            
            if last_used is None:
                return False, None
            
            current_time = time.time()
            time_passed = current_time - last_used
            
            if time_passed >= cooldown_duration:
                # Cooldown expiré, le supprimer
                self.database.remove_cooldown(command, user_id)
                return False, None
            
            remaining = int(cooldown_duration - time_passed)
            return True, remaining
        except Exception as e:
            logger.error(f"Error checking cooldown: {e}", exc_info=True)
            return False, None
    
    def set_cooldown(self, command: str, user_id: str):
        """Définir un cooldown"""
        try:
            self.database.set_cooldown(command, user_id, time.time())
        except Exception as e:
            logger.error(f"Error setting cooldown: {e}", exc_info=True)
    
    def check_daily_limit(self, command: str, user_id: str, limit: int) -> Tuple[bool, int]:
        """Vérifier la limite quotidienne"""
        try:
            today = date.today().isoformat()
            daily_commands = self.database.get_daily_commands(user_id, today)
            
            current_count = daily_commands.get(command, 0)
            
            if current_count >= limit:
                return False, current_count
            
            return True, current_count
        except Exception as e:
            logger.error(f"Error checking daily limit: {e}", exc_info=True)
            return True, 0  # En cas d'erreur, autoriser la commande
    
    def increment_daily_command(self, command: str, user_id: str):
        """Incrémenter le compteur de commande quotidienne"""
        try:
            self.database.increment_daily_command(user_id, command)
        except Exception as e:
            logger.error(f"Error incrementing daily command: {e}", exc_info=True)
    
    def get_inventory(self, user_id: str) -> List[str]:
        """Récupérer l'inventaire"""
        try:
            return self.database.get_inventory(user_id)
        except Exception as e:
            logger.error(f"Error getting inventory: {e}", exc_info=True)
            return []
    
    def add_item(self, user_id: str, item: str):
        """Ajouter un objet à l'inventaire"""
        try:
            self.database.add_item(user_id, item)
        except Exception as e:
            logger.error(f"Error adding item: {e}", exc_info=True)
    
    def remove_item(self, user_id: str, item: str) -> bool:
        """Retirer un objet de l'inventaire"""
        try:
            return self.database.remove_item(user_id, item)
        except Exception as e:
            logger.error(f"Error removing item: {e}", exc_info=True)
            return False
    
    def has_item(self, user_id: str, item: str) -> bool:
        """Vérifier si l'utilisateur a un objet"""
        try:
            inventory = self.get_inventory(user_id)
            return item in inventory
        except Exception as e:
            logger.error(f"Error checking item: {e}", exc_info=True)
            return False
    
    # Méthodes de compatibilité pour l'ancien système
    def is_in_prison(self, user_id: str) -> bool:
        """Vérifier si l'utilisateur est en prison"""
        try:
            release_time = self.database.get_prison_time(user_id)
            if release_time is None:
                return False
            
            return time.time() < release_time
        except Exception as e:
            logger.error(f"Error checking prison status: {e}", exc_info=True)
            return False
    
    def set_prison_time(self, user_id: str, duration: int):
        """Mettre en prison"""
        try:
            release_time = time.time() + duration
            self.database.set_prison_time(user_id, release_time)
        except Exception as e:
            logger.error(f"Error setting prison time: {e}", exc_info=True)
    
    def release_from_prison(self, user_id: str):
        """Libérer de prison"""
        try:
            self.database.remove_prison_time(user_id)
        except Exception as e:
            logger.error(f"Error releasing from prison: {e}", exc_info=True)
    
    def get_prison_time_remaining(self, user_id: str) -> Optional[int]:
        """Temps de prison restant"""
        try:
            release_time = self.database.get_prison_time(user_id)
            if release_time is None:
                return None
            
            remaining = release_time - time.time()
            return max(0, int(remaining))
        except Exception as e:
            logger.error(f"Error getting prison time: {e}", exc_info=True)
            return None
    
    # Méthodes de compatibilité pour l'ancien JSON
    def save_data(self):
        """Compatibility method - not needed for Supabase"""
        pass
    
    def get_user_points(self, user_id: str) -> int:
        """Get user points (compatibility method)"""
        try:
            user_data = self.get_user_data(user_id)
            return user_data.get('points', 0)
        except Exception as e:
            logger.error(f"Error getting user points: {e}", exc_info=True)
            return 0
    
    def set_user_points(self, user_id: str, points: int):
        """Set user points (compatibility method)"""
        try:
            current_points = self.get_user_points(user_id)
            difference = points - current_points
            
            if difference > 0:
                self.add_points(user_id, difference, "Points set")
            elif difference < 0:
                self.remove_points(user_id, abs(difference))
        except Exception as e:
            logger.error(f"Error setting user points: {e}", exc_info=True)
    
    async def daily_work(self, user_id: str) -> Tuple[bool, str]:
        """Complete daily work for points"""
        try:
            now = datetime.now().timestamp()
            last_work = self.database.get_last_work(user_id)
            
            WORK_COOLDOWN = 7200  # 2 hours
            WORK_MIN_AMOUNT = 100
            WORK_MAX_AMOUNT = 500
            
            if now - last_work < WORK_COOLDOWN:
                hours = int((WORK_COOLDOWN - (now - last_work)) / 3600)
                return False, f"⏰ Tu dois attendre encore {hours}h avant de pouvoir travailler à nouveau!"
            
            # Random work reward
            amount = random.randint(WORK_MIN_AMOUNT, WORK_MAX_AMOUNT)
            self.database.add_points(user_id, amount)
            self.database.set_last_work(user_id, now)
            
            return True, f"Tu as gagné **{amount}** 💵 en travaillant dur! 💼"
        except Exception as e:
            logger.error(f"Error in daily_work: {e}", exc_info=True)
            return False, "❌ Une erreur s'est produite lors du travail."
    
    async def get_monthly_leaderboard(self) -> List[Tuple[str, Dict]]:
        """Get the monthly leaderboard"""
        try:
            return self.database.get_leaderboard(limit=100)
        except Exception as e:
            logger.error(f"Error getting monthly leaderboard: {e}", exc_info=True)
            return []
    
    async def get_prison_status(self, user_id: str) -> Dict:
        """Get user prison status"""
        try:
            user_data = self.database.get_user_data(user_id)
            # Pour l'instant, retourner un dict avec les infos basiques
            # (prison n'est pas encore implémenté en full)
            return {
                'is_imprisoned': False,
                'prison_time_remaining': 0,
                'reason': 'N/A'
            }
        except Exception as e:
            logger.error(f"Error getting prison status: {e}", exc_info=True)
            return {'is_imprisoned': False, 'prison_time_remaining': 0}
    
    async def try_rob(self, robber_id: str, victim_id: str, victim_name: str = "l'utilisateur") -> Tuple[bool, int]:
        """Attempt to rob another user
        Returns: (success, amount_stolen_or_error_code)
        """
        try:
            robber_id = str(robber_id)
            victim_id = str(victim_id)
            
            # Get victim's current points
            victim_data = self.database.get_user_data(victim_id)
            if not victim_data:
                return False, -1  # User doesn't exist
            
            victim_points = victim_data.get('points', 0)
            
            # Victim must have at least 100 points to rob
            if victim_points < 100:
                return False, -2  # Not enough points
            
            # 60% success rate
            success_rate = 0.6
            if random.random() > success_rate:
                return False, -3  # Robbery failed
            
            # Calculate steal amount: 10-30% of victim's points
            steal_min = max(50, int(victim_points * 0.10))
            steal_max = int(victim_points * 0.30)
            steal_amount = random.randint(steal_min, steal_max)
            
            # Execute the robbery
            self.database.remove_points(victim_id, steal_amount)
            self.database.add_points(robber_id, steal_amount)
            
            return True, steal_amount
        except Exception as e:
            logger.error(f"Error in try_rob: {e}", exc_info=True)
            return False, -4  # Error occurred
    
    async def start_heist(self, leader_id: str) -> Tuple[bool, str]:
        """Start a heist for the user"""
        try:
            from config import HEIST_SUCCESS_RATE, HEIST_MIN_REWARD, HEIST_MAX_REWARD
            
            # Check if user has enough points
            user_data = self.database.get_user_data(leader_id)
            if not user_data or user_data.get('points', 0) < 500:
                return False, "❌ Tu as besoin d'au moins 500 💵 pour démarrer un braquage!"
            
            # 65% success rate
            if random.random() > HEIST_SUCCESS_RATE:
                # Failed heist - lose 20% of attempted stake
                loss = min(int(user_data.get('points', 0) * 0.20), 1000)
                self.database.remove_points(leader_id, loss)
                return False, f"❌ Le braquage a échoué! Tu as perdu {loss} 💵..."
            
            # Success - random reward
            reward = random.randint(HEIST_MIN_REWARD, HEIST_MAX_REWARD)
            self.database.add_points(leader_id, reward)
            
            return True, f"✅ Le braquage réussit! Tu gagnes **{reward}** 💵!"
        except Exception as e:
            logger.error(f"Error in start_heist: {e}", exc_info=True)
            return False, "❌ Une erreur s'est produite lors du braquage."
    
    async def join_heist(self, user_id: str) -> Tuple[bool, str]:
        """Join an active heist (placeholder)"""
        try:
            return True, "✅ Tu as rejoint le braquage! Attends la fin du braquage du leader..."
        except Exception as e:
            logger.error(f"Error in join_heist: {e}", exc_info=True)
            return False, "❌ Impossible de rejoindre le braquage."
    
    async def evaluate_combat_moves(self, attacker_move: str, defender_move: str) -> Tuple[str, str]:
        """Evaluate two combat moves and return winner and message"""
        from config import COMBAT_MOVE_RESULTS, COMBAT_MOVE_NAMES
        
        key = (attacker_move, defender_move)
        if key in COMBAT_MOVE_RESULTS:
            result, message = COMBAT_MOVE_RESULTS[key]
            attacker_move_name = COMBAT_MOVE_NAMES.get(attacker_move, 'Coup inconnu')
            defender_move_name = COMBAT_MOVE_NAMES.get(defender_move, 'Coup inconnu')
            full_message = f"{attacker_move} **{attacker_move_name}** vs {defender_move} **{defender_move_name}**\n\n{message}"
            return result, full_message
        return 'tie', f"Coups indefinis: {attacker_move} vs {defender_move}"
    
    async def start_combat(self, challenger_id: str, target_id: str, bet: int) -> Tuple[bool, str, dict]:
        """Prepare a combat - returns info for interactive combat
        Returns: (success, message, combat_info_dict)
        """
        try:
            from config import COMBAT_MIN_BET, COMBAT_MAX_BET
            
            challenger_id = str(challenger_id)
            target_id = str(target_id)
            
            # Validate bet
            if bet < COMBAT_MIN_BET or bet > COMBAT_MAX_BET:
                return False, f"Mise doit etre entre {COMBAT_MIN_BET} et {COMBAT_MAX_BET}!", {}
            
            # Check both players have enough points
            challenger_data = self.database.get_user_data(challenger_id)
            target_data = self.database.get_user_data(target_id)
            
            if not challenger_data or challenger_data.get('points', 0) < bet:
                return False, f"Tu n\'as pas assez de coins ({bet} requis)!", {}
            
            if not target_data or target_data.get('points', 0) < bet:
                opponent_name = target_data.get('name', 'Ton adversaire') if target_data else 'Ton adversaire'
                return False, f"{opponent_name} n\'a pas assez de coins!", {}
            
            # Success - return combat info without modifying points yet
            return True, "Combat initialise!", {
                'challenger_id': challenger_id,
                'target_id': target_id,
                'bet': bet
            }
        except Exception as e:
            logger.error(f"Error in start_combat: {e}", exc_info=True)
            return False, "Erreur lors du combat.", {}
    
    # Propriétés de compatibilité
    @property
    def data(self) -> Dict:
        """Compatibility property for legacy code"""
        logger.warning("Using legacy data property - consider migrating to specific methods")
        return {}