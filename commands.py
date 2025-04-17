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

    @commands.command(name='help', aliases=['commands', 'bothelp'])
    async def help_command(self, ctx):
        """Show all available commands"""
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
                    "!inventory": "Voir ton inventaire"
                },
                "🦹 Actions": {
                    "!rob @user": "Tenter de voler quelqu'un (3x par jour)",
                    "!revenge": "Se venger de son dernier voleur (1x par jour)",
                    "!heist": "Commencer un braquage (2x par jour)",
                    "!joinheist": "Rejoindre un braquage",
                    "!combat @user <mise>": "Engager un combat (5x par jour)"
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

    @commands.command(name='points', aliases=['money', 'balance'])
    async def points_command(self, ctx, member: discord.Member = None):
        """Check your points or another member's points"""
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

    @commands.command(name='work', aliases=['travail'])
    @check_daily_limit('work')
    async def work_command(self, ctx):
        """Do your daily work"""
        try:
            success, message = await self.points.daily_work(str(ctx.author.id))
            await ctx.send(message)
        except Exception as e:
            logger.error(f"Error in work command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='rob')
    @check_daily_limit('rob')
    async def rob_command(self, ctx, target: discord.Member = None):
        """Rob another member"""
        try:
            if not target:
                await ctx.send("❌ Mentionne la personne que tu veux voler! Exemple: `!rob @user`")
                return

            if target.id == ctx.author.id:
                await ctx.send("❌ Tu ne peux pas te voler toi-même!")
                return

            narration = random.choice(COMMAND_NARRATIONS['rob']).format(
                user=ctx.author.name,
                target=target.name
            )
            await ctx.send(narration)
            await asyncio.sleep(2)

            success, message = await self.points.try_rob(str(ctx.author.id), str(target.id))
            await ctx.send(message)
        except Exception as e:
            logger.error(f"Error in rob command: {e}", exc_info=True)
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

    @commands.command(name='combat', aliases=['fight', 'duel'])
    @check_daily_limit('combat')
    async def combat_command(self, ctx, target: discord.Member = None, bet: int = None):
        """Start a combat with another member"""
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

    @commands.command(name='prison', aliases=['status'])
    async def prison_status_command(self, ctx, member: discord.Member = None):
        """Check prison status"""
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

    @commands.command(name='activity')
    async def prison_activity_command(self, ctx, activity_name: str = None):
        """Do a prison activity or list available activities"""
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

    @commands.command(name='tribunal')
    async def tribunal_command(self, ctx, *, plea: str = None):
        """Request a trial with a plea"""
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

    @commands.command(name='inventory', aliases=['inv'])
    async def inventory_command(self, ctx):
        """Show your inventory"""
        try:
            inventory = self.points.db.get_inventory(str(ctx.author.id))

            if not inventory:
                await ctx.send("📦 Ton inventaire est vide!")
                return

            embed = discord.Embed(
                title="📦 Ton Inventaire",
                color=discord.Color.blue()
            )

            item_counts = {}
            for item_id in inventory:
                item_counts[item_id] = item_counts.get(item_id, 0) + 1

            for item_id, count in item_counts.items():
                if item_id in SHOP_ITEMS:
                    item = SHOP_ITEMS[item_id]
                    embed.add_field(
                        name=f"{item['name']} x{count}",
                        value=item['description'],
                        inline=False
                    )

            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in inventory command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='addpoints')
    @is_staff()
    async def add_points(self, ctx, member: discord.Member = None, amount: int = None):
        """[STAFF] Add points to a member"""
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

    @commands.command(name='removepoints')
    @is_staff()
    async def remove_points(self, ctx, member: discord.Member = None, amount: int = None):
        """[STAFF] Remove points from a member"""
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

    @commands.command(name='linktwitter')
    async def link_twitter(self, ctx, twitter_username: str = None):
        """Link Discord account to Twitter account"""
        try:
            if not twitter_username:
                await ctx.send("❌ Veuillez fournir votre nom d'utilisateur Twitter. Exemple: `!linktwitter MonCompteTwitter`")
                return

            # Clean up username
            twitter_username = twitter_username.lstrip('@').lower().strip()
            loading_message = await ctx.send("🔄 Vérification de votre compte Twitter en cours...")

            try:
                exists, twitter_id, metrics = await self.twitter.verify_account(twitter_username)

                if exists and twitter_id:
                    self.points.db.link_twitter_account(str(ctx.author.id), twitter_username)
                    await loading_message.edit(content=f"✅ Votre compte Discord est maintenant lié à Twitter @{twitter_username}")
                else:
                    await loading_message.edit(content="❌ Ce compte Twitter n'existe pas.")

            except TooManyRequests:
                await loading_message.edit(content="⏳ L'API Twitter est temporairement indisponible.")
            except Exception as e:
                logger.error(f"Error verifying Twitter account: {e}", exc_info=True)
                await loading_message.edit(content="❌ Une erreur s'est produite.")
        except Exception as e:
            logger.error(f"Error in link_twitter command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='twitterstats', aliases=['twstats'])
    async def twitter_stats(self, ctx):
        """Check Twitter statistics"""
        try:
            twitter_username = self.points.db.get_twitter_username(str(ctx.author.id))
            if not twitter_username:
                await ctx.send("❌ Votre compte Discord n'est pas lié à Twitter. Utilisez `!linktwitter` pour le lier.")
                return

            loading_message = await ctx.send("🔄 Récupération des statistiques...")

            try:
                exists, twitter_id, metrics = await self.twitter.verify_account(twitter_username)
                if exists:
                    stats = await self.twitter.get_user_stats(twitter_id)

                    embed = discord.Embed(
                        title=f"📊 Statistiques Twitter pour @{twitter_username}",
                        color=discord.Color.blue()
                    )

                    embed.add_field(name="👍 Likes", value=str(stats.get('likes', 0)), inline=True)
                    embed.add_field(name="🔄 Retweets", value=str(stats.get('retweets', 0)), inline=True)
                    embed.add_field(name="💬 Réponses", value=str(stats.get('replies', 0)), inline=True)

                    await loading_message.delete()
                    await ctx.send(embed=embed)
                else:
                    await loading_message.edit(content="❌ Votre compte Twitter n'est plus accessible.")

            except Exception as e:
                logger.error(f"Error getting Twitter stats: {e}", exc_info=True)
                await loading_message.edit(content="❌ Une erreur s'est produite.")
        except Exception as e:
            logger.error(f"Error in twitter_stats command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

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