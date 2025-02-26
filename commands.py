import discord
from discord.ext import commands
import logging
import tweepy

logger = logging.getLogger('EngagementBot')

class Commands(commands.Cog):
    def __init__(self, bot, point_system, twitter_handler):
        self.bot = bot
        self.points = point_system
        self.twitter = twitter_handler
        logger.info("Commands cog initialized")

    @commands.command(name='ping')
    async def ping_command(self, ctx):
        """Simple command to test if the bot is responding"""
        await ctx.send('Pong!')

    @commands.command(name='points')
    async def check_points(self, ctx):
        """Check your current points"""
        try:
            points = self.points.db.get_user_points(ctx.author.id)
            await ctx.send(f"{ctx.author.mention}, you have {points} points!")
        except Exception as e:
            logger.error(f"Error checking points: {e}")
            await ctx.send("An error occurred while checking your points.")

    @commands.command(name='linktwitter')
    async def link_twitter(self, ctx, twitter_username: str = None):
        """Link your Discord account to your Twitter account"""
        if not twitter_username:
            await ctx.send("❌ Please provide your Twitter username. Example: `!linktwitter TwitterDev`")
            return

        try:
            # Send initial status message
            status_message = await ctx.send("🔄 Verifying Twitter account...")

            exists, twitter_id = await self.twitter.verify_account(twitter_username)
            if not exists:
                await status_message.edit(content="❌ This Twitter account doesn't exist.")
                return

            self.points.db.link_twitter_account(str(ctx.author.id), twitter_username)
            await status_message.edit(content=f"✅ Your Discord account is now linked to Twitter @{twitter_username}")

        except Exception as e:
            logger.error(f"Error linking Twitter: {e}")
            await ctx.send("❌ An error occurred while linking your Twitter account.")

    @commands.command(name='twitterstats')
    async def twitter_stats(self, ctx):
        """Check your Twitter statistics"""
        try:
            # Initial status message
            status_message = await ctx.send("🔄 Fetching your Twitter stats...")

            # Get Twitter username
            twitter_username = self.points.db.get_twitter_username(str(ctx.author.id))
            if not twitter_username:
                await status_message.edit(content="❌ Your Discord account is not linked to Twitter. Use !linktwitter to link it.")
                return

            # Verify account
            exists, twitter_id = await self.twitter.verify_account(twitter_username)
            if not exists:
                await status_message.edit(content="❌ Your linked Twitter account could not be verified.")
                return

            # Get stats
            stats = await self.twitter.get_user_stats(twitter_id)
            if 'error' in stats:
                await status_message.edit(content=f"❌ Error getting Twitter stats: {stats['error']}")
                return

            # Create and send embed
            embed = discord.Embed(
                title=f"Twitter Stats for @{twitter_username}",
                color=discord.Color.blue()
            )

            embed.add_field(name="👍 Likes", value=str(stats['likes']), inline=True)
            await status_message.edit(content=None, embed=embed)

        except Exception as e:
            logger.error(f"Error in twitter_stats command: {e}")
            await ctx.send("❌ An error occurred while fetching Twitter stats.")

    @commands.command(name='bothelp')
    async def bothelp_command(self, ctx):
        """Show available commands and their usage"""
        try:
            embed = discord.Embed(
                title="Bot Commands",
                description="Here are all available commands:",
                color=discord.Color.blue()
            )

            commands_list = {
                "!ping": "Test if bot is responding",
                "!points": "Check your current points",
                "!linktwitter": "Link your Twitter account",
                "!twitterstats": "View your Twitter stats",
                "!bothelp": "Show this help message"
            }

            for cmd, desc in commands_list.items():
                embed.add_field(name=cmd, value=desc, inline=False)

            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in bothelp command: {e}")
            await ctx.send("An error occurred while displaying help.")