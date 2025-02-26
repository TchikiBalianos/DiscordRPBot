import os
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

        # Configure intents with all permissions needed
        intents = discord.Intents.all()  # Enable all intents for full functionality
        logger.info(f"Configured intents: {intents.value}")

        # Initialize the bot with required parameters
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None  # We'll use our custom help command
        )

        # Initialize components
        try:
            self.db = Database()
            self.point_system = PointSystem(self.db, self)  # Pass bot instance to PointSystem
            self.twitter_handler = TwitterHandler()
            logger.info("Bot components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize bot components: {e}", exc_info=True)
            raise

    async def setup_hook(self):
        """Set up the bot and load commands"""
        try:
            # Import Commands here to avoid circular imports
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

        # Initialize prison role in all guilds
        for guild in self.guilds:
            await self.point_system.setup_prison_role(guild)
            logger.info(f"Prison role setup complete for guild: {guild.name}")

        # Log available commands
        commands_list = [cmd.name for cmd in self.commands]
        logger.info(f"Available commands: {commands_list}")

    async def on_message(self, message):
        """Handle incoming messages"""
        if message.author.bot:
            return

        try:
            # Add detailed message logging
            if message.content.startswith(self.command_prefix):
                logger.info(f"Received command message: {message.content}")
                logger.info(f"From user: {message.author} ({message.author.id})")
                logger.info(f"In channel: {message.channel.name} ({message.channel.id})")
                logger.info(f"Guild: {message.guild.name} ({message.guild.id})")

            # Process commands
            await self.process_commands(message)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await message.channel.send("❌ Une erreur s'est produite lors du traitement de la commande.")

    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            logger.warning(f"Command not found: {ctx.message.content}")
            await ctx.send("Commande non trouvée. Utilisez !bothelp pour voir les commandes disponibles.")
        else:
            logger.error(f"Command error: {error}", exc_info=True)
            await ctx.send("Une erreur s'est produite lors de l'exécution de la commande.")

if __name__ == "__main__":
    try:
        # Start the bot
        logger.info("Starting bot...")
        bot = EngagementBot()
        bot.run(os.getenv('DISCORD_TOKEN'))
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)