import discord
from discord.ext import commands
import logging
from datetime import datetime
from gang_system import GangSystem, GangRank
from gang_wars import GangWarSystem, WarType
from territory_system import TerritorySystem

logger = logging.getLogger('EngagementBot')

class GangCommands(commands.Cog):
    """Commandes liées aux gangs"""
    
    def __init__(self, bot, database):
        self.bot = bot
        self.db = database
        self.gang_system = GangSystem(database)
        self.war_system = GangWarSystem(database, self.gang_system)
        self.territory_system = TerritorySystem(database, self.gang_system)

    # === COMMANDES DE BASE ===
    
    @commands.group(name='gang', invoke_without_command=True)
    async def gang(self, ctx):
        """Commandes de gestion des gangs"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="🏴‍☠️ Système de Gangs",
                description="Gérez votre gang et ses activités",
                color=0x8B0000
            )
            embed.add_field(
                name="Commandes principales",
                value="`!gang create <nom> <description>` - Créer un gang\n"
                      "`!gang info` - Informations du gang\n"
                      "`!gang join <nom>` - Rejoindre un gang\n"
                      "`!gang leave` - Quitter le gang\n"
                      "`!gang list` - Liste des gangs",
                inline=False
            )
            await ctx.send(embed=embed)

    @gang.command(name='create')
    async def gang_create(self, ctx, name: str, *, description: str = ""):
        """Créer un nouveau gang"""
        try:
            success, message = self.gang_system.create_gang(
                str(ctx.author.id), 
                name, 
                description
            )
            
            if success:
                embed = discord.Embed(
                    title="✅ Gang créé !",
                    description=f"Le gang **{name}** a été créé avec succès !",
                    color=0x00FF00
                )
                if description:
                    embed.add_field(name="Description", value=description, inline=False)
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ {message}")
                
        except Exception as e:
            logger.error(f"Error in gang create command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @gang.command(name='info')
    async def gang_info(self, ctx, *, gang_name: str = None):
        """Afficher les informations d'un gang"""
        try:
            if gang_name:
                # Rechercher le gang par nom
                gang_result = self.gang_system.get_gang_by_name(gang_name)
                if not gang_result:
                    await ctx.send(f"❌ Gang '{gang_name}' introuvable.")
                    return
                gang_id, gang_data = gang_result
            else:
                # Gang de l'utilisateur
                gang_id = self.gang_system.get_user_gang(str(ctx.author.id))
                if not gang_id:
                    await ctx.send("❌ Vous n'êtes membre d'aucun gang.")
                    return
                gang_data = self.gang_system.get_gang_info(gang_id)
            
            if not gang_data:
                await ctx.send("❌ Erreur lors de la récupération des données du gang.")
                return
            
            embed = discord.Embed(
                title=f"🏴‍☠️ {gang_data['name']}",
                description=gang_data.get('description', 'Aucune description'),
                color=0x8B0000
            )
            
            # Chef du gang
            boss_user = self.bot.get_user(int(gang_data['boss_id']))
            boss_name = boss_user.display_name if boss_user else "Inconnu"
            
            embed.add_field(name="👑 Chef", value=boss_name, inline=True)
            embed.add_field(name="👥 Membres", value=len(gang_data['members']), inline=True)
            embed.add_field(name="💰 Coffre", value=f"{gang_data['vault_points']:,} points", inline=True)
            embed.add_field(name="⭐ Réputation", value=gang_data['reputation'], inline=True)
            embed.add_field(name="🗺️ Territoires", value=gang_data['territory_count'], inline=True)
            
            # Date de création
            created_date = datetime.fromisoformat(gang_data['created_at']).strftime('%d/%m/%Y')
            embed.add_field(name="📅 Créé le", value=created_date, inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in gang info command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    # === COMMANDES DE GUERRE ===
    
    @commands.group(name='war', invoke_without_command=True)
    async def war(self, ctx):
        """Commandes de guerre entre gangs"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="⚔️ Système de Guerre",
                description="Gérez les guerres entre gangs",
                color=0xFF0000
            )
            embed.add_field(
                name="Commandes",
                value="`!war declare <gang> <type>` - Déclarer la guerre\n"
                      "`!war join` - Rejoindre la guerre de votre gang\n"
                      "`!war status` - Statut des guerres en cours\n"
                      "`!war history` - Historique des guerres",
                inline=False
            )
            embed.add_field(
                name="Types de guerre",
                value="`turf` - Guerre de territoires (24h)\n"
                      "`raid` - Raid rapide (2h)\n"
                      "`total` - Guerre totale (48h)",
                inline=False
            )
            await ctx.send(embed=embed)

    @war.command(name='declare')
    async def war_declare(self, ctx, target_gang: str, war_type: str = "turf"):
        """Déclarer la guerre à un autre gang"""
        try:
            # Validation du type de guerre
            valid_types = ["turf", "raid", "total"]
            if war_type.lower() not in valid_types:
                await ctx.send(f"❌ Type de guerre invalide. Types disponibles: {', '.join(valid_types)}")
                return
            
            # Simuler la déclaration de guerre (remplacez par votre logique)
            embed = discord.Embed(
                title="⚔️ Guerre déclarée !",
                description=f"Guerre de type **{war_type}** déclarée contre **{target_gang}** !",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in war declare command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    # === COMMANDES DE TERRITOIRE ===
    
    @commands.group(name='territory', invoke_without_command=True)
    async def territory(self, ctx):
        """Commandes de gestion des territoires"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="🗺️ Système de Territoires",
                description="Gérez les territoires de votre gang",
                color=0x228B22
            )
            embed.add_field(
                name="Commandes",
                value="`!territory map` - Voir la carte des territoires\n"
                      "`!territory claim <zone>` - Revendiquer un territoire\n"
                      "`!territory info <zone>` - Infos sur un territoire",
                inline=False
            )
            await ctx.send(embed=embed)

    @territory.command(name='map')
    async def territory_map(self, ctx):
        """Afficher la carte des territoires"""
        try:
            territories = self.territory_system.get_all_territories()
            
            embed = discord.Embed(
                title="🗺️ Carte des Territoires",
                description="État actuel de tous les territoires",
                color=0x228B22
            )
            
            # Afficher quelques territoires (limitez pour éviter la limite Discord)
            count = 0
            for territory_id, territory_data in territories.items():
                if count >= 10:  # Limite d'affichage
                    break
                    
                status = "🏴‍☠️ Contrôlé" if territory_data.get('controlled_by') else "🏞️ Libre"
                embed.add_field(
                    name=territory_data.get('name', territory_id),
                    value=f"{status}\n💰 {territory_data.get('income_bonus', 0)}/h",
                    inline=True
                )
                count += 1
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in territory map command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(GangCommands(bot, bot.db))