import tweepy
from config import *
import logging
import os
import asyncio
import time
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

            logger.info("Twitter Bearer Token is present")
            logger.info(f"Twitter API Key present: {bool(TWITTER_API_KEY)}")
            logger.info(f"Twitter API Secret present: {bool(TWITTER_API_SECRET)}")

            # Configuration simple avec wait_on_rate_limit
            self.client = tweepy.Client(
                bearer_token=bearer_token,
                consumer_key=TWITTER_API_KEY,
                consumer_secret=TWITTER_API_SECRET,
                return_type=dict,
                wait_on_rate_limit=True
            )

            if not self.client:
                logger.error("Failed to initialize Twitter client")
                raise Exception("Twitter client initialization failed")

            # Test the connection
            self._test_connection()
            logger.info("Twitter API initialization successful")

        except Exception as e:
            logger.error(f"Error initializing Twitter API: {e}")
            logger.exception("Full initialization error traceback:")
            raise

    def _test_connection(self):
        try:
            logger.debug("Testing Twitter API connection...")
            time.sleep(2)  # Petit délai pour éviter les limites de taux
            response = self.client.get_user(username="X")
            if response and response.get('data'):
                logger.info("Twitter API connection test successful")
            else:
                logger.error("Twitter API test failed - Could not get test user info")
                raise Exception("Failed to get test user info")
        except Exception as e:
            logger.error(f"Twitter API connection test failed: {e}")
            logger.exception("Full test connection traceback:")
            raise

    async def get_user_activity(self, username):
        if not self.client:
            logger.error("Twitter API not initialized")
            raise ValueError("Configuration Twitter invalide")

        try:
            logger.debug(f"Fetching Twitter activity for user {username}")
            time.sleep(1)  # Petit délai pour éviter les limites de taux

            # Get user ID
            user_response = self.client.get_user(username=username)
            if not user_response or not user_response.get('data'):
                raise ValueError(f"Le compte Twitter @{username} n'existe pas.")

            user_id = user_response['data']['id']
            logger.debug(f"Found Twitter user {username} with ID {user_id}")

            time.sleep(1)  # Petit délai entre les requêtes

            # Get tweets with basic metrics
            tweets_response = self.client.get_users_tweets(
                user_id,
                max_results=5,  # Réduit à 5 pour moins de données
                tweet_fields=['public_metrics']
            )

            if not tweets_response or not tweets_response.get('data'):
                logger.debug(f"No tweets found for user {username}")
                return {'likes': 0, 'retweets': 0, 'comments': 0}

            activity = {'likes': 0, 'retweets': 0, 'comments': 0}
            for tweet in tweets_response['data']:
                metrics = tweet.get('public_metrics', {})
                activity['likes'] += metrics.get('like_count', 0)
                activity['retweets'] += metrics.get('retweet_count', 0)
                activity['comments'] += metrics.get('reply_count', 0)

            logger.info(f"Activity for {username}: {activity}")
            return activity

        except ValueError as e:
            raise
        except tweepy.errors.TooManyRequests:
            logger.error("Rate limit exceeded")
            raise ValueError("Trop de requêtes Twitter. Attendez quelques minutes.")
        except tweepy.errors.Unauthorized:
            logger.error("Unauthorized access")
            raise ValueError("Accès non autorisé à Twitter.")
        except Exception as e:
            logger.error(f"Error fetching Twitter activity: {e}")
            logger.exception("Full traceback:")
            raise ValueError("Une erreur inattendue est survenue. Réessayez plus tard.")