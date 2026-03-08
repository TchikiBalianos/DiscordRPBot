import logging
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
            if attacker_gang_id == defender_gang_id:
                return False, "Vous ne pouvez pas déclarer la guerre à votre propre gang."

            attacker_data = self.gang_system.get_gang_info(attacker_gang_id)
            defender_data = self.gang_system.get_gang_info(defender_gang_id)

            if not attacker_data or not defender_data:
                return False, "Gang introuvable."

            if attacker_data["vault_points"] < self.war_declaration_cost:
                return False, f"Votre gang a besoin de {self.war_declaration_cost} points dans le coffre pour déclarer la guerre."

            if self.db.gang_in_active_war(attacker_gang_id) or self.db.gang_in_active_war(defender_gang_id):
                return False, "L'un des gangs est déjà en guerre."

            now = datetime.now()
            war_id = f"war_{int(now.timestamp())}"

            war_data = {
                "war_id": war_id,
                "attacker_gang_id": attacker_gang_id,
                "defender_gang_id": defender_gang_id,
                "war_type": war_type.value,
                "stake": stake,
                "status": WarStatus.DECLARED.value,
                "declared_at": now.isoformat(),
                "starts_at": (now + timedelta(seconds=self.preparation_time)).isoformat(),
                "ends_at": (now + timedelta(seconds=self.preparation_time + self.war_duration)).isoformat(),
                "attacker_power": 0,
                "defender_power": 0,
                "participants": {"attackers": [], "defenders": []},
                "winner": None,
                "rewards": {}
            }

            if not self.db.create_war(war_data):
                return False, "Erreur lors de la création de la guerre."

            # Deduct declaration cost
            self.db.update_gang_vault(attacker_gang_id, attacker_data["vault_points"] - self.war_declaration_cost)

            return True, f"Guerre déclarée contre '{defender_data['name']}' ! La guerre commencera dans {self.preparation_time//60} minutes."

        except Exception as e:
            logger.error(f"Error declaring war: {e}", exc_info=True)
            return False, "Erreur lors de la déclaration de guerre."

    def join_war(self, user_id: str, side: str) -> Tuple[bool, str]:
        """Join an active war"""
        try:
            gang_id = self.gang_system.get_user_gang(user_id)
            if not gang_id:
                return False, "Vous devez être membre d'un gang pour participer à une guerre."

            active_wars = self.db.get_active_wars()
            war_data = None
            for war in active_wars:
                if war["status"] in [WarStatus.PREPARATION.value, WarStatus.ACTIVE.value]:
                    if gang_id in [war["attacker_gang_id"], war["defender_gang_id"]]:
                        war_data = war
                        break

            if not war_data:
                return False, "Votre gang n'est pas en guerre actuellement."

            if gang_id == war_data["attacker_gang_id"]:
                participant_side = "attackers"
                side_name = "attaquants"
            else:
                participant_side = "defenders"
                side_name = "défenseurs"

            participants = war_data["participants"]
            if user_id in participants[participant_side]:
                return False, f"Vous participez déjà comme {side_name}."

            user_power = self._calculate_user_war_power(user_id)
            participants[participant_side].append(user_id)

            power_field = "attacker_power" if participant_side == "attackers" else "defender_power"
            new_power = war_data[power_field] + user_power

            self.db.update_war(war_data["war_id"],
                               participants=participants,
                               **{power_field: new_power})

            return True, f"Vous rejoignez la guerre comme {side_name} ! Puissance ajoutée: {user_power}"

        except Exception as e:
            logger.error(f"Error joining war: {e}", exc_info=True)
            return False, "Erreur lors de la participation à la guerre."

    def _calculate_user_war_power(self, user_id: str) -> int:
        """Calculate user's power contribution to war"""
        try:
            user_points = self.db.get_user_points(user_id)
            gang_id = self.gang_system.get_user_gang(user_id)

            if not gang_id:
                return 50

            gang_data = self.gang_system.get_gang_info(gang_id)
            member_data = gang_data["members"].get(user_id, {})

            base_power = min(user_points // 100, 1000)

            rank_bonus = {
                "recrue": 1.0,
                "Recrue": 1.0,
                "membre": 1.2,
                "Membre": 1.2,
                "lieutenant": 1.5,
                "Lieutenant": 1.5,
                "boss": 2.0,
                "Chef": 2.0
            }

            power = int(base_power * rank_bonus.get(member_data.get("rank", "recrue"), 1.0))
            return max(power, 50)

        except Exception as e:
            logger.error(f"Error calculating user war power: {e}", exc_info=True)
            return 50

    def process_war_results(self, war_id: str) -> Tuple[bool, str]:
        """Process war results and distribute rewards"""
        try:
            war_data = self.db.get_war(war_id)
            if not war_data:
                return False, "Cette guerre n'existe pas."

            if war_data["status"] != WarStatus.ACTIVE.value:
                return False, "Cette guerre n'est pas active."

            attacker_final = int(war_data["attacker_power"] * random.uniform(0.9, 1.1))
            defender_final = int(war_data["defender_power"] * random.uniform(0.9, 1.1))

            if attacker_final > defender_final:
                winner_gang_id = war_data["attacker_gang_id"]
                loser_gang_id = war_data["defender_gang_id"]
                winner_side = "attackers"
                winner_key = "attacker"
            elif defender_final > attacker_final:
                winner_gang_id = war_data["defender_gang_id"]
                loser_gang_id = war_data["attacker_gang_id"]
                winner_side = "defenders"
                winner_key = "defender"
            else:
                self.db.update_war(war_id, winner="draw", status=WarStatus.FINISHED.value)
                return True, "La guerre s'est terminée par un match nul !"

            winner_gang = self.gang_system.get_gang_info(winner_gang_id)
            loser_gang = self.gang_system.get_gang_info(loser_gang_id)

            self.db.update_gang_stats(winner_gang_id,
                                      reputation=winner_gang.get("reputation", 0) + 50)
            self.db.update_gang_stats(loser_gang_id,
                                      reputation=max(0, loser_gang.get("reputation", 0) - 25))

            rewards = self._distribute_war_rewards(war_data, winner_gang_id, loser_gang_id, winner_side, winner_gang, loser_gang)

            self.db.update_war(war_id,
                               winner=winner_key,
                               status=WarStatus.FINISHED.value,
                               rewards=rewards)

            return True, f"🏆 Guerre terminée ! '{winner_gang['name']}' a vaincu '{loser_gang['name']}' !"

        except Exception as e:
            logger.error(f"Error processing war results: {e}", exc_info=True)
            return False, "Erreur lors du traitement des résultats."

    def _distribute_war_rewards(self, war_data: Dict, winner_gang_id: str, loser_gang_id: str,
                                 winner_side: str, winner_gang: Dict, loser_gang: Dict) -> Dict:
        """Distribute rewards to war participants, return rewards dict"""
        rewards = {}
        try:
            war_type = WarType(war_data["war_type"])
            stolen_amount = 0

            if war_type == WarType.VAULT_RAID:
                stolen_amount = int(loser_gang["vault_points"] * 0.2)
                self.db.update_gang_vault(loser_gang_id, loser_gang["vault_points"] - stolen_amount)
                self.db.update_gang_vault(winner_gang_id, winner_gang["vault_points"] + stolen_amount)
                rewards["vault_stolen"] = stolen_amount

            elif war_type == WarType.TERRITORY:
                stake = war_data.get("stake")
                if stake:
                    territory = self.db.get_territory(stake)
                    if territory and territory.get("controlled_by") == loser_gang_id:
                        self.db.capture_territory(stake, winner_gang_id, defense_points=100)
                        rewards["territory_captured"] = stake

            # Individual rewards for winner participants
            participants = war_data["participants"][winner_side]
            if participants:
                individual_reward = max(1000, stolen_amount // len(participants)) if war_type == WarType.VAULT_RAID else 1000
                for participant_id in participants:
                    self.db.add_points(participant_id, individual_reward, reason="War victory reward")
                rewards["individual_reward"] = individual_reward

        except Exception as e:
            logger.error(f"Error distributing war rewards: {e}", exc_info=True)
        return rewards

    def get_active_wars(self) -> List[Dict]:
        """Get all active wars"""
        return self.db.get_active_wars()

    def get_gang_war_history(self, gang_id: str) -> List[Dict]:
        """Get war history for a gang"""
        return self.db.get_gang_war_history(gang_id)

    async def auto_update_wars(self):
        """Automatically update war statuses"""
        try:
            current_time = datetime.now()
            active_wars = self.db.get_active_wars()

            for war_data in active_wars:
                war_id = war_data["war_id"]

                if war_data["status"] == WarStatus.DECLARED.value:
                    start_time = datetime.fromisoformat(war_data["starts_at"])
                    if current_time >= start_time:
                        self.db.update_war(war_id, status=WarStatus.PREPARATION.value)
                        logger.info(f"War {war_id} moved to PREPARATION phase")

                elif war_data["status"] == WarStatus.PREPARATION.value:
                    start_time = datetime.fromisoformat(war_data["starts_at"])
                    if current_time >= start_time + timedelta(seconds=300):
                        self.db.update_war(war_id, status=WarStatus.ACTIVE.value)
                        logger.info(f"War {war_id} moved to ACTIVE phase")

                elif war_data["status"] == WarStatus.ACTIVE.value:
                    end_time = datetime.fromisoformat(war_data["ends_at"])
                    if current_time >= end_time:
                        self.process_war_results(war_id)
                        logger.info(f"War {war_id} finished and processed")

        except Exception as e:
            logger.error(f"Error in auto_update_wars: {e}", exc_info=True)

