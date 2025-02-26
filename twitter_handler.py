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

            # Initialize client for Twitter API v2 with basic configuration
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

    async def _handle_rate_limit(self, operation, max_retries=3, initial_delay=5):
        last_exception = None
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                result = await operation()
                logger.debug(f"Operation completed in {time.time() - start_time:.2f}s")
                return result
            except tweepy.errors.TooManyRequests as e:
                wait_time = int(e.response.headers.get('x-rate-limit-reset', 60))
                logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    raise ValueError("Limite de requêtes Twitter atteinte. Réessayez dans quelques minutes.")
                await asyncio.sleep(wait_time)
            except Exception as e:
                delay = initial_delay * (2 ** attempt)  # Exponential backoff
                logger.error(f"Error during operation (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    if isinstance(e, tweepy.errors.Unauthorized):
                        raise ValueError("Accès non autorisé à Twitter. Vérifiez les permissions du compte.")
                    elif isinstance(e, tweepy.errors.NotFound):
                        raise ValueError("Compte Twitter introuvable.")
                    else:
                        raise ValueError(f"Erreur Twitter: {str(e)}")
                await asyncio.sleep(delay)

    def _test_connection(self):
        try:
            logger.debug("Testing Twitter API connection...")
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
            start_time = time.time()

            # Get user ID
            user_response = await self._handle_rate_limit(
                lambda: self.client.get_user(username=username)
            )

            if not user_response or not user_response.get('data'):
                raise ValueError(f"Le compte Twitter @{username} n'existe pas.")

            user_id = user_response['data']['id']
            logger.debug(f"Found Twitter user {username} with ID {user_id}")

            # Get tweets
            tweets_response = await self._handle_rate_limit(
                lambda: self.client.get_users_tweets(
                    user_id,
                    max_results=10,
                    tweet_fields=['public_metrics']
                )
            )

            if not tweets_response or not tweets_response.get('data'):
                logger.debug(f"No tweets found for user {username}")
                return {'likes': 0, 'retweets': 0, 'comments': 0}

            activity = {'likes': 0, 'retweets': 0, 'comments': 0}
            for tweet in tweets_response['data']:
                metrics = tweet['public_metrics']
                activity['likes'] += metrics.get('like_count', 0)
                activity['retweets'] += metrics.get('retweet_count', 0)
                activity['comments'] += metrics.get('reply_count', 0)

            logger.debug(f"Activity fetched in {time.time() - start_time:.2f}s: {activity}")
            return activity

        except ValueError as e:
            # Déjà formaté pour l'utilisateur
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