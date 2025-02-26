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
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EngagementBot')

class EngagementBot(commands.Bot):
    def __init__(self):
        """Initialize bot with required intents and components"""
        logger.info("Starting bot initialization...")

        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        logger.info(f"Configured intents: {intents.value}")

        # Initialize the bot with required parameters
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )

        # Initialize components
        try:
            self.db = Database()
            self.point_system = PointSystem(self.db)
            self.twitter_handler = TwitterHandler()
            logger.info("Bot components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize bot components: {e}", exc_info=True)
            raise

    async def setup_hook(self):
        """Set up the bot and load commands"""
        try:
            from commands import Commands
            await self.add_cog(Commands(self, self.point_system, self.twitter_handler))
            logger.info("Commands cog loaded successfully")

            # Log all registered commands
            commands_list = [cmd.name for cmd in self.commands]
            logger.info(f"Registered commands: {commands_list}")
        except Exception as e:
            logger.error(f"Error in setup_hook: {e}", exc_info=True)
            raise

    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f'Bot is ready! Logged in as {self.user.name} (ID: {self.user.id})')
        logger.info(f"Connected to {len(self.guilds)} guilds")

        # Log available commands again
        commands_list = [cmd.name for cmd in self.commands]
        logger.info(f"Available commands: {commands_list}")

    async def on_message(self, message):
        """Handle incoming messages"""
        if message.author.bot:
            return

        try:
            # Log command processing
            if message.content.startswith(self.command_prefix):
                logger.info(f"Processing command: {message.content} from {message.author}")

            # Process commands
            ctx = await self.get_context(message)
            if ctx.valid:
                await self.invoke(ctx)
            else:
                await self.process_commands(message)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            logger.warning(f"Command not found: {ctx.message.content}")
            await ctx.send("Commande non trouvée. Utilisez !bothelp pour voir les commandes disponibles.")
        else:
            logger.error(f"Command error: {error}", exc_info=True)
            await ctx.send("Une erreur s'est produite lors de l'exécution de la commande.")

    async def on_error(self, event_method, *args, **kwargs):
        """Handle general errors"""
        logger.error(f"Error in {event_method}", exc_info=True)
        logger.error(f"Args: {args}")
        logger.error(f"Kwargs: {kwargs}")

if __name__ == "__main__":
    try:
        import os
        # Start the bot
        logger.info("Starting bot...")
        bot = EngagementBot()
        bot.run(os.getenv('DISCORD_TOKEN'))
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)