import discord
from discord.ext import commands
import logging

logger = logging.getLogger('EngagementBot')

class Commands(commands.Cog):
    def __init__(self, bot, point_system, twitter_handler):
        super().__init__()
        self.bot = bot
        self.points = point_system
        self.twitter = twitter_handler
        logger.info("Commands cog initialized")
        logger.info(f"Available commands: {[cmd.name for cmd in self.__cog_commands__]}")

    @commands.command(name='ping')
    async def ping_command(self, ctx):
        """Simple command to test if the bot is responding"""
        logger.info(f"Ping command received from {ctx.author}")
        try:
            await ctx.send('Pong!')
            logger.info("Ping command executed successfully")
        except Exception as e:
            logger.error(f"Error in ping command: {e}", exc_info=True)
            await ctx.send("An error occurred.")

    @commands.command(name='bothelp')
    async def bothelp_command(self, ctx):
        """Show available commands and their usage"""
        try:
            logger.info(f"Help command received from {ctx.author}")
            embed = discord.Embed(
                title="Bot Commands",
                description="Here are all available commands:",
                color=discord.Color.blue()
            )

            commands_list = {
                "!ping": "Test if bot is responding",
                "!points": "Check your current points",
                "!leaderboard": "View top 10 users",
                "!rob @user": "Try to steal points from another user",
                "!bothelp": "Show this help message"
            }

            for cmd, desc in commands_list.items():
                embed.add_field(name=cmd, value=desc, inline=False)

            await ctx.send(embed=embed)
            logger.info("Help command executed successfully")
        except Exception as e:
            logger.error(f"Error in bothelp command: {e}", exc_info=True)
            await ctx.send("An error occurred while displaying help.")

    @commands.command(name='points')
    async def check_points(self, ctx):
        """Check your current points"""
        try:
            points = self.points.db.get_user_points(ctx.author.id)
            await ctx.send(f"{ctx.author.mention}, you have {points} points!")
        except Exception as e:
            logger.error(f"Error checking points: {e}", exc_info=True)
            await ctx.send("An error occurred while checking your points.")

    @commands.command(name='leaderboard')
    async def show_leaderboard(self, ctx):
        """Display the points leaderboard"""
        try:
            leaderboard = self.points.db.get_leaderboard()
            embed = discord.Embed(title="Points Leaderboard", color=discord.Color.gold())

            for i, (user_id, data) in enumerate(leaderboard[:10], 1):
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    embed.add_field(
                        name=f"{i}. {user.name}",
                        value=f"{data['points']} points",
                        inline=False
                    )
                except:
                    continue

            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error showing leaderboard: {e}", exc_info=True)
            await ctx.send("An error occurred while fetching the leaderboard.")

    @commands.command(name='rob')
    async def rob_user(self, ctx, victim: discord.Member):
        """Try to steal points from another user"""
        try:
            if victim.id == ctx.author.id:
                await ctx.send("You can't rob yourself!")
                return

            success, message = await self.points.try_rob(ctx.author.id, victim.id)
            await ctx.send(f"{ctx.author.mention}: {message}")
        except Exception as e:
            logger.error(f"Error in rob command: {e}", exc_info=True)
            await ctx.send("An error occurred while attempting to rob.")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            logger.warning(f"Command not found: {ctx.message.content}")
            await ctx.send(f"Command not found. Use !bothelp to see available commands.")
        else:
            logger.error(f"Command error: {error}", exc_info=True)
            await ctx.send("An error occurred while processing the command.")