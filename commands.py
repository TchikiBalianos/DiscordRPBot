import discord
from discord.ext import commands
from datetime import datetime

class Commands(commands.Cog):
    def __init__(self, bot, point_system, twitter_handler):
        self.bot = bot
        self.points = point_system
        self.twitter = twitter_handler

    @commands.command(name='points')
    async def check_points(self, ctx):
        """Check your current points"""
        points = self.points.db.get_user_points(ctx.author.id)
        await ctx.send(f"{ctx.author.mention}, you have {points} points!")

    @commands.command(name='leaderboard')
    async def show_leaderboard(self, ctx):
        """Display the points leaderboard"""
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

    @commands.command(name='rob')
    async def rob_user(self, ctx, victim: discord.Member):
        """Try to steal points from another user"""
        if victim.id == ctx.author.id:
            await ctx.send("You can't rob yourself!")
            return

        success, message = await self.points.try_rob(ctx.author.id, victim.id)
        await ctx.send(f"{ctx.author.mention}: {message}")

    @commands.command(name='bothelp')
    async def bothelp_command(self, ctx):
        """Show available commands and their usage"""
        embed = discord.Embed(
            title="Bot Commands",
            description="Here are all available commands:",
            color=discord.Color.blue()
        )

        commands_list = {
            "!points": "Check your current points",
            "!leaderboard": "View the top 10 users",
            "!rob @user": "Try to steal points from another user",
            "!bothelp": "Show this help message"
        }

        for cmd, desc in commands_list.items():
            embed.add_field(name=cmd, value=desc, inline=False)

        await ctx.send(embed=embed)