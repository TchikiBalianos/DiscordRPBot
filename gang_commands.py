import nextcord as discord
from nextcord.ext import commands
import logging
import asyncio
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
                      "`!gang list` - Liste des gangs\n"
                      "`!gang invite @user` - Inviter quelqu'un\n"
                      "`!gang join` - Accepter une invitation\n"
                      "`!gang leave` - Quitter le gang\n"
                      "`!gang deposit <montant>` - Déposer au coffre\n"
                      "`!gang kick @user` - Expulser\n"
                      "`!gang promote @user` - Promouvoir\n"
                      "`!gang territory` - Territoires\n"
                      "`!gang alliance` - Alliances\n"
                      "`!gang disband` - Dissoudre le gang",
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

    # === NOUVELLES COMMANDES ADVANCED GANG WARS (Phase 4B) ===

    @gang.command(name='alliance', aliases=['ally', 'pacte'])
    async def gang_alliance(self, ctx, action: str = None, *, target_gang: str = None):
        """[GANG] Gérer les alliances de gang / [GANG] Manage gang alliances"""
        try:
            user_gang = self.gang_system.get_user_gang(str(ctx.author.id))
            if not user_gang:
                await ctx.send("❌ Tu dois être dans un gang pour utiliser cette commande!")
                return
            
            if not action:
                # Afficher les alliances actuelles
                alliances = self.db.get_gang_alliances(user_gang['id'])
                
                embed = discord.Embed(
                    title=f"🤝 Alliances de {user_gang['name']}",
                    color=discord.Color.blue()
                )
                
                if not alliances:
                    embed.description = "Aucune alliance active."
                else:
                    active_alliances = []
                    pending_alliances = []
                    
                    for alliance in alliances:
                        ally_id = alliance['gang2_id'] if alliance['gang1_id'] == user_gang['id'] else alliance['gang1_id']
                        ally_gang = self.gang_system.get_gang_by_id(ally_id)
                        ally_name = ally_gang['name'] if ally_gang else "Gang Inconnu"
                        
                        if alliance['status'] == 'active':
                            active_alliances.append(ally_name)
                        elif alliance['status'] == 'pending':
                            pending_alliances.append(f"{ally_name} (en attente)")
                    
                    if active_alliances:
                        embed.add_field(name="🤝 Alliances Actives", value="\n".join(active_alliances), inline=False)
                    if pending_alliances:
                        embed.add_field(name="⏳ En Attente", value="\n".join(pending_alliances), inline=False)
                
                await ctx.send(embed=embed)
                return
            
            # Vérifier les permissions de gang
            user_rank = self.gang_system.get_user_rank(str(ctx.author.id))
            if user_rank not in ['boss', 'lieutenant']:
                await ctx.send("❌ Seuls les boss et lieutenants peuvent gérer les alliances!")
                return
            
            if action.lower() in ['propose', 'proposer', 'offer']:
                if not target_gang:
                    await ctx.send("❌ Usage: !gang alliance propose <nom_gang>")
                    return
                
                # Trouver le gang cible
                target_gang_data = self.gang_system.get_gang_by_name(target_gang)
                if not target_gang_data:
                    await ctx.send(f"❌ Gang '{target_gang}' introuvable!")
                    return
                
                if target_gang_data['id'] == user_gang['id']:
                    await ctx.send("❌ Tu ne peux pas t'allier avec ton propre gang!")
                    return
                
                # Vérifier le coût et les limites
                from config import ADVANCED_GANG_CONFIG
                alliance_cost = ADVANCED_GANG_CONFIG['alliance_cost']
                
                if user_gang.get('bank', 0) < alliance_cost:
                    await ctx.send(f"❌ Pas assez d'argent dans le coffre du gang! Coût: {alliance_cost} DLZ")
                    return
                
                # Créer l'alliance
                success = self.db.create_gang_alliance(
                    user_gang['id'], 
                    target_gang_data['id'], 
                    str(ctx.author.id)
                )
                
                if success:
                    # Déduire les frais
                    self.gang_system.add_money_to_gang(user_gang['id'], -alliance_cost)
                    
                    embed = discord.Embed(
                        title="🤝 Alliance Proposée",
                        description=f"Alliance proposée entre **{user_gang['name']}** et **{target_gang_data['name']}**",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="💰 Coût", value=f"{alliance_cost} DLZ", inline=True)
                    embed.add_field(name="⏳ Statut", value="En attente d'acceptation", inline=True)
                    
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("❌ Échec de la proposition d'alliance!")
            
            elif action.lower() in ['accept', 'accepter']:
                # Logique d'acceptation d'alliance à implémenter
                await ctx.send("🔄 Fonction d'acceptation en développement...")
            
            else:
                await ctx.send("❌ Actions disponibles: propose, accept")
                
        except Exception as e:
            logger.error(f"Error in gang alliance command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @gang.command(name='territory', aliases=['territoire', 'zone'])
    async def gang_territory(self, ctx, action: str = None, *, territory_name: str = None):
        """[GANG] Gérer les territoires de gang / [GANG] Manage gang territories"""
        try:
            user_gang = self.gang_system.get_user_gang(str(ctx.author.id))
            
            if not action:
                # Afficher les territoires du gang ou disponibles
                if user_gang:
                    territories = self.db.get_gang_territories(user_gang['id'])
                    
                    embed = discord.Embed(
                        title=f"🗺️ Territoires de {user_gang['name']}",
                        color=discord.Color.gold()
                    )
                    
                    if territories:
                        from config import ADVANCED_GANG_CONFIG
                        territory_benefits = ADVANCED_GANG_CONFIG['territory_benefits']
                        
                        for territory in territories:
                            name = territory['territory_name']
                            benefits = territory_benefits.get(name, {})
                            daily_income = benefits.get('daily_income', 0)
                            prestige = benefits.get('prestige', 0)
                            
                            embed.add_field(
                                name=f"🏴‍☠️ {name.title()}",
                                value=f"💰 {daily_income} DLZ/jour\n✨ {prestige} prestige",
                                inline=True
                            )
                    else:
                        embed.description = "Aucun territoire contrôlé."
                else:
                    # Afficher tous les territoires disponibles
                    embed = discord.Embed(
                        title="🗺️ Territoires Disponibles",
                        description="Rejoins un gang pour revendiquer des territoires!",
                        color=discord.Color.blue()
                    )
                
                await ctx.send(embed=embed)
                return
            
            if not user_gang:
                await ctx.send("❌ Tu dois être dans un gang pour utiliser cette commande!")
                return
            
            # Vérifier les permissions
            user_rank = self.gang_system.get_user_rank(str(ctx.author.id))
            if user_rank not in ['boss', 'lieutenant']:
                await ctx.send("❌ Seuls les boss et lieutenants peuvent gérer les territoires!")
                return
            
            if action.lower() in ['claim', 'revendiquer', 'conquer']:
                if not territory_name:
                    from config import ADVANCED_GANG_CONFIG
                    available = ", ".join(ADVANCED_GANG_CONFIG['territories'])
                    await ctx.send(f"❌ Usage: !gang territory claim <territoire>\nTerritoires: {available}")
                    return
                
                from config import ADVANCED_GANG_CONFIG
                territory_cost = ADVANCED_GANG_CONFIG['territory_claim_cost']
                
                if user_gang.get('bank', 0) < territory_cost:
                    await ctx.send(f"❌ Pas assez d'argent dans le coffre! Coût: {territory_cost} DLZ")
                    return
                
                # Vérifier si le territoire existe
                if territory_name.lower() not in ADVANCED_GANG_CONFIG['territories']:
                    available = ", ".join(ADVANCED_GANG_CONFIG['territories'])
                    await ctx.send(f"❌ Territoire invalide! Disponibles: {available}")
                    return
                
                # Revendiquer le territoire
                success = self.db.claim_territory(user_gang['id'], territory_name.lower(), str(ctx.author.id))
                
                if success:
                    # Déduire les frais et ajouter réputation
                    self.gang_system.add_money_to_gang(user_gang['id'], -territory_cost)
                    self.db.update_gang_reputation(user_gang['id'], 5, f"Nouveau territoire: {territory_name}")
                    
                    embed = discord.Embed(
                        title="🗺️ Territoire Revendiqué!",
                        description=f"**{user_gang['name']}** contrôle maintenant **{territory_name.title()}**",
                        color=discord.Color.green()
                    )
                    
                    benefits = ADVANCED_GANG_CONFIG['territory_benefits'].get(territory_name.lower(), {})
                    if benefits:
                        embed.add_field(name="💰 Revenus", value=f"{benefits.get('daily_income', 0)} DLZ/jour", inline=True)
                        embed.add_field(name="✨ Prestige", value=f"+{benefits.get('prestige', 0)}", inline=True)
                    
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("❌ Territoire déjà contrôlé ou erreur!")
            
            else:
                await ctx.send("❌ Actions disponibles: claim")
                
        except Exception as e:
            logger.error(f"Error in gang territory command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @gang.command(name='asset', aliases=['actif', 'building'])
    async def gang_asset(self, ctx, action: str = None, asset_type: str = None, *, asset_data: str = None):
        """[GANG] Gérer les assets de gang / [GANG] Manage gang assets"""
        try:
            user_gang = self.gang_system.get_user_gang(str(ctx.author.id))
            if not user_gang:
                await ctx.send("❌ Tu dois être dans un gang pour utiliser cette commande!")
                return
            
            if not action:
                # Afficher les assets du gang
                assets = self.db.get_gang_assets(user_gang['id'])
                
                embed = discord.Embed(
                    title=f"🏢 Assets de {user_gang['name']}",
                    color=discord.Color.purple()
                )
                
                if assets:
                    from config import ADVANCED_GANG_CONFIG
                    asset_benefits = ADVANCED_GANG_CONFIG['asset_benefits']
                    
                    for asset in assets:
                        asset_type_name = asset['asset_type']
                        benefits = asset_benefits.get(asset_type_name, {})
                        description = benefits.get('description', 'Aucune description')
                        
                        embed.add_field(
                            name=f"🏗️ {asset_type_name.replace('_', ' ').title()}",
                            value=description,
                            inline=True
                        )
                else:
                    embed.description = "Aucun asset possédé."
                
                # Ajouter la liste des assets disponibles
                from config import ADVANCED_GANG_CONFIG
                available_assets = "\n".join([
                    f"• **{asset.replace('_', ' ').title()}**: {ADVANCED_GANG_CONFIG['asset_costs'][asset]} DLZ"
                    for asset in ADVANCED_GANG_CONFIG['asset_types']
                ])
                embed.add_field(name="🛒 Assets Disponibles", value=available_assets, inline=False)
                
                await ctx.send(embed=embed)
                return
            
            # Vérifier les permissions
            user_rank = self.gang_system.get_user_rank(str(ctx.author.id))
            if user_rank not in ['boss', 'lieutenant']:
                await ctx.send("❌ Seuls les boss et lieutenants peuvent gérer les assets!")
                return
            
            if action.lower() in ['add', 'buy', 'acheter', 'ajouter']:
                if not asset_type:
                    from config import ADVANCED_GANG_CONFIG
                    available = "\n".join([
                        f"• {asset}: {ADVANCED_GANG_CONFIG['asset_costs'][asset]} DLZ"
                        for asset in ADVANCED_GANG_CONFIG['asset_types']
                    ])
                    await ctx.send(f"❌ Usage: !gang asset add <type>\nAssets disponibles:\n{available}")
                    return
                
                from config import ADVANCED_GANG_CONFIG
                
                if asset_type not in ADVANCED_GANG_CONFIG['asset_types']:
                    await ctx.send(f"❌ Type d'asset invalide! Types: {', '.join(ADVANCED_GANG_CONFIG['asset_types'])}")
                    return
                
                cost = ADVANCED_GANG_CONFIG['asset_costs'][asset_type]
                
                if user_gang.get('bank', 0) < cost:
                    await ctx.send(f"❌ Pas assez d'argent dans le coffre! Coût: {cost} DLZ")
                    return
                
                # Vérifier si l'asset existe déjà
                existing_assets = self.db.get_gang_assets(user_gang['id'])
                if any(asset['asset_type'] == asset_type for asset in existing_assets):
                    await ctx.send(f"❌ Le gang possède déjà un {asset_type.replace('_', ' ')}!")
                    return
                
                # Acheter l'asset
                asset_info = {
                    'purchased_by': str(ctx.author.id),
                    'purchase_date': datetime.now().isoformat(),
                    'additional_data': asset_data or {}
                }
                
                success = self.db.add_gang_asset(user_gang['id'], asset_type, asset_info, str(ctx.author.id))
                
                if success:
                    # Déduire les frais et ajouter réputation
                    self.gang_system.add_money_to_gang(user_gang['id'], -cost)
                    self.db.update_gang_reputation(user_gang['id'], 2, f"Nouvel asset: {asset_type}")
                    
                    embed = discord.Embed(
                        title="🏢 Asset Acheté!",
                        description=f"**{user_gang['name']}** a acheté: **{asset_type.replace('_', ' ').title()}**",
                        color=discord.Color.green()
                    )
                    
                    benefits = ADVANCED_GANG_CONFIG['asset_benefits'].get(asset_type, {})
                    if benefits:
                        embed.add_field(name="💎 Bénéfice", value=benefits.get('description', 'Asset actif'), inline=True)
                    
                    embed.add_field(name="💰 Coût", value=f"{cost} DLZ", inline=True)
                    
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("❌ Échec de l'achat d'asset!")
            
            else:
                await ctx.send("❌ Actions disponibles: add")
                
        except Exception as e:
            logger.error(f"Error in gang asset command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @gang.command(name='reputation', aliases=['rep', 'standing'])
    async def gang_reputation(self, ctx, target_gang: str = None):
        """[GANG] Vérifier la réputation de gang / [GANG] Check gang reputation"""
        try:
            if target_gang:
                # Vérifier un autre gang
                gang_data = self.gang_system.get_gang_by_name(target_gang)
                if not gang_data:
                    await ctx.send(f"❌ Gang '{target_gang}' introuvable!")
                    return
            else:
                # Vérifier son propre gang
                gang_data = self.gang_system.get_user_gang(str(ctx.author.id))
                if not gang_data:
                    await ctx.send("❌ Tu n'es dans aucun gang!")
                    return
            
            reputation = self.db.get_gang_reputation(gang_data['id'])
            
            # Déterminer le niveau de réputation
            if reputation >= 80:
                rep_level = "🌟 Légendaire"
                color = discord.Color.gold()
            elif reputation >= 60:
                rep_level = "⭐ Respecté"
                color = discord.Color.green()
            elif reputation >= 20:
                rep_level = "👍 Connu"
                color = discord.Color.blue()
            elif reputation >= -20:
                rep_level = "😐 Neutre"
                color = discord.Color.light_grey()
            elif reputation >= -60:
                rep_level = "👎 Mal vu"
                color = discord.Color.orange()
            else:
                rep_level = "💀 Haï"
                color = discord.Color.red()
            
            embed = discord.Embed(
                title=f"📊 Réputation de {gang_data['name']}",
                color=color
            )
            
            embed.add_field(name="📈 Score", value=f"{reputation}/100", inline=True)
            embed.add_field(name="🏆 Niveau", value=rep_level, inline=True)
            
            # Ajouter des informations sur les territoires et assets
            territories = self.db.get_gang_territories(gang_data['id'])
            assets = self.db.get_gang_assets(gang_data['id'])
            
            embed.add_field(name="🗺️ Territoires", value=str(len(territories)), inline=True)
            embed.add_field(name="🏢 Assets", value=str(len(assets)), inline=True)
            
            # Barre de progression visuelle
            progress_bar = ""
            filled = int((reputation + 100) / 20)  # Convertir -100/100 en 0-10
            for i in range(10):
                if i < filled:
                    progress_bar += "🟩"
                else:
                    progress_bar += "⬜"
            
            embed.add_field(name="📊 Progression", value=progress_bar, inline=False)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in gang reputation command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    # === COMMANDES DE GANG MANQUANTES ===

    @gang.command(name='join', aliases=['rejoindre', 'accepter'])
    async def gang_join(self, ctx):
        """Accepter une invitation de gang"""
        try:
            success, message = self.gang_system.accept_invitation(str(ctx.author.id))
            await ctx.send(f"{'✅' if success else '❌'} {message}")
        except Exception as e:
            logger.error(f"Error in gang join: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @gang.command(name='leave', aliases=['quitter', 'partir'])
    async def gang_leave(self, ctx):
        """Quitter ton gang actuel"""
        try:
            success, message = self.gang_system.leave_gang(str(ctx.author.id))
            await ctx.send(f"{'✅' if success else '❌'} {message}")
        except Exception as e:
            logger.error(f"Error in gang leave: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @gang.command(name='list', aliases=['liste', 'tous'])
    async def gang_list(self, ctx):
        """Voir tous les gangs du serveur"""
        try:
            all_gangs = self.gang_system.get_all_gangs()
            if not all_gangs:
                await ctx.send("🏴 Aucun gang n'existe encore. Crée le tien avec `!gang create <nom>` !")
                return

            embed = discord.Embed(
                title="🏴‍☠️ Gangs du Serveur",
                description=f"**{len(all_gangs)}** gangs actifs",
                color=0x8B0000
            )
            for gang_id, gang in list(all_gangs.items())[:10]:
                members_count = len(gang.get('members', {}))
                rep = gang.get('reputation', 0)
                vault = gang.get('vault_points', 0)
                boss_id = gang.get('boss_id', '?')
                embed.add_field(
                    name=f"🔫 {gang.get('name', '?')}",
                    value=(
                        f"👑 Chef: <@{boss_id}>\n"
                        f"👥 Membres: **{members_count}** | 💰 Coffre: **{vault:,}** 💵\n"
                        f"⭐ Réputation: **{rep}**"
                    ),
                    inline=False
                )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in gang list: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @gang.command(name='invite', aliases=['inviter', 'recruter'])
    async def gang_invite(self, ctx, target: discord.Member = None):
        """Inviter quelqu'un dans ton gang (Chef/Lieutenant seulement)"""
        try:
            if not target:
                await ctx.send("❌ Usage: `!gang invite @user`")
                return
            if target.bot:
                await ctx.send("❌ Les bots ne rejoignent pas les gangs.")
                return
            success, message = self.gang_system.invite_member(str(ctx.author.id), str(target.id))
            if success:
                await ctx.send(f"✅ {message}\n{target.mention}, tape `!gang join` pour accepter !")
            else:
                await ctx.send(f"❌ {message}")
        except Exception as e:
            logger.error(f"Error in gang invite: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @gang.command(name='kick', aliases=['expulser', 'virer'])
    async def gang_kick(self, ctx, target: discord.Member = None):
        """Expulser un membre du gang (Chef/Lieutenant)"""
        try:
            if not target:
                await ctx.send("❌ Usage: `!gang kick @user`")
                return
            success, message = self.gang_system.kick_member(str(ctx.author.id), str(target.id))
            await ctx.send(f"{'✅' if success else '❌'} {message}")
        except Exception as e:
            logger.error(f"Error in gang kick: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @gang.command(name='promote', aliases=['promouvoir'])
    async def gang_promote_member(self, ctx, target: discord.Member = None):
        """Promouvoir un membre de ton gang (Chef seulement)"""
        try:
            if not target:
                await ctx.send("❌ Usage: `!gang promote @user`")
                return
            success, message = self.gang_system.promote_member(str(ctx.author.id), str(target.id))
            await ctx.send(f"{'✅' if success else '❌'} {message}")
        except Exception as e:
            logger.error(f"Error in gang promote: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @gang.command(name='deposit', aliases=['deposer', 'coffre', 'vault'])
    async def gang_deposit(self, ctx, amount: int = None):
        """Déposer de l'argent dans le coffre du gang"""
        try:
            if not amount or amount <= 0:
                await ctx.send("❌ Usage: `!gang deposit <montant>`")
                return
            success, message = self.gang_system.contribute_to_vault(str(ctx.author.id), amount)
            await ctx.send(f"{'✅' if success else '❌'} {message}")
        except Exception as e:
            logger.error(f"Error in gang deposit: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @gang.command(name='disband', aliases=['dissoudre', 'supprimer'])
    async def gang_disband(self, ctx):
        """Dissoudre ton gang (Chef seulement, IRRÉVERSIBLE)"""
        try:
            await ctx.send("⚠️ **ATTENTION** — Dissoudre le gang est IRRÉVERSIBLE. Tout sera perdu (coffre, territoires, réputation). Réagis ✅ pour confirmer.")
            msg = await ctx.send("Confirmer la dissolution ?")
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

            def check(reaction, user):
                return user.id == ctx.author.id and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

            try:
                reaction, _ = await self.bot.wait_for('reaction_add', check=check, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send("⏰ Dissolution annulée.")
                return

            if str(reaction.emoji) == "❌":
                await ctx.send("❌ Dissolution annulée.")
                return

            success, message = self.gang_system.disband_gang(str(ctx.author.id))
            await ctx.send(f"{'💀' if success else '❌'} {message}")
        except Exception as e:
            logger.error(f"Error in gang disband: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(GangCommands(bot, bot.db))