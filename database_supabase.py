import os
import logging
import json
import time
from typing import Optional, Dict, List, Any, Tuple
from supabase import create_client, Client
from datetime import datetime, date

logger = logging.getLogger('EngagementBot')

class SupabaseDatabase:
    """Database manager using Supabase PostgreSQL"""
    
    def __init__(self):
        self.supabase: Optional[Client] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Supabase client"""
        try:
            url = os.getenv('SUPABASE_URL')
            key = os.getenv('SUPABASE_ANON_KEY')
            
            if not url or not key:
                logger.error("Supabase credentials not found in environment variables")
                return
            
            self.supabase = create_client(url, key)
            logger.info("Supabase client initialized successfully")
            
            # Test de connexion simple
            try:
                result = self.supabase.table('users').select('count', count='exact').limit(1).execute()
                logger.info("Supabase connection test successful")
            except Exception as test_error:
                logger.warning(f"Supabase test query failed: {test_error}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}", exc_info=True)
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self.supabase is not None
    
    # === USER MANAGEMENT ===
    
    def get_user_data(self, user_id: str) -> Dict:
        """Get user data"""
        try:
            if not self.is_connected():
                return {'user_id': user_id, 'points': 0}
            
            result = self.supabase.table('users').select('*').eq('user_id', user_id).execute()
            
            if result.data:
                return result.data[0]
            else:
                # Create new user
                new_user = {
                    'user_id': user_id,
                    'points': 0
                }
                self.supabase.table('users').insert(new_user).execute()
                return new_user
                
        except Exception as e:
            logger.error(f"Error getting user data: {e}", exc_info=True)
            return {'user_id': user_id, 'points': 0}
    
    def add_points(self, user_id: str, points: int):
        """Add points to user"""
        try:
            if not self.is_connected():
                return
            
            # Use the SQL function for atomic operation
            result = self.supabase.rpc('add_user_points', {
                'p_user_id': user_id,
                'p_points': points
            }).execute()
            
            logger.info(f"Added {points} points to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error adding points: {e}", exc_info=True)
    
    def remove_points(self, user_id: str, points: int) -> bool:
        """Remove points from user"""
        try:
            if not self.is_connected():
                return False
            
            current_user = self.get_user_data(user_id)
            
            if current_user['points'] < points:
                return False
            
            new_points = current_user['points'] - points
            self.supabase.table('users').update({
                'points': new_points,
                'updated_at': datetime.now().isoformat()
            }).eq('user_id', user_id).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error removing points: {e}", exc_info=True)
            return False
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get points leaderboard"""
        try:
            if not self.is_connected():
                return []
            
            result = self.supabase.table('users').select('*').order('points', desc=True).limit(limit).execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}", exc_info=True)
            return []
    
    # === COOLDOWNS ===
    
    def set_cooldown(self, table_name: str, user_id: str, cooldown_time: float):
        """Set user cooldown"""
        try:
            if not self.is_connected():
                return
            
            self.supabase.table('user_cooldowns').upsert({
                'user_id': user_id,
                'cooldown_type': table_name,
                'cooldown_until': cooldown_time
            }).execute()
            
        except Exception as e:
            logger.error(f"Error setting cooldown: {e}", exc_info=True)
    
    def get_cooldown(self, table_name: str, user_id: str) -> Optional[float]:
        """Get user cooldown"""
        try:
            if not self.is_connected():
                return None
            
            result = self.supabase.table('user_cooldowns').select('cooldown_until').eq('user_id', user_id).eq('cooldown_type', table_name).execute()
            
            if result.data:
                return result.data[0]['cooldown_until']
            return None
            
        except Exception as e:
            logger.error(f"Error getting cooldown: {e}", exc_info=True)
            return None
    
    def remove_cooldown(self, table_name: str, user_id: str):
        """Remove user cooldown"""
        try:
            if not self.is_connected():
                return
            
            self.supabase.table('user_cooldowns').delete().eq('user_id', user_id).eq('cooldown_type', table_name).execute()
            
        except Exception as e:
            logger.error(f"Error removing cooldown: {e}", exc_info=True)
    
    # === VOICE SESSIONS ===
    
    def start_voice_session(self, user_id: str, event_name: str = None):
        """Start voice session"""
        try:
            if not self.is_connected():
                return
            
            self.supabase.table('voice_sessions').upsert({
                'user_id': user_id,
                'start_time': time.time(),
                'event_name': event_name
            }).execute()
            
        except Exception as e:
            logger.error(f"Error starting voice session: {e}", exc_info=True)
    
    def end_voice_session(self, user_id: str) -> Optional[Dict]:
        """End voice session and return session info"""
        try:
            if not self.is_connected():
                return None
            
            # Get session
            result = self.supabase.table('voice_sessions').select('*').eq('user_id', user_id).execute()
            
            if result.data:
                session = result.data[0]
                
                # Remove session
                self.supabase.table('voice_sessions').delete().eq('user_id', user_id).execute()
                
                return session
            
            return None
            
        except Exception as e:
            logger.error(f"Error ending voice session: {e}", exc_info=True)
            return None
    
    def get_voice_session(self, user_id: str) -> Optional[Dict]:
        """Get current voice session"""
        try:
            if not self.is_connected():
                return None
            
            result = self.supabase.table('voice_sessions').select('*').eq('user_id', user_id).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error getting voice session: {e}", exc_info=True)
            return None
    
    # === TWITTER ===
    
    def link_twitter(self, user_id: str, twitter_handle: str):
        """Link Twitter account"""
        try:
            if not self.is_connected():
                return
            
            self.supabase.table('twitter_links').upsert({
                'user_id': user_id,
                'twitter_handle': twitter_handle
            }).execute()
            
        except Exception as e:
            logger.error(f"Error linking Twitter: {e}", exc_info=True)
    
    def get_twitter_link(self, user_id: str) -> Optional[str]:
        """Get Twitter link"""
        try:
            if not self.is_connected():
                return None
            
            result = self.supabase.table('twitter_links').select('twitter_handle').eq('user_id', user_id).execute()
            return result.data[0]['twitter_handle'] if result.data else None
            
        except Exception as e:
            logger.error(f"Error getting Twitter link: {e}", exc_info=True)
            return None
    
    # === PRISON ===
    
    def set_prison_time(self, user_id: str, release_time: float):
        """Set prison time"""
        try:
            if not self.is_connected():
                return
            
            self.supabase.table('prison_times').upsert({
                'user_id': user_id,
                'release_time': release_time
            }).execute()
            
        except Exception as e:
            logger.error(f"Error setting prison time: {e}", exc_info=True)
    
    def get_prison_time(self, user_id: str) -> Optional[float]:
        """Get prison release time"""
        try:
            if not self.is_connected():
                return None
            
            result = self.supabase.table('prison_times').select('release_time').eq('user_id', user_id).execute()
            return result.data[0]['release_time'] if result.data else None
            
        except Exception as e:
            logger.error(f"Error getting prison time: {e}", exc_info=True)
            return None
    
    def remove_prison_time(self, user_id: str):
        """Remove prison time"""
        try:
            if not self.is_connected():
                return
            
            self.supabase.table('prison_times').delete().eq('user_id', user_id).execute()
            
        except Exception as e:
            logger.error(f"Error removing prison time: {e}", exc_info=True)
    
    # === GANGS ===
    
    def create_gang(self, name: str, boss_id: str, description: str = "") -> bool:
        """Create a new gang"""
        try:
            if not self.is_connected():
                return False
            
            # Create gang
            gang_result = self.supabase.table('gangs').insert({
                'name': name,
                'description': description,
                'boss_id': boss_id,
                'vault_points': 0,
                'reputation': 0,
                'territory_count': 0
            }).execute()
            
            if gang_result.data:
                gang_id = gang_result.data[0]['id']
                
                # Add boss as member
                self.supabase.table('gang_members').insert({
                    'gang_id': gang_id,
                    'user_id': boss_id,
                    'rank': 'boss'
                }).execute()
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error creating gang: {e}", exc_info=True)
            return False
    
    def get_gang_by_name(self, name: str) -> Optional[Tuple[str, Dict]]:
        """Get gang by name"""
        try:
            if not self.is_connected():
                return None
            
            result = self.supabase.table('gangs').select('*').eq('name', name).execute()
            
            if result.data:
                gang = result.data[0]
                return gang['id'], gang
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting gang by name: {e}", exc_info=True)
            return None
    
    def get_user_gang(self, user_id: str) -> Optional[str]:
        """Get user's gang ID"""
        try:
            if not self.is_connected():
                return None
            
            result = self.supabase.table('gang_members').select('gang_id').eq('user_id', user_id).execute()
            return result.data[0]['gang_id'] if result.data else None
            
        except Exception as e:
            logger.error(f"Error getting user gang: {e}", exc_info=True)
            return None
    
    def get_gang_info(self, gang_id: str) -> Optional[Dict]:
        """Get gang info with members"""
        try:
            if not self.is_connected():
                return None
            
            # Get gang info
            gang_result = self.supabase.table('gangs').select('*').eq('id', gang_id).execute()
            
            if not gang_result.data:
                return None
            
            gang = gang_result.data[0]
            
            # Get members
            members_result = self.supabase.table('gang_members').select('*').eq('gang_id', gang_id).execute()
            
            # Format members
            members = {}
            for member in members_result.data or []:
                members[member['user_id']] = {
                    'rank': member['rank'],
                    'joined_at': member['joined_at']
                }
            
            gang['members'] = members
            return gang
            
        except Exception as e:
            logger.error(f"Error getting gang info: {e}", exc_info=True)
            return None
    
    # === TERRITORIES ===
    
    def get_all_territories(self) -> Dict:
        """Get all territories"""
        try:
            if not self.is_connected():
                return {}
            
            result = self.supabase.table('territories').select('*').execute()
            
            territories = {}
            for territory in result.data or []:
                territories[territory['id']] = territory
            
            return territories
            
        except Exception as e:
            logger.error(f"Error getting territories: {e}", exc_info=True)
            return {}
    
    # === DAILY COMMANDS ===
    
    def get_daily_commands(self, user_id: str, command_date: str = None) -> Dict:
        """Get daily commands for user"""
        try:
            if not self.is_connected():
                return {}
            
            if not command_date:
                command_date = date.today().isoformat()
            
            result = self.supabase.table('daily_commands').select('commands').eq('user_id', user_id).eq('command_date', command_date).execute()
            
            if result.data:
                return result.data[0]['commands'] or {}
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting daily commands: {e}", exc_info=True)
            return {}
    
    def increment_daily_command(self, user_id: str, command_name: str, command_date: str = None):
        """Increment daily command count"""
        try:
            if not self.is_connected():
                return
            
            if not command_date:
                command_date = date.today().isoformat()
            
            # Get current commands
            current_commands = self.get_daily_commands(user_id, command_date)
            current_commands[command_name] = current_commands.get(command_name, 0) + 1
            
            # Update
            self.supabase.table('daily_commands').upsert({
                'user_id': user_id,
                'command_date': command_date,
                'commands': current_commands
            }).execute()
            
        except Exception as e:
            logger.error(f"Error incrementing daily command: {e}", exc_info=True)
    
    # === INVENTORIES ===
    
    def get_inventory(self, user_id: str) -> List[str]:
        """Get user inventory"""
        try:
            if not self.is_connected():
                return []
            
            result = self.supabase.table('inventories').select('items').eq('user_id', user_id).execute()
            
            if result.data:
                return result.data[0]['items'] or []
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting inventory: {e}", exc_info=True)
            return []
    
    def add_item(self, user_id: str, item: str):
        """Add item to inventory"""
        try:
            if not self.is_connected():
                return
            
            current_items = self.get_inventory(user_id)
            current_items.append(item)
            
            self.supabase.table('inventories').upsert({
                'user_id': user_id,
                'items': current_items
            }).execute()
            
        except Exception as e:
            logger.error(f"Error adding item: {e}", exc_info=True)
    
    def remove_item(self, user_id: str, item: str) -> bool:
        """Remove item from inventory"""
        try:
            if not self.is_connected():
                return False
            
            current_items = self.get_inventory(user_id)
            
            if item in current_items:
                current_items.remove(item)
                
                self.supabase.table('inventories').update({
                    'items': current_items
                }).eq('user_id', user_id).execute()
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error removing item: {e}", exc_info=True)
            return False
    
    # === MIGRATION ===
    
    def migrate_from_json(self, json_file_path: str):
        """Migrate data from JSON file to Supabase"""
        try:
            if not self.is_connected():
                logger.error("Cannot migrate: Supabase not connected")
                return
            
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info("Starting migration from JSON to Supabase...")
            
            # Migrate users
            if 'users' in data and data['users']:
                users_to_insert = []
                for user_id, user_data in data['users'].items():
                    users_to_insert.append({
                        'user_id': user_id,
                        'points': user_data.get('points', 0)
                    })
                
                if users_to_insert:
                    self.supabase.table('users').upsert(users_to_insert).execute()
                    logger.info(f"Migrated {len(users_to_insert)} users")
            
            # Migrate cooldowns
            cooldown_tables = ['rob_cooldowns', 'last_work', 'drug_deal_cooldowns', 'roulette_cooldowns']
            for table_name in cooldown_tables:
                if table_name in data and data[table_name]:
                    cooldowns_to_insert = []
                    for user_id, cooldown_time in data[table_name].items():
                        cooldowns_to_insert.append({
                            'user_id': user_id,
                            'cooldown_type': table_name,
                            'cooldown_until': cooldown_time
                        })
                    
                    if cooldowns_to_insert:
                        self.supabase.table('user_cooldowns').upsert(cooldowns_to_insert).execute()
                        logger.info(f"Migrated {len(cooldowns_to_insert)} {table_name}")
            
            # Migrate Twitter links
            if 'twitter_links' in data and data['twitter_links']:
                twitter_links = []
                for user_id, handle in data['twitter_links'].items():
                    twitter_links.append({
                        'user_id': user_id,
                        'twitter_handle': handle
                    })
                
                if twitter_links:
                    self.supabase.table('twitter_links').upsert(twitter_links).execute()
                    logger.info(f"Migrated {len(twitter_links)} Twitter links")
            
            # Migrate prison times
            if 'prison_times' in data and data['prison_times']:
                prison_times = []
                for user_id, release_time in data['prison_times'].items():
                    prison_times.append({
                        'user_id': user_id,
                        'release_time': release_time
                    })
                
                if prison_times:
                    self.supabase.table('prison_times').upsert(prison_times).execute()
                    logger.info(f"Migrated {len(prison_times)} prison times")
            
            # Migrate inventories
            if 'inventories' in data and data['inventories']:
                inventories = []
                for user_id, items in data['inventories'].items():
                    inventories.append({
                        'user_id': user_id,
                        'items': items
                    })
                
                if inventories:
                    self.supabase.table('inventories').upsert(inventories).execute()
                    logger.info(f"Migrated {len(inventories)} inventories")
            
            # Migrate daily commands
            if 'daily_commands' in data and data['daily_commands']:
                daily_commands = []
                for user_id, dates_data in data['daily_commands'].items():
                    for date_str, commands in dates_data.items():
                        daily_commands.append({
                            'user_id': user_id,
                            'command_date': date_str,
                            'commands': commands
                        })
                
                if daily_commands:
                    self.supabase.table('daily_commands').upsert(daily_commands).execute()
                    logger.info(f"Migrated {len(daily_commands)} daily command records")
            
            logger.info("Migration completed successfully!")
            
        except Exception as e:
            logger.error(f"Error during migration: {e}", exc_info=True)
    
    # === UTILITY ===
    
    def cleanup_expired_data(self):
        """Cleanup expired data"""
        try:
            if not self.is_connected():
                return
            
            # Cleanup expired cooldowns
            self.supabase.rpc('cleanup_expired_cooldowns').execute()
            logger.info("Cleaned up expired cooldowns")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
    
    def save_data(self):
        """Compatibility method - not needed for Supabase"""
        pass
    
    @property
    def data(self) -> Dict:
        """Compatibility property for legacy code"""
        logger.warning("Using legacy data property - consider migrating to specific methods")
        return {}