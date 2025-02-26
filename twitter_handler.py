import tweepy
from config import *
import logging
import os
import time
import asyncio

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

            # Initialize client for Twitter API v2 with rate limit handling
            self.client = tweepy.Client(
                bearer_token=bearer_token,
                consumer_key=TWITTER_API_KEY,
                consumer_secret=TWITTER_API_SECRET,
                return_type=dict,
                wait_on_rate_limit=True,
                retry_count=3,
                retry_delay=5,
                retry_errors={400, 401, 403, 404, 429, 500, 502, 503, 504}
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

    async def _handle_rate_limit(self, operation, max_retries=3):
        for attempt in range(max_retries):
            try:
                return await operation()
            except tweepy.errors.TooManyRequests as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = int(e.response.headers.get('x-rate-limit-reset', 60))
                logger.warning(f"Rate limit hit, waiting {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"Error during operation: {e}")
                raise

    def _test_connection(self):
        try:
            logger.debug("Testing Twitter API connection...")
            # Test API access with a simple query
            response = self.client.get_user(username="Twitter")
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

        async def fetch_user():
            return self.client.get_user(username=username)

        async def fetch_tweets(user_id):
            return self.client.get_users_tweets(
                user_id,
                max_results=10,
                tweet_fields=['public_metrics']
            )

        try:
            logger.debug(f"Fetching Twitter activity for user {username}")

            # Get user ID with rate limit handling
            user_response = await self._handle_rate_limit(fetch_user)
            if not user_response or not user_response.get('data'):
                raise tweepy.errors.NotFound()

            user_id = user_response['data']['id']
            logger.debug(f"Found Twitter user {username} with ID {user_id}")

            # Get tweets with rate limit handling
            tweets_response = await self._handle_rate_limit(lambda: fetch_tweets(user_id))

            if not tweets_response or not tweets_response.get('data'):
                logger.debug(f"No tweets found for user {username}")
                return {'likes': 0, 'retweets': 0, 'comments': 0}

            activity = {'likes': 0, 'retweets': 0, 'comments': 0}

            for tweet in tweets_response['data']:
                metrics = tweet['public_metrics']
                activity['likes'] += metrics.get('like_count', 0)
                activity['retweets'] += metrics.get('retweet_count', 0)
                activity['comments'] += metrics.get('reply_count', 0)

            logger.debug(f"Successfully fetched activity for {username}: {activity}")
            return activity

        except tweepy.errors.NotFound:
            logger.warning(f"Twitter user {username} not found")
            raise ValueError(f"Le compte Twitter @{username} n'existe pas.")
        except tweepy.errors.Unauthorized:
            logger.warning(f"Unauthorized access to Twitter user {username}")
            raise ValueError(f"Le compte Twitter @{username} est privé ou inaccessible.")
        except Exception as e:
            logger.error(f"Error fetching Twitter activity: {e}")
            logger.exception("Full traceback:")
            raise ValueError("Une erreur est survenue. Réessayez plus tard.")