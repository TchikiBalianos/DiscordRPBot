import discord
from discord.ext import commands
import logging

logger = logging.getLogger('EngagementBot')

class Commands(commands.Cog):
    def __init__(self, bot):
        """Initialize the Commands cog"""
        super().__init__()
        self.bot = bot
        self.points = bot.point_system
        self.twitter = bot.twitter_handler
        logger.info("Commands cog initialized")

async def setup(bot):
    """Setup function required for loading the cog as an extension"""
    await bot.add_cog(Commands(bot))
    logger.info("Commands cog loaded")
    logger.info(f"Available commands: {[cmd.name for cmd in bot.commands]}")

    @commands.command(name='bothelp')
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def bothelp_command(self, ctx):
        """Show available commands and their usage"""
        try:
            embed = discord.Embed(
                title="Bot Commands",
                description="Here are all available commands:",
                color=discord.Color.blue()
            )

            commands_list = {
                "!points": "Check your current points",
                "!leaderboard": "View top 10 users",
                "!rob @user": "Try to steal points from another user",
                "!linktwitter @username": "Link your Twitter account",
                "!twitterpoints": "Check your Twitter engagement points",
                "!bothelp": "Show this help message",
                "!testtwitter @username": "Test Twitter API connection"
            }

            for cmd, desc in commands_list.items():
                embed.add_field(name=cmd, value=desc, inline=False)

            await ctx.send(embed=embed)
            logger.info(f"Help command executed by {ctx.author}")
        except Exception as e:
            logger.error(f"Error in bothelp command: {e}", exc_info=True)
            await ctx.send("An error occurred while displaying help.")

    @commands.command(name='points')
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def check_points(self, ctx):
        """Check your current points"""
        try:
            points = self.points.db.get_user_points(ctx.author.id)
            await ctx.send(f"{ctx.author.mention}, you have {points} points!")
            logger.info(f"Points command executed by {ctx.author}")
        except Exception as e:
            logger.error(f"Error checking points: {e}", exc_info=True)
            await ctx.send("An error occurred while checking your points.")

    @commands.command(name='leaderboard')
    @commands.cooldown(1, 5, commands.BucketType.user)
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
            logger.info(f"Leaderboard command executed by {ctx.author}")
        except Exception as e:
            logger.error(f"Error showing leaderboard: {e}", exc_info=True)
            await ctx.send("An error occurred while fetching the leaderboard.")

    @commands.command(name='rob')
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def rob_user(self, ctx, victim: discord.Member):
        """Try to steal points from another user"""
        if victim.id == ctx.author.id:
            await ctx.send("You can't rob yourself!")
            return

        success, message = await self.points.try_rob(ctx.author.id, victim.id)
        await ctx.send(f"{ctx.author.mention}: {message}")
        logger.info(f"Rob command executed by {ctx.author} targeting {victim}")

    @commands.command(name='linktwitter')
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def link_twitter(self, ctx, twitter_username: str):
        """Link your Discord account to your Twitter username"""
        logger.info(f"Link Twitter command received from {ctx.author} for {twitter_username}")
        # Remove @ if present
        twitter_username = twitter_username.lstrip('@')

        try:
            # Verify if the Twitter account exists
            activity = await self.twitter.get_user_activity(twitter_username)
            if activity is None:
                await ctx.send(f"{ctx.author.mention}, this Twitter account doesn't exist or is not accessible.")
                return

            # Link the accounts
            self.points.db.link_twitter_account(ctx.author.id, twitter_username)
            await ctx.send(f"{ctx.author.mention}, your Discord account is now linked to Twitter @{twitter_username}!")
            logger.info(f"Successfully linked Twitter account {twitter_username} to Discord user {ctx.author}")

        except ValueError as e:
            await ctx.send(f"{ctx.author.mention}, {str(e)}")
            logger.warning(f"Failed to link Twitter account: {e}", exc_info=True)
        except Exception as e:
            await ctx.send(f"{ctx.author.mention}, an error occurred while linking with Twitter. Try again later.")
            logger.error(f"Error linking Twitter account: {e}", exc_info=True)

    @commands.command(name='twitterpoints')
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def twitter_points(self, ctx):
        """Check your Twitter engagement points"""
        logger.info(f"Twitter points command received from {ctx.author}")
        twitter_username = self.points.db.get_twitter_username(ctx.author.id)
        if not twitter_username:
            await ctx.send(f"{ctx.author.mention}, you need to link your Twitter account first with !linktwitter @youraccount")
            return

        try:
            activity = await self.twitter.get_user_activity(twitter_username)
            if activity:
                embed = discord.Embed(
                    title="Twitter Engagement Points",
                    description=f"Stats for @{twitter_username}",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Likes", value=f"{activity['likes']} likes", inline=True)
                embed.add_field(name="Retweets", value=f"{activity['retweets']} retweets", inline=True)
                embed.add_field(name="Comments", value=f"{activity['comments']} comments", inline=True)
                await ctx.send(embed=embed)
                logger.info(f"Twitter points command executed by {ctx.author}")
            else:
                await ctx.send(f"{ctx.author.mention}, couldn't fetch your Twitter stats at the moment.")
        except Exception as e:
            await ctx.send(f"{ctx.author.mention}, an error occurred while fetching your Twitter points.")
            logger.error(f"Error fetching Twitter points: {e}", exc_info=True)

    @commands.command(name='testtwitter')
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def test_twitter(self, ctx, twitter_username: str = None):
        """Test Twitter API connection and data retrieval"""
        logger.info(f"Test Twitter command received from {ctx.author}")

        if twitter_username is None:
            await ctx.send("❌ Please specify a Twitter username. Example: !testtwitter X")
            return

        try:
            # Remove @ if present
            twitter_username = twitter_username.lstrip('@')
            await ctx.send(f"🔍 Testing Twitter API for user @{twitter_username}...")

            # Test user retrieval
            user_response = self.twitter.client.get_user(username=twitter_username)

            if not user_response or not user_response.get('data'):
                await ctx.send("❌ Twitter user not found")
                return

            user_data = user_response['data']
            await ctx.send(f"✅ Twitter user found: @{user_data['username']}")

            # Get tweets with metrics
            tweets = self.twitter.client.get_users_tweets(
                user_data['id'],
                max_results=5,
                tweet_fields=['public_metrics']
            )

            if not tweets or not tweets.get('data'):
                await ctx.send("ℹ️ No recent tweets found")
                return

            # Show detailed metrics
            total_metrics = {'like_count': 0, 'retweet_count': 0, 'reply_count': 0}
            for tweet in tweets['data']:
                metrics = tweet.get('public_metrics', {})
                for key in total_metrics:
                    total_metrics[key] += metrics.get(key, 0)

            await ctx.send(
                f"📊 Last 5 tweets metrics:\n"
                f"👍 Likes: {total_metrics['like_count']}\n"
                f"🔄 Retweets: {total_metrics['retweet_count']}\n"
                f"💬 Replies: {total_metrics['reply_count']}"
            )
            logger.info(f"Test Twitter command executed by {ctx.author} for @{twitter_username}")

        except Exception as e:
            logger.error(f"Error in testtwitter command: {e}", exc_info=True)
            error_msg = (
                "❌ Twitter API error. This could be due to:\n"
                "• Rate limiting (wait a few minutes)\n"
                "• API access issues\n"
                "• Network connection problems"
            )
            await ctx.send(error_msg)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Please wait {error.retry_after:.1f}s before using this command again.")
            return

        logger.error(f"Command error: {error}")
        await ctx.send("An error occurred while processing the command.")