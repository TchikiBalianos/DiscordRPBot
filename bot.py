import os
import discord
from discord.ext import commands
import logging
from database import Database
from point_system import PointSystem
from twitter_handler import TwitterHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EngagementBot')

class EngagementBot(commands.Bot):
    """Initialize bot with required intents"""
    def __init__(self):
        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True
        intents.guilds = True
        intents.guild_messages = True
        logger.info(f"Configured intents: {intents.value}")

        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )

        # Initialize components
        self.db = Database()
        self.point_system = PointSystem(self.db, self)
        self.twitter_handler = TwitterHandler()

    async def setup_hook(self):
        """Load commands"""
        try:
            logger.info("Loading Commands cog...")
            from commands import Commands
            commands_cog = Commands(self, self.point_system, self.twitter_handler)
            await self.add_cog(commands_cog)
            logger.info(f"Cog commands: {[c.name for c in commands_cog.get_commands()]}")

            # Log all commands after loading the cog
            logger.info("Commands cog loaded successfully")
            all_commands = sorted([c.name for c in self.commands])
            logger.info(f"Available commands: {all_commands}")
            logger.info(f"Total number of commands: {len(all_commands)}")
        except Exception as e:
            logger.error(f"Failed to load Commands cog: {e}", exc_info=True)
            raise

    async def on_ready(self):
        """Called when the bot is ready"""
        try:
            logger.info(f'Bot is ready! Logged in as {self.user.name} (ID: {self.user.id})')

            # Log guild information
            for guild in self.guilds:
                logger.info(f"Connected to guild: {guild.name} (ID: {guild.id})")
                me = guild.me
                logger.info(f"Bot permissions in {guild.name}: {me.guild_permissions.value}")

            # Log available commands again after bot is ready
            all_commands = sorted([c.name for c in self.commands])
            logger.info(f"Commands available after ready: {all_commands}")
            logger.info(f"Total commands: {len(all_commands)}")
        except Exception as e:
            logger.error(f"Error in on_ready: {e}", exc_info=True)

    async def on_message(self, message):
        """Handle messages"""
        if message.author.bot:
            return

        try:
            # Log message details for debugging
            logger.info(f"Message received: '{message.content}' from {message.author} ({message.author.id})")

            if message.content.startswith(self.command_prefix):
                logger.info(f"Command detected: '{message.content}' from {message.author}")
                # Process the command
                await self.process_commands(message)
                logger.info(f"Command processed: '{message.content}'")

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await message.channel.send("❌ Une erreur s'est produite.")

    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        try:
            if isinstance(error, commands.CommandNotFound):
                logger.warning(f"Command not found: {ctx.message.content}")
                await ctx.send("❌ Commande non trouvée. Utilisez !help pour voir les commandes disponibles.")
            else:
                logger.error(f"Command error: {str(error)}", exc_info=True)
                await ctx.send("❌ Une erreur s'est produite.")
        except Exception as e:
            logger.error(f"Error in error handler: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        logger.info("Starting bot...")
        bot = EngagementBot()
        token = os.getenv('DISCORD_TOKEN')
        if not token:
            raise ValueError("DISCORD_TOKEN not found in environment variables")
        bot.run(token)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)