import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger('EngagementBot')

class TerritorySystem:
    def __init__(self, database, gang_system):
        self.db = database
        self.gang_system = gang_system
        
    def capture_territory(self, gang_id: str, territory_id: str) -> Tuple[bool, str]:
        """Attempt to capture a territory"""
        try:
            if territory_id not in self.db.data["territories"]:
                return False, "Territoire introuvable."
            
            territory = self.db.data["territories"][territory_id]
            gang_data = self.gang_system.get_gang_info(gang_id)
            
            if not gang_data:
                return False, "Gang introuvable."
            
            # Check if territory is already controlled by this gang
            if territory["controlled_by"] == gang_id:
                return False, "Votre gang contrôle déjà ce territoire."
            
            capture_cost = territory["capture_cost"]
            
            # Check if gang has enough vault points
            if gang_data["vault_points"] < capture_cost:
                return False, f"Votre gang a besoin de {capture_cost} points dans le coffre pour capturer ce territoire."
            
            # If territory is controlled by another gang, need more points due to defenses
            if territory["controlled_by"]:
                defending_gang = self.gang_system.get_gang_info(territory["controlled_by"])
                defense_multiplier = 1 + (territory["defense_points"] / 1000)
                actual_cost = int(capture_cost * defense_multiplier)
                
                if gang_data["vault_points"] < actual_cost:
                    return False, f"Ce territoire est défendu. Coût de capture: {actual_cost} points."
                
                capture_cost = actual_cost
                
                # Notify defending gang (you can implement Discord notifications here)
                logger.info(f"Territory {territory_id} attacked by {gang_data['name']}")
            
            # Deduct points and capture territory
            gang_data["vault_points"] -= capture_cost
            
            # Remove territory from previous owner
            if territory["controlled_by"]:
                old_gang = self.gang_system.get_gang_info(territory["controlled_by"])
                if old_gang:
                    old_gang["territory_count"] -= 1
            
            # Assign to new gang
            territory["controlled_by"] = gang_id
            territory["defense_points"] = 100  # Base defense
            gang_data["territory_count"] += 1
            
            self.db.save_data()
            
            return True, f"Territoire '{territory['name']}' capturé avec succès !"
            
        except Exception as e:
            logger.error(f"Error capturing territory: {e}", exc_info=True)
            return False, "Erreur lors de la capture du territoire."
    
    def upgrade_territory_defense(self, gang_id: str, territory_id: str, investment: int) -> Tuple[bool, str]:
        """Upgrade territory defenses"""
        try:
            if territory_id not in self.db.data["territories"]:
                return False, "Territoire introuvable."
            
            territory = self.db.data["territories"][territory_id]
            gang_data = self.gang_system.get_gang_info(gang_id)
            
            if territory["controlled_by"] != gang_id:
                return False, "Votre gang ne contrôle pas ce territoire."
            
            if gang_data["vault_points"] < investment:
                return False, "Pas assez de points dans le coffre du gang."
            
            # Max defense points: 1000
            if territory["defense_points"] >= 1000:
                return False, "Ce territoire est déjà au maximum de défense."
            
            # Calculate defense points gained (1 point per 10 vault points invested)
            defense_gained = investment // 10
            new_defense = min(territory["defense_points"] + defense_gained, 1000)
            actual_defense_gained = new_defense - territory["defense_points"]
            actual_cost = actual_defense_gained * 10
            
            # Update territory and gang
            territory["defense_points"] = new_defense
            gang_data["vault_points"] -= actual_cost
            
            self.db.save_data()
            
            return True, f"Défenses du territoire '{territory['name']}' améliorées ! Défense: {new_defense}/1000"
            
        except Exception as e:
            logger.error(f"Error upgrading territory defense: {e}", exc_info=True)
            return False, "Erreur lors de l'amélioration des défenses."
    
    def get_gang_territories(self, gang_id: str) -> List[Dict]:
        """Get all territories controlled by a gang"""
        territories = []
        for territory_id, territory_data in self.db.data["territories"].items():
            if territory_data["controlled_by"] == gang_id:
                territories.append({
                    "id": territory_id,
                    **territory_data
                })
        return territories
    
    def get_territory_income(self, gang_id: str) -> int:
        """Calculate total daily income from territories"""
        total_income = 0
        for territory_data in self.db.data["territories"].values():
            if territory_data["controlled_by"] == gang_id:
                total_income += territory_data["income_bonus"]
        return total_income
    
    def distribute_territory_income(self):
        """Distribute daily income from territories to gangs"""
        try:
            for territory_data in self.db.data["territories"].values():
                if territory_data["controlled_by"]:
                    gang_id = territory_data["controlled_by"]
                    gang_data = self.gang_system.get_gang_info(gang_id)
                    
                    if gang_data:
                        income = territory_data["income_bonus"]
                        gang_data["vault_points"] += income
                        logger.info(f"Gang {gang_data['name']} received {income} points from territory income")
            
            self.db.save_data()
            
        except Exception as e:
            logger.error(f"Error distributing territory income: {e}", exc_info=True)
    
    def get_all_territories(self) -> Dict[str, Dict]:
        """Get all territories with their current status"""
        return self.db.data["territories"]