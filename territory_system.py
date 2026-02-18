import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger('EngagementBot')

class TerritorySystem:
    def __init__(self, database, gang_system):
        self.db = database
        self.gang_system = gang_system

    def capture_territory(self, gang_id: str, territory_id: str) -> Tuple[bool, str]:
        """Attempt to capture a territory"""
        try:
            territory = self.db.get_territory(territory_id)
            if not territory:
                return False, "Territoire introuvable."

            gang_data = self.gang_system.get_gang_info(gang_id)
            if not gang_data:
                return False, "Gang introuvable."

            if territory["controlled_by"] == gang_id:
                return False, "Votre gang contrôle déjà ce territoire."

            capture_cost = territory["capture_cost"]

            if gang_data["vault_points"] < capture_cost:
                return False, f"Votre gang a besoin de {capture_cost} points dans le coffre pour capturer ce territoire."

            # If defended, apply defense multiplier
            if territory["controlled_by"]:
                defense_multiplier = 1 + (territory["defense_points"] / 1000)
                actual_cost = int(capture_cost * defense_multiplier)

                if gang_data["vault_points"] < actual_cost:
                    return False, f"Ce territoire est défendu. Coût de capture: {actual_cost} points."

                capture_cost = actual_cost

                # Decrement territory_count for old owner
                old_gang = self.gang_system.get_gang_info(territory["controlled_by"])
                if old_gang:
                    self.db.update_gang_stats(territory["controlled_by"], territory_count=max(0, old_gang["territory_count"] - 1))

                logger.info(f"Territory {territory_id} attacked by {gang_data['name']}")

            # Deduct vault points and transfer territory
            self.db.update_gang_vault(gang_id, gang_data["vault_points"] - capture_cost)
            self.db.capture_territory(territory_id, gang_id, defense_points=100)
            self.db.update_gang_stats(gang_id, territory_count=gang_data["territory_count"] + 1)

            return True, f"Territoire '{territory['name']}' capturé avec succès !"

        except Exception as e:
            logger.error(f"Error capturing territory: {e}", exc_info=True)
            return False, "Erreur lors de la capture du territoire."

    def upgrade_territory_defense(self, gang_id: str, territory_id: str, investment: int) -> Tuple[bool, str]:
        """Upgrade territory defenses"""
        try:
            territory = self.db.get_territory(territory_id)
            if not territory:
                return False, "Territoire introuvable."

            gang_data = self.gang_system.get_gang_info(gang_id)

            if territory["controlled_by"] != gang_id:
                return False, "Votre gang ne contrôle pas ce territoire."

            if gang_data["vault_points"] < investment:
                return False, "Pas assez de points dans le coffre du gang."

            if territory["defense_points"] >= 1000:
                return False, "Ce territoire est déjà au maximum de défense."

            defense_gained = investment // 10
            new_defense = min(territory["defense_points"] + defense_gained, 1000)
            actual_defense_gained = new_defense - territory["defense_points"]
            actual_cost = actual_defense_gained * 10

            self.db.update_territory_defense(territory_id, new_defense)
            self.db.update_gang_vault(gang_id, gang_data["vault_points"] - actual_cost)

            return True, f"Défenses du territoire '{territory['name']}' améliorées ! Défense: {new_defense}/1000"

        except Exception as e:
            logger.error(f"Error upgrading territory defense: {e}", exc_info=True)
            return False, "Erreur lors de l'amélioration des défenses."

    def get_gang_territories(self, gang_id: str) -> List[Dict]:
        """Get all territories controlled by a gang"""
        all_territories = self.db.get_all_territories()
        return [
            {"id": tid, **tdata}
            for tid, tdata in all_territories.items()
            if tdata.get("controlled_by") == gang_id
        ]

    def get_territory_income(self, gang_id: str) -> int:
        """Calculate total daily income from territories"""
        all_territories = self.db.get_all_territories()
        return sum(
            t["income_bonus"]
            for t in all_territories.values()
            if t.get("controlled_by") == gang_id
        )

    def distribute_territory_income(self):
        """Distribute daily income from territories to gangs"""
        try:
            all_territories = self.db.get_all_territories()
            for territory_data in all_territories.values():
                gang_id = territory_data.get("controlled_by")
                if gang_id:
                    gang_data = self.gang_system.get_gang_info(gang_id)
                    if gang_data:
                        income = territory_data["income_bonus"]
                        self.db.update_gang_vault(gang_id, gang_data["vault_points"] + income)
                        logger.info(f"Gang {gang_data['name']} received {income} points from territory income")
        except Exception as e:
            logger.error(f"Error distributing territory income: {e}", exc_info=True)

    def get_all_territories(self) -> Dict[str, Dict]:
        """Get all territories with their current status"""
        return self.db.get_all_territories()