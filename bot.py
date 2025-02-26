import discord
from discord.ext import commands, tasks
import asyncio
from database import Database
from point_system import PointSystem
from twitter_handler import TwitterHandler
from config import DISCORD_TOKEN
import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EngagementBot')

class EngagementBot(commands.Bot):
    def __init__(self):
        logger.info("Initializing EngagementBot...")

        # Set up intents
        intents = discord.Intents.all()  # Enable all intents to ensure message handling works

        # Initialize bot
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )

        # Initialize components
        self.db = Database()
        self.point_system = PointSystem(self.db)
        self.twitter_handler = None

    async def setup_hook(self):
        try:
            logger.info("Setting up bot components...")

            # Initialize Twitter handler
            self.twitter_handler = TwitterHandler()

            # Add commands cog
            # Get the current directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Ensure commands.py is in the Python path
            if current_dir not in sys.path:
                sys.path.append(current_dir)

            logger.info("Loading commands extension...")
            await self.load_extension("commands")
            logger.info(f"Available commands: {[command.name for command in self.commands]}")

        except Exception as e:
            logger.error(f"Error in setup_hook: {e}", exc_info=True)
            raise

    async def on_ready(self):
        logger.info(f'Bot connected as {self.user.name} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guilds')

        # Start background tasks
        self.save_data_loop.start()
        self.check_twitter_engagement.start()

    async def on_message(self, message):
        if message.author.bot:
            return

        try:
            if message.content.startswith(self.command_prefix):
                logger.info(f"Processing command: {message.content}")
                await self.process_commands(message)
            else:
                await self.point_system.award_message_points(message.author.id)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    @tasks.loop(minutes=5)
    async def save_data_loop(self):
        try:
            self.db.save_data()
            logger.info("Data saved successfully")
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    @tasks.loop(minutes=15)
    async def check_twitter_engagement(self):
        if not self.twitter_handler:
            return

        try:
            for discord_id, twitter_username in self.db.get_all_twitter_users():
                try:
                    old_stats = self.db.get_twitter_stats(discord_id)
                    new_stats = await self.twitter_handler.get_user_activity(twitter_username)
                    if new_stats:
                        await self._process_twitter_stats(discord_id, old_stats, new_stats)
                        self.db.update_twitter_stats(discord_id, new_stats)
                except Exception as e:
                    logger.error(f"Error checking Twitter for user {twitter_username}: {e}")
        except Exception as e:
            logger.error(f"Error in Twitter engagement check: {e}")

    async def _process_twitter_stats(self, discord_id, old_stats, new_stats):
        try:
            new_likes = max(0, new_stats['likes'] - old_stats['likes'])
            new_retweets = max(0, new_stats['retweets'] - old_stats['retweets'])
            new_comments = max(0, new_stats['comments'] - old_stats['comments'])

            if new_likes > 0:
                await self.point_system.award_twitter_points(discord_id, 'like')
            if new_retweets > 0:
                await self.point_system.award_twitter_points(discord_id, 'retweet')
            if new_comments > 0:
                await self.point_system.award_twitter_points(discord_id, 'comment')
        except Exception as e:
            logger.error(f"Error processing Twitter stats: {e}")

    @check_twitter_engagement.before_loop
    @save_data_loop.before_loop
    async def before_loops(self):
        await self.wait_until_ready()

async def main():
    try:
        bot = EngagementBot()
        async with bot:
            await bot.start(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())