import discord
from discord.ext import commands, tasks
import asyncio
from database import Database
from point_system import PointSystem
from twitter_handler import TwitterHandler
from commands import Commands
from config import DISCORD_TOKEN

class EngagementBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True

        super().__init__(command_prefix='!', intents=intents)

        self.db = Database()
        self.point_system = PointSystem(self.db)
        self.twitter_handler = TwitterHandler()

    async def setup_hook(self):
        # Add commands
        await self.add_cog(Commands(self, self.point_system, self.twitter_handler))

    async def on_ready(self):
        print(f'Logged in as {self.user.name}')
        print('------')
        # Start background tasks after bot is ready
        self.save_data_loop.start()

    async def on_message(self, message):
        if message.author.bot:
            return

        await self.point_system.award_message_points(message.author.id)
        await self.process_commands(message)

    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        if before.channel is None and after.channel is not None:
            # User joined voice channel
            self.db.start_voice_session(member.id)

        elif before.channel is not None and after.channel is None:
            # User left voice channel
            duration_minutes = self.db.end_voice_session(member.id) / 60
            await self.point_system.award_voice_points(member.id, duration_minutes)

    @tasks.loop(minutes=5)
    async def save_data_loop(self):
        self.db.save_data()

async def main():
    bot = EngagementBot()
    async with bot:
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())