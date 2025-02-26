import discord
from discord.ext import commands, tasks
import asyncio
from database import Database
from point_system import PointSystem
from twitter_handler import TwitterHandler
from commands import Commands
from config import DISCORD_TOKEN
import logging

# Configure le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EngagementBot')

class EngagementBot(commands.Bot):
    def __init__(self):
        # Explicitly declare all required intents
        intents = discord.Intents.all()  # Enable all intents for full functionality
        intents.message_content = True  # For reading message content
        intents.members = True         # For tracking member joins/leaves
        intents.voice_states = True    # For tracking voice activity
        intents.guilds = True          # For server information
        intents.presences = True       # For user status updates

        super().__init__(command_prefix='!', intents=intents)

        self.db = Database()
        self.point_system = PointSystem(self.db)
        self.twitter_handler = TwitterHandler()
        logger.info("Bot initialized with all components")

    async def setup_hook(self):
        # Add commands
        try:
            await self.add_cog(Commands(self, self.point_system, self.twitter_handler))
            logger.info("Commands cog added successfully")
            logger.info(f"Registered commands: {[command.name for command in self.commands]}")
        except Exception as e:
            logger.error(f"Error adding commands cog: {e}")
            raise

    async def on_ready(self):
        logger.info(f'Logged in as {self.user.name} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guilds:')
        for guild in self.guilds:
            logger.info(f'- {guild.name} (ID: {guild.id})')
        logger.info('------')
        # Start background tasks after bot is ready
        self.save_data_loop.start()
        self.check_twitter_engagement.start()
        logger.info("Background tasks started")

    async def on_message(self, message):
        if message.author.bot:
            return

        logger.info(f"Message received from {message.author}: {message.content}")
        try:
            # Log if the message is a command
            if message.content.startswith(self.command_prefix):
                logger.info(f"Command detected: {message.content}")

            # Process the message for points
            await self.point_system.award_message_points(message.author.id)
            # Process commands
            await self.process_commands(message)
            logger.info(f"Processed message from {message.author}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.exception("Full traceback:")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.errors.CommandNotFound):
            await ctx.send(f"Commande non trouvée. Utilisez !bothelp pour voir la liste des commandes.")
        else:
            logger.error(f"Command error: {error}")
            logger.exception("Full command error traceback:")
            await ctx.send(f"Une erreur s'est produite lors de l'exécution de la commande.")

    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        try:
            if before.channel is None and after.channel is not None:
                # User joined voice channel
                self.db.start_voice_session(member.id)
                logger.info(f"User {member.name} started voice session")

            elif before.channel is not None and after.channel is None:
                # User left voice channel
                duration_minutes = self.db.end_voice_session(member.id) / 60
                await self.point_system.award_voice_points(member.id, duration_minutes)
                logger.info(f"User {member.name} ended voice session, duration: {duration_minutes} minutes")
        except Exception as e:
            logger.error(f"Error in voice state update: {e}")

    @tasks.loop(minutes=5)
    async def save_data_loop(self):
        try:
            self.db.save_data()
            logger.info("Data saved successfully")
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    @tasks.loop(minutes=15)
    async def check_twitter_engagement(self):
        try:
            # Vérifier si twitter_links existe dans les données
            if 'twitter_links' not in self.db.data:
                self.db.data['twitter_links'] = {}
                self.db.save_data()
                logger.info("Created twitter_links in database")
                return

            # Parcourir tous les utilisateurs ayant lié leur compte Twitter
            for discord_id, twitter_username in self.db.get_all_twitter_users():
                logger.info(f"Checking Twitter engagement for user {twitter_username}")
                # Récupérer les anciennes stats
                old_stats = self.db.get_twitter_stats(discord_id)

                # Récupérer les nouvelles stats
                new_stats = await self.twitter_handler.get_user_activity(twitter_username)

                if new_stats:
                    # Calculer les nouvelles interactions
                    new_likes = max(0, new_stats['likes'] - old_stats['likes'])
                    new_retweets = max(0, new_stats['retweets'] - old_stats['retweets'])
                    new_comments = max(0, new_stats['comments'] - old_stats['comments'])

                    # Attribuer les points pour chaque nouvelle interaction
                    if new_likes > 0:
                        await self.point_system.award_twitter_points(discord_id, 'like')
                    if new_retweets > 0:
                        await self.point_system.award_twitter_points(discord_id, 'retweet')
                    if new_comments > 0:
                        await self.point_system.award_twitter_points(discord_id, 'comment')

                    # Mettre à jour les stats stockées
                    self.db.update_twitter_stats(discord_id, new_stats)
                    logger.info(f"Updated Twitter stats for {twitter_username}")

        except Exception as e:
            logger.error(f"Error checking Twitter engagement: {e}")

    @check_twitter_engagement.before_loop
    async def before_check_twitter(self):
        await self.wait_until_ready()

async def main():
    try:
        bot = EngagementBot()
        async with bot:
            logger.info("Starting bot...")
            await bot.start(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())