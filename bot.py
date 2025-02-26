import discord
from discord.ext import commands
import logging
from database import Database
from point_system import PointSystem

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EngagementBot')

class EngagementBot(commands.Bot):
    def __init__(self):
        logger.info("Starting bot initialization...")

        # Enable all intents
        intents = discord.Intents.all()
        logger.debug(f"Intents configured: {intents.value}")

        super().__init__(command_prefix='!', intents=intents)
        self.command_prefix = '!'

        # Initialize components
        self.db = Database()
        self.point_system = PointSystem(self.db)
        logger.info("Bot initialized with all intents")

        # Add basic commands
        @self.command(name='ping')
        async def ping(ctx):
            logger.info(f"Ping command received from {ctx.author}")
            await ctx.send('Pong!')

        @self.command(name='help')
        async def help(ctx):
            logger.info(f"Help command received from {ctx.author}")
            help_text = (
                "📋 **Commandes disponibles:**\n"
                "`!ping` - Test si le bot répond\n"
                "`!points` - Voir vos points\n"
                "`!rob @user` - Voler des points\n"
                "`!help` - Affiche cette aide"
            )
            await ctx.send(help_text)

        @self.command(name='points')
        async def points(ctx):
            logger.info(f"Points command received from {ctx.author}")
            points = self.point_system.db.get_user_points(ctx.author.id)
            await ctx.send(f"{ctx.author.mention}, vous avez {points} points!")

        @self.command(name='rob')
        async def rob(ctx, victim: discord.Member):
            logger.info(f"Rob command received from {ctx.author} targeting {victim}")
            if victim.id == ctx.author.id:
                await ctx.send("Vous ne pouvez pas vous voler vous-même!")
                return
            success, message = await self.point_system.try_rob(ctx.author.id, victim.id)
            await ctx.send(f"{ctx.author.mention}: {message}")

        logger.info(f"Commands registered: {[cmd.name for cmd in self.commands]}")

    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f'Bot is ready! Logged in as {self.user.name} (ID: {self.user.id})')
        for guild in self.guilds:
            logger.info(f'Connected to guild: {guild.name} (ID: {guild.id})')
            logger.info(f'Bot permissions: {guild.me.guild_permissions}')
            # Log each permission individually for clarity
            for perm, value in guild.me.guild_permissions:
                logger.info(f'Permission {perm}: {value}')
            logger.info(f'Bot roles: {[role.name for role in guild.me.roles]}')

    async def on_message(self, message):
        """Called when a message is received"""
        if message.author.bot:
            logger.debug(f"Ignoring bot message from {message.author}")
            return

        logger.debug(f'Message received: "{message.content}" from {message.author} in {message.channel}')
        logger.debug(f'Channel permissions: {message.channel.permissions_for(message.guild.me)}')

        try:
            await self.process_commands(message)
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

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