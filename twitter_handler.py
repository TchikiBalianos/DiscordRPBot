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
            self.client = tweepy.Client(
                bearer_token=bearer_token,
                wait_on_rate_limit=True
            )

            if not self.client:
                raise Exception("Twitter client initialization failed")

            # Cache for user data
            self._cache = {}
            self._cache_duration = timedelta(minutes=5)  # Cache data for 5 minutes

            # Test initial connection
            self._test_connection()
            logger.info("Twitter API initialization successful")

        except Exception as e:
            logger.error(f"Error initializing Twitter API: {e}")
            raise

    def _test_connection(self):
        try:
            response = self.client.get_user(username="X")
            if not response or not response.data:
                raise Exception("Could not get test user info")
            logger.info("Twitter API connection test successful")
        except tweepy.errors.TooManyRequests as e:
            logger.warning("Rate limit reached during connection test")
            # Don't raise the error, just log it
        except Exception as e:
            logger.error(f"Twitter API connection test failed: {e}")
            raise

    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get data from cache if it exists and is not expired"""
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < self._cache_duration:
                return data
            del self._cache[cache_key]
        return None

    def _store_in_cache(self, cache_key: str, data: Dict):
        """Store data in cache with current timestamp"""
        self._cache[cache_key] = (data, datetime.now())

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
                user_response = await loop.run_in_executor(
                    None, 
                    lambda: self.client.get_user(username=username)
                )
            except tweepy.errors.TooManyRequests:
                logger.warning(f"Rate limit reached while fetching user {username}")
                return {'error': 'rate_limit', 'message': 'Veuillez réessayer dans quelques minutes.'}

            if not user_response or not user_response.data:
                logger.warning(f"User not found: {username}")
                return None

            user_id = user_response.data.id

            # Get recent tweets
            try:
                tweets_response = await loop.run_in_executor(
                    None,
                    lambda: self.client.get_users_tweets(
                        user_id,
                        max_results=5,
                        tweet_fields=['public_metrics']
                    )
                )
            except tweepy.errors.TooManyRequests:
                logger.warning(f"Rate limit reached while fetching tweets for {username}")
                return {'error': 'rate_limit', 'message': 'Veuillez réessayer dans quelques minutes.'}

            if not tweets_response or not tweets_response.data:
                logger.info(f"No tweets found for user {username}")
                activity = {'likes': 0, 'retweets': 0, 'comments': 0}
            else:
                # Calculate total metrics
                activity = {'likes': 0, 'retweets': 0, 'comments': 0}
                for tweet in tweets_response.data:
                    metrics = tweet.public_metrics
                    activity['likes'] += metrics.get('like_count', 0)
                    activity['retweets'] += metrics.get('retweet_count', 0)
                    activity['comments'] += metrics.get('reply_count', 0)

            # Store in cache
            self._store_in_cache(cache_key, activity)

            logger.info(f"Successfully retrieved activity for {username}: {activity}")
            return activity

        except Exception as e:
            logger.error(f"Error getting Twitter activity: {e}", exc_info=True)
            return None