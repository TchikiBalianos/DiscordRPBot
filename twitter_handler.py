import tweepy
from config import (
    TWITTER_API_KEY, 
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_SECRET,
    TWITTER_BEARER_TOKEN
)
import logging
from tweepy.errors import TooManyRequests, NotFound, Unauthorized
import time
from datetime import datetime, timedelta

logger = logging.getLogger('EngagementBot')

class TwitterHandler:
    def __init__(self):
        """Initialize Twitter API with both OAuth 1.0a and OAuth 2.0"""
        try:
            logger.info("Initializing Twitter API with both OAuth 1.0a and OAuth 2.0...")
            # Log masked versions of tokens for debugging
            logger.debug(f"API Key starting with: {TWITTER_API_KEY[:4]}...")
            logger.debug(f"Bearer Token starting with: {TWITTER_BEARER_TOKEN[:4]}...")
            logger.debug(f"Access Token starting with: {TWITTER_ACCESS_TOKEN[:4]}...")

            # Initialize OAuth 1.0a client
            self.auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
            self.auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
            self.api = tweepy.API(self.auth)

            # Initialize OAuth 2.0 client
            self.client = tweepy.Client(
                bearer_token=TWITTER_BEARER_TOKEN,
                consumer_key=TWITTER_API_KEY,
                consumer_secret=TWITTER_API_SECRET,
                access_token=TWITTER_ACCESS_TOKEN,
                access_token_secret=TWITTER_ACCESS_SECRET
            )

            self._cache = {}
            self._cache_duration = timedelta(minutes=15)
            logger.info("Twitter API initialization complete")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter API: {str(e)}", exc_info=True)
            raise

    async def verify_account(self, username: str):
        """Verify Twitter account existence with enhanced error handling"""
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
                logger.info(f"Attempting OAuth 2.0 lookup for {username}")
                # Use OAuth 2.0 client for better rate limits
                response = self.client.get_user(username=username)

                if response and response.data:
                    result = (True, response.data.id)
                    self._set_in_cache(cache_key, result)
                    logger.info(f"Successfully verified Twitter account: {username}")
                    return result
                else:
                    logger.warning(f"User {username} not found via OAuth 2.0")
                    return (False, None)

            except TooManyRequests:
                logger.warning("Rate limited, retrying with OAuth 1.0a")
                time.sleep(1)  # Small delay before retry

                try:
                    # Fallback to OAuth 1.0a
                    user = self.api.get_user(screen_name=username)
                    if user:
                        result = (True, user.id)
                        self._set_in_cache(cache_key, result)
                        logger.info(f"Successfully verified Twitter account via OAuth 1.0a: {username}")
                        return result
                    return (False, None)
                except Exception as e:
                    logger.error(f"OAuth 1.0a error: {str(e)}")
                    return (False, None)

            except Exception as e:
                logger.error(f"Error verifying account: {str(e)}")
                return (False, None)

        except Exception as e:
            logger.error(f"Error in verify_account: {str(e)}", exc_info=True)
            return (False, None)

    async def get_user_stats(self, twitter_id: str):
        """Get user statistics with enhanced error handling"""
        try:
            logger.info(f"Getting stats for Twitter ID: {twitter_id}")

            # Check cache first
            cache_key = f"stats_{twitter_id}"
            cached_stats = self._get_from_cache(cache_key)
            if cached_stats:
                logger.info(f"Retrieved stats from cache for {twitter_id}")
                return cached_stats

            try:
                tweets = self.client.get_users_tweets(
                    id=twitter_id,
                    max_results=10,
                    tweet_fields=['public_metrics']
                )

                if tweets and tweets.data:
                    total_likes = sum(tweet.public_metrics['like_count'] for tweet in tweets.data)
                    stats = {'likes': total_likes}
                    self._set_in_cache(cache_key, stats)
                    logger.info(f"Successfully retrieved stats for {twitter_id}")
                    return stats

                return {'likes': 0}

            except TooManyRequests:
                logger.warning("Rate limit reached")
                return {'error': 'Rate limit reached. Please try again later.'}
            except Exception as e:
                logger.error(f"Error getting stats: {str(e)}")
                return {'error': str(e)}

        except Exception as e:
            logger.error(f"Error in get_user_stats: {str(e)}", exc_info=True)
            return {'error': str(e)}

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