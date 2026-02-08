import logging
import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger('EngagementBot')

class WarStatus(Enum):
    DECLARED = "declared"
    PREPARATION = "preparation"
    ACTIVE = "active"
    FINISHED = "finished"

class WarType(Enum):
    TERRITORY = "territory"
    REPUTATION = "reputation"
    VAULT_RAID = "vault_raid"

class GangWarSystem:
    def __init__(self, database, gang_system):
        self.db = database
        self.gang_system = gang_system
        self.war_declaration_cost = 5000
        self.preparation_time = 1800  # 30 minutes
        self.war_duration = 3600  # 1 hour
        
    def declare_war(self, attacker_gang_id: str, defender_gang_id: str, war_type: WarType, stake: str = None) -> Tuple[bool, str]:
        """Declare war against another gang"""
        try:
            # Ensure gang_wars dict exists
            if "gang_wars" not in self.db.data:
                self.db.data["gang_wars"] = {}
            
            if attacker_gang_id == defender_gang_id:
                return False, "Vous ne pouvez pas déclarer la guerre à votre propre gang."
            
            attacker_data = self.gang_system.get_gang_info(attacker_gang_id)
            defender_data = self.gang_system.get_gang_info(defender_gang_id)
            
            if not attacker_data or not defender_data:
                return False, "Gang introuvable."
            
            # Check if attacker gang has enough vault points
            if attacker_data["vault_points"] < self.war_declaration_cost:
                return False, f"Votre gang a besoin de {self.war_declaration_cost} points dans le coffre pour déclarer la guerre."
            
            # Check if either gang is already in war
            if self._gang_in_active_war(attacker_gang_id) or self._gang_in_active_war(defender_gang_id):
                return False, "L'un des gangs est déjà en guerre."
            
            # Generate war ID
            war_id = f"war_{int(datetime.now().timestamp())}"
            
            # Create war
            war_data = {
                "war_id": war_id,
                "attacker_gang_id": attacker_gang_id,
                "defender_gang_id": defender_gang_id,
                "war_type": war_type.value,
                "stake": stake,
                "status": WarStatus.DECLARED.value,
                "declared_at": datetime.now().isoformat(),
                "starts_at": (datetime.now() + timedelta(seconds=self.preparation_time)).isoformat(),
                "ends_at": (datetime.now() + timedelta(seconds=self.preparation_time + self.war_duration)).isoformat(),
                "attacker_power": 0,
                "defender_power": 0,
                "participants": {
                    "attackers": [],
                    "defenders": []
                },
                "winner": None,
                "rewards": {}
            }
            
            self.db.data["gang_wars"][war_id] = war_data
            
            # Deduct declaration cost
            attacker_data["vault_points"] -= self.war_declaration_cost
            
            self.db.save_data()
            
            return True, f"Guerre déclarée contre '{defender_data['name']}' ! La guerre commencera dans {self.preparation_time//60} minutes."
            
        except Exception as e:
            logger.error(f"Error declaring war: {e}", exc_info=True)
            return False, "Erreur lors de la déclaration de guerre."
    
    def join_war(self, user_id: str, side: str) -> Tuple[bool, str]:
        """Join an active war"""
        try:
            if "gang_wars" not in self.db.data:
                return False, "Aucune guerre n'est en cours."
            
            gang_id = self.gang_system.get_user_gang(user_id)
            if not gang_id:
                return False, "Vous devez être membre d'un gang pour participer à une guerre."
            
            # Find active war for this gang
            war_data = None
            for war in self.db.data["gang_wars"].values():
                if war["status"] in [WarStatus.PREPARATION.value, WarStatus.ACTIVE.value]:
                    if gang_id in [war["attacker_gang_id"], war["defender_gang_id"]]:
                        war_data = war
                        break
            
            if not war_data:
                return False, "Votre gang n'est pas en guerre actuellement."
            
            # Determine correct side
            if gang_id == war_data["attacker_gang_id"]:
                participant_side = "attackers"
                side_name = "attaquants"
            elif gang_id == war_data["defender_gang_id"]:
                participant_side = "defenders"
                side_name = "défenseurs"
            else:
                return False, "Votre gang n'est pas impliqué dans cette guerre."
            
            # Check if already participating
            if user_id in war_data["participants"][participant_side]:
                return False, f"Vous participez déjà comme {side_name}."
            
            # Add participant
            war_data["participants"][participant_side].append(user_id)
            
            # Calculate participant power based on user stats
            user_power = self._calculate_user_war_power(user_id)
            
            if participant_side == "attackers":
                war_data["attacker_power"] += user_power
            else:
                war_data["defender_power"] += user_power
            
            self.db.save_data()
            
            return True, f"Vous rejoignez la guerre comme {side_name} ! Puissance ajoutée: {user_power}"
            
        except Exception as e:
            logger.error(f"Error joining war: {e}", exc_info=True)
            return False, "Erreur lors de la participation à la guerre."
    
    def _calculate_user_war_power(self, user_id: str) -> int:
        """Calculate user's power contribution to war"""
        try:
            user_points = self.db.get_points(user_id)
            gang_id = self.gang_system.get_user_gang(user_id)
            
            if not gang_id:
                return 0
            
            gang_data = self.gang_system.get_gang_info(gang_id)
            member_data = gang_data["members"][user_id]
            
            # Base power from points (scaled down)
            base_power = min(user_points // 100, 1000)
            
            # Rank bonus
            rank_bonus = {
                "Recrue": 1.0,
                "Membre": 1.2,
                "Lieutenant": 1.5,
                "Chef": 2.0
            }
            
            power = int(base_power * rank_bonus.get(member_data["rank"], 1.0))
            
            # Gang upgrade bonus
            war_bonus_level = gang_data["upgrades"].get("war_bonus", 1)
            power = int(power * (1 + (war_bonus_level - 1) * 0.1))
            
            return max(power, 50)  # Minimum power
            
        except Exception as e:
            logger.error(f"Error calculating user war power: {e}", exc_info=True)
            return 50
    
    def process_war_results(self, war_id: str) -> Tuple[bool, str]:
        """Process war results and distribute rewards"""
        try:
            if "gang_wars" not in self.db.data or war_id not in self.db.data.get("gang_wars", {}):
                return False, "Cette guerre n'existe pas."
            
            war_data = self.db.data["gang_wars"][war_id]
            
            if war_data["status"] != WarStatus.ACTIVE.value:
                return False, "Cette guerre n'est pas active."
            
            # Determine winner
            attacker_power = war_data["attacker_power"]
            defender_power = war_data["defender_power"]
            
            # Add some randomness (10% variance)
            attacker_final = int(attacker_power * random.uniform(0.9, 1.1))
            defender_final = int(defender_power * random.uniform(0.9, 1.1))
            
            if attacker_final > defender_final:
                winner_gang_id = war_data["attacker_gang_id"]
                loser_gang_id = war_data["defender_gang_id"]
                winner_side = "attackers"
                war_data["winner"] = "attacker"
            elif defender_final > attacker_final:
                winner_gang_id = war_data["defender_gang_id"]
                loser_gang_id = war_data["attacker_gang_id"]
                winner_side = "defenders"
                war_data["winner"] = "defender"
            else:
                # Draw
                war_data["winner"] = "draw"
                war_data["status"] = WarStatus.FINISHED.value
                self.db.save_data()
                return True, "La guerre s'est terminée par un match nul !"
            
            # Update gang stats
            winner_gang = self.gang_system.get_gang_info(winner_gang_id)
            loser_gang = self.gang_system.get_gang_info(loser_gang_id)
            
            winner_gang["war_stats"]["wars_won"] += 1
            winner_gang["war_stats"]["total_wars"] += 1
            winner_gang["reputation"] += 50
            
            loser_gang["war_stats"]["wars_lost"] += 1
            loser_gang["war_stats"]["total_wars"] += 1
            loser_gang["reputation"] -= 25
            
            # Distribute rewards based on war type
            self._distribute_war_rewards(war_data, winner_gang_id, loser_gang_id, winner_side)
            
            war_data["status"] = WarStatus.FINISHED.value
            self.db.save_data()
            
            winner_name = winner_gang["name"]
            loser_name = loser_gang["name"]
            
            return True, f"🏆 Guerre terminée ! '{winner_name}' a vaincu '{loser_name}' !"
            
        except Exception as e:
            logger.error(f"Error processing war results: {e}", exc_info=True)
            return False, "Erreur lors du traitement des résultats."
    
    def _distribute_war_rewards(self, war_data: Dict, winner_gang_id: str, loser_gang_id: str, winner_side: str):
        """Distribute rewards to war participants"""
        try:
            war_type = WarType(war_data["war_type"])
            
            winner_gang = self.gang_system.get_gang_info(winner_gang_id)
            loser_gang = self.gang_system.get_gang_info(loser_gang_id)
            
            if war_type == WarType.VAULT_RAID:
                # Winner steals 20% of loser's vault
                stolen_amount = int(loser_gang["vault_points"] * 0.2)
                loser_gang["vault_points"] -= stolen_amount
                winner_gang["vault_points"] += stolen_amount
                
                war_data["rewards"]["vault_stolen"] = stolen_amount
                
            elif war_type == WarType.TERRITORY:
                # Winner can claim a territory from loser
                if war_data["stake"] and "territories" in self.db.data and war_data["stake"] in self.db.data["territories"]:
                    territory = self.db.data["territories"][war_data["stake"]]
                    if territory["controlled_by"] == loser_gang_id:
                        territory["controlled_by"] = winner_gang_id
                        territory["defense_points"] = 100
                        war_data["rewards"]["territory_captured"] = war_data["stake"]
            
            # Individual rewards for participants
            participants = war_data["participants"][winner_side]
            if participants:
                individual_reward = max(1000, stolen_amount // len(participants)) if war_type == WarType.VAULT_RAID else 1000
                
                for participant_id in participants:
                    self.db.add_points(participant_id, individual_reward)
                
                war_data["rewards"]["individual_reward"] = individual_reward
                
        except Exception as e:
            logger.error(f"Error distributing war rewards: {e}", exc_info=True)
    
    def _gang_in_active_war(self, gang_id: str) -> bool:
        """Check if gang is in an active war"""
        if "gang_wars" not in self.db.data:
            return False
        for war in self.db.data["gang_wars"].values():
            if war["status"] in [WarStatus.DECLARED.value, WarStatus.PREPARATION.value, WarStatus.ACTIVE.value]:
                if gang_id in [war["attacker_gang_id"], war["defender_gang_id"]]:
                    return True
        return False
    
    def get_active_wars(self) -> List[Dict]:
        """Get all active wars"""
        active_wars = []
        if "gang_wars" not in self.db.data:
            return active_wars
        for war in self.db.data["gang_wars"].values():
            if war["status"] in [WarStatus.DECLARED.value, WarStatus.PREPARATION.value, WarStatus.ACTIVE.value]:
                active_wars.append(war)
        return active_wars
    
    def get_gang_war_history(self, gang_id: str) -> List[Dict]:
        """Get war history for a gang"""
        history = []
        if "gang_wars" not in self.db.data:
            return history
        for war in self.db.data["gang_wars"].values():
            if gang_id in [war["attacker_gang_id"], war["defender_gang_id"]]:
                history.append(war)
        return sorted(history, key=lambda x: x["declared_at"], reverse=True)
    
    async def auto_update_wars(self):
        """Automatically update war statuses"""
        try:
            if "gang_wars" not in self.db.data:
                return
            
            current_time = datetime.now()
            
            for war_id, war_data in self.db.data["gang_wars"].items():
                if war_data["status"] == WarStatus.DECLARED.value:
                    start_time = datetime.fromisoformat(war_data["starts_at"])
                    if current_time >= start_time:
                        war_data["status"] = WarStatus.PREPARATION.value
                        logger.info(f"War {war_id} moved to PREPARATION phase")
                
                elif war_data["status"] == WarStatus.PREPARATION.value:
                    # Check if preparation time is over, start active phase
                    start_time = datetime.fromisoformat(war_data["starts_at"])
                    if current_time >= start_time + timedelta(seconds=300):  # 5 min preparation
                        war_data["status"] = WarStatus.ACTIVE.value
                        logger.info(f"War {war_id} moved to ACTIVE phase")
                
                elif war_data["status"] == WarStatus.ACTIVE.value:
                    end_time = datetime.fromisoformat(war_data["ends_at"])
                    if current_time >= end_time:
                        # Process war results
                        self.process_war_results(war_id)
                        logger.info(f"War {war_id} finished and processed")
            
            self.db.save_data()
            
        except Exception as e:
            logger.error(f"Error in auto_update_wars: {e}", exc_info=True)