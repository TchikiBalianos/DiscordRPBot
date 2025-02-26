import discord
from discord.ext import commands
import logging

logger = logging.getLogger('EngagementBot')

class Commands(commands.Cog):
    def __init__(self, bot, point_system, twitter_handler):
        self.bot = bot
        self.points = point_system
        self.twitter = twitter_handler

        # Register commands with the bot
        self.bot.add_cog(self)
        logger.info("Commands cog initialized")
        logger.info(f"Available commands: {[cmd.name for cmd in self.__cog_commands__]}")

    @commands.command(name='bothelp', help="Show available commands and their usage")
    @commands.cooldown(1, 3, commands.BucketType.user)  # 1 use every 3 seconds per user
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
                "!bothelp": "Show this help message"
            }

            for cmd, desc in commands_list.items():
                embed.add_field(name=cmd, value=desc, inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in bothelp command: {e}")
            await ctx.send("An error occurred while displaying help.")

    @commands.command(name='points')
    @commands.cooldown(1, 3, commands.BucketType.user)  # 1 use every 3 seconds per user
    async def check_points(self, ctx):
        """Check your current points"""
        try:
            points = self.points.db.get_user_points(ctx.author.id)
            await ctx.send(f"{ctx.author.mention}, you have {points} points!")
        except Exception as e:
            logger.error(f"Error checking points: {e}")
            await ctx.send("An error occurred while checking your points.")

    @commands.command(name='leaderboard')
    @commands.cooldown(1, 5, commands.BucketType.user)  # 1 use every 5 seconds per user
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
            logger.error(f"Error showing leaderboard: {e}")
            await ctx.send("An error occurred while fetching the leaderboard.")

    @commands.command(name='rob')
    @commands.cooldown(1, 5, commands.BucketType.user)  # 1 use every 5 seconds per user
    async def rob_user(self, ctx, victim: discord.Member):
        """Try to steal points from another user"""
        if victim.id == ctx.author.id:
            await ctx.send("You can't rob yourself!")
            return

        success, message = await self.points.try_rob(ctx.author.id, victim.id)
        await ctx.send(f"{ctx.author.mention}: {message}")

    @commands.command(name='linktwitter')
    @commands.cooldown(1, 5, commands.BucketType.user)  # 1 use every 5 seconds per user
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
            logger.warning(f"Failed to link Twitter account: {e}")
        except Exception as e:
            await ctx.send(f"{ctx.author.mention}, an error occurred while linking with Twitter. Try again later.")
            logger.error(f"Error linking Twitter account: {e}")
            logger.exception("Full traceback:")

    @commands.command(name='twitterpoints')
    @commands.cooldown(1, 5, commands.BucketType.user)  # 1 use every 5 seconds per user
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
            else:
                await ctx.send(f"{ctx.author.mention}, couldn't fetch your Twitter stats at the moment.")
        except Exception as e:
            await ctx.send(f"{ctx.author.mention}, an error occurred while fetching your Twitter points.")
            logger.error(f"Error fetching Twitter points: {e}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Please wait {error.retry_after:.1f}s before using this command again.")
            return

        logger.error(f"Command error: {error}")
        await ctx.send("An error occurred while processing the command.")