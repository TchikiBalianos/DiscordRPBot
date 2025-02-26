import discord
from discord.ext import commands
import logging

logger = logging.getLogger('EngagementBot')

class Commands(commands.Cog):
    def __init__(self, bot, point_system, twitter_handler):
        """Initialize the Commands cog"""
        super().__init__()
        self.bot = bot
        self.points = point_system
        self.twitter = twitter_handler
        logger.info("Commands cog initialized")

    @commands.command(name='ping')
    async def ping_command(self, ctx):
        """Simple ping command to test bot responsiveness"""
        try:
            logger.info(f"Ping command received from {ctx.author} in channel {ctx.channel.name}")
            await ctx.send("Pong! ✅")
            logger.info(f"Ping command executed successfully for {ctx.author}")
        except Exception as e:
            logger.error(f"Error in ping command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='help', aliases=['commands', 'bothelp'])
    async def help_command(self, ctx):
        """Show all available commands"""
        try:
            embed = discord.Embed(
                title="🦹 Commandes du Bot",
                description="Voici les commandes disponibles:",
                color=discord.Color.blue()
            )

            # Basic commands
            embed.add_field(
                name="📌 Commandes de base",
                value="!ping - Tester si le bot répond\n!help - Voir cette aide",
                inline=False
            )

            await ctx.send(embed=embed)
            logger.info(f"Help command executed by {ctx.author}")
        except Exception as e:
            logger.error(f"Error in help command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")