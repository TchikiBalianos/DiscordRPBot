import discord
from discord.ext import commands
import logging
import os
from datetime import datetime
import asyncio
import time

# Import our systems
from database_supabase import SupabaseDatabase
from point_system import PointSystem
from twitter_handler import TwitterHandler
from gang_events import setup_gang_events, shutdown_gang_events

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('EngagementBot')

class EngagementBot(commands.Bot):
    """Enhanced Discord bot with Supabase database"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.members = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        # Initialize systems
        self.db = SupabaseDatabase()
        self.point_system = PointSystem(self.db, self)
        self.twitter_handler = TwitterHandler()
        
        # Check database connection
        if not self.db.is_connected():
            logger.error("Failed to connect to Supabase! Bot will run with limited functionality.")
        else:
            logger.info("Successfully connected to Supabase database")

    async def setup_hook(self):
        """Load commands and setup systems"""
        try:
            # Start Twitter handler
            await self.twitter_handler.start()
            
            logger.info("Loading Commands cog...")
            from commands import Commands
            commands_cog = Commands(self, self.point_system, self.twitter_handler)
            await self.add_cog(commands_cog)
            
            # Load gang commands
            logger.info("Loading Gang Commands cog...")
            from gang_commands import GangCommands
            gang_commands_cog = GangCommands(self, self.db)
            await self.add_cog(gang_commands_cog)
            
            logger.info("Commands cogs loaded successfully")
            all_commands = sorted([c.name for c in self.commands])
            logger.info(f"Available commands: {all_commands}")
            logger.info(f"Total number of commands: {len(all_commands)}")

            # Setup gang events
            if self.db.is_connected():
                await setup_gang_events(self, self.db)
                logger.info("Gang events system started")
            else:
                logger.warning("Skipping gang events setup due to database connection issues")
            
            # Migrate data if needed
            await self._check_migration()

        except Exception as e:
            logger.error(f"Failed to load cogs: {e}", exc_info=True)
            raise
    
    async def _check_migration(self):
        """Check if migration from JSON is needed"""
        try:
            if not self.db.is_connected():
                return
            
            # Check if we have users in database
            users = self.db.get_leaderboard(1)
            
            # If no users and data.json exists, migrate
            if not users and os.path.exists('data.json'):
                logger.info("No users found in database, checking for data.json migration...")
                
                # Ask user or migrate automatically
                self.db.migrate_from_json('data.json')
                
                # Backup old file
                import shutil
                shutil.copy('data.json', 'data.json.backup')
                logger.info("Created backup of data.json")
        
        except Exception as e:
            logger.error(f"Error during migration check: {e}", exc_info=True)

    async def on_ready(self):
        """Bot is ready"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Vérifier l'intégrité des systèmes
        await self._health_check()
        
        # Set status
        activity = discord.Game(name="Système de gangs | !help")
        await self.change_presence(activity=activity)
        
        # Cleanup expired data
        if self.db and self.db.is_connected():
            try:
                self.db.cleanup_expired_data()
                logger.info("✅ Database cleanup completed")
            except Exception as e:
                logger.error(f"Database cleanup failed: {e}")
    
    async def _health_check(self):
        """Vérifier la santé des systèmes"""
        try:
            # Vérifier la base de données
            if not self.db or not self.db.is_connected():
                logger.error("❌ Database connection failed")
            else:
                logger.info("✅ Database connection OK")
            
            # Vérifier le système de points
            if not self.point_system:
                logger.error("❌ Point system not initialized")
            elif not hasattr(self.point_system, 'database'):
                logger.error("❌ Point system missing database")
            else:
                logger.info("✅ Point system OK")
            
            # Vérifier Twitter
            if not self.twitter_handler:
                logger.warning("⚠️ Twitter handler not available")
            else:
                logger.info("✅ Twitter handler OK")
            
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)

    async def on_voice_state_update(self, member, before, after):
        """Handle voice state changes"""
        try:
            if member.bot:
                return
            
            user_id = str(member.id)
            
            # User joined voice channel
            if before.channel is None and after.channel is not None:
                self.db.start_voice_session(user_id)
                logger.info(f"User {member.display_name} joined voice channel")
            
            # User left voice channel
            elif before.channel is not None and after.channel is None:
                session = self.db.end_voice_session(user_id)
                
                if session:
                    # Calculate time spent
                    time_spent = time.time() - session['start_time']
                    
                    if time_spent >= 300:  # 5 minutes minimum
                        points = min(int(time_spent / 60) * 2, 120)  # 2 points per minute, max 120
                        self.point_system.add_points(user_id, points, f"Voice chat ({int(time_spent/60)} min)")
                        logger.info(f"Awarded {points} points to {member.display_name} for voice activity")
        
        except Exception as e:
            logger.error(f"Error in voice state update: {e}", exc_info=True)

    async def on_command_error(self, ctx, error):
        """Handle command errors with better logging"""
        try:
            if isinstance(error, commands.CommandNotFound):
                return
            
            elif isinstance(error, commands.MissingRequiredArgument):
                await ctx.send(f"❌ Argument manquant. Utilisez `!help {ctx.command}` pour voir la syntaxe.")
            
            elif isinstance(error, commands.BadArgument):
                await ctx.send("❌ Argument invalide. Vérifiez votre commande.")
            
            elif isinstance(error, commands.CheckFailure):
                logger.warning(f"Check failure for {ctx.author}: {str(error)}")
                await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande ou vous avez atteint la limite quotidienne.")
            
            elif isinstance(error, AttributeError):
                logger.error(f"AttributeError in command {ctx.command}: {str(error)}", exc_info=True)
                await ctx.send("❌ Erreur système. L'équipe a été notifiée.")
            
            else:
                logger.error(f"Unhandled command error: {str(error)}", exc_info=True)
                logger.error(f"Command: {ctx.command} | Author: {ctx.author} | Guild: {ctx.guild}")
                await ctx.send("❌ Une erreur s'est produite lors de l'exécution de la commande.")
        
        except Exception as e:
            logger.error(f"Error in error handler: {e}", exc_info=True)

    async def close(self):
        """Override close to include shutdown of gang events and Twitter"""
        try:
            logger.info("Shutting down bot...")
            
            if hasattr(self, 'gang_events'):
                await shutdown_gang_events(self)
            
            await self.twitter_handler.stop()
            await super().close()
            
        except Exception as e:
            logger.error(f"Error during bot shutdown: {e}", exc_info=True)

async def main():
    """Main function to run the bot"""
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("DISCORD_TOKEN not found in environment variables!")
        return
    
    bot = EngagementBot()
    
    try:
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)
    finally:
        await bot.close()

def run_bot():
    """Function for Railway deployment"""
    import asyncio
    asyncio.run(main())

if __name__ == "__main__":
    run_bot()