import json
import os
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
            'voice_sessions': {},
            'twitter_links': {},
            'twitter_stats': {}
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
            for key in ['users', 'rob_cooldowns', 'voice_sessions', 'twitter_links', 'twitter_stats']:
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

    def get_leaderboard(self):
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