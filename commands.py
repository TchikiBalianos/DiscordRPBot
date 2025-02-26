from functools import wraps
import discord
from discord.ext import commands
import logging
from tweepy.errors import TooManyRequests, NotFound, Unauthorized
from datetime import datetime, timedelta

logger = logging.getLogger('EngagementBot')

def is_staff():
    """Check if the user has staff role or is an administrator"""
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        return any(role.name.lower() in ['staff', 'modo', 'admin'] for role in ctx.author.roles)
    return commands.check(predicate)

SHOP_ITEMS = {
    "lockpick": {"name": "Lockpick", "price": 50, "description": "Increases heist success rate by 10%"},
    "getaway_car": {"name": "Getaway Car", "price": 200, "description": "Increases escape success rate by 20%"},
    "burner_phone": {"name": "Burner Phone", "price": 100, "description": "Reduces chance of being caught during drug deals by 15%"}
}

DRUG_DEAL_MIN_INVESTMENT = 100

COMBAT_MOVES = ["👊", "🦵", "🛡️"]
VOTE_REACTIONS = ["✅", "❌"]
PRISON_ACTIVITIES = { #Example data, needs to be defined elsewhere in the project
    'clean': {'name': 'Nettoyer les cellules', 'points': 5},
    'cook': {'name': 'Préparer les repas', 'points': 10},
    'gardening': {'name': 'Entretenir le jardin', 'points': 8}
}

class Commands(commands.Cog):
    def __init__(self, bot, point_system, twitter_handler):
        """Initialize the Commands cog"""
        self.bot = bot
        self.points = point_system
        self.twitter = twitter_handler
        logger.info("Commands cog initialized")

    @commands.Cog.listener()
    async def on_ready(self):
        """Setup prison role when bot is ready"""
        for guild in self.bot.guilds:
            await self.points.setup_prison_role(guild)

    @commands.command(name='addpoints')
    @is_staff()
    async def add_points(self, ctx, member: discord.Member = None, amount: int = None):
        """[STAFF] Add points to a member"""
        try:
            if not member or amount is None:
                await ctx.send("❌ Usage: !addpoints @user <montant>")
                return

            if amount <= 0:
                await ctx.send("❌ Le montant doit être positif!")
                return

            self.points.db.add_points(member.id, amount)
            await ctx.send(f"✅ {amount} points ajoutés à {member.name}!")
            logger.info(f"Staff {ctx.author} added {amount} points to {member}")

        except Exception as e:
            logger.error(f"Error in add_points command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='removepoints')
    @is_staff()
    async def remove_points(self, ctx, member: discord.Member = None, amount: int = None):
        """[STAFF] Remove points from a member"""
        try:
            if not member or amount is None:
                await ctx.send("❌ Usage: !removepoints @user <montant>")
                return

            if amount <= 0:
                await ctx.send("❌ Le montant doit être positif!")
                return

            current_points = self.points.db.get_user_points(member.id)
            if current_points < amount:
                amount = current_points

            self.points.db.add_points(member.id, -amount)
            await ctx.send(f"✅ {amount} points retirés à {member.name}!")
            logger.info(f"Staff {ctx.author} removed {amount} points from {member}")

        except Exception as e:
            logger.error(f"Error in remove_points command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='freeprison')
    @is_staff()
    async def free_prison(self, ctx, member: discord.Member = None):
        """[STAFF] Free a member from prison"""
        try:
            if not member:
                await ctx.send("❌ Usage: !freeprison @user")
                return

            prison_time = self.points.db.get_prison_time(member.id)
            if prison_time > datetime.now().timestamp():
                self.points.db.set_prison_time(member.id, 0)
                await ctx.send(f"🔓 {member.name} a été libéré de prison!")
                logger.info(f"Staff {ctx.author} freed {member} from prison")
            else:
                await ctx.send(f"❌ {member.name} n'est pas en prison!")

        except Exception as e:
            logger.error(f"Error in free_prison command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

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

    @commands.command(name='rob')
    async def rob_command(self, ctx, target: discord.Member = None):
        """Rob another member"""
        try:
            if not target:
                await ctx.send("❌ Mentionne la personne que tu veux voler! Exemple: `!rob @user`")
                return

            if target.id == ctx.author.id:
                await ctx.send("❌ Tu ne peux pas te voler toi-même!")
                return

            success, message = await self.points.try_rob(ctx.author.id, target.id)
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in rob command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='revenge', aliases=['vengeance'])
    async def revenge_command(self, ctx):
        """Get revenge on your last robber"""
        try:
            success, message = await self.points.try_revenge(ctx.author.id)
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in revenge command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='work', aliases=['travail'])
    async def work_command(self, ctx):
        """Do your daily work"""
        try:
            success, message = await self.points.daily_work(ctx.author.id)
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in work command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='points', aliases=['money', 'balance'])
    async def points_command(self, ctx, member: discord.Member = None):
        """Check your points or another member's points"""
        try:
            target = member or ctx.author
            points = self.points.db.get_user_points(target.id)

            if target == ctx.author:
                await ctx.send(f"💰 Tu as **{points}** points!")
            else:
                await ctx.send(f"💰 {target.name} a **{points}** points!")

        except Exception as e:
            logger.error(f"Error in points command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='leaderboard', aliases=['classement', 'top'])
    async def leaderboard_command(self, ctx):
        """Show the monthly leaderboard"""
        try:
            leaderboard = await self.points.get_monthly_leaderboard()

            embed = discord.Embed(
                title="🏆 Classement Mensuel des Thugz",
                description="Les plus grands gangsters du mois:",
                color=discord.Color.gold()
            )

            for i, (user_id, data) in enumerate(leaderboard[:10], 1):
                try:
                    member = await ctx.guild.fetch_member(int(user_id))
                    name = member.name if member else f"Membre {user_id}"
                    embed.add_field(
                        name=f"{i}. {name}",
                        value=f"💰 {data['points']} points",
                        inline=False
                    )
                except:
                    continue

            current_month = datetime.now().strftime('%B %Y')
            embed.set_footer(text=f"Classement pour {current_month}")
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='help', aliases=['commands', 'bothelp'])
    async def help_command(self, ctx):
        """Show all available commands"""
        try:
            embed = discord.Embed(
                title="🦹 Commandes du Thugz Bot",
                description="Voici toutes les commandes disponibles:",
                color=discord.Color.blue()
            )

        commands_list = {
            "💰 Économie": {
                "!work": "Travailler pour gagner des points (1x par jour)",
                "!points": "Voir ton solde de points",
                "!leaderboard": "Voir le classement mensuel",
                "!shop": "Voir les objets disponibles à la vente",
                "!inventory": "Voir ton inventaire"
            },
            "🦹 Actions": {
                "!rob @user": "Tenter de voler quelqu'un",
                "!revenge": "Se venger de son dernier voleur",
                "!heist": "Commencer un braquage",
                "!joinheist": "Rejoindre un braquage",
                "!deal <montant>": "Faire un trafic de drogue",
                "!escape": "Tenter de fuir la police",
                "!combat @user <mise>": "Engager un combat avec un autre membre"
            },
            "🏢 Prison": {
                "!prison": "Voir ton statut en prison",
                "!activity": "Voir les activités disponibles",
                "!activity <nom>": "Faire une activité en prison",
                "!tribunal <plaidoyer>": "Demander un procès (500 points)",
                "!vote @user oui/non": "Voter pour un procès"
            },
            "🐦 Twitter": {
                "!linktwitter": "Lier ton compte Twitter",
                "!twitterstats": "Voir tes stats Twitter"
            }
        }

        # Add staff commands if user is staff
        is_staff = ctx.author.guild_permissions.administrator or \
                  any(role.name.lower() in ['staff', 'modo', 'admin'] for role in ctx.author.roles)

        if is_staff:
            commands_list["⚡ Staff"] = {
                "!addpoints @user montant": "Ajouter des points à un membre",
                "!removepoints @user montant": "Retirer des points à un membre",
                "!freeprison @user": "Libérer un membre de prison"
            }

        for category, cmds in commands_list.items():
            embed.add_field(
                name=category,
                value="\n".join([f"`{cmd}`: {desc}" for cmd, desc in cmds.items()]),
                inline=False
            )

        await ctx.send(embed=embed)
        logger.info(f"Help command executed by {ctx.author}")

        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await ctx.send("❌ Une erreur s'est produite.")

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

    @commands.command(name='shop', aliases=['boutique'])
    async def shop_command(self, ctx):
        """Show the shop items"""
        try:
            embed = discord.Embed(
                title="🏪 Boutique du Crime",
                description="Utilise !buy <item> pour acheter un objet",
                color=discord.Color.gold()
            )

            for item_id, item in SHOP_ITEMS.items():
                embed.add_field(
                    name=f"{item['name']} - {item['price']} points",
                    value=f"{item['description']}\nID: `{item_id}`",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in shop command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='buy', aliases=['acheter'])
    async def buy_command(self, ctx, item_id: str = None):
        """Buy an item from the shop"""
        try:
            if not item_id:
                await ctx.send("❌ Spécifie l'objet à acheter! Exemple: `!buy lockpick`")
                return

            success, message = await self.points.buy_item(str(ctx.author.id), item_id.lower())
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in buy command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='inventory', aliases=['inv'])
    async def inventory_command(self, ctx):
        """Show your inventory"""
        try:
            inventory = self.points.db.get_inventory(str(ctx.author.id))

            if not inventory:
                await ctx.send("📦 Ton inventaire est vide!")
                return

            embed = discord.Embed(
                title="📦 Ton Inventaire",
                color=discord.Color.blue()
            )

            item_counts = {}
            for item_id in inventory:
                if item_id in SHOP_ITEMS:
                    item_counts[item_id] = item_counts.get(item_id, 0) + 1

            for item_id, count in item_counts.items():
                item = SHOP_ITEMS[item_id]
                embed.add_field(
                    name=f"{item['name']} x{count}",
                    value=item['description'],
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in inventory command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")
            
    @commands.command(name='heist', aliases=['braquage'])
    async def heist_command(self, ctx):
        """Start a heist"""
        try:
            success, message = await self.points.start_heist(str(ctx.author.id))
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in heist command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='joinheist', aliases=['rejoindre'])
    async def join_heist_command(self, ctx):
        """Join an active heist"""
        try:
            success, message = await self.points.join_heist(str(ctx.author.id))
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in join_heist command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='deal')
    async def drug_deal_command(self, ctx, amount: int = None):
        """Start a drug deal"""
        try:
            if amount is None:
                await ctx.send(f"❌ Spécifie le montant à investir! Exemple: `!deal {DRUG_DEAL_MIN_INVESTMENT}`")
                return

            success, message = await self.points.start_drug_deal(str(ctx.author.id), amount)
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in drug_deal command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='escape', aliases=['fuite'])
    async def escape_command(self, ctx):
        """Try to escape from police"""
        try:
            success, message = await self.points.try_escape_police(str(ctx.author.id))
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in escape command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='combat', aliases=['fight', 'duel'])
    async def combat_command(self, ctx, target: discord.Member = None, bet: int = None):
        """Start a combat with another member"""
        try:
            if not target or not bet:
                await ctx.send("❌ Usage: !combat @user <mise>")
                return

            if target.id == ctx.author.id:
                await ctx.send("❌ Tu ne peux pas te battre contre toi-même!")
                return

            success, message = await self.points.start_combat(str(ctx.author.id), str(target.id), bet)
            if success:
                combat_msg = await ctx.send(message)
                for move in COMBAT_MOVES:
                    await combat_msg.add_reaction(move)
            else:
                await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in combat command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle reactions for combat and voting"""
        if user.bot:
            return

        message = reaction.message
        emoji = str(reaction.emoji)

        # Handle combat moves
        if message.content.startswith("⚔️ Combat"):
            if emoji in COMBAT_MOVES:
                success, message = await self.points.process_combat_move(
                    str(message.id), str(user.id), emoji
                )
                if success:
                    await message.channel.send(message)

        # Handle tribunal votes
        elif message.content.startswith("⚖️ Nouveau Procès"):
            if emoji in VOTE_REACTIONS:
                defendant = message.mentions[0] if message.mentions else None
                if defendant:
                    vote_value = emoji == "✅"
                    success, result = await self.points.vote_trial(
                        str(user.id), str(defendant.id), vote_value
                    )
                    if not success:
                        await message.remove_reaction(emoji, user)
                        await message.channel.send(result)

    @commands.command(name='prison', aliases=['status'])
    async def prison_status_command(self, ctx, member: discord.Member = None):
        """Check prison status"""
        try:
            target = member or ctx.author
            status = await self.points.get_prison_status(str(target.id))

            if not status:
                await ctx.send("🆓 Ce membre n'est pas en prison!")
                return

            embed = discord.Embed(
                title="🏢 Status Prison",
                description=f"Status de {target.name}:",
                color=discord.Color.red()
            )

            embed.add_field(name="⏳ Temps restant", value=f"{status['time_left']} secondes", inline=False)
            if status['role']:
                embed.add_field(name="👔 Rôle", value=f"{status['role']} (Bonus: {status['role_bonus']})", inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in prison_status command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='activity', aliases=['activite'])
    async def prison_activity_command(self, ctx, activity: str = None):
        """Do an activity in prison"""
        try:
            if not activity:
                activities = "\n".join([f"- `{k}`: {v['name']}" for k, v in PRISON_ACTIVITIES.items()])
                await ctx.send(f"📋 Activités disponibles:\n{activities}")
                return

            success, message = await self.points.do_prison_activity(str(ctx.author.id), activity.lower())
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in prison_activity command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='tribunal', aliases=['trial'])
    async def request_trial_command(self, ctx, *, plea: str = None):
        """Request a trial"""
        try:
            if not plea:
                await ctx.send("❌ Tu dois écrire un plaidoyer! Exemple: `!tribunal Je suis innocent, c'était de la légitime défense!`")
                return

            success, message = await self.points.request_trial(str(ctx.author.id), plea)
            if success:
                # Announce trial to everyone
                embed = discord.Embed(
                    title="⚖️ Nouveau Procès",
                    description=f"Un procès commence pour {ctx.author.name}!",
                    color=discord.Color.gold()
                )
                embed.add_field(name="📜 Plaidoyer", value=plea, inline=False)
                embed.add_field(name="🗳️ Vote", value="Utilisez `!vote @user oui/non` pour voter!", inline=False)
                embed.set_footer(text="Le procès dure 5 minutes!")
                await ctx.send(embed=embed)
            else:
                await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in request_trial command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='vote')
    async def vote_trial_command(self, ctx, member: discord.Member = None, vote: str = None):
        """Vote in a trial"""
        try:
            if not member or not vote:
                await ctx.send("❌ Usage: `!vote @user oui/non`")
                return

            vote_bool = vote.lower() in ['oui', 'yes', '1', 'true']
            success, message = await self.points.vote_trial(str(ctx.author.id), str(member.id), vote_bool)
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in vote_trial command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")