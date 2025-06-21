import discord
from discord.ext import commands
import logging
import time
import random
from typing import Optional, Dict, List, Tuple
from datetime import datetime, date

logger = logging.getLogger('EngagementBot')

class PointSystem:
    """Système de points adapté pour Supabase"""
    
    def __init__(self, database, bot):
        self.database = database
        self.bot = bot
    
    def get_user_data(self, user_id: str) -> Dict:
        """Récupérer les données utilisateur"""
        return self.database.get_user_data(user_id)
    
    def add_points(self, user_id: str, points: int, reason: str = ""):
        """Ajouter des points à un utilisateur"""
        self.database.add_points(user_id, points)
        if reason:
            logger.info(f"Added {points} points to {user_id}: {reason}")
    
    def remove_points(self, user_id: str, points: int) -> bool:
        """Retirer des points à un utilisateur"""
        return self.database.remove_points(user_id, points)
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Récupérer le classement"""
        return self.database.get_leaderboard(limit)
    
    def is_on_cooldown(self, command: str, user_id: str, cooldown_duration: int) -> Tuple[bool, Optional[int]]:
        """Vérifier si l'utilisateur est en cooldown"""
        last_used = self.database.get_cooldown(command, user_id)
        
        if last_used is None:
            return False, None
        
        current_time = time.time()
        time_passed = current_time - last_used
        
        if time_passed >= cooldown_duration:
            return False, None
        
        remaining = int(cooldown_duration - time_passed)
        return True, remaining
    
    def set_cooldown(self, command: str, user_id: str):
        """Définir un cooldown"""
        self.database.set_cooldown(command, user_id, time.time())
    
    def check_daily_limit(self, command: str, user_id: str, limit: int) -> Tuple[bool, int]:
        """Vérifier la limite quotidienne"""
        today = date.today().isoformat()
        daily_commands = self.database.get_daily_commands(user_id, today)
        
        current_count = daily_commands.get(command, 0)
        
        if current_count >= limit:
            return False, current_count
        
        return True, current_count
    
    def increment_daily_command(self, command: str, user_id: str):
        """Incrémenter le compteur de commande quotidienne"""
        self.database.increment_daily_command(user_id, command)
    
    def get_inventory(self, user_id: str) -> List[str]:
        """Récupérer l'inventaire"""
        return self.database.get_inventory(user_id)
    
    def add_item(self, user_id: str, item: str):
        """Ajouter un objet à l'inventaire"""
        self.database.add_item(user_id, item)
    
    def remove_item(self, user_id: str, item: str) -> bool:
        """Retirer un objet de l'inventaire"""
        return self.database.remove_item(user_id, item)
    
    def has_item(self, user_id: str, item: str) -> bool:
        """Vérifier si l'utilisateur a un objet"""
        inventory = self.get_inventory(user_id)
        return item in inventory
    
    # Méthodes de compatibilité pour l'ancien système
    def is_in_prison(self, user_id: str) -> bool:
        """Vérifier si l'utilisateur est en prison"""
        release_time = self.database.get_prison_time(user_id)
        if release_time is None:
            return False
        
        return time.time() < release_time
    
    def set_prison_time(self, user_id: str, duration: int):
        """Mettre en prison"""
        release_time = time.time() + duration
        self.database.set_prison_time(user_id, release_time)
    
    def release_from_prison(self, user_id: str):
        """Libérer de prison"""
        self.database.remove_prison_time(user_id)
    
    def get_prison_time_remaining(self, user_id: str) -> Optional[int]:
        """Temps de prison restant"""
        release_time = self.database.get_prison_time(user_id)
        if release_time is None:
            return None
        
        remaining = release_time - time.time()
        return max(0, int(remaining))