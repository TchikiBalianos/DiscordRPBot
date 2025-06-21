import asyncio
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from gang_system import GangSystem
from gang_wars import GangWarSystem
from territory_system import TerritorySystem
import discord

logger = logging.getLogger('EngagementBot')

class GangEventType:
    """Types d'événements de gang"""
    TERRITORY_INCOME = "territory_income"
    RANDOM_EVENT = "random_event"
    WAR_UPDATE = "war_update"
    TERRITORY_ATTACK = "territory_attack"
    GANG_BONUS = "gang_bonus"
    RIVAL_ENCOUNTER = "rival_encounter"
    POLICE_RAID = "police_raid"
    TREASURE_HUNT = "treasure_hunt"

class GangEvents:
    """Gestionnaire d'événements automatiques pour les gangs"""
    
    def __init__(self, database, bot, gang_system: GangSystem, war_system: GangWarSystem, territory_system: TerritorySystem):
        self.db = database
        self.bot = bot
        self.gang_system = gang_system
        self.war_system = war_system
        self.territory_system = territory_system
        self.running = False
        self.event_tasks = []
        
        # Configuration des événements
        self.event_config = {
            GangEventType.TERRITORY_INCOME: {
                "interval": 3600,  # 1 heure
                "enabled": True
            },
            GangEventType.RANDOM_EVENT: {
                "interval": 7200,  # 2 heures
                "enabled": True,
                "chance": 0.3  # 30% de chance
            },
            GangEventType.WAR_UPDATE: {
                "interval": 600,  # 10 minutes
                "enabled": True
            },
            GangEventType.TERRITORY_ATTACK: {
                "interval": 10800,  # 3 heures
                "enabled": True,
                "chance": 0.2  # 20% de chance
            },
            GangEventType.GANG_BONUS: {
                "interval": 86400,  # 24 heures
                "enabled": True
            }
        }
        
        # Événements aléatoires disponibles
        self.random_events = [
            {
                "name": "Police Raid",
                "type": "police_raid",
                "description": "La police effectue des raids sur plusieurs territoires !",
                "effect": self._handle_police_raid,
                "weight": 20
            },
            {
                "name": "Treasure Hunt",
                "type": "treasure_hunt", 
                "description": "Un trésor caché a été découvert quelque part dans la ville !",
                "effect": self._handle_treasure_hunt,
                "weight": 15
            },
            {
                "name": "Gang Betrayal",
                "type": "betrayal",
                "description": "Un membre d'un gang a trahi son propre gang !",
                "effect": self._handle_betrayal,
                "weight": 10
            },
            {
                "name": "Territory Revolt",
                "type": "revolt",
                "description": "Les habitants d'un territoire se révoltent !",
                "effect": self._handle_territory_revolt,
                "weight": 15
            },
            {
                "name": "Black Market",
                "type": "black_market",
                "description": "Un marché noir temporaire apparaît !",
                "effect": self._handle_black_market,
                "weight": 25
            },
            {
                "name": "Gang Alliance",
                "type": "alliance",
                "description": "Deux gangs rivaux forment une alliance temporaire !",
                "effect": self._handle_temporary_alliance,
                "weight": 15
            }
        ]
    
    async def start_events(self):
        """Démarrer tous les événements automatiques"""
        if self.running:
            logger.warning("Gang events already running")
            return
        
        self.running = True
        logger.info("Starting gang events system...")
        
        # Créer les tâches pour chaque type d'événement
        for event_type, config in self.event_config.items():
            if config["enabled"]:
                task = asyncio.create_task(self._event_loop(event_type, config))
                self.event_tasks.append(task)
                logger.info(f"Started event loop for {event_type}")
        
        logger.info(f"Gang events system started with {len(self.event_tasks)} active loops")
    
    async def stop_events(self):
        """Arrêter tous les événements automatiques"""
        self.running = False
        logger.info("Stopping gang events system...")
        
        for task in self.event_tasks:
            task.cancel()
        
        await asyncio.gather(*self.event_tasks, return_exceptions=True)
        self.event_tasks.clear()
        logger.info("Gang events system stopped")
    
    async def _event_loop(self, event_type: str, config: Dict):
        """Boucle principale pour un type d'événement"""
        try:
            while self.running:
                await asyncio.sleep(config["interval"])
                
                if not self.running:
                    break
                
                try:
                    # Vérifier si l'événement doit se déclencher
                    should_trigger = True
                    if "chance" in config:
                        should_trigger = random.random() < config["chance"]
                    
                    if should_trigger:
                        await self._handle_event(event_type)
                
                except Exception as e:
                    logger.error(f"Error in event loop {event_type}: {e}", exc_info=True)
        
        except asyncio.CancelledError:
            logger.info(f"Event loop {event_type} cancelled")
        except Exception as e:
            logger.error(f"Fatal error in event loop {event_type}: {e}", exc_info=True)
    
    async def _handle_event(self, event_type: str):
        """Gérer un événement spécifique"""
        try:
            if event_type == GangEventType.TERRITORY_INCOME:
                await self._process_territory_income()
            elif event_type == GangEventType.RANDOM_EVENT:
                await self._trigger_random_event()
            elif event_type == GangEventType.WAR_UPDATE:
                await self._update_wars()
            elif event_type == GangEventType.TERRITORY_ATTACK:
                await self._random_territory_attack()
            elif event_type == GangEventType.GANG_BONUS:
                await self._daily_gang_bonuses()
            
            logger.info(f"Successfully processed event: {event_type}")
        
        except Exception as e:
            logger.error(f"Error handling event {event_type}: {e}", exc_info=True)
    
    async def _process_territory_income(self):
        """Traiter les revenus des territoires toutes les heures"""
        territories = self.territory_system.get_all_territories()
        total_income = 0
        gangs_updated = 0
        
        for territory_id, territory_data in territories.items():
            if territory_data['controlled_by']:
                gang_id = territory_data['controlled_by']
                income = territory_data['income_per_hour']
                
                # Ajouter les revenus au coffre du gang
                success = self.gang_system.add_vault_points(gang_id, income)
                if success:
                    total_income += income
                    gangs_updated += 1
        
        if gangs_updated > 0:
            logger.info(f"Processed territory income: {total_income} points distributed to {gangs_updated} gangs")
    
    async def _trigger_random_event(self):
        """Déclencher un événement aléatoire"""
        if not self.random_events:
            return
        
        # Sélectionner un événement basé sur les poids
        total_weight = sum(event["weight"] for event in self.random_events)
        random_choice = random.randint(1, total_weight)
        
        current_weight = 0
        selected_event = None
        
        for event in self.random_events:
            current_weight += event["weight"]
            if random_choice <= current_weight:
                selected_event = event
                break
        
        if selected_event:
            logger.info(f"Triggering random event: {selected_event['name']}")
            await selected_event["effect"](selected_event)
    
    async def _update_wars(self):
        """Mettre à jour l'état des guerres"""
        active_wars = self.war_system.get_active_wars()
        
        for war_id, war_data in active_wars.items():
            # Vérifier si la guerre doit se terminer
            if self.war_system.is_war_expired(war_id):
                await self._end_war(war_id, war_data)
            
            # Vérifier si la guerre doit passer en phase active
            elif war_data['status'] == 'preparation' and self.war_system.should_start_war(war_id):
                await self._start_war_phase(war_id, war_data)
    
    async def _random_territory_attack(self):
        """Attaque aléatoire sur un territoire"""
        territories = self.territory_system.get_all_territories()
        controlled_territories = [
            (tid, tdata) for tid, tdata in territories.items() 
            if tdata['controlled_by']
        ]
        
        if not controlled_territories:
            return
        
        # Sélectionner un territoire aléatoire
        territory_id, territory_data = random.choice(controlled_territories)
        controlling_gang = territory_data['controlled_by']
        
        # Créer une attaque simulée
        attack_strength = random.randint(50, 150)
        defense_strength = self.territory_system.calculate_defense_strength(territory_id)
        
        if attack_strength > defense_strength:
            # L'attaque réussit - libérer le territoire
            self.territory_system.release_territory(territory_id)
            
            # Notifier le gang
            await self._notify_gang_territory_lost(controlling_gang, territory_data['name'])
            logger.info(f"Territory {territory_data['name']} was lost due to random attack")
        else:
            # L'attaque échoue - augmenter légèrement la défense
            self.territory_system.boost_defense(territory_id, 5)
            logger.info(f"Territory {territory_data['name']} successfully defended against random attack")
    
    async def _daily_gang_bonuses(self):
        """Distribuer les bonus quotidiens aux gangs"""
        gangs = self.gang_system.get_all_gangs()
        
        for gang_id, gang_data in gangs.items():
            member_count = len(gang_data['members'])
            territory_count = gang_data['territory_count']
            
            # Bonus basé sur l'activité du gang
            base_bonus = 100
            member_bonus = member_count * 50
            territory_bonus = territory_count * 200
            
            total_bonus = base_bonus + member_bonus + territory_bonus
            
            # Ajouter le bonus au coffre
            self.gang_system.add_vault_points(gang_id, total_bonus)
            
            # Notifier le gang
            await self._notify_gang_daily_bonus(gang_id, total_bonus)
    
    # Événements spécifiques
    async def _handle_police_raid(self, event_data):
        """Gérer un raid de police"""
        gangs = self.gang_system.get_all_gangs()
        affected_gangs = random.sample(list(gangs.keys()), min(3, len(gangs)))
        
        for gang_id in affected_gangs:
            # Perte de points du coffre (10-30%)
            vault_points = gangs[gang_id]['vault_points']
            loss_percentage = random.uniform(0.1, 0.3)
            points_lost = int(vault_points * loss_percentage)
            
            self.gang_system.remove_vault_points(gang_id, points_lost)
            
            # Notifier le gang
            await self._notify_gang_police_raid(gang_id, points_lost)
        
        # Notification globale
        await self._send_global_notification(
            "🚨 Raid de Police",
            f"La police a effectué des raids sur {len(affected_gangs)} gangs !",
            0xFF0000
        )
    
    async def _handle_treasure_hunt(self, event_data):
        """Gérer une chasse au trésor"""
        # Créer un trésor temporaire
        treasure_value = random.randint(5000, 20000)
        treasure_location = random.choice([
            "Entrepôt abandonné", "Sous les docks", "Parking souterrain",
            "Ancienne usine", "Tunnels de métro", "Toit d'un gratte-ciel"
        ])
        
        # Le premier gang à réagir obtient le trésor
        treasure_id = f"treasure_{datetime.now().timestamp()}"
        self.db.data.setdefault("active_treasures", {})[treasure_id] = {
            "value": treasure_value,
            "location": treasure_location,
            "created_at": datetime.now().isoformat(),
            "claimed": False
        }
        
        await self._send_global_notification(
            "💰 Trésor Découvert",
            f"Un trésor de {treasure_value:,} points a été découvert au {treasure_location} !\n"
            f"Premier gang à réagir avec 💰 l'obtient !",
            0xFFD700
        )
    
    async def _handle_betrayal(self, event_data):
        """Gérer une trahison dans un gang"""
        gangs = self.gang_system.get_all_gangs()
        eligible_gangs = [
            (gid, gdata) for gid, gdata in gangs.items() 
            if len(gdata['members']) > 2  # Au moins 3 membres
        ]
        
        if not eligible_gangs:
            return
        
        gang_id, gang_data = random.choice(eligible_gangs)
        
        # Sélectionner un membre traître (pas le chef)
        members = [mid for mid in gang_data['members'].keys() if mid != gang_data['boss_id']]
        if not members:
            return
        
        traitor_id = random.choice(members)
        
        # Le traître vole une partie du coffre et quitte
        vault_points = gang_data['vault_points']
        stolen_amount = int(vault_points * random.uniform(0.15, 0.35))
        
        self.gang_system.remove_vault_points(gang_id, stolen_amount)
        self.gang_system.remove_member(gang_id, traitor_id)
        
        # Donner les points volés au traître
        self.db.add_points(traitor_id, stolen_amount)
        
        await self._notify_gang_betrayal(gang_id, traitor_id, stolen_amount)
    
    async def _handle_territory_revolt(self, event_data):
        """Gérer une révolte de territoire"""
        territories = self.territory_system.get_all_territories()
        controlled_territories = [
            (tid, tdata) for tid, tdata in territories.items() 
            if tdata['controlled_by']
        ]
        
        if not controlled_territories:
            return
        
        territory_id, territory_data = random.choice(controlled_territories)
        controlling_gang = territory_data['controlled_by']
        
        # Réduire les revenus du territoire temporairement
        original_income = territory_data['income_per_hour']
        reduced_income = int(original_income * 0.5)
        
        self.territory_system.set_territory_income(territory_id, reduced_income)
        
        # Programmer la restauration dans 6 heures
        restore_time = datetime.now() + timedelta(hours=6)
        self.db.data.setdefault("territory_effects", {})[territory_id] = {
            "type": "revolt",
            "original_income": original_income,
            "restore_at": restore_time.isoformat()
        }
        
        await self._notify_gang_territory_revolt(controlling_gang, territory_data['name'])
    
    async def _handle_black_market(self, event_data):
        """Gérer l'apparition d'un marché noir"""
        # Créer des objets spéciaux temporaires
        market_items = [
            {"name": "🔫 Arme Illegale", "price": 5000, "effect": "+20% succès braquage"},
            {"name": "🛡️ Gilet Pare-balles", "price": 7000, "effect": "+15% défense territoire"},
            {"name": "💎 Diamant Volé", "price": 15000, "effect": "+1000 réputation"},
            {"name": "🗝️ Clé Mystérieuse", "price": 10000, "effect": "Ouvre coffre secret"}
        ]
        
        market_id = f"market_{datetime.now().timestamp()}"
        self.db.data.setdefault("black_markets", {})[market_id] = {
            "items": market_items,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=2)).isoformat(),
            "purchases": {}
        }
        
        items_text = "\n".join([f"{item['name']} - {item['price']:,} points" for item in market_items])
        
        await self._send_global_notification(
            "🏴‍☠️ Marché Noir",
            f"Un marché noir secret est ouvert pendant 2h !\n\n{items_text}\n\n"
            f"Utilisez `!blackmarket buy <item>` pour acheter",
            0x4B0082
        )
    
    async def _handle_temporary_alliance(self, event_data):
        """Gérer une alliance temporaire"""
        gangs = list(self.gang_system.get_all_gangs().keys())
        if len(gangs) < 2:
            return
        
        gang1, gang2 = random.sample(gangs, 2)
        
        # Créer l'alliance temporaire
        alliance_id = f"alliance_{datetime.now().timestamp()}"
        alliance_data = {
            "gang1": gang1,
            "gang2": gang2,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=12)).isoformat(),
            "benefits": {
                "shared_territory_income": True,
                "mutual_defense": True,
                "combined_war_power": True
            }
        }
        
        self.db.data.setdefault("temporary_alliances", {})[alliance_id] = alliance_data
        
        gang1_info = self.gang_system.get_gang_info(gang1)
        gang2_info = self.gang_system.get_gang_info(gang2)
        
        await self._send_global_notification(
            "🤝 Alliance Temporaire",
            f"Les gangs **{gang1_info['name']}** et **{gang2_info['name']}** "
            f"ont formé une alliance temporaire de 12h !",
            0x9932CC
        )
    
    # Méthodes de notification
    async def _notify_gang_territory_lost(self, gang_id: str, territory_name: str):
        """Notifier qu'un gang a perdu un territoire"""
        gang_info = self.gang_system.get_gang_info(gang_id)
        
        embed = discord.Embed(
            title="💀 Territoire Perdu",
            description=f"Votre gang a perdu le contrôle de **{territory_name}** suite à une attaque !",
            color=0xFF0000
        )
        
        await self._send_gang_notification(gang_id, embed)
    
    async def _notify_gang_daily_bonus(self, gang_id: str, bonus_amount: int):
        """Notifier le bonus quotidien"""
        embed = discord.Embed(
            title="💰 Bonus Quotidien",
            description=f"Votre gang a reçu **{bonus_amount:,} points** de bonus quotidien !",
            color=0x00FF00
        )
        
        await self._send_gang_notification(gang_id, embed)
    
    async def _notify_gang_police_raid(self, gang_id: str, points_lost: int):
        """Notifier d'un raid de police"""
        embed = discord.Embed(
            title="🚨 Raid de Police",
            description=f"La police a saisi **{points_lost:,} points** du coffre de votre gang !",
            color=0xFF0000
        )
        
        await self._send_gang_notification(gang_id, embed)
    
    async def _notify_gang_betrayal(self, gang_id: str, traitor_id: str, stolen_amount: int):
        """Notifier d'une trahison"""
        embed = discord.Embed(
            title="🗡️ Trahison",
            description=f"<@{traitor_id}> a trahi le gang et volé **{stolen_amount:,} points** avant de partir !",
            color=0x8B0000
        )
        
        await self._send_gang_notification(gang_id, embed)
    
    async def _notify_gang_territory_revolt(self, gang_id: str, territory_name: str):
        """Notifier d'une révolte de territoire"""
        embed = discord.Embed(
            title="⚡ Révolte de Territoire",
            description=f"Les habitants de **{territory_name}** se révoltent ! "
            f"Les revenus sont réduits de 50% pendant 6h.",
            color=0xFFA500
        )
        
        await self._send_gang_notification(gang_id, embed)
    
    async def _send_gang_notification(self, gang_id: str, embed: discord.Embed):
        """Envoyer une notification à tous les membres d'un gang"""
        try:
            gang_info = self.gang_system.get_gang_info(gang_id)
            if not gang_info:
                return
            
            # Envoyer le message au chef du gang
            boss_id = int(gang_info['boss_id'])
            boss_user = self.bot.get_user(boss_id)
            
            if boss_user:
                try:
                    await boss_user.send(embed=embed)
                except discord.Forbidden:
                    logger.warning(f"Cannot send DM to gang boss {boss_id}")
        
        except Exception as e:
            logger.error(f"Error sending gang notification: {e}", exc_info=True)
    
    async def _send_global_notification(self, title: str, description: str, color: int):
        """Envoyer une notification globale à tous les serveurs"""
        try:
            embed = discord.Embed(
                title=title,
                description=description,
                color=color,
                timestamp=datetime.now()
            )
            
            # Envoyer dans un canal spécifique si configuré
            for guild in self.bot.guilds:
                # Chercher un canal nommé "gang-events" ou similaire
                channel = discord.utils.get(guild.channels, name="gang-events")
                if not channel:
                    channel = discord.utils.get(guild.channels, name="general")
                
                if channel and channel.permissions_for(guild.me).send_messages:
                    try:
                        await channel.send(embed=embed)
                    except discord.Forbidden:
                        logger.warning(f"Cannot send message to channel {channel.id} in guild {guild.id}")
        
        except Exception as e:
            logger.error(f"Error sending global notification: {e}", exc_info=True)
    
    async def _end_war(self, war_id: str, war_data: Dict):
        """Terminer une guerre"""
        try:
            winner_gang = self.war_system.calculate_war_winner(war_id)
            rewards = self.war_system.calculate_war_rewards(war_id, winner_gang)
            
            # Distribuer les récompenses
            if winner_gang:
                self.gang_system.add_vault_points(winner_gang, rewards['points'])
                self.gang_system.add_reputation(winner_gang, rewards['reputation'])
            
            # Marquer la guerre comme terminée
            self.war_system.end_war(war_id, winner_gang, rewards)
            
            # Notifier les gangs participants
            await self._notify_war_ended(war_data, winner_gang, rewards)
            
            logger.info(f"War {war_id} ended, winner: {winner_gang}")
        
        except Exception as e:
            logger.error(f"Error ending war {war_id}: {e}", exc_info=True)
    
    async def _start_war_phase(self, war_id: str, war_data: Dict):
        """Démarrer la phase active d'une guerre"""
        try:
            self.war_system.start_war_active_phase(war_id)
            
            # Notifier le début de la guerre
            attacker_gang = self.gang_system.get_gang_info(war_data['attacker_gang'])
            defender_gang = self.gang_system.get_gang_info(war_data['defender_gang'])
            
            await self._send_global_notification(
                "⚔️ Guerre Commencée",
                f"La guerre entre **{attacker_gang['name']}** et **{defender_gang['name']}** commence !",
                0xFF4500
            )
            
            logger.info(f"War {war_id} active phase started")
        
        except Exception as e:
            logger.error(f"Error starting war phase {war_id}: {e}", exc_info=True)
    
    async def _notify_war_ended(self, war_data: Dict, winner_gang: str, rewards: Dict):
        """Notifier la fin d'une guerre"""
        try:
            attacker_gang = self.gang_system.get_gang_info(war_data['attacker_gang'])
            defender_gang = self.gang_system.get_gang_info(war_data['defender_gang'])
            winner_info = self.gang_system.get_gang_info(winner_gang) if winner_gang else None
            
            if winner_info:
                title = "🏆 Victoire de Guerre"
                description = f"**{winner_info['name']}** remporte la guerre !"
                color = 0x00FF00
            else:
                title = "⚔️ Guerre Terminée"
                description = "La guerre se termine par un match nul."
                color = 0xFFA500
            
            embed = discord.Embed(
                title=title,
                description=description,
                color=color
            )
            
            embed.add_field(
                name="Participants",
                value=f"{attacker_gang['name']} vs {defender_gang['name']}",
                inline=False
            )
            
            if winner_gang and rewards:
                embed.add_field(
                    name="Récompenses",
                    value=f"💰 {rewards['points']:,} points\n⭐ {rewards['reputation']} réputation",
                    inline=True
                )
            
            await self._send_global_notification(title, embed.description, color)
        
        except Exception as e:
            logger.error(f"Error notifying war end: {e}", exc_info=True)

# Fonction pour intégrer les événements au bot principal
async def setup_gang_events(bot, database):
    """Configurer et démarrer le système d'événements de gang"""
    try:
        gang_system = GangSystem(database)
        war_system = GangWarSystem(database, gang_system)
        territory_system = TerritorySystem(database, gang_system)
        
        gang_events = GangEvents(database, bot, gang_system, war_system, territory_system)
        await gang_events.start_events()
        
        # Stocker la référence pour pouvoir l'arrêter plus tard
        bot.gang_events = gang_events
        
        logger.info("Gang events system successfully set up")
        return gang_events
    
    except Exception as e:
        logger.error(f"Error setting up gang events: {e}", exc_info=True)
        raise

async def shutdown_gang_events(bot):
    """Arrêter le système d'événements de gang"""
    if hasattr(bot, 'gang_events'):
        await bot.gang_events.stop_events()
        logger.info("Gang events system shut down")