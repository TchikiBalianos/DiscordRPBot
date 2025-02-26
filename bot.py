import discord
from discord.ext import commands, tasks
import asyncio
from database import Database
from point_system import PointSystem
from twitter_handler import TwitterHandler
from commands import Commands
from config import DISCORD_TOKEN
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EngagementBot')

class EngagementBot(commands.Bot):
    def __init__(self):
        logger.debug("Initializing EngagementBot...")

        # Set up required intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        intents.guilds = True

        # Initialize bot with required settings
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )

        # Set up components
        self.db = Database()
        self.point_system = PointSystem(self.db)
        self.twitter_handler = None

        logger.info("Bot initialization complete")

    async def setup_hook(self):
        try:
            logger.debug("Starting setup_hook...")

            # Initialize Twitter handler
            self.twitter_handler = TwitterHandler()

            # Add commands
            await self.add_cog(Commands(self, self.point_system, self.twitter_handler))

            # Verify commands registration
            commands_list = [command.name for command in self.commands]
            logger.info(f"Registered commands: {commands_list}")

            if not commands_list:
                logger.error("No commands were registered!")

        except Exception as e:
            logger.error(f"Error in setup_hook: {e}")
            logger.exception("Full setup error traceback:")
            raise

    async def on_ready(self):
        logger.info(f'Logged in as {self.user.name} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guilds')

        # Verify command registration again
        logger.info(f"Available commands: {[cmd.name for cmd in self.commands]}")

        # Start background tasks
        self.save_data_loop.start()
        self.check_twitter_engagement.start()

    async def on_message(self, message):
        if message.author.bot:
            return

        try:
            # Log message details for debugging
            logger.debug(f"Message received from {message.author}: {message.content}")

            if message.content.startswith(self.command_prefix):
                logger.debug(f"Command detected: {message.content}")
                await self.process_commands(message)
                logger.debug("Command processed")
            else:
                await self.point_system.award_message_points(message.author.id)
                logger.debug("Points awarded for message")

        except Exception as e:
            logger.error(f"Error in on_message: {e}")
            logger.exception("Full traceback:")

    async def on_command_error(self, ctx, error):
        """Gestion des erreurs de commande"""
        if isinstance(error, commands.errors.CommandNotFound):
            logger.warning(f"Commande non trouvée: {ctx.message.content}")
            await ctx.send(f"Commande non trouvée. Utilisez !bothelp pour voir la liste des commandes.")
        else:
            logger.error(f"Erreur de commande: {error}")
            logger.exception("Traceback complet de l'erreur:")
            await ctx.send(f"Une erreur s'est produite lors de l'exécution de la commande.")


    @tasks.loop(minutes=5)
    async def save_data_loop(self):
        try:
            self.db.save_data()
            logger.info("Data saved successfully")
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    @tasks.loop(minutes=15)
    async def check_twitter_engagement(self):
        try:
            if not self.twitter_handler:
                logger.warning("Twitter handler not initialized")
                return

            logger.info("Starting Twitter engagement check")
            for discord_id, twitter_username in self.db.get_all_twitter_users():
                try:
                    old_stats = self.db.get_twitter_stats(discord_id)
                    new_stats = await self.twitter_handler.get_user_activity(twitter_username)

                    if new_stats:
                        await self._process_twitter_stats(discord_id, old_stats, new_stats)
                        self.db.update_twitter_stats(discord_id, new_stats)
                except Exception as e:
                    logger.error(f"Error checking Twitter for user {twitter_username}: {e}")

        except Exception as e:
            logger.error(f"Error in check_twitter_engagement: {e}")

    async def _process_twitter_stats(self, discord_id, old_stats, new_stats):
        try:
            # Calculate new interactions
            new_likes = max(0, new_stats['likes'] - old_stats['likes'])
            new_retweets = max(0, new_stats['retweets'] - old_stats['retweets'])
            new_comments = max(0, new_stats['comments'] - old_stats['comments'])

            # Award points for new interactions
            if new_likes > 0:
                await self.point_system.award_twitter_points(discord_id, 'like')
            if new_retweets > 0:
                await self.point_system.award_twitter_points(discord_id, 'retweet')
            if new_comments > 0:
                await self.point_system.award_twitter_points(discord_id, 'comment')
        except Exception as e:
            logger.error(f"Error processing Twitter stats: {e}")

    @check_twitter_engagement.before_loop
    async def before_check_twitter(self):
        await self.wait_until_ready()

    @save_data_loop.before_loop
    async def before_save_data(self):
        await self.wait_until_ready()

async def main():
    try:
        bot = EngagementBot()
        async with bot:
            await bot.start(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Error in main: {e}")
        logger.exception("Full main error traceback:")
        raise

if __name__ == "__main__":
    asyncio.run(main())