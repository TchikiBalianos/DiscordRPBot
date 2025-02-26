import tweepy
from config import *
import logging
import asyncio
import os
from datetime import datetime

logger = logging.getLogger('EngagementBot')

class TwitterHandler:
    def __init__(self):
        try:
            logger.info("Initializing Twitter API...")
            bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
            if not bearer_token:
                logger.error("Bearer Token is missing")
                raise ValueError("Bearer Token is required for Twitter API v2")

            # Configuration simple avec wait_on_rate_limit
            self.client = tweepy.Client(
                bearer_token=bearer_token,
                consumer_key=TWITTER_API_KEY,
                consumer_secret=TWITTER_API_SECRET,
                return_type=dict,
                wait_on_rate_limit=True
            )

            if not self.client:
                raise Exception("Twitter client initialization failed")

            # Test initial de la connexion
            self._test_connection()
            logger.info("Twitter API initialization successful")

        except Exception as e:
            logger.error(f"Error initializing Twitter API: {e}")
            raise

    def _test_connection(self):
        try:
            response = self.client.get_user(username="X")
            if not response or not response.get('data'):
                raise Exception("Could not get test user info")
            logger.info("Twitter API connection test successful")
        except Exception as e:
            logger.error(f"Twitter API connection test failed: {e}")
            raise

    async def get_user_activity(self, username):
        """Récupère l'activité d'un utilisateur Twitter de manière asynchrone"""
        try:
            logger.info(f"Getting activity for Twitter user: {username}")

            # Utilise asyncio pour éviter le blocage
            loop = asyncio.get_event_loop()
            user_response = await loop.run_in_executor(
                None, 
                lambda: self.client.get_user(username=username)
            )

            if not user_response or not user_response.get('data'):
                logger.warning(f"User not found: {username}")
                return None

            user_id = user_response['data']['id']

            # Récupère les tweets récents
            tweets_response = await loop.run_in_executor(
                None,
                lambda: self.client.get_users_tweets(
                    user_id,
                    max_results=5,
                    tweet_fields=['public_metrics']
                )
            )

            if not tweets_response or not tweets_response.get('data'):
                logger.info(f"No tweets found for user {username}")
                return {'likes': 0, 'retweets': 0, 'comments': 0}

            # Calcule les métriques totales
            activity = {'likes': 0, 'retweets': 0, 'comments': 0}
            for tweet in tweets_response['data']:
                metrics = tweet.get('public_metrics', {})
                activity['likes'] += metrics.get('like_count', 0)
                activity['retweets'] += metrics.get('retweet_count', 0)
                activity['comments'] += metrics.get('reply_count', 0)

            logger.info(f"Successfully retrieved activity for {username}: {activity}")
            return activity

        except Exception as e:
            logger.error(f"Error getting Twitter activity: {e}", exc_info=True)
            return None