import json
import logging
import asyncio
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
        
        # Initialize gang data structure in database
        if "gangs" not in self.db.data:
            self.db.data["gangs"] = {}
        if "gang_wars" not in self.db.data:
            self.db.data["gang_wars"] = {}
        if "territories" not in self.db.data:
            self.db.data["territories"] = self._initialize_territories()
        if "gang_members" not in self.db.data:
            self.db.data["gang_members"] = {}  # user_id -> gang_id mapping
        
    def _initialize_territories(self) -> Dict:
        """Initialize the territory system with predefined zones"""
        territories = {
            "downtown": {
                "name": "Centre-ville",
                "description": "Le cœur économique de la ville",
                "income_bonus": 1000,
                "controlled_by": None,
                "defense_points": 0,
                "capture_cost": 5000
            },
            "docks": {
                "name": "Les Docks",
                "description": "Zone portuaire stratégique",
                "income_bonus": 800,
                "controlled_by": None,
                "defense_points": 0,
                "capture_cost": 4000
            },
            "industrial": {
                "name": "Zone Industrielle",
                "description": "Parfait pour les opérations illégales",
                "income_bonus": 600,
                "controlled_by": None,
                "defense_points": 0,
                "capture_cost": 3000
            },
            "suburbs": {
                "name": "Banlieues",
                "description": "Territoire résidentiel calme",
                "income_bonus": 400,
                "controlled_by": None,
                "defense_points": 0,
                "capture_cost": 2000
            },
            "casino_district": {
                "name": "District du Casino",
                "description": "Zone de divertissement lucrative",
                "income_bonus": 1200,
                "controlled_by": None,
                "defense_points": 0,
                "capture_cost": 6000
            }
        }
        return territories
    
    def create_gang(self, boss_id: str, gang_name: str, description: str) -> Tuple[bool, str]:
        """Create a new gang"""
        try:
            # Verify user has enough points
            user_points = self.db.get_points(boss_id)
            if user_points < self.gang_creation_cost:
                return False, f"Vous avez besoin de {self.gang_creation_cost} points pour créer un gang."
            
            # Check if user is already in a gang
            if self.get_user_gang(boss_id):
                return False, "Vous êtes déjà membre d'un gang."
            
            # Check if gang name is unique
            for gang_data in self.db.data["gangs"].values():
                if gang_data["name"].lower() == gang_name.lower():
                    return False, "Ce nom de gang est déjà pris."
            
            # Generate unique gang ID
            gang_id = f"gang_{len(self.db.data['gangs']) + 1}_{int(datetime.now().timestamp())}"
            
            # Create gang
            gang = Gang(
                gang_id=gang_id,
                name=gang_name,
                description=description,
                boss_id=boss_id,
                created_date=datetime.now(),
                members={boss_id: GangMember(
                    user_id=boss_id,
                    rank=GangRank.BOSS,
                    joined_date=datetime.now(),
                    contributions=0,
                    last_activity=datetime.now()
                )},
                vault_points=0,
                reputation=100,
                territory_count=0,
                upgrades={
                    "vault_capacity": 1,
                    "war_bonus": 1,
                    "territory_defense": 1,
                    "recruitment_bonus": 1
                },
                war_stats={
                    "wars_won": 0,
                    "wars_lost": 0,
                    "total_wars": 0
                }
            )
            
            # Save to database
            self.db.data["gangs"][gang_id] = self._gang_to_dict(gang)
            self.db.data["gang_members"][boss_id] = gang_id
            
            # Deduct points
            self.db.subtract_points(boss_id, self.gang_creation_cost)
            self.db.save_data()
            
            logger.info(f"Gang '{gang_name}' created by {boss_id}")
            return True, f"Gang '{gang_name}' créé avec succès ! ID: {gang_id}"
            
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
            
            gang_data = self.db.data["gangs"][inviter_gang_id]
            inviter_rank = GangRank(gang_data["members"][inviter_id]["rank"])
            
            if inviter_rank not in [GangRank.BOSS, GangRank.LIEUTENANT]:
                return False, "Seuls les chefs et lieutenants peuvent inviter des membres."
            
            # Check if target is already in a gang
            if self.get_user_gang(target_id):
                return False, "Cette personne est déjà membre d'un gang."
            
            # Check gang capacity
            if len(gang_data["members"]) >= self.max_gang_size:
                return False, f"Le gang est plein (limite: {self.max_gang_size} membres)."
            
            # Add invitation to pending invitations
            if "gang_invitations" not in self.db.data:
                self.db.data["gang_invitations"] = {}
            
            self.db.data["gang_invitations"][target_id] = {
                "gang_id": inviter_gang_id,
                "gang_name": gang_data["name"],
                "inviter_id": inviter_id,
                "invited_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(hours=24)).isoformat()
            }
            
            self.db.save_data()
            return True, f"Invitation envoyée à <@{target_id}> pour rejoindre '{gang_data['name']}'."
            
        except Exception as e:
            logger.error(f"Error inviting member: {e}", exc_info=True)
            return False, "Erreur lors de l'invitation."
    
    def accept_invitation(self, user_id: str) -> Tuple[bool, str]:
        """Accept a gang invitation"""
        try:
            if "gang_invitations" not in self.db.data or user_id not in self.db.data["gang_invitations"]:
                return False, "Vous n'avez aucune invitation en attente."
            
            invitation = self.db.data["gang_invitations"][user_id]
            
            # Check if invitation is still valid
            expires_at = datetime.fromisoformat(invitation["expires_at"])
            if datetime.now() > expires_at:
                del self.db.data["gang_invitations"][user_id]
                self.db.save_data()
                return False, "L'invitation a expiré."
            
            # Check if user is already in a gang
            if self.get_user_gang(user_id):
                return False, "Vous êtes déjà membre d'un gang."
            
            gang_id = invitation["gang_id"]
            gang_data = self.db.data["gangs"][gang_id]
            
            # Add member to gang
            gang_data["members"][user_id] = {
                "user_id": user_id,
                "rank": GangRank.RECRUIT.value,
                "joined_date": datetime.now().isoformat(),
                "contributions": 0,
                "last_activity": datetime.now().isoformat()
            }
            
            self.db.data["gang_members"][user_id] = gang_id
            
            # Remove invitation
            del self.db.data["gang_invitations"][user_id]
            
            self.db.save_data()
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
            
            gang_data = self.db.data["gangs"][gang_id]
            
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
            
            gang_data["members"][target_id]["rank"] = new_rank.value
            self.db.save_data()
            
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
            
            gang_data = self.db.data["gangs"][gang_id]
            
            # Check permissions
            kicker_rank = GangRank(gang_data["members"][kicker_id]["rank"])
            if kicker_rank not in [GangRank.BOSS, GangRank.LIEUTENANT]:
                return False, "Seuls les chefs et lieutenants peuvent expulser des membres."
            
            if target_id not in gang_data["members"]:
                return False, "Cette personne n'est pas membre de votre gang."
            
            target_rank = GangRank(gang_data["members"][target_id]["rank"])
            
            # Boss can kick anyone, Lieutenant can only kick Recruit/Member
            if kicker_rank == GangRank.LIEUTENANT and target_rank in [GangRank.BOSS, GangRank.LIEUTENANT]:
                return False, "Vous ne pouvez pas expulser un chef ou un lieutenant."
            
            if target_id == gang_data["boss_id"]:
                return False, "Le chef ne peut pas être expulsé."
            
            # Remove member
            del gang_data["members"][target_id]
            del self.db.data["gang_members"][target_id]
            
            self.db.save_data()
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
            
            gang_data = self.db.data["gangs"][gang_id]
            
            # Boss cannot leave, must transfer leadership or disband
            if gang_data["boss_id"] == user_id:
                return False, "Le chef ne peut pas quitter le gang. Utilisez !gang transfer ou !gang disband."
            
            # Remove member
            del gang_data["members"][user_id]
            del self.db.data["gang_members"][user_id]
            
            self.db.save_data()
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
            
            gang_data = self.db.data["gangs"][gang_id]
            
            if gang_data["boss_id"] != current_boss_id:
                return False, "Seul le chef peut transférer la direction."
            
            if new_boss_id not in gang_data["members"]:
                return False, "Cette personne n'est pas membre de votre gang."
            
            # Transfer leadership
            gang_data["boss_id"] = new_boss_id
            gang_data["members"][current_boss_id]["rank"] = GangRank.LIEUTENANT.value
            gang_data["members"][new_boss_id]["rank"] = GangRank.BOSS.value
            
            self.db.save_data()
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
            
            gang_data = self.db.data["gangs"][gang_id]
            
            if gang_data["boss_id"] != boss_id:
                return False, "Seul le chef peut dissoudre le gang."
            
            # Remove all members from gang_members mapping
            for member_id in gang_data["members"].keys():
                if member_id in self.db.data["gang_members"]:
                    del self.db.data["gang_members"][member_id]
            
            # Release all territories
            for territory_id, territory_data in self.db.data["territories"].items():
                if territory_data["controlled_by"] == gang_id:
                    territory_data["controlled_by"] = None
                    territory_data["defense_points"] = 0
            
            # Remove gang
            gang_name = gang_data["name"]
            del self.db.data["gangs"][gang_id]
            
            self.db.save_data()
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
            user_points = self.db.get_points(user_id)
            if user_points < amount:
                return False, "Vous n'avez pas assez de points."
            
            # Check daily contribution limit
            daily_contributions = self.get_daily_contributions(user_id)
            if daily_contributions + amount > self.daily_vault_limit:
                remaining = self.daily_vault_limit - daily_contributions
                return False, f"Limite quotidienne atteinte. Vous pouvez encore contribuer {remaining} points aujourd'hui."
            
            gang_data = self.db.data["gangs"][gang_id]
            
            # Transfer points
            self.db.subtract_points(user_id, amount)
            gang_data["vault_points"] += amount
            gang_data["members"][user_id]["contributions"] += amount
            
            # Track daily contributions
            today = datetime.now().strftime("%Y-%m-%d")
            if "daily_contributions" not in self.db.data:
                self.db.data["daily_contributions"] = {}
            if user_id not in self.db.data["daily_contributions"]:
                self.db.data["daily_contributions"][user_id] = {}
            
            self.db.data["daily_contributions"][user_id][today] = daily_contributions + amount
            
            self.db.save_data()
            return True, f"Vous avez contribué {amount} points au coffre du gang ! Total du coffre: {gang_data['vault_points']}"
            
        except Exception as e:
            logger.error(f"Error contributing to vault: {e}", exc_info=True)
            return False, "Erreur lors de la contribution."
    
    def get_daily_contributions(self, user_id: str) -> int:
        """Get user's daily contributions"""
        today = datetime.now().strftime("%Y-%m-%d")
        if "daily_contributions" not in self.db.data:
            return 0
        if user_id not in self.db.data["daily_contributions"]:
            return 0
        return self.db.data["daily_contributions"][user_id].get(today, 0)
    
    def get_user_gang(self, user_id: str) -> Optional[str]:
        """Get the gang ID of a user"""
        return self.db.data["gang_members"].get(user_id)
    
    def get_gang_info(self, gang_id: str) -> Optional[Dict]:
        """Get gang information"""
        return self.db.data["gangs"].get(gang_id)
    
    def get_gang_by_name(self, gang_name: str) -> Optional[Tuple[str, Dict]]:
        """Get gang by name"""
        for gang_id, gang_data in self.db.data["gangs"].items():
            if gang_data["name"].lower() == gang_name.lower():
                return gang_id, gang_data
        return None
    
    def get_all_gangs(self) -> Dict[str, Dict]:
        """Get all gangs"""
        return self.db.data["gangs"]
    
    def _gang_to_dict(self, gang: Gang) -> Dict:
        """Convert Gang object to dictionary for storage"""
        return {
            "gang_id": gang.gang_id,
            "name": gang.name,
            "description": gang.description,
            "boss_id": gang.boss_id,
            "created_date": gang.created_date.isoformat(),
            "members": {
                member_id: {
                    "user_id": member.user_id,
                    "rank": member.rank.value,
                    "joined_date": member.joined_date.isoformat(),
                    "contributions": member.contributions,
                    "last_activity": member.last_activity.isoformat()
                }
                for member_id, member in gang.members.items()
            },
            "vault_points": gang.vault_points,
            "reputation": gang.reputation,
            "territory_count": gang.territory_count,
            "upgrades": gang.upgrades,
            "war_stats": gang.war_stats
        }