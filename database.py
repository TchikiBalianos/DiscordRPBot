import json
import os
import uuid
from datetime import datetime
import logging
import stat
from typing import Dict, Any, Optional

logger = logging.getLogger('EngagementBot')

class Database:
    def __init__(self):
        """Initialize database with empty structure and load data"""
        logger.info("Initializing database...")
        self._initialize_empty_structure()
        self.load_data()
        logger.info("Database initialization complete")

    def _initialize_empty_structure(self):
        """Initialize empty data structure with all required keys"""
        self.data: Dict[str, Dict[str, Any]] = {
            'users': {},
            'rob_cooldowns': {},
            'prison_times': {},  # New: Track prison sentences
            'last_robbers': {},  # New: Track who robbed whom
            'last_work': {},     # New: Track daily work
            'voice_sessions': {},
            'twitter_links': {},
            'twitter_stats': {},
            'prison_roles': {},
            'prison_activities': {},
            'trials': {},
            'trial_cooldowns': {},
            'escape_cooldowns': {}, # Added for escape cooldown
            'combats': {} # Added for combat system
        }
        logger.info("Empty data structure initialized")

    def load_data(self):
        """Load data from JSON file with initialization if needed"""
        try:
            logger.info("Attempting to load data from data.json")

            if os.path.exists('data.json'):
                # Check file permissions
                st = os.stat('data.json')
                is_writable = bool(st.st_mode & stat.S_IWUSR)
                logger.info(f"data.json exists and is {'writable' if is_writable else 'not writable'}")

                if not is_writable:
                    logger.warning("data.json exists but is not writable, attempting to fix permissions")
                    os.chmod('data.json', st.st_mode | stat.S_IWUSR)

                try:
                    with open('data.json', 'r') as f:
                        loaded_data = json.load(f)
                        logger.info("Successfully read data.json")

                        # Ensure all required keys exist with proper types
                        for key in self.data.keys():
                            if key not in loaded_data or not isinstance(loaded_data[key], dict):
                                logger.warning(f"Missing or invalid key {key} in loaded data, using empty dict")
                                loaded_data[key] = {}

                        self.data = loaded_data
                        logger.info("Successfully loaded and validated data structure")
                        logger.debug(f"Current data state: {self.data}")
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding data.json: {e}", exc_info=True)
                    logger.info("Creating new data.json with default structure due to corruption")
                    self._initialize_empty_structure()
                    self.save_data()
            else:
                logger.info("No existing data.json found, creating new file with default structure")
                # Create the data.json file with proper permissions
                try:
                    with open('data.json', 'w') as f:
                        json.dump(self.data, f, indent=2)
                    os.chmod('data.json', stat.S_IRUSR | stat.S_IWUSR)
                    logger.info("Successfully created new data.json file")
                except Exception as e:
                    logger.error(f"Error creating data.json: {e}", exc_info=True)
                    raise RuntimeError(f"Failed to create data.json: {str(e)}")

        except Exception as e:
            logger.error(f"Error loading data: {e}", exc_info=True)
            raise RuntimeError(f"Failed to load data: {str(e)}")

    def save_data(self):
        """Save current data to JSON file with detailed error logging"""
        try:
            logger.info("Attempting to save data to data.json")
            logger.debug(f"Current data state: {self.data}")

            # Validate data structure
            if not isinstance(self.data, dict):
                raise ValueError("Data must be a dictionary")

            # Ensure all required sections exist
            for key in ['users', 'rob_cooldowns', 'voice_sessions', 'twitter_links', 'twitter_stats', 'prison_times', 'last_robbers', 'last_work', 'prison_roles', 'prison_activities', 'trials', 'trial_cooldowns', 'escape_cooldowns', 'combats']: # Added new keys
                if key not in self.data:
                    logger.warning(f"Missing key {key} in data, initializing empty")
                    self.data[key] = {}
                if not isinstance(self.data[key], dict):
                    raise ValueError(f"Data[{key}] must be a dictionary")

            # Ensure the directory is writable
            try:
                with open('test_write', 'w') as f:
                    f.write('test')
                os.remove('test_write')
                logger.info("Directory is writable")
            except Exception as e:
                logger.error(f"Directory is not writable: {e}", exc_info=True)
                raise RuntimeError("Directory is not writable")

            # Create a temporary file first
            temp_file = 'data.json.tmp'
            logger.debug(f"Writing to temporary file: {temp_file}")

            try:
                with open(temp_file, 'w') as f:
                    json.dump(self.data, f, indent=2)
                logger.info(f"Successfully wrote to temporary file {temp_file}")
            except Exception as e:
                logger.error(f"Error writing to temporary file: {e}", exc_info=True)
                raise RuntimeError(f"Failed to write temporary file: {str(e)}")

            # If successful, rename to the actual file
            try:
                logger.debug(f"Attempting to replace data.json with {temp_file}")
                os.replace(temp_file, 'data.json')
                os.chmod('data.json', stat.S_IRUSR | stat.S_IWUSR)
                logger.info("Successfully saved data to data.json")
            except Exception as e:
                logger.error(f"Error replacing data.json with temporary file: {e}", exc_info=True)
                raise RuntimeError(f"Failed to replace data.json: {str(e)}")

            # Verify the save was successful
            if os.path.exists('data.json'):
                st = os.stat('data.json')
                logger.info(f"Verified data.json exists with size {st.st_size} bytes")
            else:
                raise RuntimeError("data.json not found after save")

        except Exception as e:
            logger.error(f"Error saving data: {e}", exc_info=True)
            if os.path.exists('data.json.tmp'):
                try:
                    logger.info("Cleaning up temporary file")
                    os.remove('data.json.tmp')
                except Exception as cleanup_error:
                    logger.error(f"Error cleaning up temporary file: {cleanup_error}")
            raise RuntimeError(f"Failed to save data: {str(e)}")

    def link_twitter_account(self, discord_id: str, twitter_username: str) -> None:
        """Link Discord ID to Twitter username with enhanced error handling"""
        try:
            discord_id = str(discord_id)
            twitter_username = twitter_username.lower()

            logger.info(f"Attempting to link Twitter {twitter_username} to Discord {discord_id}")

            # Verify data structure
            if 'twitter_links' not in self.data:
                logger.info("Initializing twitter_links in data structure")
                self.data['twitter_links'] = {}

            if 'twitter_stats' not in self.data:
                logger.info("Initializing twitter_stats in data structure")
                self.data['twitter_stats'] = {}

            # Store the link
            self.data['twitter_links'][discord_id] = twitter_username
            logger.info(f"Successfully stored Twitter link in memory")

            # Initialize stats
            if discord_id not in self.data['twitter_stats']:
                self.data['twitter_stats'][discord_id] = {
                    'likes': 0,
                    'month': datetime.now().month,
                    'year': datetime.now().year,
                    'last_reset': datetime.now().timestamp()
                }
                logger.info(f"Initialized Twitter stats for {discord_id}")

            # Save to file
            self.save_data()
            logger.info(f"Successfully saved Twitter link and stats for {discord_id}")

        except Exception as e:
            logger.error(f"Error in link_twitter_account: {e}", exc_info=True)
            raise RuntimeError(f"Failed to link Twitter account: {str(e)}")

    def get_user_points(self, user_id):
        return self.data['users'].get(str(user_id), {'points': 0})['points']

    def add_points(self, user_id, points):
        user_id = str(user_id)
        if user_id not in self.data['users']:
            self.data['users'][user_id] = {'points': 0}
        self.data['users'][user_id]['points'] += points
        self.save_data()

    def set_rob_cooldown(self, user_id):
        self.data['rob_cooldowns'][str(user_id)] = datetime.now().timestamp()
        self.save_data()

    def get_rob_cooldown(self, user_id):
        return self.data['rob_cooldowns'].get(str(user_id), 0)

    # New methods for prison system
    def set_prison_time(self, user_id, release_time):
        self.data['prison_times'][str(user_id)] = release_time
        self.save_data()

    def get_prison_time(self, user_id):
        return self.data['prison_times'].get(str(user_id), 0)

    # New methods for revenge system
    def set_last_robber(self, victim_id, robber_id):
        self.data['last_robbers'][str(victim_id)] = str(robber_id)
        self.save_data()

    def get_last_robber(self, victim_id):
        return self.data['last_robbers'].get(str(victim_id))

    def clear_last_robber(self, victim_id):
        self.data['last_robbers'].pop(str(victim_id), None)
        self.save_data()

    # New methods for daily work
    def set_last_work(self, user_id, timestamp):
        self.data['last_work'][str(user_id)] = timestamp
        self.save_data()

    def get_last_work(self, user_id):
        return self.data['last_work'].get(str(user_id), 0)

    def get_leaderboard(self):
        """Get monthly leaderboard with reset check"""
        current_month = datetime.now().month
        current_year = datetime.now().year

        # Check if we need to reset the leaderboard
        if not hasattr(self, '_last_reset_month') or self._last_reset_month != current_month:
            logger.info("Monthly leaderboard reset")
            self.data['users'] = {user_id: {'points': 0} for user_id in self.data['users']}
            self._last_reset_month = current_month
            self.save_data()

        sorted_users = sorted(
            self.data['users'].items(),
            key=lambda x: x[1]['points'],
            reverse=True
        )
        return sorted_users

    def start_voice_session(self, user_id):
        self.data['voice_sessions'][str(user_id)] = datetime.now().timestamp()
        self.save_data()

    def end_voice_session(self, user_id):
        user_id = str(user_id)
        if user_id in self.data['voice_sessions']:
            start_time = self.data['voice_sessions'][user_id]
            duration = datetime.now().timestamp() - start_time
            del self.data['voice_sessions'][user_id]
            self.save_data()
            return duration
        return 0

    # Méthodes pour la gestion Twitter    
    def get_twitter_username(self, discord_id):
        """Récupère le nom d'utilisateur Twitter lié à un ID Discord"""
        discord_id = str(discord_id)
        username = self.data['twitter_links'].get(discord_id)
        logger.info(f"Retrieved Twitter username for Discord ID {discord_id}: {username}")
        return username

    def get_discord_id_by_twitter(self, twitter_username):
        """Récupère l'ID Discord lié à un nom d'utilisateur Twitter"""
        twitter_username = twitter_username.lower()
        for discord_id, linked_twitter in self.data['twitter_links'].items():
            if linked_twitter == twitter_username:
                return discord_id
        return None

    def get_twitter_stats(self, discord_id):
        """Récupère les statistiques Twitter du mois en cours pour un utilisateur"""
        discord_id = str(discord_id)
        if discord_id not in self.data['twitter_stats']:
            return {
                'likes': 0,
                'month': datetime.now().month,
                'year': datetime.now().year,
                'last_reset': datetime.now().timestamp()
            }

        stats = self.data['twitter_stats'][discord_id]
        current_month = datetime.now().month
        current_year = datetime.now().year

        # Si on a changé de mois, on réinitialise les stats
        if (stats.get('month', 0) != current_month or 
            stats.get('year', 0) != current_year):
            stats = {
                'likes': 0,
                'month': current_month,
                'year': current_year,
                'last_reset': datetime.now().timestamp()
            }
            self.data['twitter_stats'][discord_id] = stats
            self.save_data()

        return stats

    def update_twitter_stats(self, discord_id, new_stats):
        """Met à jour les statistiques Twitter d'un utilisateur"""
        discord_id = str(discord_id)
        current_stats = self.get_twitter_stats(discord_id)  # Ceci va gérer la réinitialisation si nécessaire

        try:
            self.data['twitter_stats'][discord_id] = {
                'likes': new_stats.get('likes', 0),
                'month': datetime.now().month,
                'year': datetime.now().year,
                'last_reset': current_stats.get('last_reset', datetime.now().timestamp())
            }
            self.save_data()
            logger.info(f"Successfully updated Twitter stats for {discord_id}")
        except Exception as e:
            logger.error(f"Error updating Twitter stats: {e}", exc_info=True)
            raise

    def get_all_twitter_users(self):
        """Récupère tous les utilisateurs ayant lié leur compte Twitter"""
        return self.data['twitter_links'].items()

    def add_item_to_inventory(self, user_id: str, item_id: str):
        """Add an item to user's inventory"""
        user_id = str(user_id)
        if 'inventories' not in self.data:
            self.data['inventories'] = {}
        if user_id not in self.data['inventories']:
            self.data['inventories'][user_id] = []
        self.data['inventories'][user_id].append(item_id)
        self.save_data()

    def get_inventory(self, user_id: str):
        """Get user's inventory"""
        return self.data.get('inventories', {}).get(str(user_id), [])

    def get_active_heist(self):
        """Get active heist if any"""
        return self.data.get('active_heist')

    def create_heist(self, leader_id: str):
        """Create a new heist"""
        self.data['active_heist'] = {
            'leader': str(leader_id),
            'participants': [str(leader_id)],
            'start_time': datetime.now().timestamp()
        }
        self.save_data()

    def add_heist_participant(self, user_id: str):
        """Add participant to active heist"""
        if 'active_heist' in self.data:
            self.data['active_heist']['participants'].append(str(user_id))
            self.save_data()

    def clear_active_heist(self):
        """Clear active heist"""
        if 'active_heist' in self.data:
            del self.data['active_heist']
            self.save_data()

    def set_drug_deal_cooldown(self, user_id: str):
        """Set drug deal cooldown"""
        if 'drug_deal_cooldowns' not in self.data:
            self.data['drug_deal_cooldowns'] = {}
        self.data['drug_deal_cooldowns'][str(user_id)] = datetime.now().timestamp()
        self.save_data()

    def get_drug_deal_cooldown(self, user_id: str):
        """Get drug deal cooldown"""
        return self.data.get('drug_deal_cooldowns', {}).get(str(user_id), 0)

    def set_chase_cooldown(self, user_id: str):
        """Set police chase cooldown"""
        if 'chase_cooldowns' not in self.data:
            self.data['chase_cooldowns'] = {}
        self.data['chase_cooldowns'][str(user_id)] = datetime.now().timestamp()
        self.save_data()

    def get_chase_cooldown(self, user_id: str):
        """Get police chase cooldown"""
        return self.data.get('chase_cooldowns', {}).get(str(user_id), 0)

    def set_prison_role(self, user_id: str, role: str):
        """Set prison role for user"""
        if 'prison_roles' not in self.data:
            self.data['prison_roles'] = {}
        self.data['prison_roles'][str(user_id)] = role
        self.save_data()

    def get_prison_role(self, user_id: str):
        """Get user's prison role"""
        return self.data.get('prison_roles', {}).get(str(user_id))

    def set_last_prison_activity(self, user_id: str, timestamp: float):
        """Set timestamp of last prison activity"""
        if 'prison_activities' not in self.data:
            self.data['prison_activities'] = {}
        self.data['prison_activities'][str(user_id)] = timestamp
        self.save_data()

    def get_last_prison_activity(self, user_id: str):
        """Get timestamp of last prison activity"""
        return self.data.get('prison_activities', {}).get(str(user_id), 0)

    def create_trial(self, user_id: str, plea: str, end_time: float):
        """Create a new trial"""
        if 'trials' not in self.data:
            self.data['trials'] = {}
        self.data['trials'][str(user_id)] = {
            'plea': plea,
            'end_time': end_time,
            'votes': {}
        }
        self.save_data()

    def get_active_trial(self, user_id: str):
        """Get active trial for user"""
        return self.data.get('trials', {}).get(str(user_id))

    def add_trial_vote(self, defendant_id: str, voter_id: str, vote: bool):
        """Add a vote to a trial"""
        if 'trials' in self.data and str(defendant_id) in self.data['trials']:
            self.data['trials'][str(defendant_id)]['votes'][str(voter_id)] = vote
            self.save_data()

    def get_trial_votes(self, user_id: str):
        """Get votes for a trial"""
        trial = self.get_active_trial(user_id)
        return trial['votes'] if trial else {}

    def clear_active_trial(self, user_id: str):
        """Clear active trial"""
        if 'trials' in self.data:
            self.data['trials'].pop(str(user_id), None)
            self.save_data()

    def set_trial_cooldown(self, user_id: str, timestamp: float):
        """Set trial cooldown"""
        if 'trial_cooldowns' not in self.data:
            self.data['trial_cooldowns'] = {}
        self.data['trial_cooldowns'][str(user_id)] = timestamp
        self.save_data()

    def get_trial_cooldown(self, user_id: str):
        """Get trial cooldown"""
        return self.data.get('trial_cooldowns', {}).get(str(user_id), 0)

    def get_escape_cooldown(self, user_id: str):
        """Get last escape attempt timestamp"""
        return self.data.get('escape_cooldowns', {}).get(str(user_id), 0)

    def set_escape_cooldown(self, user_id: str, timestamp: float):
        """Set escape attempt cooldown"""
        if 'escape_cooldowns' not in self.data:
            self.data['escape_cooldowns'] = {}
        self.data['escape_cooldowns'][str(user_id)] = timestamp
        self.save_data()

    def create_combat(self, combat_data: dict):
        """Create a new combat"""
        if 'combats' not in self.data:
            self.data['combats'] = {}
        combat_id = str(uuid.uuid4())
        self.data['combats'][combat_id] = combat_data
        self.save_data()
        return combat_id

    def get_combat(self, combat_id: str):
        """Get combat data"""
        return self.data.get('combats', {}).get(combat_id)

    def update_combat(self, combat_id: str, combat_data: dict):
        """Update combat data"""
        if 'combats' in self.data and combat_id in self.data['combats']:
            self.data['combats'][combat_id] = combat_data
            self.save_data()

    def end_combat(self, combat_id: str):
        """End and remove combat"""
        if 'combats' in self.data:
            self.data['combats'].pop(combat_id, None)
            self.save_data()