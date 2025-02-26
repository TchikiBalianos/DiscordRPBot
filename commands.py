from functools import wraps
import discord
from discord.ext import commands, tasks
import logging
from tweepy.errors import TooManyRequests, NotFound, Unauthorized
from datetime import datetime, timedelta
import random
import asyncio
from config import (
    COMMAND_NARRATIONS, 
    SHOP_ITEMS_NEW,
    SHOP_ITEMS,
    DAILY_LIMITS,
    ROULETTE_MIN_BET,
    ROULETTE_MAX_BET,
    ROULETTE_MULTIPLIER,
    ROULETTE_LOSS_PENALTY,
    RACE_HORSES,
    PRISON_ACTIVITIES,
    LOTTERY_TICKET_PRICE,
    LOTTERY_MAX_TICKETS,
    DRUG_DEAL_MIN_INVESTMENT,
    COMBAT_MOVES,
    VOTE_REACTIONS,
    RACE_MIN_BET,
    RACE_MAX_BET,
    RACE_INJURY_MULTIPLIER,
    DICE_MIN_BET,
    DICE_MAX_BET,
    DICE_BONUS_MULTIPLIER,
    DICE_COOLDOWN,
    ROULETTE_COOLDOWN,
    LOTTERY_DRAW_INTERVAL,
    POINTS_VOICE_PER_MINUTE,
    POINTS_MESSAGE,
    POINTS_TWITTER_LIKE,
    POINTS_TWITTER_RT,
    POINTS_TWITTER_COMMENT
)

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
        usage = ctx.bot.point_system.db.get_daily_usage(str(ctx.author.id), command_name)
        if usage >= DAILY_LIMITS.get(command_name, float('inf')):
            await ctx.send(f"❌ Tu as atteint la limite quotidienne pour cette commande ({DAILY_LIMITS[command_name]}x par jour)")
            return False
        return True
    return commands.check(predicate)

class Commands(commands.Cog):
    def __init__(self, bot, point_system, twitter_handler):
        """Initialize the Commands cog"""
        self.bot = bot
        self.points = point_system
        self.twitter = twitter_handler
        logger.info("Commands cog initialized")
        self.lottery_task.start()

    @commands.Cog.listener()
    async def on_ready(self):
        """Setup prison role when bot is ready"""
        for guild in self.bot.guilds:
            await self.points.setup_prison_role(guild)

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

            self.points.db.add_points(member.id, amount)
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

            current_points = self.points.db.get_user_points(member.id)
            if current_points < amount:
                amount = current_points

            self.points.db.add_points(member.id, -amount)
            await ctx.send(f"✅ {amount} points retirés à {member.name}!")
            logger.info(f"Staff {ctx.author} removed {amount} points from {member}")

        except Exception as e:
            logger.error(f"Error in remove_points command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='freeprison')
    @is_staff()
    async def free_prison(self, ctx, member: discord.Member = None):
        """[STAFF] Free a member from prison"""
        try:
            if not member:
                await ctx.send("❌ Usage: !freeprison @user")
                return

            prison_time = self.points.db.get_prison_time(member.id)
            if prison_time > datetime.now().timestamp():
                self.points.db.set_prison_time(member.id, 0)
                await ctx.send(f"🔓 {member.name} a été libéré de prison!")
                logger.info(f"Staff {ctx.author} freed {member} from prison")
            else:
                await ctx.send(f"❌ {member.name} n'est pas en prison!")

        except Exception as e:
            logger.error(f"Error in free_prison command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='ping')
    async def ping_command(self, ctx):
        """Simple command to test if the bot is responding"""
        try:
            await ctx.send('Pong!')
            logger.info(f"Ping command executed by {ctx.author}")
        except Exception as e:
            logger.error(f"Error in ping command: {e}")
            await ctx.send("Une erreur s'est produite.")

    @commands.command(name='linktwitter')
    async def link_twitter(self, ctx, twitter_username: str = None):
        """Link Discord account to Twitter account"""
        try:
            if not twitter_username:
                await ctx.send("❌ Veuillez fournir votre nom d'utilisateur Twitter. Exemple: `!linktwitter MonCompteTwitter`")
                return

            # Clean up username
            twitter_username = twitter_username.lstrip('@').lower().strip()
            logger.info(f"Attempting to link Twitter account @{twitter_username} for user {ctx.author}")

            loading_message = await ctx.send("🔄 Vérification de votre compte Twitter en cours...")
            try:
                exists, twitter_id, metrics = await self.twitter.verify_account(twitter_username)
                logger.info(f"Verification result for @{twitter_username}: exists={exists}, id={twitter_id}, metrics={metrics}")

                if exists and twitter_id:
                    # Store the link
                    self.points.db.link_twitter_account(str(ctx.author.id), twitter_username)
                    await loading_message.edit(content=f"✅ Votre compte Discord est maintenant lié à Twitter @{twitter_username}")

                    # Show initial metrics if available
                    if metrics:
                        await ctx.send(f"📊 Stats initiales :\n"
                                     f"• Followers: {metrics.get('followers_count', 0)}\n"
                                     f"• Following: {metrics.get('following_count', 0)}\n"
                                     f"• Tweets: {metrics.get('tweet_count', 0)}")
                else:
                    await loading_message.edit(content="❌ Ce compte Twitter n'existe pas. Vérifiez le nom d'utilisateur et réessayez.")

            except TooManyRequests:
                await loading_message.edit(content="⏳ L'API Twitter est temporairement indisponible. Veuillez réessayer dans quelques minutes.")
            except Unauthorized:
                logger.error("Twitter API authentication failed")
                await loading_message.edit(content="❌ Erreur d'authentification Twitter. Un administrateur a été notifié.")
            except Exception as e:
                logger.error(f"Error verifying Twitter account: {str(e)}", exc_info=True)
                await loading_message.edit(content="❌ Une erreur s'est produite lors de la vérification du compte Twitter.")

        except Exception as e:
            logger.error(f"Error in link_twitter command: {str(e)}", exc_info=True)
            await ctx.send("❌ Une erreur inattendue s'est produite.")

    @commands.command(name='testtwitter')
    async def test_twitter(self, ctx, twitter_username: str = None):
        """Test Twitter API connection with a username"""
        try:
            if not twitter_username:
                await ctx.send("❌ Veuillez fournir un nom d'utilisateur Twitter à tester. Exemple: `!testtwitter elonmusk`")
                return

            # Clean up username
            twitter_username = twitter_username.lstrip('@').lower().strip()
            await ctx.send(f"🔍 Test de connexion à Twitter pour le compte @{twitter_username}...")

            try:
                exists, twitter_id, metrics = await self.twitter.verify_account(twitter_username)

                if exists and twitter_id:
                    await ctx.send(f"✅ Compte Twitter trouvé! ID: {twitter_id}\nMétriques: {metrics}")
                else:
                    await ctx.send(f"❌ Le compte Twitter @{twitter_username} n'a pas été trouvé.")

            except TooManyRequests:
                await ctx.send("⏳ L'API Twitter est temporairement indisponible (rate limit). Veuillez réessayer dans quelques minutes.")
            except Unauthorized:
                await ctx.send("❌ Erreur d'authentification avec l'API Twitter. Les clés d'API doivent être vérifiées.")
            except Exception as e:
                logger.error(f"Error in Twitter API test: {str(e)}", exc_info=True)
                await ctx.send(f"❌ Erreur lors du test: {str(e)}")

        except Exception as e:
            logger.error(f"Error in test_twitter command: {str(e)}", exc_info=True)
            await ctx.send("❌ Une erreur inattendue s'est produite.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Track voice channel activity"""
        try:
            # Si l'utilisateur rejoint un canal vocal
            if before.channel is None and after.channel is not None:
                logger.info(f"User {member} joined voice channel {after.channel}")
                self.points.db.start_voice_session(str(member.id))

            # Si l'utilisateur quitte un canal vocal
            elif before.channel is not None and after.channel is None:
                logger.info(f"User {member} left voice channel {before.channel}")
                minutes = self.points.db.end_voice_session(str(member.id))
                if minutes > 0:
                    points = minutes * POINTS_VOICE_PER_MINUTE
                    self.points.db.add_points(str(member.id), points)
                    logger.info(f"Added {points} points to {member} for {minutes} minutes in voice")

        except Exception as e:
            logger.error(f"Error in voice state update: {e}", exc_info=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Award points for messages"""
        try:
            # Ignore bot messages and commands
            if message.author.bot or message.content.startswith('!'):
                return

            # Award points for messages
            self.points.db.add_points(str(message.author.id), POINTS_MESSAGE)
            logger.info(f"Added {POINTS_MESSAGE} points to {message.author} for message")

        except Exception as e:
            logger.error(f"Error in message points: {e}", exc_info=True)

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

            # Get random narration for rob
            narration = random.choice(COMMAND_NARRATIONS['rob']).format(
                user=ctx.author.name,
                target=target.name
            )
            logger.info(f"Rob command initiated by {ctx.author} targeting {target}. Using narration: {narration}")
            await ctx.send(narration)

            # Wait for tension
            await asyncio.sleep(2)

            success, message = await self.points.try_rob(ctx.author.id, target.id)
            logger.info(f"Rob attempt result - Success: {success}, Message: {message}")
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in rob command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='revenge', aliases=['vengeance'])
    @check_daily_limit('revenge')
    async def revenge_command(self, ctx):
        """Get revenge on your last robber"""
        try:
            success, message = await self.points.try_revenge(ctx.author.id)
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in revenge command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='work', aliases=['travail'])
    @check_daily_limit('work')
    async def work_command(self, ctx):
        """Do your daily work"""
        try:
            success, message = await self.points.daily_work(ctx.author.id)
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in work command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='points', aliases=['money', 'balance'])
    async def points_command(self, ctx, member: discord.Member = None):
        """Check your points or another member's points"""
        try:
            target = member or ctx.author
            points = self.points.db.get_user_points(target.id)

            if target == ctx.author:
                await ctx.send(f"💰 Tu as **{points}** points!")
            else:
                await ctx.send(f"💰 {target.name} a **{points}** points!")

        except Exception as e:
            logger.error(f"Error in points command: {e}", exc_info=True)
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

            current_month = datetime.now().strftime('%B %Y')
            embed.set_footer(text=f"Classement pour {current_month}")
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}", exc_info=True)
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

            commands_list = {
                "💰 Économie": {
                    "!work": "Travailler pour gagner des points (1x par jour)",
                    "!points": "Voir ton solde de points",
                    "!leaderboard": "Voir le classement mensuel",
                    "!shop": "Voir les objets disponibles à la vente",
                    "!inventory": "Voir ton inventaire",
                    "!lottery": "Acheter un ticket de loto",
                },
                "🦹 Actions": {
                    "!rob @user": "Tenter de voler quelqu'un (3x par jour)",
                    "!revenge": "Se venger de son dernier voleur (1x par jour)",
                    "!heist": "Commencer un braquage (2x par jour)",
                    "!joinheist": "Rejoindre un braquage",
                    "!deal <montant>": "Faire un trafic de drogue (5x par jour)",
                    "!escape": "Tenter de fuir la prison (2x par jour)",
                    "!combat @user <mise>": "Engager un combat (5x par jour)",
                    "!roulette <mise>": "Jouer à la roulette russe (10x par jour)",
                    "!race <numéro> <mise>": "Parier sur une course de chevaux (15x par jour)",
                    "!dice @user <mise>": "Défier un autre membre à un duel de dés (5x par jour)"
                },
                "🏢 Prison": {
                    "!prison": "Voir ton statut en prison",
                    "!activity": "Voir les activités disponibles",
                    "!activity <nom>": "Faire une activité en prison",
                    "!tribunal <plaidoyer>": "Demander un procès (500 points)",
                    "!vote @user oui/non": "Voter pour un procès"
                },
                "🐦 Twitter": {
                    "!linktwitter": "Lier ton compte Twitter",
                    "!twitterstats": "Voir tes stats Twitter",
                    "!testtwitter": "Tester la connexion Twitter"
                }
            }

            # Add staff commands if user is staff
            is_staff = ctx.author.guild_permissions.administrator or \
                      any(role.name.lower() in ['staff', 'modo', 'admin'] for role in ctx.author.roles)

            if is_staff:
                commands_list["⚡ Staff"] = {
                    "!addpoints @user montant": "Ajouter des points à un membre",
                    "!removepoints @user montant": "Retirer des points à un membre",
                    "!freeprison @user": "Libérer un membre de prison"
                }

            # Add daily limits information
            limits_info = "📊 Limites quotidiennes:\n" + "\n".join([
                f"• {cmd.capitalize()}: {limit}x par jour"
                for cmd, limit in DAILY_LIMITS.items()
            ])
            embed.add_field(name="⚠️ Limites", value=limits_info, inline=False)

            for category, cmds in commands_list.items():
                embed.add_field(
                    name=category,
                    value="\n".join([f"`{cmd}`: {desc}" for cmd, desc in cmds.items()]),
                    inline=False
                )

            await ctx.send(embed=embed)
            logger.info(f"Help command executed by {ctx.author}")

        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='twitterstats', aliases=['twstats'])
    async def twitter_stats(self, ctx):
        """Check Twitter statistics"""
        try:
            # Get linked Twitter username
            twitter_username = self.points.db.get_twitter_username(str(ctx.author.id))
            if not twitter_username:
                await ctx.send("❌ Votre compte Discord n'est pas lié à Twitter. Utilisez `!linktwitter` pour le lier.")
                return

            # Verify account and get stats
            exists, twitter_id, metrics = await self.twitter.verify_account(twitter_username)
            if not exists:
                await ctx.send("❌ Votre compte Twitter lié n'est plus accessible.")
                return

            stats = await self.twitter.get_user_stats(twitter_id)

            embed = discord.Embed(
                title=f"📊 Statistiques Twitter pour @{twitter_username}",
                color=discord.Color.blue()
            )

            # Afficher les statistiques d'engagement
            embed.add_field(name="👍 Likes", value=str(stats.get('likes', 0)), inline=True)
            embed.add_field(name="🔄 Retweets", value=str(stats.get('retweets', 0)), inline=True)
            embed.add_field(name="💬 Réponses", value=str(stats.get('replies', 0)), inline=True)

            # Afficher l'engagement total et les points gagnés
            embed.add_field(
                name="📈 Engagement Total",
                value=str(stats.get('total_engagement', 0)),
                inline=False
            )
            embed.add_field(
                name="💰 Points Gagnés",
                value=str(stats.get('points_earned', 0)),
                inline=False
            )

            # Afficher les taux de points
            embed.add_field(
                name="ℹ️ Points par interaction",
                value=f"• Like: {POINTS_TWITTER_LIKE} points\n"
                      f"• Retweet: {POINTS_TWITTER_RT} points\n"
                      f"• Réponse: {POINTS_TWITTER_COMMENT} points",
                inline=False
            )

            embed.set_footer(text="Dernière mise à jour: maintenant")
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in twitter_stats command: {str(e)}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite lors de la récupération des statistiques.")

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

            # Add special items
            embed.add_field(
                name="🌟 Items Spéciaux", 
                value="Collection unique et limitée:",
                inline=False
            )

            for item_id, item in SHOP_ITEMS_NEW.items():
                quantity_text = f"(Reste: {item['quantity']})" if item['quantity'] > 0 else "(SOLD OUT)"
                embed.add_field(
                    name=f"{item['name']} - {item['price']} points {quantity_text}",
                    value=f"{item['description']}\nID: `{item_id}`\nType: {item['type']}",
                    inline=False
                )

            logger.info(f"Shop displayed to {ctx.author}, showing {len(SHOP_ITEMS)} regular items and {len(SHOP_ITEMS_NEW)} special items")
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in shop command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='buy', aliases=['acheter'])
    async def buy_command(self, ctx, item_id: str = None):
        """Buy an item from the shop"""
        try:
            if not item_id:
                await ctx.send("❌ Spécifie l'objet à acheter! Exemple: `!buy thugz_nft`")
                return

            item_id = item_id.lower()
            logger.info(f"{ctx.author} attempting to buy item: {item_id}")

            # Check special items first
            if item_id in SHOP_ITEMS_NEW:
                item = SHOP_ITEMS_NEW[item_id]
                logger.info(f"Special item purchase attempt - Item: {item['name']}, Quantity left: {item['quantity']}")

                # Check quantity
                if item['quantity'] <= 0:
                    await ctx.send("❌ Cet objet n'est plus disponible!")
                    return

                # Check points
                points = self.points.db.get_user_points(str(ctx.author.id))
                if points < item['price']:
                    await ctx.send(f"❌ Tu n'as pas assez de points! (Prix: {item['price']} points)")
                    return

                # Process purchase
                self.points.db.add_points(str(ctx.author.id), -item['price'])
                self.points.db.add_special_item(str(ctx.author.id), item_id)

                await ctx.send(f"✅ Tu as acheté {item['name']} pour {item['price']} points!")
                logger.info(f"Special item purchased successfully - User: {ctx.author}, Item: {item['name']}")

                # Special announcement for rare items
                if item['type'] == 'collectible':
                    announcement = f"🎉 {ctx.author.name} vient d'acquérir le {item['name']}!"
                    logger.info(f"Broadcasting collectible purchase announcement")
                    for guild in self.bot.guilds:
                        try:
                            channel = discord.utils.get(guild.text_channels, name='général') or guild.text_channels[0]
                            await channel.send(announcement)
                        except Exception as e:
                            logger.error(f"Failed to send announcement in guild {guild.id}: {e}")
                            continue

            # Check regular items
            elif item_id in SHOP_ITEMS:
                success, message = await self.points.buy_item(str(ctx.author.id), item_id)
                logger.info(f"Regular item purchase attempt - Success: {success}, Message: {message}")
                await ctx.send(message)

            else:
                await ctx.send("❌ Cet objet n'existe pas!")

        except Exception as e:
            logger.error(f"Error in buy command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='inventory', aliases=['inv'])
    async def inventory_command(self, ctx):
        """Show your inventory"""
        try:
            inventory = self.points.db.get_inventory(str(ctx.author.id))
            special_items = self.points.db.get_special_items(str(ctx.author.id))
            logger.info(f"Fetching inventory for {ctx.author} - Regular items: {len(inventory)}, Special items: {len(special_items)}")

            embed = discord.Embed(
                title="📦 Ton Inventaire",
                color=discord.Color.blue()
            )

            # Regular items
            if inventory:
                item_counts = {}
                for item_id in inventory:
                    if item_id in SHOP_ITEMS:
                        item_counts[item_id] = item_counts.get(item_id, 0) + 1

                for item_id, count in item_counts.items():
                    item = SHOP_ITEMS[item_id]
                    embed.add_field(
                        name=f"{item['name']} x{count}",
                        value=item['description'],
                        inline=False
                    )

            # Special items
            if special_items:
                embed.add_field(
                    name="🌟 Items Spéciaux",
                    value="Collection unique:",
                    inline=False
                )
                for item in special_items:
                    if item['item_id'] in SHOP_ITEMS_NEW:
                        special_item = SHOP_ITEMS_NEW[item['item_id']]
                        acquired_date = datetime.fromtimestamp(item['acquired_at']).strftime('%d/%m/%Y')
                        embed.add_field(
                            name=f"{special_item['name']}",
                            value=f"{special_item['description']}\nAcquis le: {acquired_date}",
                            inline=False
                        )

            if not inventory and not special_items:
                await ctx.send("📦 Ton inventaire est vide!")
                return

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in inventory command: {e}", exc_info=True)
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

    @commands.command(name='deal')
    @check_daily_limit('deal')
    async def drug_deal_command(self, ctx, amount: int = None):
        """Start a drug deal"""
        try:
            if amount is None:
                await ctx.send(f"❌ Spécifie le montant à investir! Exemple: `!deal {DRUG_DEAL_MIN_INVESTMENT}`")
                return

            # Get random narration for deal
            narration = random.choice(COMMAND_NARRATIONS['deal']).format(user=ctx.author.name)
            await ctx.send(narration)

            # Wait for tension
            await asyncio.sleep(2)

            success, message = await self.points.start_drug_deal(str(ctx.author.id), amount)
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in drug_deal command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='escape', aliases=['fuite'])
    @check_daily_limit('escape')
    async def escape_command(self, ctx):
        """Try to escape from police"""
        try:
            # Get random narration for escape
            narration = random.choice(COMMAND_NARRATIONS['escape']).format(user=ctx.author.name)
            await ctx.send(narration)

            # Wait for tension
            await asyncio.sleep(2)

            success, message = await self.points.try_escape_police(str(ctx.author.id))
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in escape command: {e}", exc_info=True)
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
                combat_msg= await ctx.send(message)
                for move in COMBAT_MOVES:
                    await combat_msg.add_reaction(move)
            else:
                await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in combat command: {e}", exc_info=True)
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
                success, message = await self.points.process_combat_move(
                    str(message.id), str(user.id), emoji
                )
                if success:
                    await message.channel.send(message)

        # Handle tribunal votes
        elif message.content.startswith("⚖️ Nouveau Procès"):
            if emoji in VOTE_REACTIONS:
                defendant = message.mentions[0] if message.mentions else None
                if defendant:
                    vote_value = emoji == "✅"
                    success, result = await self.points.vote_trial(
                        str(user.id), str(defendant.id), vote_value
                    )
                    if not success:
                        await message.remove_reaction(emoji, user)
                        await message.channel.send(result)

    @commands.command(name='prison', aliases=['status'])
    async def prison_status_command(self, ctx, member: discord.Member = None):
        """Check prison status"""
        try:
            target = member or ctx.author
            status = await self.points.get_prison_status(str(target.id))

            if not status:
                await ctx.send("🆓 Ce membre n'est pas en prison!")
                return

            embed = discord.Embed(
                title="🏢 Status Prison",
                description=f"Status de {target.name}:",
                color=discord.Color.red()
            )

            embed.add_field(name="⏳ Temps restant", value=f"{status['time_left']} secondes", inline=False)
            if status['role']:
                embed.add_field(name="👔 Rôle", value=f"{status['role']} (Bonus: {status['role_bonus']})", inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in prison_status command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='activity', aliases=['activite'])
    async def prison_activity_command(self, ctx, activity: str = None):
        """Do an activity in prison"""
        try:
            if not activity:
                activities = "\n".join([f"- `{k}`: {v['name']}" for k, v in PRISON_ACTIVITIES.items()])
                await ctx.send(f"📋 Activités disponibles:\n{activities}")
                return

            success, message = await self.points.do_prison_activity(str(ctx.author.id), activity.lower())
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in prison_activity command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='tribunal', aliases=['trial'])
    async def request_trial_command(self, ctx, *, plea: str = None):
        """Request a trial"""
        try:
            if not plea:
                await ctx.send("❌ Tu dois écrire un plaidoyer! Exemple: `!tribunal Je suis innocent, c'était de la légitime défense!`")
                return

            logger.info(f"Trial request from {ctx.author} with plea: {plea}")
            success, message = await self.points.request_trial(str(ctx.author.id), plea)

            if success:
                # Announce trial to everyone
                embed = discord.Embed(
                    title="⚖️ Nouveau Procès",
                    description=f"Un procès commence pour {ctx.author.name}!",
                    color=discord.Color.gold()
                )
                embed.add_field(name="📜 Plaidoyer", value=plea, inline=False)
                embed.add_field(name="🗳️ Vote", value="Utilisez `!vote @user oui/non` pour voter!", inline=False)
                embed.set_footer(text="Le procès dure 5 minutes!")
                await ctx.send(embed=embed)
                logger.info(f"Trial started successfully for {ctx.author}")
            else:
                await ctx.send(message)
                logger.warning(f"Trial request denied for {ctx.author}: {message}")

        except Exception as e:
            logger.error(f"Error in request_trial command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='vote')
    async def vote_trial_command(self, ctx, member: discord.Member = None, vote: str = None):
        """Vote in a trial"""
        try:
            if not member or not vote:
                await ctx.send("❌ Usage: `!vote @user oui/non`")
                return

            vote_bool = vote.lower() in ['oui', 'yes', '1', 'true']
            success, message = await self.points.vote_trial(str(ctx.author.id), str(member.id), vote_bool)
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in vote_trial command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='roulette')
    @check_daily_limit('roulette')
    async def roulette_command(self, ctx, bet: int = None):
        """Play Russian roulette with points"""
        try:
            if bet is None:
                await ctx.send(f"❌ Tu dois parier! Exemple: `!roulette {ROULETTE_MIN_BET}`")
                return

            if bet < ROULETTE_MIN_BET or bet > ROULETTE_MAX_BET:
                await ctx.send(f"❌ Le pari doit être entre {ROULETTE_MIN_BET} et {ROULETTE_MAX_BET} points!")
                return

            # Get random narration for roulette
            narration = random.choice(COMMAND_NARRATIONS['roulette']).format(user=ctx.author.name)
            await ctx.send(narration)

            # Wait for tension
            await asyncio.sleep(2)

            points = self.points.db.get_user_points(str(ctx.author.id))
            if points < bet:
                await ctx.send("❌ Tu n'as pas assez de points!")
                return

            # Check cooldown
            last_play = self.points.db.get_roulette_cooldown(str(ctx.author.id))
            now = datetime.now().timestamp()
            if now - last_play < ROULETTE_COOLDOWN:
                remaining = int(ROULETTE_COOLDOWN - (now - last_play))
                await ctx.send(f"⏳ Tu dois attendre {remaining} secondes avant de rejouer!")
                return

            # 1/6 chance to survive
            if random.randint(1, 6) == 6:
                reward = bet * ROULETTE_MULTIPLIER
                self.points.db.add_points(str(ctx.author.id), reward - bet)
                await ctx.send(f"🎯 *click* ... Tu as survécu! Tu gagnes {reward} points!")
            else:
                # Apply loss penalty
                penalty = bet * (1 + ROULETTE_LOSS_PENALTY)
                self.points.db.add_points(str(ctx.author.id), -int(penalty))
                await ctx.send(f"💥 *BANG* ... Tu es mort! Tu perds {int(penalty)} points!")

            self.points.db.set_roulette_cooldown(str(ctx.author.id))

        except Exception as e:
            logger.error(f"Error in roulette command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='race', aliases=['course'])
    @check_daily_limit('race')
    async def race_command(self, ctx, horse: str = None, bet: int = None):
        """Bet on a horse race"""
        try:
            if horse is None or bet is None:
                horses = "\n".join([f"{k}: {v['name']} (x{v['odds']})" for k, v in RACE_HORSES.items()])
                await ctx.send(f"🐎 Chevaux disponibles:\n{horses}\nUtilise `!race <numéro> <mise>`")
                return

            if horse not in RACE_HORSES:
                await ctx.send("❌ Ce cheval n'existe pas!")
                return

            if bet < RACE_MIN_BET or bet > RACE_MAX_BET:
                await ctx.send(f"❌ La mise doit être entre {RACE_MIN_BET} et {RACE_MAX_BET} points!")
                return

            points = self.points.db.get_user_points(str(ctx.author.id))
            if points < bet:
                await ctx.send("❌ Tu n'as pas assez de points!")
                return

            # Get random narration for race
            narration = random.choice(COMMAND_NARRATIONS['race']).format(user=ctx.author.name, horse=RACE_HORSES[horse]['name'])
            await ctx.send(narration)

            # Wait for tension
            await asyncio.sleep(2)

            # Place bet
            self.points.db.add_points(str(ctx.author.id), -bet)

            # Start race
            message = await ctx.send("🏁 La course commence!")

            # Simulate race
            positions = {h: 0 for h in RACE_HORSES.keys()}
            for _ in range(3):  # 3 updates
                await asyncio.sleep(2)
                for h in positions:
                    positions[h] += random.randint(1, 4)

                race_status = "\n".join([
                    f"{RACE_HORSES[h]['name']}: {'=' * min(positions[h], 10)}{'>' if positions[h] < 10 else '🏁'}"                    for h in positions
                ])
                await message.edit(content=f"🏁 Course en cours!\n{race_status}")

            # Determine winner and check for injury
            winner = max(positions.items(), key=lambda x: x[1])[0]
            selected_horse = RACE_HORSES[horse]
            injury = random.random() < selected_horse['risk']

            if horse == winner and not injury:
                winnings = int(bet * selected_horse['odds'])
                self.points.db.add_points(str(ctx.author.id), winnings)
                await ctx.send(f"🏆 {selected_horse['name']} gagne! Tu remportes {winnings} points!")
            else:
                loss_message = ""
                if injury:
                    extra_loss = int(bet * (RACE_INJURY_MULTIPLIER - 1))
                    self.points.db.add_points(str(ctx.author.id), -extra_loss)
                    loss_message = f"\n🤕 Ton cheval s'est blessé! Tu perds {extra_loss} points supplémentaires!"

                await ctx.send(f"😢 {RACE_HORSES[winner]['name']} gagne! Tu perds ton pari!{loss_message}")

        except Exception as e:
            logger.error(f"Error in race command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.Cog.listener()
    async def on_ready(self):
        """Setup prison role and start lottery draw task when bot is ready"""
        for guild in self.bot.guilds:
            await self.points.setup_prison_role(guild)

    @commands.command(name='lottery', aliases=['loto'])
    async def lottery_command(self, ctx, *numbers: int):
        """Buy a lottery ticket"""
        try:
            if not numbers or len(numbers) != 3:
                await ctx.send("❌ Tu dois choisir 3 numéros! Exemple: `!lottery 7 13 24`")
                return

            if not all(1 <= n <= 30 for n in numbers):
                await ctx.send("❌ Les numéros doivent être entre 1 et 30!")
                return

            points = self.points.db.get_user_points(str(ctx.author.id))
            if points < LOTTERY_TICKET_PRICE:
                await ctx.send(f"❌ Tu n'as pas assez de points! Un ticket coûte {LOTTERY_TICKET_PRICE} points.")
                return

            logger.info(f"Lottery ticket purchase attempt by {ctx.author} with numbers: {numbers}")
            if self.points.db.buy_lottery_ticket(str(ctx.author.id), list(numbers)):
                self.points.db.add_points(str(ctx.author.id), -LOTTERY_TICKET_PRICE)
                await ctx.send(f"🎫 Ticket acheté avec les numéros {', '.join(map(str, numbers))}!")
                logger.info(f"Lottery ticket purchased successfully by {ctx.author}")
            else:
                await ctx.send(f"❌ Tu as déjà {LOTTERY_MAX_TICKETS} tickets!")
                logger.warning(f"Lottery ticket purchase failed - max tickets reached for {ctx.author}")

        except Exception as e:
            logger.error(f"Error in lottery command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='tribunal', aliases=['trial'])
    async def request_trial_command(self, ctx, *, plea: str = None):
        """Request a trial"""
        try:
            if not plea:
                await ctx.send("❌ Tu dois écrire un plaidoyer! Exemple: `!tribunal Je suis innocent, c'était de la légitime défense!`")
                return

            logger.info(f"Trial request from {ctx.author} with plea: {plea}")
            success, message = await self.points.request_trial(str(ctx.author.id), plea)

            if success:
                # Announce trial to everyone
                embed = discord.Embed(
                    title="⚖️ Nouveau Procès",
                    description=f"Un procès commence pour {ctx.author.name}!",
                    color=discord.Color.gold()
                )
                embed.add_field(name="📜 Plaidoyer", value=plea, inline=False)
                embed.add_field(name="🗳️ Vote", value="Utilisez `!vote @user oui/non` pour voter!", inline=False)
                embed.set_footer(text="Le procès dure 5 minutes!")
                await ctx.send(embed=embed)
                logger.info(f"Trial started successfully for {ctx.author}")
            else:
                await ctx.send(message)
                logger.warning(f"Trial request denied for {ctx.author}: {message}")

        except Exception as e:
            logger.error(f"Error in request_trial command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @tasks.loop(seconds=LOTTERY_DRAW_INTERVAL)
    async def lottery_task(self):
        """Daily lottery draw"""
        try:
            # Get all tickets
            all_tickets = self.points.db.data['lottery_tickets']
            if not all_tickets:
                return

            # Draw winning numbers
            winning_numbers = sorted(random.sample(range(1, 31), 3))

            # Find winners
            winners = []
            for user_id, tickets in all_tickets.items():
                for ticket in tickets:
                    matches = len(set(ticket) & set(winning_numbers))
                    if matches >= 2:  # Need at least 2 matching numbers
                        winners.append((user_id, matches))

            # Calculate prizes
            jackpot = self.points.db.data['lottery_jackpot']
            base_prize = jackpot // (len(winners) or 1)  # Avoid division by zero

            # Announce results
            announcement = f"🎰 **Tirage du Loto !**\nNuméros gagnants : {', '.join(map(str, winning_numbers))}\n"

            if winners:
                for user_id, matches in winners:
                    try:
                        member = await self.bot.guilds[0].fetch_member(int(user_id))
                        prize = base_prize * (2 if matches == 2 else 5 if matches == 3 else 1)
                        self.points.db.add_points(user_id, prize)
                        announcement += f"\n{member.name} a trouvé {matches} numéros ! Gain : {prize} points !"
                    except:
                        continue
            else:
                announcement += "\nAucun gagnant ! Le jackpot augmente ! 💰"

            # Send announcement in all guilds
            for guild in self.bot.guilds:
                try:
                    # Try to find a general chat channel
                    channel = discord.utils.get(guild.text_channels, name='général') or \
                             discord.utils.get(guild.text_channels, name='general') or \
                             guild.text_channels[0]
                    await channel.send(announcement)
                except:
                    continue

            # Reset tickets and update jackpot
            self.points.db.clear_lottery_tickets()

        except Exception as e:
            logger.error(f"Error in lottery draw: {e}", exc_info=True)
    @commands.command(name='dice', aliases=['dés', 'des'])
    @check_daily_limit('dice')
    async def dice_command(self, ctx, target: discord.Member = None, bet: int = None):
        """Start a dice duel with another member"""
        try:
            if not target or bet is None:
                await ctx.send("❌ Usage: !dice @user <mise>")
                return

            if target.id == ctx.author.id:
                await ctx.send("❌ Tu ne peux pas jouer contre toi-même!")
                return

            if bet < DICE_MIN_BET or bet > DICE_MAX_BET:
                await ctx.send(f"❌ La mise doit être entre {DICE_MIN_BET} et {DICE_MAX_BET} points!")
                return

            # Check cooldown
            last_play = self.points.db.get_dice_cooldown(str(ctx.author.id))
            now = datetime.now().timestamp()
            if now - last_play < DICE_COOLDOWN:
                remaining = int(DICE_COOLDOWN - (now - last_play))
                await ctx.send(f"⏳ Tu dois attendre {remaining} secondes avant de rejouer!")
                return

            # Check if target has enough points
            challenger_points = self.points.db.get_user_points(str(ctx.author.id))
            target_points = self.points.db.get_user_points(str(target.id))

            if challenger_points < bet:
                await ctx.send("❌ Tu n'as pas assez de points!")
                return
            if target_points < bet:
                await ctx.send(f"❌ {target.name} n'a pas assez de points!")
                return

            # Get random narration for dice
            narration = random.choice(COMMAND_NARRATIONS['dice']).format(
                user=ctx.author.name,
                target=target.name
            )
            await ctx.send(narration)

            # Wait for tension
            await asyncio.sleep(2)

            # Roll dice
            challenger_dice = [random.randint(1, 6), random.randint(1, 6)]
            target_dice = [random.randint(1, 6), random.randint(1, 6)]

            challenger_total = sum(challenger_dice)
            target_total = sum(target_dice)

            # Check for matching dice bonus
            challenger_bonus = challenger_dice[0] == challenger_dice[1]
            target_bonus = target_dice[0] == target_dice[1]

            # Calculate final scores with bonuses
            if challenger_bonus:
                challenger_total = int(challenger_total * DICE_BONUS_MULTIPLIER)
            if target_bonus:
                target_total = int(target_total * DICE_BONUS_MULTIPLIER)

            # Create message
            message = f"🎲 **Duel de dés**\n\n"
            message += f"{ctx.author.name}: [{challenger_dice[0]}] [{challenger_dice[1]}] = {challenger_total}"
            if challenger_bonus:
                message += " (BONUS x1.5!)"
            message += f"\n{target.name}: [{target_dice[0]}] [{target_dice[1]}] = {target_total}"
            if target_bonus:
                message += " (BONUS x1.5!)"

            # Determine winner and apply streak penalties
            if challenger_total > target_total:
                # Calculate penalty for target based on losing streak
                penalty_multiplier = self.points.db.calculate_penalty_multiplier(str(target.id), 'dice')
                actual_loss = int(bet * penalty_multiplier)

                self.points.db.add_points(str(ctx.author.id), bet)
                self.points.db.add_points(str(target.id), -actual_loss)

                self.points.db.update_losing_streak(str(ctx.author.id), 'dice', True)
                self.points.db.update_losing_streak(str(target.id), 'dice', False)

                message += f"\n\n🏆 {ctx.author.name} gagne {bet} points!"
                if penalty_multiplier > 1:
                    message += f"\n😰 Malus de défaite pour {target.name}: -{actual_loss} points!"
            elif target_total > challenger_total:
                # Calculate penalty for challenger based on losing streak
                penalty_multiplier = self.points.db.calculate_penalty_multiplier(str(ctx.author.id), 'dice')
                actual_loss = int(bet * penalty_multiplier)

                self.points.db.add_points(str(target.id), bet)
                self.points.db.add_points(str(ctx.author.id), -actual_loss)

                self.points.db.update_losing_streak(str(target.id), 'dice', True)
                self.points.db.update_losing_streak(str(ctx.author.id), 'dice', False)

                message += f"\n\n🏆 {target.name} gagne {bet} points!"
                if penalty_multiplier > 1:
                    message += f"\n😰 Malus de défaite pour {ctx.author.name}: -{actual_loss} points!"
            else:
                # Tie - no points exchanged
                message += "\n\n🤝 Égalité! Personne ne gagne de points."
                # Reset both losing streaks on tie
                self.points.db.update_losing_streak(str(ctx.author.id), 'dice', True)
                self.points.db.update_losing_streak(str(target.id), 'dice', True)

            await ctx.send(message)
            self.points.db.set_dice_cooldown(str(ctx.author.id))

        except Exception as e:
            logger.error(f"Error in dice command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")