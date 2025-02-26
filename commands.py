import discord
from discord.ext import commands
import logging
from discord.errors import TooManyRequests, Unauthorized

logger = logging.getLogger('EngagementBot')

class Commands(commands.Cog):
    def __init__(self, bot, point_system, twitter_handler):
        self.bot = bot
        self.points = point_system
        self.twitter = twitter_handler

    @commands.command(name='ping')
    async def ping_command(self, ctx):
        """Simple command to test if the bot is responding"""
        await ctx.send('Pong!')

    @commands.command(name='linktwitter')
    async def link_twitter(self, ctx, twitter_username: str = None):
        """Link your Discord account to your Twitter account"""
        if not twitter_username:
            await ctx.send("❌ Veuillez fournir votre nom d'utilisateur Twitter. Exemple: `!linktwitter MonCompteTwitter`")
            return

        try:
            # Remove @ if present
            twitter_username = twitter_username.lstrip('@')
            logger.info(f"Attempting to link Twitter account {twitter_username} for {ctx.author.id}")

            # Verify if Twitter account exists
            try:
                exists, twitter_id = await self.twitter.verify_account(twitter_username)

                if exists:
                    # Link the account
                    self.points.db.link_twitter_account(str(ctx.author.id), twitter_username)
                    await ctx.send(f"✅ Votre compte Discord est maintenant lié à Twitter @{twitter_username}")
                else:
                    await ctx.send("❌ Ce compte Twitter n'existe pas. Vérifiez que le nom d'utilisateur est correct.")

            except TooManyRequests:
                await ctx.send("⏳ L'API Twitter est temporairement indisponible en raison des limites de taux. Veuillez réessayer dans quelques minutes.")
            except Unauthorized:
                logger.error("Twitter API authentication failed")
                await ctx.send("❌ Erreur d'authentification avec Twitter. Un administrateur a été notifié.")
            except Exception as e:
                logger.error(f"Error in account verification: {str(e)}")
                await ctx.send("❌ Une erreur s'est produite lors de la vérification du compte Twitter. Veuillez réessayer plus tard.")

        except Exception as e:
            logger.error(f"Error in link_twitter command: {str(e)}")
            await ctx.send("❌ Une erreur inattendue s'est produite. Veuillez réessayer plus tard.")

    @commands.command(name='twitterstats')
    async def twitter_stats(self, ctx):
        """Check your Twitter statistics"""
        try:
            twitter_username = self.points.db.get_twitter_username(str(ctx.author.id))
            if not twitter_username:
                await ctx.send("❌ Votre compte Discord n'est pas lié à Twitter. Utilisez !linktwitter pour le lier.")
                return

            exists, twitter_id = await self.twitter.verify_account(twitter_username)
            if not exists:
                await ctx.send("❌ Votre compte Twitter lié n'est plus accessible.")
                return

            stats = await self.twitter.get_user_stats(twitter_id)
            if 'error' in stats:
                if 'rate limit' in stats['error'].lower():
                    await ctx.send("❌ Le nombre de requêtes Twitter est trop élevé actuellement. Veuillez réessayer dans quelques minutes.")
                else:
                    await ctx.send(f"❌ Erreur lors de la récupération des stats: {stats['error']}")
                return

            embed = discord.Embed(
                title=f"Statistiques Twitter pour @{twitter_username}",
                color=discord.Color.blue()
            )
            embed.add_field(name="👍 Likes", value=str(stats['likes']), inline=True)
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Erreur dans la commande twitterstats: {e}")
            await ctx.send("❌ Une erreur s'est produite lors de la récupération de vos stats Twitter.")

    @commands.command(name='bothelp')
    async def bothelp_command(self, ctx):
        """Show all available commands"""
        embed = discord.Embed(
            title="Commandes du Bot",
            description="Voici toutes les commandes disponibles:",
            color=discord.Color.blue()
        )

        commands_list = {
            "!ping": "Vérifier si le bot répond",
            "!linktwitter": "Lier votre compte Twitter",
            "!twitterstats": "Voir vos statistiques Twitter",
            "!bothelp": "Afficher ce message d'aide"
        }

        for cmd, desc in commands_list.items():
            embed.add_field(name=cmd, value=desc, inline=False)

        await ctx.send(embed=embed)