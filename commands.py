import discord
from discord.ext import commands
import logging
from tweepy.errors import TooManyRequests, NotFound, Unauthorized

logger = logging.getLogger('EngagementBot')

class Commands(commands.Cog):
    def __init__(self, bot, point_system, twitter_handler):
        """Initialize the Commands cog"""
        self.bot = bot
        self.points = point_system
        self.twitter = twitter_handler
        logger.info("Commands cog initialized")

    @commands.command(name='ping')
    async def ping_command(self, ctx):
        """Simple command to test if the bot is responding"""
        try:
            await ctx.send('Pong!')
            logger.info(f"Ping command executed by {ctx.author}")
        except Exception as e:
            logger.error(f"Error in ping command: {e}")
            await ctx.send("Une erreur s'est produite.")

    @commands.command(name='linktwitter')
    async def link_twitter(self, ctx, twitter_username: str = None):
        """Link Discord account to Twitter account"""
        try:
            if not twitter_username:
                await ctx.send("❌ Veuillez fournir votre nom d'utilisateur Twitter. Exemple: `!linktwitter MonCompteTwitter`")
                return

            # Clean up username
            twitter_username = twitter_username.lstrip('@').lower().strip()
            logger.info(f"Attempting to link Twitter account @{twitter_username} for user {ctx.author}")

            try:
                exists, twitter_id = await self.twitter.verify_account(twitter_username)
                logger.info(f"Verification result for @{twitter_username}: exists={exists}, id={twitter_id}")

                if exists and twitter_id:
                    # Store the link
                    self.points.db.link_twitter_account(str(ctx.author.id), twitter_username)
                    await ctx.send(f"✅ Votre compte Discord est maintenant lié à Twitter @{twitter_username}")
                else:
                    await ctx.send("❌ Ce compte Twitter n'existe pas. Vérifiez le nom d'utilisateur et réessayez.")

            except TooManyRequests:
                await ctx.send("⏳ L'API Twitter est temporairement indisponible. Veuillez réessayer dans quelques minutes.")
            except Unauthorized:
                logger.error("Twitter API authentication failed")
                await ctx.send("❌ Erreur d'authentification Twitter. Un administrateur a été notifié.")
            except Exception as e:
                logger.error(f"Error verifying Twitter account: {str(e)}", exc_info=True)
                await ctx.send("❌ Une erreur s'est produite lors de la vérification du compte Twitter.")

        except Exception as e:
            logger.error(f"Error in link_twitter command: {str(e)}", exc_info=True)
            await ctx.send("❌ Une erreur inattendue s'est produite.")

    @commands.command(name='testtwitter')
    async def test_twitter(self, ctx, twitter_username: str = None):
        """Test Twitter API connection with a username"""
        try:
            if not twitter_username:
                await ctx.send("❌ Veuillez fournir un nom d'utilisateur Twitter à tester. Exemple: `!testtwitter elonmusk`")
                return

            # Clean up username
            twitter_username = twitter_username.lstrip('@').lower().strip()
            await ctx.send(f"🔍 Test de connexion à Twitter pour le compte @{twitter_username}...")

            try:
                exists, twitter_id = await self.twitter.verify_account(twitter_username)

                if exists and twitter_id:
                    await ctx.send(f"✅ Compte Twitter trouvé! ID: {twitter_id}")
                else:
                    await ctx.send(f"❌ Le compte Twitter @{twitter_username} n'a pas été trouvé.")

            except TooManyRequests:
                await ctx.send("⏳ L'API Twitter est temporairement indisponible (rate limit). Veuillez réessayer dans quelques minutes.")
            except Unauthorized:
                await ctx.send("❌ Erreur d'authentification avec l'API Twitter. Les clés d'API doivent être vérifiées.")
            except Exception as e:
                logger.error(f"Error in Twitter API test: {str(e)}", exc_info=True)
                await ctx.send(f"❌ Erreur lors du test: {str(e)}")

        except Exception as e:
            logger.error(f"Error in test_twitter command: {str(e)}", exc_info=True)
            await ctx.send("❌ Une erreur inattendue s'est produite.")

    @commands.command(name='twitterstats')
    async def twitter_stats(self, ctx):
        """Check Twitter statistics"""
        try:
            # Get linked Twitter username
            twitter_username = self.points.db.get_twitter_username(str(ctx.author.id))
            if not twitter_username:
                await ctx.send("❌ Votre compte Discord n'est pas lié à Twitter. Utilisez `!linktwitter` pour le lier.")
                return

            # Verify account and get stats
            exists, twitter_id = await self.twitter.verify_account(twitter_username)
            if not exists:
                await ctx.send("❌ Votre compte Twitter lié n'est plus accessible.")
                return

            stats = await self.twitter.get_user_stats(twitter_id)

            embed = discord.Embed(
                title=f"Statistiques Twitter pour @{twitter_username}",
                color=discord.Color.blue()
            )
            embed.add_field(name="👍 Likes", value=str(stats.get('likes', 0)), inline=True)
            embed.add_field(name="🔄 Dernière mise à jour", value="À l'instant", inline=True)
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in twitter_stats command: {str(e)}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite lors de la récupération des statistiques.")

    @commands.command(name='bothelp')
    async def bothelp_command(self, ctx):
        """Show all available commands"""
        try:
            embed = discord.Embed(
                title="Commandes du Bot",
                description="Voici toutes les commandes disponibles:",
                color=discord.Color.blue()
            )

            commands_list = {
                "!ping": "Vérifier si le bot répond",
                "!testtwitter": "Tester la connexion à l'API Twitter",
                "!linktwitter": "Lier votre compte Twitter",
                "!twitterstats": "Voir vos statistiques Twitter",
                "!bothelp": "Afficher ce message d'aide"
            }

            for cmd, desc in commands_list.items():
                embed.add_field(name=cmd, value=desc, inline=False)

            await ctx.send(embed=embed)
            logger.info(f"Help command executed by {ctx.author}")
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await ctx.send("Une erreur s'est produite lors de l'affichage de l'aide.")