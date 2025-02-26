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
    def __init__(self):
        """Initialize bot with required intents"""
        intents = discord.Intents.all()

        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )

        self.db = Database()
        self.point_system = PointSystem(self.db, self)
        self.twitter_handler = TwitterHandler()

        # Register ping command directly in the bot class
        @self.command(name='ping')
        async def ping(ctx):
            try:
                logger.info(f"Ping command received from {ctx.author} in {ctx.guild.name}")
                await ctx.send("Pong! ✅")
                logger.info("Ping command executed successfully")
            except Exception as e:
                logger.error(f"Error in ping command: {e}", exc_info=True)
                await ctx.send("❌ Une erreur s'est produite.")

    async def setup_hook(self):
        """Load other commands from the Commands cog"""
        try:
            from commands import Commands
            await self.add_cog(Commands(self, self.point_system, self.twitter_handler))
            logger.info("Commands cog loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Commands cog: {e}", exc_info=True)

    async def on_ready(self):
        """Called when the bot is ready"""
        try:
            logger.info(f'Bot is ready! Logged in as {self.user.name} (ID: {self.user.id})')
            logger.info(f"Connected to {len(self.guilds)} guilds")
            logger.info(f"Available commands: {[c.name for c in self.commands]}")
        except Exception as e:
            logger.error(f"Error in on_ready: {e}", exc_info=True)

    async def on_message(self, message):
        """Handle messages"""
        if message.author.bot:
            return

        try:
            if message.content.startswith(self.command_prefix):
                logger.info(f"Received command: '{message.content}' from {message.author}")

            await self.process_commands(message)
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
        bot.run(os.getenv('DISCORD_TOKEN'))
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)