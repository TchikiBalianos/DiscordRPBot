import tweepy
from config import (
    TWITTER_API_KEY, 
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_SECRET,
    TWITTER_BEARER_TOKEN
)
import logging
from tweepy.errors import TooManyRequests, NotFound
import time
from datetime import datetime, timedelta

logger = logging.getLogger('EngagementBot')

class TwitterHandler:
    def __init__(self):
        try:
            logger.info("Initializing Twitter API...")
            self.client = tweepy.Client(
                bearer_token=TWITTER_BEARER_TOKEN,
                consumer_key=TWITTER_API_KEY,
                consumer_secret=TWITTER_API_SECRET,
                access_token=TWITTER_ACCESS_TOKEN,
                access_token_secret=TWITTER_ACCESS_SECRET,
                wait_on_rate_limit=True
            )
            self._cache = {}
            self._cache_duration = timedelta(minutes=5)
            logger.info("Twitter API initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter API: {str(e)}", exc_info=True)
            raise

    def _get_from_cache(self, key):
        """Get value from cache if not expired"""
        if key in self._cache:
            timestamp, value = self._cache[key]
            if datetime.now() - timestamp < self._cache_duration:
                return value
            del self._cache[key]
        return None

    def _set_in_cache(self, key, value):
        """Set value in cache with current timestamp"""
        self._cache[key] = (datetime.now(), value)

    async def verify_account(self, username: str):
        try:
            username = username.lstrip('@')
            logger.info(f"Attempting to verify Twitter account: {username}")

            # Check cache first
            cache_key = f"user_{username}"
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                logger.info(f"Retrieved user info from cache for {username}")
                return cached_result

            try:
                logger.debug(f"Making API call to get_user for username: {username}")
                response = self.client.get_user(username=username)
                logger.debug(f"API response for get_user: {response}")

                if response and response.data:
                    result = (True, response.data.id)
                    self._set_in_cache(cache_key, result)
                    logger.info(f"Successfully verified and cached Twitter account: {username}")
                    return result

                logger.warning(f"User data not found for {username}")
                return False, None

            except TooManyRequests as e:
                logger.error(f"Twitter API rate limit reached: {str(e)}")
                return False, None
            except NotFound:
                logger.warning(f"Twitter account not found: {username}")
                return False, None
            except Exception as e:
                logger.error(f"Unexpected error for {username}: {str(e)}")
                return False, None

        except Exception as e:
            logger.error(f"Error in verify_account: {str(e)}", exc_info=True)
            return False, None

    async def get_user_stats(self, twitter_id: str):
        try:
            logger.info(f"Getting stats for Twitter ID: {twitter_id}")

            # Check cache first
            cache_key = f"stats_{twitter_id}"
            cached_stats = self._get_from_cache(cache_key)
            if cached_stats:
                logger.info(f"Retrieved stats from cache for {twitter_id}")
                return cached_stats

            try:
                logger.debug(f"Making API call to get tweets for ID: {twitter_id}")
                tweets = self.client.get_users_tweets(
                    id=twitter_id,
                    max_results=3,  # Reduced to minimize API calls
                    tweet_fields=['public_metrics']
                )
                logger.debug(f"API response for get_users_tweets: {tweets}")

                if not tweets or not tweets.data:
                    logger.info(f"No tweets found for user ID: {twitter_id}")
                    return {'likes': 0}

                total_likes = sum(tweet.public_metrics['like_count'] for tweet in tweets.data)
                stats = {'likes': total_likes}
                self._set_in_cache(cache_key, stats)
                logger.info(f"Successfully retrieved and cached stats for {twitter_id}")
                return stats

            except TooManyRequests as e:
                logger.error(f"Rate limit reached: {str(e)}")
                return {'error': 'Rate limit reached. Please try again later.'}
            except Exception as e:
                logger.error(f"Error getting stats: {str(e)}")
                return {'error': str(e)}

        except Exception as e:
            logger.error(f"Error in get_user_stats: {str(e)}", exc_info=True)
            return {'error': str(e)}