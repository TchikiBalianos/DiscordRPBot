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
    
    # Propriétés de compatibilité
    @property
    def data(self) -> Dict:
        """Compatibility property for legacy code"""
        logger.warning("Using legacy data property - consider migrating to specific methods")
        return {}