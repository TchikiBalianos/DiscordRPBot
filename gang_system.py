import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger('EngagementBot')

class GangRank(Enum):
    RECRUIT = "Recrue"
    MEMBER = "Membre"
    LIEUTENANT = "Lieutenant"
    BOSS = "Chef"

class GangUpgrade(Enum):
    VAULT_CAPACITY = "vault_capacity"
    WAR_BONUS = "war_bonus"
    TERRITORY_DEFENSE = "territory_defense"
    RECRUITMENT_BONUS = "recruitment_bonus"

@dataclass
class GangMember:
    user_id: str
    rank: GangRank
    joined_date: datetime
    contributions: int
    last_activity: datetime

@dataclass
class Gang:
    gang_id: str
    name: str
    description: str
    boss_id: str
    created_date: datetime
    members: Dict[str, GangMember]
    vault_points: int
    reputation: int
    territory_count: int
    upgrades: Dict[str, int]
    war_stats: Dict[str, int]
    
class GangSystem:
    def __init__(self, database):
        self.db = database
        self.gang_creation_cost = 15000
        self.max_gang_size = 20
        self.daily_vault_limit = 5000
        
    def create_gang(self, boss_id: str, gang_name: str, description: str) -> Tuple[bool, str]:
        """Create a new gang"""
        try:
            # Verify user has enough points
            user_points = self.db.get_user_points(boss_id)
            if user_points < self.gang_creation_cost:
                return False, f"Vous avez besoin de {self.gang_creation_cost} points pour créer un gang."
            
            # Check if user is already in a gang
            if self.get_user_gang(boss_id):
                return False, "Vous êtes déjà membre d'un gang."
            
            # Check if gang name is unique (via Supabase)
            existing = self.db.get_gang_by_name(gang_name)
            if existing:
                return False, "Ce nom de gang est déjà pris."
            
            # Create gang via Supabase
            success = self.db.create_gang(gang_name, boss_id, description)
            if not success:
                return False, "Erreur lors de la création du gang."
            
            # Deduct points
            self.db.remove_points(boss_id, self.gang_creation_cost)
            
            logger.info(f"Gang '{gang_name}' created by {boss_id}")
            return True, f"Gang '{gang_name}' créé avec succès !"
            
        except Exception as e:
            logger.error(f"Error creating gang: {e}", exc_info=True)
            return False, "Erreur lors de la création du gang."
    
    def invite_member(self, inviter_id: str, target_id: str) -> Tuple[bool, str]:
        """Invite a player to join the gang"""
        try:
            # Check if inviter is in a gang and has permission
            inviter_gang_id = self.get_user_gang(inviter_id)
            if not inviter_gang_id:
                return False, "Vous n'êtes membre d'aucun gang."
            
            gang_data = self.get_gang_info(inviter_gang_id)
            if not gang_data:
                return False, "Erreur lors de la récupération du gang."
            inviter_rank = GangRank(gang_data["members"].get(inviter_id, {}).get("rank", GangRank.RECRUIT.value))
            
            if inviter_rank not in [GangRank.BOSS, GangRank.LIEUTENANT]:
                return False, "Seuls les chefs et lieutenants peuvent inviter des membres."
            
            # Check if target is already in a gang
            if self.get_user_gang(target_id):
                return False, "Cette personne est déjà membre d'un gang."
            
            # Check gang capacity
            if len(gang_data["members"]) >= self.max_gang_size:
                return False, f"Le gang est plein (limite: {self.max_gang_size} membres)."
            
            # Store invitation in Supabase
            success = self.db.create_gang_invitation(target_id, inviter_gang_id, inviter_id)
            if not success:
                return False, "Erreur lors de l'envoi de l'invitation."
            
            return True, f"Invitation envoyée à <@{target_id}> pour rejoindre '{gang_data['name']}'."
            
        except Exception as e:
            logger.error(f"Error inviting member: {e}", exc_info=True)
            return False, "Erreur lors de l'invitation."
    
    def accept_invitation(self, user_id: str) -> Tuple[bool, str]:
        """Accept a gang invitation"""
        try:
            invitation = self.db.get_gang_invitation(user_id)
            if not invitation:
                return False, "Vous n'avez aucune invitation en attente."
            
            # Check if invitation is still valid
            expires_at = datetime.fromisoformat(invitation["expires_at"])
            if datetime.now() > expires_at:
                self.db.delete_gang_invitation(user_id)
                return False, "L'invitation a expiré."
            
            # Check if user is already in a gang
            if self.get_user_gang(user_id):
                return False, "Vous êtes déjà membre d'un gang."
            
            gang_id = invitation["gang_id"]
            gang_data = self.get_gang_info(gang_id)
            if not gang_data:
                return False, "Le gang n'existe plus."
            
            # Add member to gang via Supabase
            success = self.db.add_gang_member(gang_id, user_id, GangRank.RECRUIT.value)
            if not success:
                return False, "Erreur lors de l'ajout au gang."
            
            # Remove invitation
            self.db.delete_gang_invitation(user_id)
            
            return True, f"Vous avez rejoint le gang '{gang_data['name']}' !"
            
        except Exception as e:
            logger.error(f"Error accepting invitation: {e}", exc_info=True)
            return False, "Erreur lors de l'acceptation de l'invitation."
    
    def promote_member(self, promoter_id: str, target_id: str) -> Tuple[bool, str]:
        """Promote a gang member"""
        try:
            gang_id = self.get_user_gang(promoter_id)
            if not gang_id:
                return False, "Vous n'êtes membre d'aucun gang."
            
            gang_data = self.get_gang_info(gang_id)
            if not gang_data:
                return False, "Erreur lors de la récupération du gang."
            
            # Check permissions
            if gang_data["boss_id"] != promoter_id:
                return False, "Seul le chef peut promouvoir des membres."
            
            if target_id not in gang_data["members"]:
                return False, "Cette personne n'est pas membre de votre gang."
            
            current_rank = GangRank(gang_data["members"][target_id]["rank"])
            
            if current_rank == GangRank.BOSS:
                return False, "Cette personne est déjà chef."
            elif current_rank == GangRank.LIEUTENANT:
                return False, "Cette personne est déjà lieutenant (rang maximum pour les membres)."
            elif current_rank == GangRank.MEMBER:
                new_rank = GangRank.LIEUTENANT
            else:  # RECRUIT
                new_rank = GangRank.MEMBER
            
            self.db.update_gang_member_rank(gang_id, target_id, new_rank.value)
            
            return True, f"<@{target_id}> a été promu au rang de {new_rank.value} !"
            
        except Exception as e:
            logger.error(f"Error promoting member: {e}", exc_info=True)
            return False, "Erreur lors de la promotion."
    
    def kick_member(self, kicker_id: str, target_id: str) -> Tuple[bool, str]:
        """Kick a member from the gang"""
        try:
            gang_id = self.get_user_gang(kicker_id)
            if not gang_id:
                return False, "Vous n'êtes membre d'aucun gang."
            
            gang_data = self.get_gang_info(gang_id)
            if not gang_data:
                return False, "Erreur lors de la récupération du gang."
            
            # Check permissions
            kicker_rank = GangRank(gang_data["members"].get(kicker_id, {}).get("rank", GangRank.RECRUIT.value))
            if kicker_rank not in [GangRank.BOSS, GangRank.LIEUTENANT]:
                return False, "Seuls les chefs et lieutenants peuvent expulser des membres."
            
            if target_id not in gang_data["members"]:
                return False, "Cette personne n'est pas membre de votre gang."
            
            target_rank = GangRank(gang_data["members"][target_id].get("rank", GangRank.RECRUIT.value))
            
            # Boss can kick anyone, Lieutenant can only kick Recruit/Member
            if kicker_rank == GangRank.LIEUTENANT and target_rank in [GangRank.BOSS, GangRank.LIEUTENANT]:
                return False, "Vous ne pouvez pas expulser un chef ou un lieutenant."
            
            if target_id == gang_data["boss_id"]:
                return False, "Le chef ne peut pas être expulsé."
            
            # Remove member via Supabase
            self.db.remove_gang_member(gang_id, target_id)
            
            return True, f"<@{target_id}> a été expulsé du gang."
            
        except Exception as e:
            logger.error(f"Error kicking member: {e}", exc_info=True)
            return False, "Erreur lors de l'expulsion."
    
    def leave_gang(self, user_id: str) -> Tuple[bool, str]:
        """Leave the current gang"""
        try:
            gang_id = self.get_user_gang(user_id)
            if not gang_id:
                return False, "Vous n'êtes membre d'aucun gang."
            
            gang_data = self.get_gang_info(gang_id)
            if not gang_data:
                return False, "Erreur lors de la récupération du gang."
            
            # Boss cannot leave, must transfer leadership or disband
            if gang_data["boss_id"] == user_id:
                return False, "Le chef ne peut pas quitter le gang. Utilisez !gang transfer ou !gang disband."
            
            # Remove member via Supabase
            self.db.remove_gang_member(gang_id, user_id)
            
            return True, f"Vous avez quitté le gang '{gang_data['name']}'."
            
        except Exception as e:
            logger.error(f"Error leaving gang: {e}", exc_info=True)
            return False, "Erreur lors de la sortie du gang."
    
    def transfer_leadership(self, current_boss_id: str, new_boss_id: str) -> Tuple[bool, str]:
        """Transfer gang leadership"""
        try:
            gang_id = self.get_user_gang(current_boss_id)
            if not gang_id:
                return False, "Vous n'êtes membre d'aucun gang."
            
            gang_data = self.get_gang_info(gang_id)
            if not gang_data:
                return False, "Erreur lors de la récupération du gang."
            
            if gang_data["boss_id"] != current_boss_id:
                return False, "Seul le chef peut transférer la direction."
            
            if new_boss_id not in gang_data["members"]:
                return False, "Cette personne n'est pas membre de votre gang."
            
            # Transfer leadership via Supabase
            self.db.transfer_gang_leadership(gang_id, current_boss_id, new_boss_id)
            
            return True, f"<@{new_boss_id}> est maintenant le nouveau chef du gang !"
            
        except Exception as e:
            logger.error(f"Error transferring leadership: {e}", exc_info=True)
            return False, "Erreur lors du transfert de direction."
    
    def disband_gang(self, boss_id: str) -> Tuple[bool, str]:
        """Disband the gang"""
        try:
            gang_id = self.get_user_gang(boss_id)
            if not gang_id:
                return False, "Vous n'êtes membre d'aucun gang."
            
            gang_data = self.get_gang_info(gang_id)
            if not gang_data:
                return False, "Erreur lors de la récupération du gang."
            
            if gang_data["boss_id"] != boss_id:
                return False, "Seul le chef peut dissoudre le gang."
            
            gang_name = gang_data["name"]
            # Disband via Supabase (deletes members, territories, then gang)
            success = self.db.disband_gang(gang_id)
            if not success:
                return False, "Erreur lors de la dissolution du gang."
            
            return True, f"Le gang '{gang_name}' a été dissous."
            
        except Exception as e:
            logger.error(f"Error disbanding gang: {e}", exc_info=True)
            return False, "Erreur lors de la dissolution du gang."
    
    def contribute_to_vault(self, user_id: str, amount: int) -> Tuple[bool, str]:
        """Contribute points to gang vault"""
        try:
            gang_id = self.get_user_gang(user_id)
            if not gang_id:
                return False, "Vous n'êtes membre d'aucun gang."
            
            # Check if user has enough points
            user_points = self.db.get_user_points(user_id)
            if user_points < amount:
                return False, "Vous n'avez pas assez de points."
            
            # Check daily contribution limit
            daily_contributions = self.get_daily_contributions(user_id)
            if daily_contributions + amount > self.daily_vault_limit:
                remaining = self.daily_vault_limit - daily_contributions
                return False, f"Limite quotidienne atteinte. Vous pouvez encore contribuer {remaining} points aujourd'hui."
            
            gang_data = self.get_gang_info(gang_id)
            if not gang_data:
                return False, "Erreur lors de la récupération du gang."
            
            # Transfer points via Supabase
            self.db.remove_points(user_id, amount)
            self.db.update_gang_vault(gang_id, gang_data["vault_points"] + amount)
            self.db.record_daily_contribution(user_id, amount)
            
            new_vault = gang_data["vault_points"] + amount
            return True, f"Vous avez contribué {amount} points au coffre du gang ! Total du coffre: {new_vault}"
            
        except Exception as e:
            logger.error(f"Error contributing to vault: {e}", exc_info=True)
            return False, "Erreur lors de la contribution."
    
    def get_daily_contributions(self, user_id: str) -> int:
        """Get user's daily contributions"""
        try:
            return self.db.get_daily_contributions(user_id)
        except Exception as e:
            logger.warning(f"Error getting daily contributions: {e}")
            return 0
    
    def get_user_gang(self, user_id: str) -> Optional[str]:
        """Get the gang ID of a user"""
        try:
            return self.db.get_user_gang(user_id)
        except Exception as e:
            logger.warning(f"Error getting user gang: {e}")
            return None
    
    def get_gang_info(self, gang_id: str) -> Optional[Dict]:
        """Get gang information"""
        try:
            return self.db.get_gang_info(gang_id)
        except Exception as e:
            logger.warning(f"Error getting gang info: {e}")
            return None
    
    def get_gang_by_name(self, gang_name: str) -> Optional[Tuple[str, Dict]]:
        """Get gang by name"""
        try:
            return self.db.get_gang_by_name(gang_name)
        except Exception as e:
            logger.warning(f"Error getting gang by name: {e}")
            return None
    
    def get_all_gangs(self) -> Dict[str, Dict]:
        """Get all gangs"""
        try:
            result = self.db.get_all_gangs()
            return result if result else {}
        except Exception as e:
            logger.warning(f"Error getting all gangs: {e}")
            return {}