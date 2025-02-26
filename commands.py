import discord
from discord.ext import commands
import logging

logger = logging.getLogger('EngagementBot')

class Commands(commands.Cog):
    def __init__(self, bot, point_system, twitter_handler):
        self.bot = bot
        self.points = point_system
        self.twitter = twitter_handler
        super().__init__()
        logger.info("Commands cog initialized")

    @commands.command(name='ping')
    async def ping_command(self, ctx):
        """Simple command to test if the bot is responding"""
        logger.info(f"Ping command received from {ctx.author}")
        await ctx.send('Pong!')

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

    @commands.command(name='linktwitter')
    async def link_twitter(self, ctx, twitter_username: str = None):
        """Link your Discord account to your Twitter account"""
        if not twitter_username:
            await ctx.send("❌ Please provide your Twitter username. Example: `!linktwitter TwitterDev`")
            return

        exists, twitter_id = await self.twitter.verify_account(twitter_username)
        if not exists:
            await ctx.send("❌ This Twitter account doesn't exist.")
            return

        try:
            self.points.db.link_twitter_account(str(ctx.author.id), twitter_username)
            await ctx.send(f"✅ Your Discord account is now linked to Twitter @{twitter_username}")
        except Exception as e:
            logger.error(f"Error linking Twitter: {e}")
            await ctx.send("❌ An error occurred while linking your Twitter account.")

    @commands.command(name='twitterstats')
    async def twitter_stats(self, ctx, days: int = 7):
        """Check your Twitter statistics for the last X days"""
        try:
            logger.info(f"Twitter stats command received from {ctx.author}")

            if days < 1 or days > 30:
                await ctx.send("❌ Please specify a number of days between 1 and 30.")
                return

            twitter_username = self.points.db.get_twitter_username(str(ctx.author.id))
            logger.info(f"Found Twitter username: {twitter_username}")

            if not twitter_username:
                await ctx.send("❌ Your Discord account is not linked to Twitter. Use !linktwitter to link it.")
                return

            # First message to show we're working
            status_message = await ctx.send("🔄 Fetching your Twitter stats...")

            # Verify account
            logger.info(f"Verifying Twitter account: {twitter_username}")
            exists, twitter_id = await self.twitter.verify_account(twitter_username)

            if not exists or not twitter_id:
                await status_message.edit(content="❌ Could not verify your Twitter account. Please try linking it again with !linktwitter")
                return

            # Get stats
            logger.info(f"Getting stats for Twitter ID: {twitter_id}")
            stats = await self.twitter.get_user_stats(twitter_id, days)

            if 'error' in stats:
                await status_message.edit(content=f"❌ Error getting Twitter stats: {stats['error']}")
                return

            # Create embed message
            embed = discord.Embed(
                title=f"Twitter Stats for @{twitter_username}",
                description=f"Last {days} days:",
                color=discord.Color.blue()
            )

            # Activity stats
            embed.add_field(
                name="📊 Activity",
                value=f"Total Tweets: {stats['tweets']}\nEngagement Rate: {stats['engagement_rate']}%",
                inline=False
            )

            # Engagement stats with emoji
            embed.add_field(name="👍 Likes", value=str(stats['likes']), inline=True)
            embed.add_field(name="🔄 Retweets", value=str(stats['retweets']), inline=True)
            embed.add_field(name="💬 Replies", value=str(stats['replies']), inline=True)

            await status_message.edit(content=None, embed=embed)
            logger.info(f"Successfully sent Twitter stats for {twitter_username}")

        except Exception as e:
            logger.error(f"Error in twitter_stats command: {e}", exc_info=True)
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
                "!leaderboard": "View top 10 users",
                "!rob @user": "Try to steal points from another user",
                "!linktwitter": "Link your Twitter account",
                "!twitterstats [days]": "View your Twitter stats (default: 7 days)",
                "!bothelp": "Show this help message"
            }

            for cmd, desc in commands_list.items():
                embed.add_field(name=cmd, value=desc, inline=False)

            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in bothelp command: {e}", exc_info=True)
            await ctx.send("An error occurred while displaying help.")