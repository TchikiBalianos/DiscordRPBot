import discord
from discord.ext import commands
from datetime import datetime
import logging
import tweepy

logger = logging.getLogger('EngagementBot')

class Commands(commands.Cog):
    def __init__(self, bot, point_system, twitter_handler):
        self.bot = bot
        self.points = point_system
        self.twitter = twitter_handler
        logger.info("Commands cog initialized")

    @commands.command(name='testtwitter')
    async def test_twitter(self, ctx, twitter_username: str = None):
        """Test Twitter API connection and data retrieval"""
        logger.debug(f"Commande testtwitter reçue de {ctx.author}")

        if twitter_username is None:
            await ctx.send("❌ Veuillez spécifier un nom d'utilisateur Twitter. Exemple: !testtwitter X")
            return

        try:
            # Remove @ if present
            twitter_username = twitter_username.lstrip('@')
            logger.info(f"Test de l'API Twitter pour l'utilisateur: {twitter_username}")

            # Test user retrieval
            user_response = self.twitter.client.get_user(username=twitter_username)
            if user_response and user_response.get('data'):
                await ctx.send(f"✅ Utilisateur Twitter trouvé: @{user_response['data']['username']} (ID: {user_response['data']['id']})")
                logger.info(f"Utilisateur Twitter trouvé: {user_response['data']}")

                # Test tweets retrieval
                tweets_response = self.twitter.client.get_users_tweets(
                    user_response['data']['id'],
                    max_results=10,
                    tweet_fields=['public_metrics']
                )

                if tweets_response and tweets_response.get('data'):
                    tweet_count = len(tweets_response['data'])
                    await ctx.send(f"✅ {tweet_count} tweets récupérés")
                    if tweet_count > 0:
                        metrics = tweets_response['data'][0]['public_metrics']
                        logger.info(f"Métriques du premier tweet: {metrics}")
                        await ctx.send(f"Exemple de métriques: {metrics}")
                else:
                    await ctx.send("❌ Aucun tweet trouvé pour cet utilisateur")
            else:
                await ctx.send("❌ Utilisateur Twitter non trouvé")

        except Exception as e:
            logger.error(f"Erreur dans la commande testtwitter: {e}")
            logger.exception("Traceback complet:")
            await ctx.send(f"❌ Erreur lors du test de l'API Twitter: {str(e)}")

    @commands.command(name='bothelp')
    async def bothelp_command(self, ctx):
        """Show available commands and their usage"""
        logger.debug(f"Commande bothelp reçue de {ctx.author}")
        try:
            embed = discord.Embed(
                title="Commandes du Bot",
                description="Voici toutes les commandes disponibles :",
                color=discord.Color.blue()
            )

            commands_list = {
                "!points": "Voir vos points actuels",
                "!leaderboard": "Voir le top 10 des utilisateurs",
                "!rob @user": "Essayer de voler des points à un autre utilisateur",
                "!linktwitter @username": "Lier votre compte Twitter",
                "!twitterpoints": "Voir vos points d'engagement Twitter",
                "!bothelp": "Afficher ce message d'aide",
                "!testtwitter @username": "Tester la connexion à l'API Twitter"
            }

            for cmd, desc in commands_list.items():
                embed.add_field(name=cmd, value=desc, inline=False)

            await ctx.send(embed=embed)
            logger.debug("Message d'aide envoyé avec succès")
        except Exception as e:
            logger.error(f"Erreur dans la commande bothelp: {e}")
            logger.exception("Traceback complet:")
            await ctx.send("Une erreur s'est produite lors de l'affichage de l'aide.")

    @commands.command(name='points')
    async def check_points(self, ctx):
        """Check your current points"""
        try:
            points = self.points.db.get_user_points(ctx.author.id)
            await ctx.send(f"{ctx.author.mention}, you have {points} points!")
        except Exception as e:
            logger.error(f"Error checking points: {e}")
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
            logger.error(f"Error showing leaderboard: {e}")
            await ctx.send("An error occurred while fetching the leaderboard.")

    @commands.command(name='rob')
    async def rob_user(self, ctx, victim: discord.Member):
        """Try to steal points from another user"""
        logger.info(f"Rob command received from {ctx.author} targeting {victim}")
        if victim.id == ctx.author.id:
            await ctx.send("You can't rob yourself!")
            return

        success, message = await self.points.try_rob(ctx.author.id, victim.id)
        await ctx.send(f"{ctx.author.mention}: {message}")

    @commands.command(name='linktwitter')
    async def link_twitter(self, ctx, twitter_username: str):
        """Link your Discord account to your Twitter username"""
        logger.info(f"Link Twitter command received from {ctx.author} for {twitter_username}")
        # Remove @ if present
        twitter_username = twitter_username.lstrip('@')

        try:
            # Verify if the Twitter account exists
            activity = await self.twitter.get_user_activity(twitter_username)
            if activity is None:
                await ctx.send(f"{ctx.author.mention}, ce compte Twitter n'existe pas ou n'est pas accessible.")
                return

            # Link the accounts
            self.points.db.link_twitter_account(ctx.author.id, twitter_username)
            await ctx.send(f"{ctx.author.mention}, votre compte Discord est maintenant lié à Twitter @{twitter_username}!")
            logger.info(f"Successfully linked Twitter account {twitter_username} to Discord user {ctx.author}")

        except ValueError as e:
            await ctx.send(f"{ctx.author.mention}, {str(e)}")
            logger.warning(f"Failed to link Twitter account: {e}")
        except Exception as e:
            await ctx.send(f"{ctx.author.mention}, une erreur est survenue lors de la liaison avec Twitter. Réessayez plus tard.")
            logger.error(f"Error linking Twitter account: {e}")
            logger.exception("Full traceback:")

    @commands.command(name='twitterpoints')
    async def twitter_points(self, ctx):
        """Check your Twitter engagement points"""
        logger.info(f"Twitter points command received from {ctx.author}")
        twitter_username = self.points.db.get_twitter_username(ctx.author.id)
        if not twitter_username:
            await ctx.send(f"{ctx.author.mention}, vous devez d'abord lier votre compte Twitter avec !linktwitter @votrecompte")
            return

        try:
            activity = await self.twitter.get_user_activity(twitter_username)
            if activity:
                embed = discord.Embed(
                    title="Points d'engagement Twitter",
                    description=f"Statistiques pour @{twitter_username}",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Likes", value=f"{activity['likes']} likes", inline=True)
                embed.add_field(name="Retweets", value=f"{activity['retweets']} retweets", inline=True)
                embed.add_field(name="Commentaires", value=f"{activity['comments']} commentaires", inline=True)
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"{ctx.author.mention}, impossible de récupérer vos statistiques Twitter pour le moment.")
        except Exception as e:
            await ctx.send(f"{ctx.author.mention}, une erreur est survenue lors de la récupération de vos points Twitter.")
            logger.error(f"Error fetching Twitter points: {e}")