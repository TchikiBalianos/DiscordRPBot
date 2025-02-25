import json
import os
from datetime import datetime

class Database:
    def __init__(self):
        self.data = {
            'users': {},
            'rob_cooldowns': {},
            'voice_sessions': {},
            'twitter_links': {},  # Stockage des liens Twitter-Discord
            'twitter_stats': {}   # Stockage des statistiques Twitter précédentes
        }
        self.load_data()

    def load_data(self):
        try:
            if os.path.exists('data.json'):
                with open('data.json', 'r') as f:
                    self.data = json.load(f)
        except Exception as e:
            print(f"Error loading data: {e}")

    def save_data(self):
        try:
            with open('data.json', 'w') as f:
                json.dump(self.data, f)
        except Exception as e:
            print(f"Error saving data: {e}")

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
    def link_twitter_account(self, discord_id, twitter_username):
        """Lie un compte Twitter à un ID Discord"""
        self.data['twitter_links'][str(discord_id)] = twitter_username.lower()
        self.save_data()

    def get_twitter_username(self, discord_id):
        """Récupère le nom d'utilisateur Twitter lié à un ID Discord"""
        return self.data['twitter_links'].get(str(discord_id))

    def get_discord_id_by_twitter(self, twitter_username):
        """Récupère l'ID Discord lié à un nom d'utilisateur Twitter"""
        twitter_username = twitter_username.lower()
        for discord_id, linked_twitter in self.data['twitter_links'].items():
            if linked_twitter == twitter_username:
                return discord_id
        return None

    # Nouvelles méthodes pour les statistiques Twitter
    def get_twitter_stats(self, discord_id):
        """Récupère les statistiques Twitter précédentes d'un utilisateur"""
        return self.data['twitter_stats'].get(str(discord_id), {
            'likes': 0,
            'retweets': 0,
            'comments': 0
        })

    def update_twitter_stats(self, discord_id, stats):
        """Met à jour les statistiques Twitter d'un utilisateur"""
        self.data['twitter_stats'][str(discord_id)] = stats
        self.save_data()

    def get_all_twitter_users(self):
        """Récupère tous les utilisateurs ayant lié leur compte Twitter"""
        return self.data['twitter_links'].items()