import tweepy
from config import *
import logging
import asyncio
import os
from datetime import datetime, timedelta
from typing import Optional, Dict

logger = logging.getLogger('EngagementBot')

class TwitterHandler:
    def __init__(self):
        try:
            logger.info("Initializing Twitter API...")
            bearer_token = TWITTER_BEARER_TOKEN
            if not bearer_token:
                logger.error("Bearer Token is missing")
                raise ValueError("Bearer Token is required for Twitter API v2")

            # Initialize with bearer token only for read-only access
            logger.info(f"Bearer Token present: {bool(bearer_token)}")

            self.client = tweepy.Client(
                bearer_token=bearer_token,
                wait_on_rate_limit=True
            )

            if not self.client:
                raise Exception("Twitter client initialization failed")

            # Cache for user data
            self._cache = {}
            self._cache_duration = timedelta(minutes=15)  # Increased cache duration
            logger.info("Twitter API initialization successful")

        except Exception as e:
            logger.error(f"Error initializing Twitter API: {e}")
            raise

    async def get_user_activity(self, username):
        """Get user's Twitter activity asynchronously"""
        try:
            logger.info(f"Getting activity for Twitter user: {username}")

            # Check cache first
            cache_key = f"activity_{username}"
            cached_data = self._get_from_cache(cache_key)
            if cached_data:
                logger.info(f"Returning cached data for {username}")
                return cached_data

            # Use asyncio to avoid blocking
            loop = asyncio.get_event_loop()
            try:
                logger.debug(f"Making API request for user @{username}")
                user_response = await loop.run_in_executor(
                    None, 
                    lambda: self.client.get_user(username=username)
                )
                logger.debug(f"Raw user response: {user_response}")
            except tweepy.errors.TooManyRequests as e:
                wait_time = int(e.response.headers.get('x-rate-limit-reset', 0)) - int(datetime.now().timestamp())
                wait_time = max(wait_time, 60)  # Minimum wait of 60 seconds
                logger.warning(f"Rate limit reached while fetching user {username}. Wait time: {wait_time} seconds")
                return {
                    'error': 'rate_limit',
                    'message': f"Limite d'API atteinte. Veuillez réessayer dans {wait_time//60} minutes."
                }
            except tweepy.errors.Unauthorized as e:
                logger.error(f"Authentication failed: {e}")
                return {
                    'error': 'auth',
                    'message': "Erreur d'authentification Twitter. Veuillez contacter l'administrateur."
                }
            except tweepy.errors.NotFound as e:
                logger.error(f"User not found: {username}")
                return {
                    'error': 'not_found',
                    'message': f"Le compte Twitter @{username} n'existe pas."
                }
            except Exception as e:
                logger.error(f"Error fetching user info: {e}", exc_info=True)
                return None

            if not user_response or not user_response.data:
                logger.warning(f"User not found: {username}")
                return {
                    'error': 'not_found',
                    'message': f"Le compte Twitter @{username} n'existe pas ou n'est pas accessible."
                }

            user_id = user_response.data.id
            logger.info(f"User ID for @{username}: {user_id}")

            # For testing: Return success with test data
            test_activity = {'likes': 10}  # Test data
            self._store_in_cache(cache_key, test_activity)
            logger.info(f"Returning test activity for {username}: {test_activity}")
            return test_activity

        except Exception as e:
            logger.error(f"Error getting Twitter activity: {e}", exc_info=True)
            return {
                'error': 'unknown',
                'message': "Une erreur inattendue s'est produite lors de l'accès à Twitter."
            }

    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get data from cache if it exists and is not expired"""
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < self._cache_duration:
                logger.debug(f"Cache hit for key: {cache_key}")
                return data
            logger.debug(f"Cache expired for key: {cache_key}")
            del self._cache[cache_key]
        return None

    def _store_in_cache(self, cache_key: str, data: Dict):
        """Store data in cache with current timestamp"""
        self._cache[cache_key] = (data, datetime.now())
        logger.debug(f"Stored in cache: {cache_key}")