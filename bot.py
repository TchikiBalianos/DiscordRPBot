import discord
from discord.ext import commands
import logging
from database import Database
from point_system import PointSystem
from twitter_handler import TwitterHandler
from datetime import datetime
from config import POINTS_TWITTER_LIKE

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EngagementBot')

class CommandsCog(commands.Cog):
    def __init__(self, bot, point_system, twitter_handler):
        self.bot = bot
        self.points = point_system
        self.twitter = twitter_handler
        logger.info("Commands cog initialized")

    @commands.command(name='ping')
    async def ping(self, ctx):
        """Test if bot is responding"""
        logger.info(f"Ping command received from {ctx.author}")
        await ctx.send('Pong!')

    @commands.command(name='help')
    async def help(self, ctx):
        """Show help message"""
        logger.info(f"Help command received from {ctx.author}")
        help_text = (
            "📋 **Commandes disponibles:**\n"
            "`!ping` - Test si le bot répond\n"
            "`!points` - Voir vos points\n"
            "`!rob @user` - Voler des points\n"
            "`!linktwitter @username` - Lier votre compte Twitter\n"
            "`!twitterstats` - Voir vos statistiques Twitter\n"
            "`!help` - Affiche cette aide"
        )
        await ctx.send(help_text)

    @commands.command(name='linktwitter')
    async def link_twitter(self, ctx, twitter_username: str):
        """Link your Discord account to your Twitter account"""
        try:
            # Remove @ if present
            twitter_username = twitter_username.lstrip('@')

            await ctx.send(f"🔄 Tentative de liaison avec le compte Twitter @{twitter_username}...")

            # Verify that the Twitter account exists
            logger.info(f"Attempting to get user activity for {twitter_username}")
            user_info = await self.twitter.get_user_activity(twitter_username)
            logger.info(f"Received user info: {user_info}")

            if user_info is None:
                await ctx.send("❌ Ce compte Twitter n'existe pas ou n'est pas accessible.")
                return
            elif 'error' in user_info:
                if user_info['error'] == 'rate_limit':
                    await ctx.send(f"⚠️ {user_info['message']}")
                elif user_info['error'] == 'auth':
                    await ctx.send(f"⚠️ {user_info['message']}")
                elif user_info['error'] == 'not_found':
                    await ctx.send(f"❌ {user_info['message']}")
                else:
                    await ctx.send(f"⚠️ {user_info['message']}")
                return

            # Store the link in database
            logger.info(f"Storing Twitter link in database for user {ctx.author.id}")
            self.points.db.link_twitter_account(ctx.author.id, twitter_username)
            await ctx.send(f"✅ Votre compte Discord est maintenant lié à Twitter @{twitter_username}")
            logger.info(f"Twitter account @{twitter_username} linked to Discord user {ctx.author}")

            # Try to get initial stats
            initial_stats = await self.twitter.get_user_activity(twitter_username)
            if initial_stats and 'error' not in initial_stats:
                self.points.db.update_twitter_stats(ctx.author.id, initial_stats)
                logger.info(f"Initial Twitter stats stored for {ctx.author}")

        except Exception as e:
            logger.error(f"Error linking Twitter account: {e}", exc_info=True)
            await ctx.send(f"❌ Une erreur s'est produite lors de la liaison du compte Twitter: {str(e)}")

    @commands.command(name='twitterstats')
    async def twitter_stats(self, ctx):
        """Show your Twitter engagement statistics for the current month"""
        logger.info(f"Twitter stats command received from {ctx.author}")
        try:
            # Get linked Twitter username
            twitter_username = self.points.db.get_twitter_username(ctx.author.id)
            logger.info(f"Retrieved Twitter username for {ctx.author.id}: {twitter_username}")

            if not twitter_username:
                await ctx.send("❌ Vous n'avez pas encore lié votre compte Twitter. Utilisez `!linktwitter @username`")
                return

            await ctx.send(f"🔍 Récupération des statistiques pour @{twitter_username}...")

            # Get current Twitter stats
            logger.info(f"Fetching Twitter stats for @{twitter_username}")
            current_stats = await self.twitter.get_user_activity(twitter_username)
            logger.info(f"Received current stats: {current_stats}")

            if current_stats is None:
                await ctx.send("❌ Impossible de récupérer les statistiques Twitter.")
                return
            elif 'error' in current_stats:
                await ctx.send(f"⚠️ {current_stats['message']}")
                return

            # Get previous stats from database (will handle monthly reset)
            previous_stats = self.points.db.get_twitter_stats(ctx.author.id)
            logger.info(f"Previous stats from database: {previous_stats}")
            current_month = datetime.now().strftime('%B %Y')

            try:
                # Create embed
                embed = discord.Embed(
                    title=f"Statistiques Twitter pour @{twitter_username}",
                    description=f"📅 Mois en cours : {current_month}",
                    color=discord.Color.blue()
                )

                # Add fields
                likes = current_stats.get('likes', 0)
                embed.add_field(name="👍 Likes", value=str(likes), inline=True)

                last_reset = previous_stats.get('last_reset', datetime.now().timestamp())
                reset_date = datetime.fromtimestamp(last_reset).strftime('%d/%m/%Y')
                embed.add_field(name="🔄 Dernier reset", value=reset_date, inline=True)

                # Calculate and display points if earned
                prev_likes = previous_stats.get('likes', 0)
                if likes > prev_likes:
                    points_earned = (likes - prev_likes) * POINTS_TWITTER_LIKE
                    logger.info(f"Points earned: {points_earned}")
                    if points_earned > 0:
                        embed.add_field(
                            name="✨ Points gagnés",
                            value=f"+{points_earned} points depuis la dernière vérification!",
                            inline=False
                        )

                    # Update stats and points in database
                    self.points.db.update_twitter_stats(ctx.author.id, {'likes': likes})
                    self.points.db.add_points(ctx.author.id, points_earned)

                # Send the embed
                await ctx.send(embed=embed)
                logger.info("Successfully sent Twitter stats embed")

            except Exception as e:
                logger.error(f"Error creating or sending embed: {e}", exc_info=True)
                # Fallback to simple message if embed fails
                await ctx.send(f"""
📊 Statistiques Twitter pour @{twitter_username}
📅 Mois: {current_month}
👍 Likes: {current_stats.get('likes', 0)}
🔄 Dernier reset: {datetime.fromtimestamp(previous_stats.get('last_reset', datetime.now().timestamp())).strftime('%d/%m/%Y')}
""")

        except Exception as e:
            logger.error(f"Error in twitter_stats command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite lors de la récupération des statistiques Twitter.")

    @commands.command(name='points')
    async def points(self, ctx):
        """Check your points"""
        logger.info(f"Points command received from {ctx.author}")
        points = self.points.db.get_user_points(ctx.author.id)
        await ctx.send(f"{ctx.author.mention}, vous avez {points} points!")

    @commands.command(name='rob')
    async def rob(self, ctx, victim: discord.Member):
        """Rob points from another user"""
        logger.info(f"Rob command received from {ctx.author} targeting {victim}")
        if victim.id == ctx.author.id:
            await ctx.send("Vous ne pouvez pas vous voler vous-même!")
            return
        success, message = await self.points.try_rob(ctx.author.id, victim.id)
        await ctx.send(f"{ctx.author.mention}: {message}")

class EngagementBot(commands.Bot):
    def __init__(self):
        logger.info("Starting bot initialization...")
        intents = discord.Intents.all()
        logger.debug(f"Intents configured: {intents.value}")

        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )

        # Initialize components
        self.db = Database()
        self.point_system = PointSystem(self.db)
        self.twitter_handler = TwitterHandler()
        logger.info("Bot components initialized")

    async def setup_hook(self):
        """This is called when the bot starts up"""
        try:
            await self.add_cog(CommandsCog(self, self.point_system, self.twitter_handler))
            logger.info(f"Commands cog loaded with commands: {[cmd.name for cmd in self.commands]}")
        except Exception as e:
            logger.error(f"Error in setup_hook: {e}", exc_info=True)
            raise

    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f'Bot is ready! Logged in as {self.user.name} (ID: {self.user.id})')
        for guild in self.guilds:
            logger.info(f'Connected to guild: {guild.name} (ID: {guild.id})')
            logger.info(f'Bot permissions: {guild.me.guild_permissions}')
            for perm, value in guild.me.guild_permissions:
                logger.info(f'Permission {perm}: {value}')

    async def on_message(self, message):
        """Called when a message is received"""
        if message.author.bot:
            logger.debug(f"Ignoring bot message from {message.author}")
            return

        logger.debug(f'Message received: "{message.content}" from {message.author} in {message.channel}')

        try:
            await self.process_commands(message)
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    # Add more detailed error logging for command processing
    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            logger.warning(f"Command not found: {ctx.message.content}")
            await ctx.send(f"Commande non trouvée. Utilisez !help pour voir les commandes disponibles.")
        else:
            logger.error(f"Command error: {error}", exc_info=True)
            await ctx.send("Une erreur s'est produite lors du traitement de la commande.")
            # Log the full context of the error
            logger.error(f"Error context - Channel: {ctx.channel}, Author: {ctx.author}, Message: {ctx.message.content}")

    async def on_error(self, event_method, *args, **kwargs):
        """Handle general errors"""
        logger.error(f"Error in {event_method}", exc_info=True)
        logger.error(f"Args: {args}")
        logger.error(f"Kwargs: {kwargs}")


if __name__ == "__main__":
    try:
        import os
        token = os.getenv('DISCORD_TOKEN')
        if not token:
            raise ValueError("DISCORD_TOKEN is missing!")

        logger.info("Starting bot...")
        bot = EngagementBot()
        bot.run(token)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)