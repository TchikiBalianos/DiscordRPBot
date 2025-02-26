import discord
from discord.ext import commands
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
        logger.info("Initializing EngagementBot...")

        # Set up required intents
        intents = discord.Intents.all()

        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )

        # Initialize components
        self.db = Database()
        self.point_system = PointSystem(self.db)
        self.twitter_handler = None

    async def setup_hook(self):
        try:
            # Add commands cog
            await self.add_cog(Commands(self, self.point_system, self.twitter_handler))
            logger.info(f"Registered commands: {[command.name for command in self.commands]}")
        except Exception as e:
            logger.error(f"Error in setup_hook: {e}", exc_info=True)
            raise

    async def on_ready(self):
        logger.info(f'Bot is ready! Logged in as {self.user.name} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guilds')
        logger.info(f'Available commands: {[cmd.name for cmd in self.commands]}')

    async def on_message(self, message):
        if message.author.bot:
            return

        try:
            if message.content.startswith(self.command_prefix):
                logger.info(f"Received command: {message.content} from {message.author}")
                await self.process_commands(message)
                logger.info("Command processed")
            else:
                await self.point_system.award_message_points(message.author.id)
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        # Verify token
        if not DISCORD_TOKEN:
            raise ValueError("Discord token is missing!")

        logger.info("Starting bot...")
        bot = EngagementBot()
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)