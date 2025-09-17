import os
import logging
import json
import time
from typing import Optional, Dict, List, Any, Tuple
from supabase import create_client, Client
from datetime import datetime, date, timedelta

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
                # Mode dégradé
                self.supabase = None
                return
            
            self.supabase = create_client(url, key)
            logger.info("Supabase client initialized successfully")
            
            # Test de connexion simple et robuste
            try:
                # Test avec une requête simple
                result = self.supabase.table('users').select('user_id').limit(1).execute()
                logger.info("✅ Supabase connection test successful")
            except Exception as test_error:
                logger.warning(f"⚠️ Supabase test query failed, but client created: {test_error}")
                # Ne pas désactiver le client, juste avertir
        
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}", exc_info=True)
            self.supabase = None
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self.supabase is not None
    
    # === USER MANAGEMENT ===
    
    def get_user_data(self, user_id: str) -> Dict:
        """Get user data with fallback"""
        try:
            if not self.is_connected():
                # Mode dégradé : retourner des données par défaut
                logger.warning("Database not connected, using default user data")
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
                try:
                    self.supabase.table('users').insert(new_user).execute()
                    logger.info(f"Created new user: {user_id}")
                except Exception as insert_error:
                    logger.error(f"Failed to create new user: {insert_error}")
                
                return new_user
                
        except Exception as e:
            logger.error(f"Error getting user data for {user_id}: {e}", exc_info=True)
            # Fallback : retourner des données par défaut
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

    # === COMMAND COOLDOWNS (TECH Brief Implementation) ===
    
    def set_command_cooldown(self, user_id: str, command_name: str, cooldown_seconds: int):
        """Set command cooldown according to TECH Brief specs"""
        cooldown_until = time.time() + cooldown_seconds
        self.set_cooldown(f"command_{command_name}", user_id, cooldown_until)
    
    def get_command_cooldown(self, user_id: str, command_name: str) -> int:
        """Get remaining cooldown time in seconds for a command"""
        try:
            cooldown_until = self.get_cooldown(f"command_{command_name}", user_id)
            if cooldown_until is None:
                return 0
            
            remaining = int(cooldown_until - time.time())
            return max(0, remaining)  # Ne jamais retourner de valeur négative
            
        except Exception as e:
            logger.error(f"Error getting command cooldown: {e}", exc_info=True)
            return 0
    
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

    # === JUSTICE SYSTEM METHODS ===
    
    def arrest_user(self, arrester_id: str, target_id: str, reason: str, prison_time: int) -> bool:
        """Arrest a user and put them in prison"""
        try:
            if not self.is_connected():
                return False
            
            # Create arrest record
            arrest_data = {
                'arrester_id': arrester_id,
                'target_id': target_id,
                'reason': reason,
                'prison_time': prison_time,
                'arrested_at': datetime.now().isoformat(),
                'status': 'active'
            }
            
            self.supabase.table('arrests').insert(arrest_data).execute()
            
            # Update user prison status
            prison_data = {
                'user_id': target_id,
                'imprisoned_at': datetime.now().isoformat(),
                'release_at': (datetime.now() + timedelta(seconds=prison_time)).isoformat(),
                'reason': reason,
                'arrester_id': arrester_id,
                'status': 'imprisoned'
            }
            
            # Upsert prison record
            self.supabase.table('prison_records').upsert(prison_data).execute()
            
            logger.info(f"User {target_id} arrested by {arrester_id} for {prison_time}s")
            return True
            
        except Exception as e:
            logger.error(f"Error arresting user: {e}", exc_info=True)
            return False
    
    def get_prison_status(self, user_id: str) -> Optional[Dict]:
        """Get user's current prison status"""
        try:
            if not self.is_connected():
                return None
            
            result = self.supabase.table('prison_records').select('*').eq('user_id', user_id).eq('status', 'imprisoned').execute()
            
            if result.data:
                prison_data = result.data[0]
                release_time = datetime.fromisoformat(prison_data['release_at'])
                now = datetime.now()
                
                if now >= release_time:
                    # User should be released
                    self.release_from_prison(user_id)
                    return None
                
                time_left = (release_time - now).total_seconds()
                return {
                    'time_left': int(time_left),
                    'reason': prison_data['reason'],
                    'arrester_id': prison_data['arrester_id']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting prison status: {e}", exc_info=True)
            return None
    
    def release_from_prison(self, user_id: str) -> bool:
        """Release user from prison"""
        try:
            if not self.is_connected():
                return False
            
            self.supabase.table('prison_records').update({'status': 'released'}).eq('user_id', user_id).eq('status', 'imprisoned').execute()
            
            logger.info(f"Released user {user_id} from prison")
            return True
            
        except Exception as e:
            logger.error(f"Error releasing from prison: {e}", exc_info=True)
            return False
    
    def pay_bail(self, user_id: str, bail_amount: int) -> bool:
        """Pay bail to get out of prison"""
        try:
            if not self.is_connected():
                return False
            
            # Check if user has enough points
            user_data = self.get_user_data(user_id)
            if user_data['points'] < bail_amount:
                return False
            
            # Remove points
            self.remove_points(user_id, bail_amount)
            
            # Release from prison
            self.release_from_prison(user_id)
            
            # Record bail payment
            bail_data = {
                'user_id': user_id,
                'amount': bail_amount,
                'paid_at': datetime.now().isoformat()
            }
            
            self.supabase.table('bail_payments').insert(bail_data).execute()
            
            logger.info(f"User {user_id} paid bail of {bail_amount}")
            return True
            
        except Exception as e:
            logger.error(f"Error paying bail: {e}", exc_info=True)
            return False
    
    def add_prison_visit(self, visitor_id: str, prisoner_id: str, message: str) -> bool:
        """Record a prison visit"""
        try:
            if not self.is_connected():
                return False
            
            visit_data = {
                'visitor_id': visitor_id,
                'prisoner_id': prisoner_id,
                'message': message,
                'visited_at': datetime.now().isoformat()
            }
            
            self.supabase.table('prison_visits').insert(visit_data).execute()
            
            logger.info(f"Prison visit recorded: {visitor_id} visited {prisoner_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording prison visit: {e}", exc_info=True)
            return False
    
    def submit_plea(self, user_id: str, plea_text: str) -> bool:
        """Submit a plea for trial"""
        try:
            if not self.is_connected():
                return False
            
            plea_data = {
                'user_id': user_id,
                'plea_text': plea_text,
                'submitted_at': datetime.now().isoformat(),
                'status': 'pending'
            }
            
            self.supabase.table('pleas').insert(plea_data).execute()
            
            logger.info(f"Plea submitted by user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error submitting plea: {e}", exc_info=True)
            return False
    
    def do_prison_work(self, user_id: str) -> Tuple[bool, int]:
        """Do work in prison to earn points and reduce sentence"""
        try:
            if not self.is_connected():
                return False, 0
            
            # Check if user is in prison
            prison_status = self.get_prison_status(user_id)
            if not prison_status:
                return False, 0
            
            # Award points for prison work
            from config import JUSTICE_CONFIG
            reward_points = JUSTICE_CONFIG['prison_work_reward']
            self.add_points(user_id, reward_points)
            
            # Reduce sentence by 30 minutes
            time_reduction = 30 * 60  # 30 minutes
            
            # Update release time
            result = self.supabase.table('prison_records').select('release_at').eq('user_id', user_id).eq('status', 'imprisoned').execute()
            
            if result.data:
                current_release = datetime.fromisoformat(result.data[0]['release_at'])
                new_release = current_release - timedelta(seconds=time_reduction)
                
                # Don't reduce below current time
                if new_release < datetime.now():
                    new_release = datetime.now()
                
                self.supabase.table('prison_records').update({'release_at': new_release.isoformat()}).eq('user_id', user_id).eq('status', 'imprisoned').execute()
            
            # Record work session
            work_data = {
                'user_id': user_id,
                'points_earned': reward_points,
                'time_reduced': time_reduction,
                'worked_at': datetime.now().isoformat()
            }
            
            self.supabase.table('prison_work').insert(work_data).execute()
            
            logger.info(f"Prison work completed by {user_id}: +{reward_points} points, -{time_reduction}s")
            return True, reward_points
            
        except Exception as e:
            logger.error(f"Error doing prison work: {e}", exc_info=True)
            return False, 0

    # === ADMIN SYSTEM METHODS ===
    
    def admin_add_item(self, admin_id: str, target_id: str, item_id: str, quantity: int = 1, reason: str = "") -> bool:
        """Add item to user's inventory (admin action)"""
        try:
            if not self.is_connected():
                return False
            
            # Add items to inventory
            for _ in range(quantity):
                self.add_item_to_inventory(target_id, item_id)
            
            # Log admin action
            log_data = {
                'admin_id': admin_id,
                'target_id': target_id,
                'action': 'add_item',
                'details': {'item_id': item_id, 'quantity': quantity},
                'reason': reason,
                'performed_at': datetime.now().isoformat()
            }
            
            self.supabase.table('admin_actions').insert(log_data).execute()
            
            logger.info(f"Admin {admin_id} added {quantity}x {item_id} to user {target_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error in admin add item: {e}", exc_info=True)
            return False
    
    def admin_remove_item(self, admin_id: str, target_id: str, item_id: str, quantity: int = 1, reason: str = "") -> Tuple[bool, int]:
        """Remove item from user's inventory (admin action)"""
        try:
            if not self.is_connected():
                return False, 0
            
            # Get current inventory
            inventory = self.get_inventory(target_id)
            items_to_remove = min(quantity, inventory.count(item_id))
            
            # Remove items
            for _ in range(items_to_remove):
                self.remove_item_from_inventory(target_id, item_id)
            
            # Log admin action
            log_data = {
                'admin_id': admin_id,
                'target_id': target_id,
                'action': 'remove_item',
                'details': {'item_id': item_id, 'quantity': items_to_remove},
                'reason': reason,
                'performed_at': datetime.now().isoformat()
            }
            
            self.supabase.table('admin_actions').insert(log_data).execute()
            
            logger.info(f"Admin {admin_id} removed {items_to_remove}x {item_id} from user {target_id}")
            return True, items_to_remove
            
        except Exception as e:
            logger.error(f"Error in admin remove item: {e}", exc_info=True)
            return False, 0
    
    def admin_set_user_role(self, admin_id: str, target_id: str, new_role: str, reason: str = "") -> bool:
        """Set user role (admin action)"""
        try:
            if not self.is_connected():
                return False
            
            # Update user role
            role_data = {
                'user_id': target_id,
                'role': new_role,
                'assigned_by': admin_id,
                'assigned_at': datetime.now().isoformat(),
                'reason': reason
            }
            
            # Upsert user role
            self.supabase.table('user_roles').upsert(role_data).execute()
            
            # Log admin action
            log_data = {
                'admin_id': admin_id,
                'target_id': target_id,
                'action': 'set_role',
                'details': {'new_role': new_role},
                'reason': reason,
                'performed_at': datetime.now().isoformat()
            }
            
            self.supabase.table('admin_actions').insert(log_data).execute()
            
            logger.info(f"Admin {admin_id} set role {new_role} for user {target_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting user role: {e}", exc_info=True)
            return False
    
    def get_user_role(self, user_id: str) -> Optional[str]:
        """Get user's current role"""
        try:
            if not self.is_connected():
                return None
            
            result = self.supabase.table('user_roles').select('role').eq('user_id', user_id).execute()
            
            if result.data:
                return result.data[0]['role']
            
            return "member"  # Default role
            
        except Exception as e:
            logger.error(f"Error getting user role: {e}", exc_info=True)
            return "member"
    
    def get_admin_actions(self, admin_id: str = None, target_id: str = None, limit: int = 50) -> List[Dict]:
        """Get admin action history"""
        try:
            if not self.is_connected():
                return []
            
            query = self.supabase.table('admin_actions').select('*').order('performed_at', desc=True).limit(limit)
            
            if admin_id:
                query = query.eq('admin_id', admin_id)
            
            if target_id:
                query = query.eq('target_id', target_id)
            
            result = query.execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting admin actions: {e}", exc_info=True)
            return []

    def save_data(self):
        """Compatibility method - not needed for Supabase"""
        pass
    
    @property
    def data(self) -> Dict:
        """Compatibility property for legacy code"""
        logger.warning("Using legacy data property - consider migrating to specific methods")
        return {}

    # === ADVANCED GANG WARS METHODS (Phase 4B) ===
    
    def create_gang_alliance(self, gang1_id: int, gang2_id: int, proposed_by: str) -> bool:
        """Créer une proposition d'alliance entre gangs"""
        if not self.supabase:
            return False
        
        try:
            result = self.supabase.table('gang_alliances').insert({
                'gang1_id': gang1_id,
                'gang2_id': gang2_id,
                'status': 'pending',
                'proposed_by': proposed_by,
                'created_at': datetime.now().isoformat()
            }).execute()
            
            logger.info(f"Alliance proposed between gangs {gang1_id} and {gang2_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating gang alliance: {e}", exc_info=True)
            return False
    
    def get_gang_alliances(self, gang_id: int) -> List[Dict[str, Any]]:
        """Récupérer les alliances d'un gang"""
        if not self.supabase:
            return []
        
        try:
            result = self.supabase.table('gang_alliances').select('*').or_(
                f'gang1_id.eq.{gang_id},gang2_id.eq.{gang_id}'
            ).execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting gang alliances: {e}", exc_info=True)
            return []
    
    def accept_gang_alliance(self, alliance_id: int) -> bool:
        """Accepter une alliance de gang"""
        if not self.supabase:
            return False
        
        try:
            result = self.supabase.table('gang_alliances').update({
                'status': 'active',
                'accepted_at': datetime.now().isoformat()
            }).eq('id', alliance_id).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error accepting alliance: {e}", exc_info=True)
            return False
    
    def break_gang_alliance(self, alliance_id: int, broken_by: str) -> bool:
        """Rompre une alliance de gang"""
        if not self.supabase:
            return False
        
        try:
            result = self.supabase.table('gang_alliances').update({
                'status': 'broken',
                'broken_by': broken_by,
                'broken_at': datetime.now().isoformat()
            }).eq('id', alliance_id).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error breaking alliance: {e}", exc_info=True)
            return False
    
    def claim_territory(self, gang_id: int, territory_name: str, claimed_by: str) -> bool:
        """Revendiquer un territoire pour un gang"""
        if not self.supabase:
            return False
        
        try:
            # Vérifier si le territoire est déjà pris
            existing = self.supabase.table('gang_territories').select('*').eq(
                'territory_name', territory_name
            ).eq('status', 'claimed').execute()
            
            if existing.data:
                return False  # Territoire déjà pris
            
            # Revendiquer le territoire
            result = self.supabase.table('gang_territories').insert({
                'gang_id': gang_id,
                'territory_name': territory_name,
                'claimed_by': claimed_by,
                'claimed_at': datetime.now().isoformat(),
                'status': 'claimed'
            }).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error claiming territory: {e}", exc_info=True)
            return False
    
    def get_gang_territories(self, gang_id: int) -> List[Dict[str, Any]]:
        """Récupérer les territoires d'un gang"""
        if not self.supabase:
            return []
        
        try:
            result = self.supabase.table('gang_territories').select('*').eq(
                'gang_id', gang_id
            ).eq('status', 'claimed').execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting gang territories: {e}", exc_info=True)
            return []
    
    def add_gang_asset(self, gang_id: int, asset_type: str, asset_data: Dict, added_by: str) -> bool:
        """Ajouter un asset à un gang"""
        if not self.supabase:
            return False
        
        try:
            result = self.supabase.table('gang_assets').insert({
                'gang_id': gang_id,
                'asset_type': asset_type,
                'asset_data': json.dumps(asset_data),
                'added_by': added_by,
                'created_at': datetime.now().isoformat(),
                'status': 'active'
            }).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error adding gang asset: {e}", exc_info=True)
            return False
    
    def get_gang_assets(self, gang_id: int) -> List[Dict[str, Any]]:
        """Récupérer les assets d'un gang"""
        if not self.supabase:
            return []
        
        try:
            result = self.supabase.table('gang_assets').select('*').eq(
                'gang_id', gang_id
            ).eq('status', 'active').execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting gang assets: {e}", exc_info=True)
            return []
    
    def update_gang_reputation(self, gang_id: int, reputation_change: int, reason: str) -> bool:
        """Mettre à jour la réputation d'un gang"""
        if not self.supabase:
            return False
        
        try:
            # Récupérer la réputation actuelle
            gang = self.supabase.table('gangs').select('reputation').eq('id', gang_id).execute()
            if not gang.data:
                return False
            
            current_rep = gang.data[0].get('reputation', 0)
            new_rep = max(-100, min(100, current_rep + reputation_change))  # Clamp entre -100 et 100
            
            # Mettre à jour
            result = self.supabase.table('gangs').update({
                'reputation': new_rep
            }).eq('id', gang_id).execute()
            
            # Logger l'historique
            self.supabase.table('gang_reputation_history').insert({
                'gang_id': gang_id,
                'reputation_change': reputation_change,
                'new_reputation': new_rep,
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            }).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating gang reputation: {e}", exc_info=True)
            return False
    
    def get_gang_reputation(self, gang_id: int) -> int:
        """Récupérer la réputation d'un gang"""
        if not self.supabase:
            return 0
        
        try:
            result = self.supabase.table('gangs').select('reputation').eq('id', gang_id).execute()
            
            if result.data:
                return result.data[0].get('reputation', 0)
            return 0
            
        except Exception as e:
            logger.error(f"Error getting gang reputation: {e}", exc_info=True)
            return 0
    
    def get_all_territories_status(self) -> Dict[str, Dict[str, Any]]:
        """Récupérer le statut de tous les territoires"""
        if not self.supabase:
            return {}
        
        try:
            result = self.supabase.table('gang_territories').select(
                'territory_name, gang_id, claimed_at, gangs(name)'
            ).eq('status', 'claimed').execute()
            
            territories = {}
            for territory in result.data or []:
                territories[territory['territory_name']] = {
                    'gang_id': territory['gang_id'],
                    'gang_name': territory['gangs']['name'] if territory.get('gangs') else 'Unknown',
                    'claimed_at': territory['claimed_at']
                }
            
            return territories
            
        except Exception as e:
            logger.error(f"Error getting territories status: {e}", exc_info=True)
            return {}