import json
import os
import uuid
from datetime import datetime
import logging
import stat
from typing import Dict, Any, Optional
from config import SHOP_ITEMS_NEW  # Ajout de l'import manquant

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
            'prison_times': {},
            'last_robbers': {},
            'last_work': {},
            'voice_sessions': {},
            'twitter_links': {},
            'twitter_stats': {},
            'prison_roles': {},
            'prison_activities': {},
            'trials': {},
            'trial_cooldowns': {},
            'escape_cooldowns': {},
            'combats': {},
            'daily_commands': {},    # Track daily command usage
            'lottery_tickets': {},    # Track lottery tickets
            'lottery_jackpot': 1000,  # Base lottery jackpot
            'race_bets': {},         # Track race bets
            'roulette_cooldowns': {}, # Track roulette cooldowns
            'losing_streaks': {},     # Track losing streaks for games
            'special_items': {}       # Track special items (NFTs, etc.)
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
            for key in ['users', 'rob_cooldowns', 'voice_sessions', 'twitter_links', 'twitter_stats', 'prison_times', 'last_robbers', 'last_work', 'prison_roles', 'prison_activities', 'trials', 'trial_cooldowns', 'escape_cooldowns', 'combats', 'daily_commands', 'lottery_tickets', 'lottery_jackpot', 'race_bets', 'roulette_cooldowns', 'losing_streaks', 'special_items']:
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

    def start_voice_session(self, user_id, event_name=None):
        """Start tracking voice time for a user"""
        user_id = str(user_id)
        timestamp = datetime.now().timestamp()

        if 'voice_sessions' not in self.data:
            self.data['voice_sessions'] = {}

        self.data['voice_sessions'][user_id] = {
            'start_time': timestamp,
            'event_name': event_name  # Si c'est pendant un événement spécial
        }

        logger.info(f"Started voice session for {user_id}" + (f" during event: {event_name}" if event_name else ""))
        self.save_data()

    def end_voice_session(self, user_id):
        """End voice session and award points"""
        user_id = str(user_id)
        if user_id not in self.data['voice_sessions']:
            return 0

        session = self.data['voice_sessions'][user_id]
        duration = datetime.now().timestamp() - session['start_time']
        points_earned = 0

        # Points de base pour le vocal (1 point par minute)
        base_points = int(duration / 60)

        # Bonus si c'était pendant un événement
        if session.get('event_name'):
            base_points *= 2  # Double points pendant les événements
            logger.info(f"Event bonus applied for {user_id} in {session['event_name']}")

        points_earned = base_points
        self.add_points(user_id, points_earned)

        del self.data['voice_sessions'][user_id]
        self.save_data()

        logger.info(f"Ended voice session for {user_id}. Duration: {duration:.0f}s, Points earned: {points_earned}")
        return duration, points_earned

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

    def add_special_item(self, user_id: str, item_id: str) -> None:
        """Add a special item (NFT, gift card, etc.) to user's inventory"""
        user_id = str(user_id)
        logger.info(f"Adding special item {item_id} to user {user_id}")

        if 'special_items' not in self.data:
            self.data['special_items'] = {}

        if user_id not in self.data['special_items']:
            self.data['special_items'][user_id] = []

        self.data['special_items'][user_id].append({
            'item_id': item_id,
            'acquired_at': datetime.now().timestamp()
        })

        # Update remaining quantity in SHOP_ITEMS_NEW
        if item_id in SHOP_ITEMS_NEW:
            SHOP_ITEMS_NEW[item_id]['quantity'] -= 1

        self.save_data()
        logger.info(f"Successfully added special item {item_id} to user {user_id}")

    def get_special_items(self, user_id: str) -> list:
        """Get user's special items"""
        return self.data.get('special_items', {}).get(str(user_id), [])

    def check_item_availability(self, item_id: str) -> bool:
        """Check if a special item is still available for purchase"""
        if item_id not in SHOP_ITEMS_NEW:
            return False
        return SHOP_ITEMS_NEW[item_id]['quantity'] > 0


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

    def get_daily_usage(self, user_id: str, command: str) -> int:
        """Get number of times a command was used today"""
        user_id = str(user_id)
        today = datetime.now().strftime('%Y-%m-%d')

        if user_id not in self.data['daily_commands']:
            self.data['daily_commands'][user_id] = {}

        if today not in self.data['daily_commands'][user_id]:
            self.data['daily_commands'][user_id][today] = {}

        return self.data['daily_commands'][user_id][today].get(command, 0)

    def increment_daily_usage(self, user_id: str, command: str) -> None:
        """Increment command usage counter"""
        user_id = str(user_id)
        today = datetime.now().strftime('%Y-%m-%d')

        if user_id not in self.data['daily_commands']:
            self.data['daily_commands'][user_id] = {}

        if today not in self.data['daily_commands'][user_id]:
            self.data['daily_commands'][user_id][today] = {}

        current = self.data['daily_commands'][user_id][today].get(command, 0)
        self.data['daily_commands'][user_id][today][command] = current + 1
        self.save_data()

    LOTTERY_MAX_TICKETS = 5 #Example value, adjust as needed
    LOTTERY_TICKET_PRICE = 100 #Example value, adjust as needed
    LOTTERY_JACKPOT_BASE = 1000 #Example value, adjust as needed

    def buy_lottery_ticket(self, user_id: str, numbers: list) -> bool:
        """Buy a lottery ticket"""
        user_id = str(user_id)
        if user_id not in self.data['lottery_tickets']:
            self.data['lottery_tickets'][user_id] = []

        # Check if user hasn't exceeded max tickets
        if len(self.data['lottery_tickets'][user_id]) >= self.LOTTERY_MAX_TICKETS:
            return False

        self.data['lottery_tickets'][user_id].append(numbers)
        self.data['lottery_jackpot'] += self.LOTTERY_TICKET_PRICE // 2  # Half of ticket price goes to jackpot
        self.save_data()
        return True

    def get_lottery_tickets(self, user_id: str) -> list:
        """Get user's lottery tickets"""
        return self.data['lottery_tickets'].get(str(user_id), [])

    def clear_lottery_tickets(self) -> None:
        """Clear all lottery tickets after draw"""
        self.data['lottery_tickets'] = {}
        self.data['lottery_jackpot'] = self.LOTTERY_JACKPOT_BASE
        self.save_data()

    def place_race_bet(self, user_id: str, horse: str, amount: int) -> None:
        """Place a bet on a horse"""
        user_id = str(user_id)
        if 'race_bets' not in self.data:
            self.data['race_bets'] = {}

        self.data['race_bets'][user_id] = {
            'horse': horse,
            'amount': amount,
            'time': datetime.now().timestamp()
        }
        self.save_data()

    def get_race_bet(self, user_id: str) -> dict:
        """Get user's race bet"""
        return self.data.get('race_bets', {}).get(str(user_id))

    def clear_race_bets(self) -> None:
        """Clear all race bets"""
        self.data['race_bets'] = {}
        self.save_data()

    def set_roulette_cooldown(self, user_id: str) -> None:
        """Set roulette cooldown"""
        self.data['roulette_cooldowns'][str(user_id)] = datetime.now().timestamp()
        self.save_data()

    def get_roulette_cooldown(self, user_id: str) -> float:
        """Get roulette cooldown"""
        return self.data['roulette_cooldowns'].get(str(user_id), 0)

    def get_losing_streak(self, user_id: str, game_type: str) -> int:
        """Get current losing streak for a specific game"""
        if 'losing_streaks' not in self.data:
            self.data['losing_streaks'] = {}

        if user_id not in self.data['losing_streaks']:
            self.data['losing_streaks'][user_id] = {}

        return self.data['losing_streaks'][user_id].get(game_type, 0)

    def update_losing_streak(self, user_id: str, game_type: str, won: bool) -> None:
        """Update losing streak counter"""
        if 'losing_streaks' not in self.data:
            self.data['losing_streaks'] = {}

        if user_id not in self.data['losing_streaks']:
            self.data['losing_streaks'][user_id] = {}

        if won:
            self.data['losing_streaks'][user_id][game_type] = 0
        else:
            current = self.data['losing_streaks'][user_id].get(game_type, 0)
            self.data['losing_streaks'][user_id][game_type] = current + 1
        self.save_data()

    DICE_LOSING_STREAK_PENALTY = 0.2 #Example value, adjust as needed
    BLACKJACK_STREAK_PENALTY = True #Example value, adjust as needed

    def calculate_penalty_multiplier(self, user_id: str, game_type: str) -> float:
        """Calculate penalty multiplier based on losing streak"""
        streak = self.get_losing_streak(user_id, game_type)
        if game_type == 'dice' and streak >= 3:
            return 1 + self.DICE_LOSING_STREAK_PENALTY
        elif game_type == 'blackjack' and self.BLACKJACK_STREAK_PENALTY:
            return 1 + (0.1 * min(streak, 5))  # Max 50% additional loss after 5 losses
        return 1.0

    def add_twitter_interaction(self, discord_id: str, interaction_type: str, count: int = 1):
        """Track Twitter interactions (likes, RT, replies)"""
        discord_id = str(discord_id)
        if 'twitter_stats' not in self.data:
            self.data['twitter_stats'] = {}

        if discord_id not in self.data['twitter_stats']:
            self.data['twitter_stats'][discord_id] = {
                'likes': 0,
                'retweets': 0,
                'replies': 0,
                'month': datetime.now().month,
                'year': datetime.now().year
            }

        # Points par type d'interaction
        points_per_action = {
            'like': 1,
            'retweet': 3,
            'reply': 2
        }

        if interaction_type in points_per_action:
            self.data['twitter_stats'][discord_id][interaction_type + 's'] += count
            points = points_per_action[interaction_type] * count
            self.add_points(discord_id, points)
            logger.info(f"Added {count} {interaction_type}(s) for {discord_id}, earned {points} points")

        self.save_data()

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

    def add_special_item(self, user_id: str, item_id: str) -> None:
        """Add a special item (NFT, gift card, etc.) to user's inventory"""
        user_id = str(user_id)
        logger.info(f"Adding special item {item_id} to user {user_id}")

        if 'special_items' not in self.data:
            self.data['special_items'] = {}

        if user_id not in self.data['special_items']:
            self.data['special_items'][user_id] = []

        self.data['special_items'][user_id].append({
            'item_id': item_id,
            'acquired_at': datetime.now().timestamp()
        })

        # Update remaining quantity in SHOP_ITEMS_NEW
        if item_id in SHOP_ITEMS_NEW:
            SHOP_ITEMS_NEW[item_id]['quantity'] -= 1

        self.save_data()
        logger.info(f"Successfully added special item {item_id} to user {user_id}")

    def get_special_items(self, user_id: str) -> list:
        """Get user's special items"""
        return self.data.get('special_items', {}).get(str(user_id), [])

    def check_item_availability(self, item_id: str) -> bool:
        """Check if a special item is still available for purchase"""
        if item_id not in SHOP_ITEMS_NEW:
            return False
        return SHOP_ITEMS_NEW[item_id]['quantity'] > 0


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

    def get_daily_usage(self, user_id: str, command: str) -> int:
        """Get number of times a command was used today"""
        user_id = str(user_id)
        today = datetime.now().strftime('%Y-%m-%d')

        if user_id not in self.data['daily_commands']:
            self.data['daily_commands'][user_id] = {}

        if today not in self.data['daily_commands'][user_id]:
            self.data['daily_commands'][user_id][today] = {}

        return self.data['daily_commands'][user_id][today].get(command, 0)

    def increment_daily_usage(self, user_id: str, command: str) -> None:
        """Increment command usage counter"""
        user_id = str(user_id)
        today = datetime.now().strftime('%Y-%m-%d')

        if user_id not in self.data['daily_commands']:
            self.data['daily_commands'][user_id] = {}

        if today not in self.data['daily_commands'][user_id]:
            self.data['daily_commands'][user_id][today] = {}

        current = self.data['daily_commands'][user_id][today].get(command, 0)
        self.data['daily_commands'][user_id][today][command] = current + 1
        self.save_data()

    LOTTERY_MAX_TICKETS = 5 #Example value, adjust as needed
    LOTTERY_TICKET_PRICE = 100 #Example value, adjust as needed
    LOTTERY_JACKPOT_BASE = 1000 #Example value, adjust as needed

    def buy_lottery_ticket(self, user_id: str, numbers: list) -> bool:
        """Buy a lottery ticket"""
        user_id = str(user_id)
        if user_id not in self.data['lottery_tickets']:
            self.data['lottery_tickets'][user_id] = []

        # Check if user hasn't exceeded max tickets
        if len(self.data['lottery_tickets'][user_id]) >= self.LOTTERY_MAX_TICKETS:
            return False

        self.data['lottery_tickets'][user_id].append(numbers)
        self.data['lottery_jackpot'] += self.LOTTERY_TICKET_PRICE // 2  # Half of ticket price goes to jackpot
        self.save_data()
        return True

    def get_lottery_tickets(self, user_id: str) -> list:
        """Get user's lottery tickets"""
        return self.data['lottery_tickets'].get(str(user_id), [])

    def clear_lottery_tickets(self) -> None:
        """Clear all lottery tickets after draw"""
        self.data['lottery_tickets'] = {}
        self.data['lottery_jackpot'] = self.LOTTERY_JACKPOT_BASE
        self.save_data()

    def place_race_bet(self, user_id: str, horse: str, amount: int) -> None:
        """Place a bet on a horse"""
        user_id = str(user_id)
        if 'race_bets' not in self.data:
            self.data['race_bets'] = {}

        self.data['race_bets'][user_id] = {
            'horse': horse,
            'amount': amount,
            'time': datetime.now().timestamp()
        }
        self.save_data()

    def get_race_bet(self, user_id: str) -> dict:
        """Get user's race bet"""
        return self.data.get('race_bets', {}).get(str(user_id))

    def clear_race_bets(self) -> None:
        """Clear all race bets"""
        self.data['race_bets'] = {}
        self.save_data()

    def set_roulette_cooldown(self, user_id: str) -> None:
        """Set roulette cooldown"""
        self.data['roulette_cooldowns'][str(user_id)] = datetime.now().timestamp()
        self.save_data()

    def get_roulette_cooldown(self, user_id: str) -> float:
        """Get roulette cooldown"""
        return self.data['roulette_cooldowns'].get(str(user_id), 0)

    def get_losing_streak(self, user_id: str, game_type: str) -> int:
        """Get current losing streak for a specific game"""
        if 'losing_streaks' not in self.data:
            self.data['losing_streaks'] = {}

        if user_id not in self.data['losing_streaks']:
            self.data['losing_streaks'][user_id] = {}

        return self.data['losing_streaks'][user_id].get(game_type, 0)

    def update_losing_streak(self, user_id: str, game_type: str, won: bool) -> None:
        """Update losing streak counter"""
        if 'losing_streaks' not in self.data:
            self.data['losing_streaks'] = {}

        if user_id not in self.data['losing_streaks']:
            self.data['losing_streaks'][user_id] = {}

        if won:
            self.data['losing_streaks'][user_id][game_type] = 0
        else:
            current = self.data['losing_streaks'][user_id].get(game_type, 0)
            self.data['losing_streaks'][user_id][game_type] = current + 1
        self.save_data()

    DICE_LOSING_STREAK_PENALTY = 0.2 #Example value, adjust as needed
    BLACKJACK_STREAK_PENALTY = True #Example value, adjust as needed

    def calculate_penalty_multiplier(self, user_id: str, game_type: str) -> float:
        """Calculate penalty multiplier based on losing streak"""
        streak = self.get_losing_streak(user_id, game_type)
        if game_type == 'dice' and streak >= 3:
            return 1 + self.DICE_LOSING_STREAK_PENALTY
        elif game_type == 'blackjack' and self.BLACKJACK_STREAK_PENALTY:
            return 1 + (0.1 * min(streak, 5))  # Max 50% additional loss after 5 losses
        return 1.0

    def end_voice_session(self, user_id):
        """End voice session and award points"""
        user_id = str(user_id)
        if user_id not in self.data['voice_sessions']:
            return 0

        session = self.data['voice_sessions'][user_id]
        duration = datetime.now().timestamp() - session['start_time']
        points_earned = 0

        # Points de base pour le vocal (1 point par minute)
        base_points = int(duration / 60)

        # Bonus si c'était pendant un événement
        if session.get('event_name'):
            base_points *= 2  # Double points pendant les événements
            logger.info(f"Event bonus applied for {user_id} in {session['event_name']}")

        points_earned = base_points
        self.add_points(user_id, points_earned)

        del self.data['voice_sessions'][user_id]
        self.save_data()

        logger.info(f"Ended voice session for {user_id}. Duration: {duration:.0f}s, Points earned: {points_earned}")
        return duration, points_earned