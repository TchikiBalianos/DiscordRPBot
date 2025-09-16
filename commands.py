import discord
from discord.ext import commands
import logging
from datetime import datetime
import random
import asyncio
from config import *
from tweepy.errors import TooManyRequests, NotFound, Unauthorized

logger = logging.getLogger('EngagementBot')

def is_staff():
    """Check if the user has staff role or is an administrator"""
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        return any(role.name.lower() in ['staff', 'modo', 'admin'] for role in ctx.author.roles)
    return commands.check(predicate)

def check_daily_limit(command_name):
    """Decorator to check daily command limits"""
    async def predicate(ctx):
        # Accéder à la base de données pour vérifier l'utilisation quotidienne
        try:
            # Incrémenter l'utilisation quotidienne pour ce tracage
            if hasattr(ctx.bot, 'db'):
                # Accès direct à la base de données
                usage = ctx.bot.db.get_daily_usage(str(ctx.author.id), command_name)
            elif hasattr(ctx.bot, 'point_system') and hasattr(ctx.bot.point_system, 'db'):
                # Accès via point_system
                usage = ctx.bot.point_system.db.get_daily_usage(str(ctx.author.id), command_name)
            else:
                # Cas de fallback si la structure n'est pas comme prévu
                logger.warning(f"Impossible d'accéder à la base de données pour vérifier les limites quotidiennes: {command_name}")
                return True  # Permettre l'exécution par défaut
                
            if usage >= DAILY_LIMITS.get(command_name, float('inf')):
                await ctx.send(f"❌ Tu as atteint la limite quotidienne pour cette commande ({DAILY_LIMITS[command_name]}x par jour)")
                return False
            
            # Incrémenter uniquement si le check passe, pour ne pas compter les tentatives échouées
            if hasattr(ctx.bot, 'db'):
                ctx.bot.db.increment_daily_usage(str(ctx.author.id), command_name)
            elif hasattr(ctx.bot, 'point_system') and hasattr(ctx.bot.point_system, 'db'):
                ctx.bot.point_system.db.increment_daily_usage(str(ctx.author.id), command_name)
                
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des limites quotidiennes: {e}", exc_info=True)
            return True  # En cas d'erreur, permettre l'exécution
    return commands.check(predicate)

def check_cooldown_and_limit(command_name):
    """Decorator to check both cooldown and daily command limits selon TECH Brief"""
    async def predicate(ctx):
        try:
            # 1. Vérifier le cooldown d'abord
            cooldown_seconds = COMMAND_COOLDOWNS.get(command_name, 0)
            if cooldown_seconds > 0:
                # Accéder à la base de données pour le cooldown
                db = None
                if hasattr(ctx.bot, 'db'):
                    db = ctx.bot.db
                elif hasattr(ctx.bot, 'point_system') and hasattr(ctx.bot.point_system, 'db'):
                    db = ctx.bot.point_system.db
                
                if db and hasattr(db, 'get_command_cooldown'):
                    remaining_cooldown = db.get_command_cooldown(str(ctx.author.id), command_name)
                    if remaining_cooldown > 0:
                        hours = remaining_cooldown // 3600
                        minutes = (remaining_cooldown % 3600) // 60
                        await ctx.send(f"⏰ Tu dois attendre encore {hours}h {minutes}m avant de réutiliser cette commande.")
                        return False
            
            # 2. Vérifier la limite quotidienne
            if hasattr(ctx.bot, 'db'):
                usage = ctx.bot.db.get_daily_usage(str(ctx.author.id), command_name)
            elif hasattr(ctx.bot, 'point_system') and hasattr(ctx.bot.point_system, 'db'):
                usage = ctx.bot.point_system.db.get_daily_usage(str(ctx.author.id), command_name)
            else:
                logger.warning(f"Impossible d'accéder à la base de données pour {command_name}")
                return True
                
            if usage >= DAILY_LIMITS.get(command_name, float('inf')):
                await ctx.send(f"❌ Tu as atteint la limite quotidienne pour cette commande ({DAILY_LIMITS[command_name]}x par jour)")
                return False
            
            # 3. Si tout est OK, enregistrer l'utilisation et définir le nouveau cooldown
            if hasattr(ctx.bot, 'db'):
                ctx.bot.db.increment_daily_usage(str(ctx.author.id), command_name)
                if cooldown_seconds > 0 and hasattr(ctx.bot.db, 'set_command_cooldown'):
                    ctx.bot.db.set_command_cooldown(str(ctx.author.id), command_name, cooldown_seconds)
            elif hasattr(ctx.bot, 'point_system') and hasattr(ctx.bot.point_system, 'db'):
                ctx.bot.point_system.db.increment_daily_usage(str(ctx.author.id), command_name)
                if cooldown_seconds > 0 and hasattr(ctx.bot.point_system.db, 'set_command_cooldown'):
                    ctx.bot.point_system.db.set_command_cooldown(str(ctx.author.id), command_name, cooldown_seconds)
                
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des cooldowns/limites: {e}", exc_info=True)
            return True
    return commands.check(predicate)

class Commands(commands.Cog):
    """Commands cog containing all bot commands"""

    def __init__(self, bot, point_system, twitter_handler):
        """Initialize the Commands cog"""
        super().__init__()  # Important: Call the parent class's __init__
        self.bot = bot
        self.points = point_system
        self.twitter = twitter_handler
        logger.info("Commands cog initialized")
        # Log all commands that will be registered
        logger.info(f"Commands being registered: {[method for method in dir(self) if method.endswith('_command')]}")

    @commands.command(name='debug')
    @is_staff()
    async def debug_command(self, ctx):
        """[STAFF] Debug command to check registered commands"""
        try:
            # Get all registered commands
            all_commands = sorted([c.name for c in self.bot.commands])
            cog_commands = sorted([c.name for c in self.get_commands()])

            embed = discord.Embed(
                title="🔧 Debug Information",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="Bot Commands",
                value=f"Total: {len(all_commands)}\n" + "\n".join(all_commands),
                inline=False
            )

            embed.add_field(
                name="Cog Commands",
                value=f"Total: {len(cog_commands)}\n" + "\n".join(cog_commands),
                inline=False
            )

            await ctx.send(embed=embed)
            logger.info(f"Debug command executed by {ctx.author}")

        except Exception as e:
            logger.error(f"Error in debug command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='ping')
    async def ping_command(self, ctx):
        """Simple ping command to test bot responsiveness"""
        try:
            logger.info(f"Ping command received from {ctx.author} in channel {ctx.channel.name}")

            # Calculate bot latency
            latency = round(self.bot.latency * 1000)

            # Send response with more information
            await ctx.send(f"Pong! ✅ Latence : {latency}ms\nLe bot fonctionne correctement.")

            # Log available commands
            all_commands = [c.name for c in self.bot.commands]
            logger.info(f"Available commands when ping was executed: {all_commands}")
            logger.info(f"Ping command executed successfully for {ctx.author}")
        except Exception as e:
            logger.error(f"Error in ping command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='help', aliases=['commands', 'bothelp', 'aide', 'commandes'])
    async def help_command(self, ctx):
        """Show all available commands / Afficher toutes les commandes disponibles"""
        try:
            embed = discord.Embed(
                title="🦹 Commandes du Thugz Bot",
                description="Voici toutes les commandes disponibles:",
                color=discord.Color.blue()
            )

            # Define command categories with descriptions
            commands_list = {
                "💰 Économie": {
                    "!work": "Travailler pour gagner des points (1x par jour)",
                    "!points": "Voir ton solde de points",
                    "!leaderboard": "Voir le classement mensuel",
                    "!shop": "Voir les objets disponibles à la vente",
                    "!inventory": "Voir ton inventaire",
                    "!trade @user <item_id>": "Propose un échange d’objet à un autre joueur"
                },
                "🦹 Actions Spéciales": {
                    "!steal @user": "Voler quelqu'un (4h cooldown, 5x/jour) [NOUVEAU]",
                    "!rob @user": "Voler (alias de !steal, compatibilité)",
                    "!revenge": "Se venger de son dernier voleur (1x par jour)",
                    "!heist": "Commencer un braquage (2x par jour)",
                    "!joinheist": "Rejoindre un braquage"
                },
                "⚔️ Combat": {
                    "!fight @user [mise]": "Se battre (6h cooldown, 3x/jour) [NOUVEAU]",
                    "!duel @user <mise>": "Duel d'honneur (12h cooldown, 2x/jour) [NOUVEAU]", 
                    "!combat @user <mise>": "Combat général (3h cooldown, 5x/jour)",
                    "!gift @user <montant>": "Donner des points (1h cooldown, 10x/jour) [NOUVEAU]"
                },
                "🏢 Prison": {
                    "!prison": "Voir ton statut en prison",
                    "!activity": "Voir les activités disponibles",
                    "!activity <nom>": "Faire une activité en prison",
                    "!tribunal <plaidoyer>": "Demander un procès"
                },
                "🐦 Twitter": {
                    "!linktwitter": "Lier ton compte Twitter",
                    "!twitterstats": "Voir tes stats Twitter"
                },
                "📌 Divers": {
                    "!ping": "Tester si le bot répond",
                    "!help": "Voir cette aide",
                    "!debug": "Afficher les commandes enregistrées (Staff)"
                }
            }

            # Add staff commands if user is staff
            if ctx.author.guild_permissions.administrator or \
               any(role.name.lower() in ['staff', 'modo', 'admin'] for role in ctx.author.roles):
                commands_list["⚡ Staff"] = {
                    "!addpoints @user montant": "Ajouter des points à un membre",
                    "!removepoints @user montant": "Retirer des points à un membre"
                }

            # Add daily limits information
            limits_info = "📊 Limites quotidiennes:\n" + "\n".join([
                f"• {cmd.capitalize()}: {limit}x par jour"
                for cmd, limit in DAILY_LIMITS.items()
                if limit > 0
            ])

            embed.add_field(name="⚠️ Limites", value=limits_info, inline=False)

            # Add each category to the embed
            for category, cmds in commands_list.items():
                embed.add_field(
                    name=category,
                    value="\n".join([f"`{cmd}`: {desc}" for cmd, desc in cmds.items()]),
                    inline=False
                )

            await ctx.send(embed=embed)
            logger.info(f"Help command executed successfully for {ctx.author}")
        except Exception as e:
            logger.error(f"Error in help command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='points', aliases=['money', 'balance', 'solde', 'argent'])
    async def points_command(self, ctx, member: discord.Member = None):
        """Check your points or another member's points / Vérifier tes points ou ceux d'un autre membre"""
        try:
            target = member or ctx.author
            points = self.points.db.get_user_points(str(target.id))

            if target == ctx.author:
                await ctx.send(f"💰 Tu as **{points}** points!")
            else:
                await ctx.send(f"💰 {target.name} a **{points}** points!")
        except Exception as e:
            logger.error(f"Error in points command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='work', aliases=['travail', 'boulot', 'job'])
    @check_cooldown_and_limit('work')
    async def work_command(self, ctx):
        """Do your daily work (TECH Brief: 2h cooldown, max 8x/day) / Faire ton travail quotidien"""
        try:
            success, message = await self.points.daily_work(str(ctx.author.id))
            await ctx.send(message)
        except Exception as e:
            logger.error(f"Error in work command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='steal', aliases=['rob', 'voler', 'cambrioler'])  # steal = nouvelle commande selon brief, rob = alias pour compatibilité
    @check_cooldown_and_limit('steal')
    async def steal_command(self, ctx, target: discord.Member = None):
        """Steal from another member (TECH Brief: 4h cooldown, max 5x/day) / Voler un autre membre"""
        try:
            if not target:
                await ctx.send("❌ Mentionne la personne que tu veux voler! Exemple: `!steal @user`")
                return

            if target.id == ctx.author.id:
                await ctx.send("❌ Tu ne peux pas te voler toi-même!")
                return

            # Utiliser les narrations de 'rob' existantes pour compatibilité
            narration = random.choice(COMMAND_NARRATIONS['rob']).format(
                user=ctx.author.name,
                target=target.name
            )
            await ctx.send(narration)
            await asyncio.sleep(2)

            success, message = await self.points.try_rob(str(ctx.author.id), str(target.id))
            await ctx.send(message)
        except Exception as e:
            logger.error(f"Error in steal command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='gift', aliases=['cadeau', 'give'])
    @check_cooldown_and_limit('gift')
    async def gift_command(self, ctx, target: discord.Member = None, amount: int = None):
        """Give points to another member (TECH Brief: 1h cooldown, max 10x/day)"""
        try:
            if not target or amount is None:
                await ctx.send("❌ Usage: `!gift @user <montant>` - Exemple: `!gift @user 100`")
                return

            if target.id == ctx.author.id:
                await ctx.send("❌ Tu ne peux pas te faire un cadeau à toi-même!")
                return

            if amount <= 0:
                await ctx.send("❌ Le montant doit être positif!")
                return

            if amount > 1000:
                await ctx.send("❌ Tu ne peux pas donner plus de 1000 points à la fois!")
                return

            # Vérifier si l'utilisateur a assez de points
            sender_points = self.points.db.get_user_points(str(ctx.author.id))
            if sender_points < amount:
                await ctx.send(f"❌ Tu n'as que {sender_points} points! Tu ne peux pas donner {amount} points.")
                return

            # Effectuer le transfert
            success_remove = self.points.remove_points(str(ctx.author.id), amount)
            if success_remove:
                self.points.add_points(str(target.id), amount, f"Cadeau de {ctx.author.name}")
                
                embed = discord.Embed(
                    title="🎁 Cadeau envoyé!",
                    description=f"{ctx.author.mention} a donné **{amount} points** à {target.mention}!",
                    color=0x00FF00
                )
                embed.add_field(name="Expéditeur", value=ctx.author.name, inline=True)
                embed.add_field(name="Destinataire", value=target.name, inline=True)
                embed.add_field(name="Montant", value=f"{amount} points", inline=True)
                
                await ctx.send(embed=embed)
                
                # Log de l'activité
                logger.info(f"Gift: {ctx.author.name} gave {amount} points to {target.name}")
            else:
                await ctx.send("❌ Erreur lors du transfert des points.")

        except Exception as e:
            logger.error(f"Error in gift command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='revenge', aliases=['vengeance'])
    @check_daily_limit('revenge')
    async def revenge_command(self, ctx):
        """Get revenge on your last robber"""
        try:
            success, message = await self.points.try_revenge(str(ctx.author.id))
            await ctx.send(message)
        except Exception as e:
            logger.error(f"Error in revenge command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='leaderboard', aliases=['classement', 'top'])
    async def leaderboard_command(self, ctx):
        """Show the monthly leaderboard"""
        try:
            leaderboard = await self.points.get_monthly_leaderboard()

            embed = discord.Embed(
                title="🏆 Classement Mensuel des Thugz",
                description="Les plus grands gangsters du mois:",
                color=discord.Color.gold()
            )

            for i, (user_id, data) in enumerate(leaderboard[:10], 1):
                try:
                    member = await ctx.guild.fetch_member(int(user_id))
                    name = member.name if member else f"Membre {user_id}"
                    embed.add_field(
                        name=f"{i}. {name}",
                        value=f"💰 {data['points']} points",
                        inline=False
                    )
                except:
                    continue

            embed.set_footer(text=f"Classement pour {datetime.now().strftime('%B %Y')}")
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='heist', aliases=['braquage'])
    @check_daily_limit('heist')
    async def heist_command(self, ctx):
        """Start a heist"""
        try:
            # Get random narration for heist
            narration = random.choice(COMMAND_NARRATIONS['heist']).format(user=ctx.author.name)
            await ctx.send(narration)

            # Wait for tension
            await asyncio.sleep(2)

            success, message = await self.points.start_heist(str(ctx.author.id))
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in heist command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='joinheist', aliases=['rejoindre'])
    async def join_heist_command(self, ctx):
        """Join an active heist"""
        try:
            success, message = await self.points.join_heist(str(ctx.author.id))
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in join_heist command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='combat', aliases=['bataille', 'fight_general'])
    @check_cooldown_and_limit('combat')
    async def combat_command(self, ctx, target: discord.Member = None, bet: int = None):
        """Start a general combat with another member (3h cooldown, max 5x/day) / Combat général"""
        try:
            if not target or not bet:
                await ctx.send("❌ Usage: !combat @user <mise>")
                return

            if target.id == ctx.author.id:
                await ctx.send("❌ Tu ne peux pas te battre contre toi-même!")
                return

            # Get random narration for combat
            narration = random.choice(COMMAND_NARRATIONS['combat']).format(
                user=ctx.author.name,
                target=target.name
            )
            await ctx.send(narration)

            # Wait for tension
            await asyncio.sleep(2)

            success, message = await self.points.start_combat(str(ctx.author.id), str(target.id), bet)
            if success:
                combat_msg = await ctx.send(message)
                for move in COMBAT_MOVES:
                    await combat_msg.add_reaction(move)
            else:
                await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in combat command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='fight', aliases=['bagarre'])
    @check_cooldown_and_limit('fight')
    async def fight_command(self, ctx, target: discord.Member = None, bet: int = None):
        """Fight another member (TECH Brief: 6h cooldown, max 3x/day)"""
        try:
            if not target:
                await ctx.send("❌ Usage: !fight @user [mise_optionnelle]")
                return

            if target.id == ctx.author.id:
                await ctx.send("❌ Tu ne peux pas te battre contre toi-même!")
                return

            # Default bet si non spécifié
            if bet is None:
                bet = 100

            await ctx.send(f"⚔️ {ctx.author.mention} défie {target.mention} en combat singulier!")
            await asyncio.sleep(1)

            success, message = await self.points.start_combat(str(ctx.author.id), str(target.id), bet)
            if success:
                combat_msg = await ctx.send(message)
                for move in COMBAT_MOVES:
                    await combat_msg.add_reaction(move)
            else:
                await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in fight command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='duel', aliases=['duel_honneur'])
    @check_cooldown_and_limit('duel')
    async def duel_command(self, ctx, target: discord.Member = None, bet: int = None):
        """Challenge someone to an honor duel (TECH Brief: 12h cooldown, max 2x/day) / Défier en duel d'honneur"""
        try:
            if not target or not bet:
                await ctx.send("❌ Usage: !duel @user <mise> - Duel d'honneur avec mise obligatoire!")
                return

            if target.id == ctx.author.id:
                await ctx.send("❌ Tu ne peux pas te défier toi-même en duel!")
                return

            if bet < 200:
                await ctx.send("❌ La mise minimale pour un duel d'honneur est de 200 points!")
                return

            await ctx.send(f"🤺 {ctx.author.mention} défie {target.mention} en DUEL D'HONNEUR pour {bet} points!")
            await ctx.send("*Les duels sont des combats prestigieux avec des enjeux élevés...*")
            await asyncio.sleep(2)

            success, message = await self.points.start_combat(str(ctx.author.id), str(target.id), bet)
            if success:
                combat_msg = await ctx.send(message)
                for move in COMBAT_MOVES:
                    await combat_msg.add_reaction(move)
            else:
                await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in duel command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='prison', aliases=['status', 'statut', 'cellule'])
    async def prison_status_command(self, ctx, member: discord.Member = None):
        """Check prison status / Vérifier le statut de prison"""
        try:
            target = member or ctx.author
            status = await self.points.get_prison_status(str(target.id))

            if not status:
                await ctx.send(f"✅ {target.name} n'est pas en prison!")
                return

            embed = discord.Embed(
                title="🏢 Status Prison",
                description=f"Status de {target.name}",
                color=discord.Color.dark_grey()
            )

            embed.add_field(name="⏳ Temps restant", value=f"{status['time_left']} secondes", inline=False)
            if status['role']:
                embed.add_field(name="👤 Rôle", value=status['role'], inline=True)
                embed.add_field(name="📈 Bonus", value=status['role_bonus'], inline=True)

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in prison status command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='activity', aliases=['activite', 'action', 'faire'])
    async def prison_activity_command(self, ctx, activity_name: str = None):
        """Do a prison activity or list available activities / Faire une activité en prison"""
        try:
            if not activity_name:
                embed = discord.Embed(
                    title="🏢 Activités Prison",
                    description="Liste des activités disponibles:",
                    color=discord.Color.blue()
                )

                for act_id, activity in PRISON_ACTIVITIES.items():
                    embed.add_field(
                        name=activity['name'],
                        value=f"Réduction: {activity['reduction']} secondes\nID: `{act_id}`",
                        inline=False
                    )

                await ctx.send(embed=embed)
                return

            success, message = await self.points.do_prison_activity(str(ctx.author.id), activity_name)
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in prison activity command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='tribunal', aliases=['proces', 'cour', 'justice'])
    async def tribunal_command(self, ctx, *, plea: str = None):
        """Request a trial with a plea / Demander un procès avec plaidoyer"""
        try:
            if not plea:
                await ctx.send("❌ Tu dois inclure un plaidoyer! Exemple: `!tribunal Je suis innocent!`")
                return

            success, message = await self.points.request_trial(str(ctx.author.id), plea)
            if success:
                trial_msg = await ctx.send(message)
                await trial_msg.add_reaction("✅")
                await trial_msg.add_reaction("❌")
            else:
                await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in tribunal command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='shop', aliases=['boutique'])
    async def shop_command(self, ctx):
        """Show the shop items"""
        try:
            embed = discord.Embed(
                title="🏪 Boutique du Crime",
                description="Utilise !buy <item> pour acheter un objet",
                color=discord.Color.gold()
            )

            # Add regular items
            for item_id, item in SHOP_ITEMS.items():
                embed.add_field(
                    name=f"{item['name']} - {item['price']} points",
                    value=f"{item['description']}\nID: `{item_id}`",
                    inline=False
                )

            # Add special items if available
            if SHOP_ITEMS_NEW:
                embed.add_field(
                    name="🌟 Items Spéciaux",
                    value="Collection unique et limitée:",
                    inline=False
                )

                for item_id, item in SHOP_ITEMS_NEW.items():
                    quantity_text = f"(Reste: {item['quantity']})" if item['quantity'] > 0 else "(SOLD OUT)"
                    embed.add_field(
                        name=f"{item['name']} - {item['price']} points {quantity_text}",
                        value=f"{item['description']}\nID: `{item_id}`",
                        inline=False
                    )

            await ctx.send(embed=embed)
            logger.info(f"Shop displayed to {ctx.author}")
        except Exception as e:
            logger.error(f"Error in shop command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='buy', aliases=['acheter'])
    async def buy_command(self, ctx, item_id: str = None):
        """Buy an item from the shop"""
        try:
            if not item_id:
                await ctx.send("❌ Spécifie l'objet à acheter! Exemple: `!buy lockpick`")
                return

            success, message = await self.points.buy_item(str(ctx.author.id), item_id)
            await ctx.send(message)
        except Exception as e:
            logger.error(f"Error in buy command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='inventory', aliases=['inventaire', 'inv', 'objets'])
    async def inventory(self, ctx):
        """Show your inventory / Affiche l'inventaire de l'utilisateur."""
        inv = self.points.db.get_inventory(str(ctx.author.id))
        if not inv:
            await ctx.send("Votre inventaire est vide.")
        else:
            items = "\n".join(f"- {item_id}" for item_id in inv)
            await ctx.send(f"**Votre inventaire :**\n{items}")

    @commands.command(name='trade', aliases=['echanger', 'troquer', 'echange'])
    async def trade(self, ctx, member: discord.Member, my_item_id: str):
        """Trade an item with another player / Propose un échange d'objet à un autre joueur."""
        author_id = str(ctx.author.id)
        target_id = str(member.id)
        db = self.points.db

        # Vérifie que l'auteur possède bien l'objet proposé
        if my_item_id not in db.get_inventory(author_id):
            await ctx.send("Vous ne possédez pas cet objet.")
            return
        if author_id == target_id:
            await ctx.send("Vous ne pouvez pas échanger avec vous-même.")
            return

        # Demande à B quel objet il souhaite proposer en échange
        await ctx.send(
            f"{member.mention}, {ctx.author.display_name} souhaite échanger son objet `{my_item_id}` avec vous.\n"
            "Réponds avec l'identifiant de l'objet de ton inventaire que tu proposes en échange, ou 'annuler' pour refuser.\n"
            f"Ton inventaire : {', '.join(db.get_inventory(target_id)) or 'vide'}"
        )

        def check_item(m):
            return m.author.id == member.id and m.channel == ctx.channel

        try:
            msg = await ctx.bot.wait_for("message", check=check_item, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send("Échange annulé (temps écoulé).")
            return

        # Si B annule
        if msg.content.lower() == "annuler":
            await ctx.send("Échange annulé.")
            return

        their_item_id = msg.content.strip()

        # Vérifie que B possède bien l'objet proposé
        if their_item_id not in db.get_inventory(target_id):
            await ctx.send(f"{member.display_name} ne possède pas cet objet. Échange annulé.")
            return

        # Demande à A de confirmer l'échange
        await ctx.send(
            f"{ctx.author.mention}, {member.display_name} propose d'échanger son objet `{their_item_id}` contre ton `{my_item_id}`.\n"
            "Réponds 'oui' pour accepter, 'non' pour refuser."
        )

        def check_confirm(m):
            return m.author.id == ctx.author.id and m.channel == ctx.channel and m.content.lower() in ["oui", "non"]

        try:
            confirm_msg = await ctx.bot.wait_for("message", check=check_confirm, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("Échange annulé (temps écoulé).")
            return

        if confirm_msg.content.lower() == "oui":
            # Retire les objets des inventaires respectifs et les ajoute à l'autre
            db.remove_item_from_inventory(author_id, my_item_id)
            db.add_item_to_inventory(target_id, my_item_id)
            db.remove_item_from_inventory(target_id, their_item_id)
            db.add_item_to_inventory(author_id, their_item_id)
            await ctx.send(
                f"Échange réussi ! `{my_item_id}` a été échangé contre `{their_item_id}` entre {ctx.author.display_name} et {member.display_name}."
            )
        else:
            await ctx.send("Échange refusé.")

    @commands.command(name='addpoints', aliases=['ajouterpoints', 'donnerpoints'])
    @is_staff()
    async def add_points(self, ctx, member: discord.Member = None, amount: int = None):
        """[STAFF] Add points to a member / [STAFF] Ajouter des points à un membre"""
        try:
            if not member or amount is None:
                await ctx.send("❌ Usage: !addpoints @user <montant>")
                return

            if amount <= 0:
                await ctx.send("❌ Le montant doit être positif!")
                return

            self.points.db.add_points(str(member.id), amount)
            await ctx.send(f"✅ {amount} points ajoutés à {member.name}!")
            logger.info(f"Staff {ctx.author} added {amount} points to {member}")
        except Exception as e:
            logger.error(f"Error in add_points command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='removepoints', aliases=['retirerpoints', 'enleverpoints'])
    @is_staff()
    async def remove_points(self, ctx, member: discord.Member = None, amount: int = None):
        """[STAFF] Remove points from a member / [STAFF] Retirer des points à un membre"""
        try:
            if not member or amount is None:
                await ctx.send("❌ Usage: !removepoints @user <montant>")
                return

            if amount <= 0:
                await ctx.send("❌ Le montant doit être positif!")
                return

            current_points = self.points.db.get_user_points(str(member.id))
            if current_points < amount:
                amount = current_points

            self.points.db.add_points(str(member.id), -amount)
            await ctx.send(f"✅ {amount} points retirés à {member.name}!")
            logger.info(f"Staff {ctx.author} removed {amount} points from {member}")
        except Exception as e:
            logger.error(f"Error in remove_points command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='linktwitter', aliases=['liertwitter', 'connecttwitter'])
    @commands.cooldown(1, 900, commands.BucketType.user)  # 1 fois par 15 minutes par utilisateur
    async def link_twitter(self, ctx, username: str):
        """Link a Twitter account (limited to 1 time per 15min) / Lier un compte Twitter"""
        try:
            if not self.twitter_handler.is_available():
                await ctx.send("❌ Service Twitter temporairement indisponible.")
                return
            
            # Vérifier si l'utilisateur a déjà un compte lié
            user_data = self.point_system.database.get_user_data(str(ctx.author.id))
            if user_data.get('twitter'):
                await ctx.send("❌ Vous avez déjà un compte Twitter lié. Utilisez `!unlinktwitter` d'abord.")
                return
            
            # Nettoyer le nom d'utilisateur
            username = username.replace('@', '').strip()
            
            # Notification que la requête est en queue
            embed = discord.Embed(
                title="🐦 Vérification en cours...",
                description=f"Vérification du compte @{username} en cours.\n"
                           f"Cela peut prendre jusqu'à 15 minutes selon la file d'attente.",
                color=0x1DA1F2
            )
            status_msg = await ctx.send(embed=embed)
            
            # Vérifier le compte avec rate limiting
            success, data = await self.twitter_handler.verify_account(username)
            
            if success:
                # Sauvegarder le lien
                user_data['twitter'] = data
                self.point_system.database.save_data()
                
                # Donner des points bonus pour la liaison
                bonus_points = 500
                self.point_system.database.add_points(str(ctx.author.id), bonus_points)
                
                embed = discord.Embed(
                    title="✅ Compte Twitter lié",
                    description=f"Votre compte Discord est maintenant lié à [@{data['username']}]",
                    color=0x00FF00
                )
                embed.add_field(name="Nom", value=data['name'], inline=True)
                embed.add_field(name="Followers", value=f"{data['followers_count']:,}", inline=True)
                embed.add_field(name="Bonus", value=f"+{bonus_points} points", inline=True)
                
                await status_msg.edit(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Erreur de vérification",
                    description=str(data),
                    color=0xFF0000
                )
                await status_msg.edit(embed=embed)
                
        except commands.CommandOnCooldown as e:
            remaining_time = int(e.retry_after)
            minutes = remaining_time // 60
            seconds = remaining_time % 60
            await ctx.send(f"❌ Vous devez attendre {minutes}m {seconds}s avant de pouvoir lier un autre compte Twitter.")
        except Exception as e:
            logger.error(f"Error in link_twitter command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite lors de la liaison du compte Twitter.")

    @commands.command(name='twitterstatus', aliases=['statustwitter', 'statut_x'])
    @commands.has_permissions(administrator=True)
    async def twitter_status(self, ctx):
        """Check Twitter service status (Admin only) / Vérifier l'état du service Twitter (Admin seulement)"""
        try:
            # Vérifier la santé
            is_healthy, health_message = await self.twitter_handler.health_check()
            
            # Obtenir le statut du rate limiter
            rate_status = self.twitter_handler.get_rate_limit_status()
            
            embed = discord.Embed(
                title="🐦 État du Service Twitter",
                description=health_message,
                color=0x00FF00 if is_healthy else 0xFF0000
            )
            
            embed.add_field(
                name="Service",
                value="✅ Actif" if self.twitter_handler.is_available() else "❌ Inactif",
                inline=True
            )
            
            embed.add_field(
                name="Requêtes en attente",
                value=rate_status.get('pending_requests', 0),
                inline=True
            )
            
            embed.add_field(
                name="Cache actif",
                value=f"{rate_status.get('cache_entries', 0)} entrées",
                inline=True
            )
            
            # Statut des endpoints
            endpoints_info = ""
            for endpoint, info in rate_status.get('endpoints', {}).items():
                endpoints_info += f"**{endpoint}**: {info['next_available']}\n"
            
            if endpoints_info:
                embed.add_field(
                    name="Prochaines disponibilités",
                    value=endpoints_info,
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in twitter_status command: {e}", exc_info=True)
            await ctx.send("❌ Erreur lors de la vérification du statut Twitter.")

    @commands.command(name='twitterqueue', aliases=['queuetwitter', 'file_x'])
    @commands.has_permissions(administrator=True)
    async def twitter_queue(self, ctx):
        """View Twitter queue (Admin only) / Voir la file d'attente Twitter (Admin seulement)"""
        try:
            queue_info = await self.twitter_handler.queue_info()
            
            embed = discord.Embed(
                title="📋 File d'attente Twitter",
                color=0x1DA1F2
            )
            
            embed.add_field(
                name="Requêtes en attente",
                value=queue_info.get('pending_requests', 0),
                inline=True
            )
            
            embed.add_field(
                name="Résultats en cache",
                value=queue_info.get('cache_entries', 0),
                inline=True
            )
            
            # Détails des endpoints
            endpoints_status = queue_info.get('endpoints_status', {})
            if endpoints_status:
                status_text = ""
                for endpoint, info in endpoints_status.items():
                    status_text += f"**{endpoint}**:\n"
                    status_text += f"  Utilisé: {info['requests_used']}/{info['requests_limit']}\n"
                    status_text += f"  Prochain: {info['next_available']}\n\n"
                
                embed.add_field(
                    name="État des endpoints",
                    value=status_text or "Aucun endpoint actif",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in twitter_queue command: {e}", exc_info=True)
            await ctx.send("❌ Erreur lors de la récupération des informations de queue.")

    @commands.command(name='unlinktwitter', aliases=['deconnectertwitter', 'delier_x'])
    async def unlink_twitter(self, ctx):
        """Unlink Twitter account / Délier le compte Twitter"""
        try:
            user_data = self.point_system.database.get_user_data(str(ctx.author.id))
            
            if not user_data.get('twitter'):
                await ctx.send("❌ Aucun compte Twitter lié.")
                return
            
            # Supprimer le lien
            del user_data['twitter']
            self.point_system.database.save_data()
            
            embed = discord.Embed(
                title="✅ Compte Twitter délié",
                description="Votre compte Twitter a été délié avec succès.",
                color=0x00FF00
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in unlink_twitter command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite lors du délien du compte Twitter.")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle reactions for combat and voting"""
        if user.bot:
            return

        message = reaction.message
        emoji = str(reaction.emoji)

        # Handle combat moves
        if message.content.startswith("⚔️ Combat"):
            if emoji in COMBAT_MOVES:
                success, result = await self.points.process_combat_move(
                    str(message.id), str(user.id), emoji
                )
                if success:
                    await message.channel.send(result)

        # Handle tribunal votes
        elif message.content.startswith("⚖️"):
            if emoji in ["✅", "❌"]:
                vote = emoji == "✅"
                try:
                    # Extract defendant ID from message content
                    defendant_id = message.content.split('<@')[1].split('>')[0]
                    success, result = await self.points.vote_trial(
                        str(user.id), defendant_id, vote
                    )
                    await message.channel.send(result)
                except Exception as e:
                    logger.error(f"Error processing trial vote: {e}", exc_info=True)