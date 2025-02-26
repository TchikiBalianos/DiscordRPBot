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
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EngagementBot')

class EngagementBot(commands.Bot):
    def __init__(self):
        logger.debug("Initializing EngagementBot...")
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        intents.guilds = True
        intents.presences = True

        super().__init__(command_prefix='!', intents=intents)

        logger.debug("Setting up bot components...")
        self.db = Database()
        self.point_system = PointSystem(self.db)
        self.twitter_handler = None
        logger.info("Bot components initialized")

    async def setup_hook(self):
        try:
            logger.debug("Starting setup_hook...")
            self.twitter_handler = TwitterHandler()
            logger.debug("Adding Commands cog...")
            await self.add_cog(Commands(self, self.point_system, self.twitter_handler))
            logger.info(f"Registered commands: {[command.name for command in self.commands]}")
        except Exception as e:
            logger.error(f"Error in setup_hook: {e}")
            logger.exception("Full setup error traceback:")
            raise

    async def on_ready(self):
        logger.info(f'Logged in as {self.user.name} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guilds:')
        for guild in self.guilds:
            logger.info(f'- {guild.name} (ID: {guild.id})')

        # Verify command registration
        logger.debug(f"Available commands: {[command.name for command in self.commands]}")
        logger.debug(f"Command prefix: {self.command_prefix}")

        # Start background tasks
        self.save_data_loop.start()
        self.check_twitter_engagement.start()
        logger.info("Bot is fully ready and listening for commands")

    async def on_message(self, message):
        if message.author.bot:
            return

        try:
            logger.debug(f"Message received: content='{message.content}' author={message.author}")

            if message.content.startswith(self.command_prefix):
                logger.debug(f"Processing command: {message.content}")
                await self.process_commands(message)
            else:
                await self.point_system.award_message_points(message.author.id)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.exception("Full message processing traceback:")

    @tasks.loop(minutes=5)
    async def save_data_loop(self):
        try:
            self.db.save_data()
            logger.info("Data saved successfully")
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            logger.exception("Full save data traceback:")

    @tasks.loop(minutes=15)
    async def check_twitter_engagement(self):
        try:
            # Skip if Twitter handler isn't initialized
            if not self.twitter_handler:
                logger.warning("Twitter handler not initialized, skipping engagement check")
                return

            for discord_id, twitter_username in self.db.get_all_twitter_users():
                try:
                    logger.info(f"Checking Twitter engagement for {twitter_username}")
                    old_stats = self.db.get_twitter_stats(discord_id)
                    new_stats = await self.twitter_handler.get_user_activity(twitter_username)

                    if new_stats:
                        # Process stats and award points
                        await self._process_twitter_stats(discord_id, old_stats, new_stats)
                        self.db.update_twitter_stats(discord_id, new_stats)
                        logger.info(f"Updated Twitter stats for {twitter_username}")
                except Exception as e:
                    logger.error(f"Error processing Twitter stats for {twitter_username}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in check_twitter_engagement: {e}")
            logger.exception("Full Twitter engagement check traceback:")

    async def _process_twitter_stats(self, discord_id, old_stats, new_stats):
        """Process Twitter stats and award points for new interactions"""
        try:
            # Calculate new interactions
            new_likes = max(0, new_stats['likes'] - old_stats['likes'])
            new_retweets = max(0, new_stats['retweets'] - old_stats['retweets'])
            new_comments = max(0, new_stats['comments'] - old_stats['comments'])

            # Award points for each new interaction
            if new_likes > 0:
                await self.point_system.award_twitter_points(discord_id, 'like')
            if new_retweets > 0:
                await self.point_system.award_twitter_points(discord_id, 'retweet')
            if new_comments > 0:
                await self.point_system.award_twitter_points(discord_id, 'comment')

        except Exception as e:
            logger.error(f"Error processing Twitter stats for user {discord_id}: {e}")
            raise

    @check_twitter_engagement.before_loop
    async def before_check_twitter(self):
        await self.wait_until_ready()

    @save_data_loop.before_loop
    async def before_save_data(self):
        await self.wait_until_ready()

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


async def main():
    try:
        bot = EngagementBot()
        async with bot:
            logger.info("Starting bot...")
            await bot.start(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Error in main: {e}")
        logger.exception("Full main error traceback:")
        raise

if __name__ == "__main__":
    asyncio.run(main())