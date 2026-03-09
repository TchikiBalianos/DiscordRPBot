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
            self.database.add_points(user_id, points, reason=reason)
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
        """Complete work for points. Cooldown is handled by the command decorator."""
        try:
            from config import WORK_MIN_AMOUNT, WORK_MAX_AMOUNT
            
            # Random work reward
            amount = random.randint(WORK_MIN_AMOUNT, WORK_MAX_AMOUNT)
            
            # Work narrations for variety
            jobs = [
                f"💼 Tu as bossé comme serveur et gagné **{amount}** 💵 !",
                f"🔧 Tu as réparé des bagnoles au garage, **{amount}** 💵 en poche !",
                f"📦 Tu as livré des colis toute la journée, **{amount}** 💵 gagnés !",
                f"🧹 Tu as nettoyé le quartier, la mairie te file **{amount}** 💵 !",
                f"🍕 Tu as livré des pizzas comme un fou, **{amount}** 💵 !",
                f"🏗️ Tu as fait le maçon sur un chantier, **{amount}** 💵 !",
                f"🎧 Tu as fait le DJ au bar du coin, **{amount}** 💵 !",
                f"🚕 Tu as conduit un Uber toute la nuit, **{amount}** 💵 !",
            ]
            
            self.database.add_points(user_id, amount, reason="Work")
            self.database.set_last_work(user_id, datetime.now().timestamp())
            
            return True, random.choice(jobs)
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
        """Get user prison status - checks both justice system and legacy tables"""
        try:
            user_id = str(user_id)
            now = time.time()

            # 1. Check justice system (prison_records table) first
            if hasattr(self.database, 'get_prison_status'):
                status = self.database.get_prison_status(user_id)
                if status:
                    return {
                        'is_imprisoned': True,
                        'prison_time_remaining': status.get('remaining_seconds', 0),
                        'reason': status.get('reason', 'N/A'),
                        'release_at': status.get('release_at', None)
                    }

            # 2. Fallback: legacy prison_times table
            release_time = self.database.get_prison_time(user_id)
            if release_time and float(release_time) > now:
                remaining = int(float(release_time) - now)
                return {
                    'is_imprisoned': True,
                    'prison_time_remaining': remaining,
                    'reason': 'N/A'
                }

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
            self.database.add_points(robber_id, steal_amount, reason="Rob")
            
            # Track last robbery for revenge feature
            self._set_last_robbery(victim_id, robber_id, steal_amount)

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
            self.database.add_points(leader_id, reward, reason="Heist reward")
            
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
    
    async def evaluate_combat_moves(self, attacker_idx: int, defender_idx: int, selected_emojis: list) -> Tuple[str, str]:
        """
        Evaluate combat moves based on emoji indices
        Args:
            attacker_idx: Index (0-5) of attacker's emoji in selected_emojis
            defender_idx: Index (0-5) of defender's emoji in selected_emojis
            selected_emojis: List of 6 selected emojis for this combat
        Returns:
            (result, message) where result is 'win' (attacker), 'lose' (defender), or 'tie'
        """
        import random
        from config import COMBAT_MATRIX
        
        # Clé: (attacker_idx, defender_idx)
        key = (attacker_idx, defender_idx)
        
        if key in COMBAT_MATRIX:
            result, messages_list = COMBAT_MATRIX[key]
            message = random.choice(messages_list)
            
            # Ajouter les emojis choisis
            attacker_emoji = selected_emojis[attacker_idx]
            defender_emoji = selected_emojis[defender_idx]
            
            full_message = f"{attacker_emoji} vs {defender_emoji}\n\n{message}"
            return result, full_message
        
        # Fallback si clé non trouvée
        return 'tie', f"Emojis: {selected_emojis[attacker_idx]} vs {selected_emojis[defender_idx]}\n\nCombat indécis!"
    
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
    
    # === FEATURES: shop / prison activities / tribunal / revenge (stabilisation) ===

    def _load_state(self, key: str, default):
        """Load JSON state from Supabase bot_state table if available."""
        try:
            if hasattr(self.database, "load_bot_state") and self.database.is_connected():
                data = self.database.load_bot_state(key)
                return data if data is not None else default
        except Exception:
            pass
        return default

    def _save_state(self, key: str, value) -> None:
        """Save JSON state to Supabase bot_state table if available."""
        try:
            if hasattr(self.database, "save_bot_state") and self.database.is_connected():
                self.database.save_bot_state(key, value)
        except Exception:
            pass

    def _set_last_robbery(self, victim_id: str, robber_id: str, amount: int) -> None:
        """Store last robbery info for revenge command."""
        state = self._load_state("last_robbery", {})
        state[str(victim_id)] = {
            "robber_id": str(robber_id),
            "amount": int(amount),
            "ts": int(time.time())
        }
        self._save_state("last_robbery", state)

    async def try_revenge(self, user_id: str) -> Tuple[bool, str]:
        """Attempt revenge on the last robber."""
        try:
            from config import REVENGE_SUCCESS_RATE
            user_id = str(user_id)

            state = self._load_state("last_robbery", {})
            entry = state.get(user_id)
            if not entry:
                return False, "❌ Personne à qui se venger pour le moment."

            robber_id = str(entry.get("robber_id", ""))
            if not robber_id or robber_id == user_id:
                return False, "❌ Impossible d'identifier le voleur."

            robber_data = self.database.get_user_data(robber_id) or {"points": 0}
            robber_points = int(robber_data.get("points", 0))

            if robber_points < 100:
                return False, "❌ Ton voleur est fauché, ça ne vaut pas le coup."

            if random.random() > REVENGE_SUCCESS_RATE:
                return True, "❌ Ta vengeance a échoué… il/elle était sur ses gardes."

            # 5-20% de ses points
            steal_amount = random.randint(max(50, int(robber_points * 0.05)), max(50, int(robber_points * 0.20)))
            steal_amount = min(steal_amount, robber_points)

            self.database.remove_points(robber_id, steal_amount)
            self.database.add_points(user_id, steal_amount, reason="Revenge")

            # Clear after success
            state.pop(user_id, None)
            self._save_state("last_robbery", state)

            return True, f"✅ Vengeance réussie ! Tu récupères **{steal_amount}** 💵 sur <@{robber_id}>."
        except Exception as e:
            logger.error(f"Error in try_revenge: {e}", exc_info=True)
            return False, "❌ Une erreur s'est produite pendant la vengeance."

    async def buy_item(self, user_id: str, item_id: str) -> Tuple[bool, str]:
        """Buy an item from the shop."""
        try:
            from config import SHOP_ITEMS
            user_id = str(user_id)
            item_id = str(item_id)

            if item_id not in SHOP_ITEMS:
                available = ", ".join([f"`{k}`" for k in SHOP_ITEMS.keys()])
                return False, f"❌ Item inconnu. Disponibles: {available}"

            item = SHOP_ITEMS[item_id]
            price = int(item.get("price", 0))
            user_points = int((self.database.get_user_data(user_id) or {}).get("points", 0))

            if user_points < price:
                return False, f"❌ Tu n'as que {user_points} points. Il te faut {price} points."

            if not self.database.remove_points(user_id, price):
                return False, "❌ Impossible de débiter tes points (erreur DB)."

            self.database.add_item(user_id, item_id)
            return True, f"✅ Achat réussi : {item.get('name', item_id)} pour **{price}** 💵."
        except Exception as e:
            logger.error(f"Error in buy_item: {e}", exc_info=True)
            return False, "❌ Une erreur s'est produite lors de l'achat."

    async def do_prison_activity(self, user_id: str, activity_id: str) -> Tuple[bool, str]:
        """Do a prison activity that reduces remaining prison time (justice-system compatible)."""
        try:
            from config import PRISON_ACTIVITIES
            user_id = str(user_id)
            activity_id = str(activity_id)

            if activity_id not in PRISON_ACTIVITIES:
                available = ", ".join([f"`{k}`" for k in PRISON_ACTIVITIES.keys()])
                return False, f"❌ Activité inconnue. Disponibles: {available}"

            reduction = int(PRISON_ACTIVITIES[activity_id].get("reduction", 0))

            # Prefer justice system tables if available
            if hasattr(self.database, "get_prison_status") and self.database.get_prison_status(user_id):
                if not getattr(self.database, "supabase", None) or not self.database.is_connected():
                    return False, "❌ Base de données indisponible."

                # Fetch current release_at and update it
                res = self.database.supabase.table("prison_records").select("release_at").eq("user_id", user_id).eq("status", "imprisoned").execute()
                if not res.data:
                    return False, "❌ Tu n'es pas en prison."
                from datetime import datetime, timedelta
                current_release = datetime.fromisoformat(res.data[0]["release_at"])
                new_release = current_release - timedelta(seconds=reduction)
                if new_release < datetime.now():
                    new_release = datetime.now()
                self.database.supabase.table("prison_records").update({"release_at": new_release.isoformat()}).eq("user_id", user_id).eq("status", "imprisoned").execute()

                remaining = int(max(0, (new_release - datetime.now()).total_seconds()))
                return True, f"✅ Activité effectuée ! Peine réduite de **{reduction}s**. Temps restant: **{remaining}s**."

            # Fallback legacy prison_times table
            release_time = self.database.get_prison_time(user_id)
            now_ts = time.time()
            if release_time is None or release_time <= now_ts:
                return False, "❌ Tu n'es pas en prison."

            new_release_ts = max(now_ts, float(release_time) - reduction)
            self.database.set_prison_time(user_id, new_release_ts)

            remaining = int(max(0, new_release_ts - now_ts))
            return True, f"✅ Activité effectuée ! Peine réduite de **{reduction}s**. Temps restant: **{remaining}s**."
        except Exception as e:
            logger.error(f"Error in do_prison_activity: {e}", exc_info=True)
            return False, "❌ Une erreur s'est produite pendant l'activité."

    async def request_trial(self, user_id: str, plea_text: str) -> Tuple[bool, str]:
        """Create a tribunal vote message. The vote itself is handled in vote_trial."""
        try:
            from config import TRIBUNAL_COST, TRIBUNAL_VOTE_DURATION, TRIBUNAL_COOLDOWN
            user_id = str(user_id)
            now = int(time.time())

            # Must be in prison to request trial (game logic)
            in_prison = False
            if hasattr(self.database, "get_prison_status"):
                in_prison = self.database.get_prison_status(user_id) is not None
            if not in_prison:
                # fallback legacy
                release_time = self.database.get_prison_time(user_id)
                in_prison = release_time is not None and release_time > now

            if not in_prison:
                return False, "❌ Tu n'es pas en prison, donc pas de procès à demander."

            # Cooldown managed via bot_state (simple + robust)
            cooldowns = self._load_state("tribunal_cooldowns", {})
            last = int(cooldowns.get(user_id, 0))
            if now - last < TRIBUNAL_COOLDOWN:
                remaining = TRIBUNAL_COOLDOWN - (now - last)
                minutes = max(1, remaining // 60)
                return False, f"⏰ Tu dois attendre encore ~{minutes} min avant de redemander un procès."

            user_points = int((self.database.get_user_data(user_id) or {}).get("points", 0))
            if user_points < TRIBUNAL_COST:
                return False, f"❌ Il te faut {TRIBUNAL_COST} points pour demander un procès."

            if not self.database.remove_points(user_id, TRIBUNAL_COST):
                return False, "❌ Erreur lors du paiement des frais de procès."

            trials = self._load_state("tribunal_trials", {})
            trial = {
                "defendant_id": user_id,
                "plea": plea_text[:500],
                "created_at": now,
                "ends_at": now + int(TRIBUNAL_VOTE_DURATION),
                "yes": [],
                "no": []
            }
            trials[user_id] = trial
            self._save_state("tribunal_trials", trials)

            cooldowns[user_id] = now
            self._save_state("tribunal_cooldowns", cooldowns)

            minutes = max(1, int(TRIBUNAL_VOTE_DURATION) // 60)
            msg = (
                f"⚖️ **PROCÈS** : <@{user_id}> demande un jugement !\n"
                f"📝 **Plaidoyer** : {plea_text}\n\n"
                f"Votez avec ✅ (acquitter) ou ❌ (condamner) pendant **{minutes} min**."
            )
            return True, msg
        except Exception as e:
            logger.error(f"Error in request_trial: {e}", exc_info=True)
            return False, "❌ Une erreur s'est produite lors de la demande de procès."

    async def vote_trial(self, voter_id: str, defendant_id: str, vote_yes: bool) -> Tuple[bool, str]:
        """Record a vote and decide the outcome when conditions are met."""
        try:
            from config import TRIBUNAL_MIN_VOTERS, TRIBUNAL_ACQUIT_RATE, TRIBUNAL_VOTE_DURATION
            voter_id = str(voter_id)
            defendant_id = str(defendant_id)
            now = int(time.time())

            if voter_id == defendant_id:
                return False, "❌ Tu ne peux pas voter pour ton propre procès."

            trials = self._load_state("tribunal_trials", {})
            trial = trials.get(defendant_id)
            if not trial:
                return False, "❌ Aucun procès actif trouvé."

            ends_at = int(trial.get("ends_at", trial.get("created_at", now) + int(TRIBUNAL_VOTE_DURATION)))
            yes = set(trial.get("yes", []))
            no = set(trial.get("no", []))

            if voter_id in yes or voter_id in no:
                return False, "⚠️ Tu as déjà voté."

            if now > ends_at:
                # Time expired: finalize with current votes
                return await self._finalize_trial(defendant_id, trial)

            if vote_yes:
                yes.add(voter_id)
            else:
                no.add(voter_id)

            trial["yes"] = list(yes)
            trial["no"] = list(no)
            trials[defendant_id] = trial
            self._save_state("tribunal_trials", trials)

            total = len(yes) + len(no)
            # Decide early if enough votes
            if total >= int(TRIBUNAL_MIN_VOTERS):
                return await self._finalize_trial(defendant_id, trial)

            return True, f"🗳️ Vote enregistré. ✅ {len(yes)} / ❌ {len(no)} (min {TRIBUNAL_MIN_VOTERS} votes)."
        except Exception as e:
            logger.error(f"Error in vote_trial: {e}", exc_info=True)
            return False, "❌ Erreur lors du vote."

    async def _finalize_trial(self, defendant_id: str, trial: dict) -> Tuple[bool, str]:
        """Finalize a trial and apply the result."""
        try:
            from config import TRIBUNAL_MIN_VOTERS, TRIBUNAL_ACQUIT_RATE
            defendant_id = str(defendant_id)

            yes = set(trial.get("yes", []))
            no = set(trial.get("no", []))
            total = len(yes) + len(no)

            # Remove the trial no matter what (avoid stuck states)
            trials = self._load_state("tribunal_trials", {})
            trials.pop(defendant_id, None)
            self._save_state("tribunal_trials", trials)

            if total < int(TRIBUNAL_MIN_VOTERS):
                return True, f"⚖️ Procès terminé : pas assez de votes ({total}/{TRIBUNAL_MIN_VOTERS}). Le jugement est reporté."

            acquit_ratio = (len(yes) / total) if total else 0.0
            if acquit_ratio >= float(TRIBUNAL_ACQUIT_RATE):
                # Acquitted: release from prison
                self.database.release_from_prison(defendant_id) if hasattr(self.database, 'release_from_prison') else self.database.remove_prison_time(defendant_id)
                return True, f"⚖️ Verdict : **ACQUITTÉ** ✅ ({len(yes)}/{total}) — <@{defendant_id}> est libéré(e) !"
            else:
                return True, f"⚖️ Verdict : **COUPABLE** ❌ ({len(no)}/{total}) — <@{defendant_id}> reste en prison."
        except Exception as e:
            logger.error(f"Error finalizing trial: {e}", exc_info=True)
            return False, "❌ Erreur lors de la finalisation du procès."
    # Propriétés de compatibilité
    @property
    def data(self) -> Dict:
        """Compatibility property for legacy code"""
        logger.warning("Using legacy data property - consider migrating to specific methods")
        return {}
