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

            # Initialize OAuth 1.0a client
            self.auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
            self.auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
            self.api = tweepy.API(self.auth, wait_on_rate_limit=True)

            # Initialize OAuth 2.0 client
            self.client = tweepy.Client(
                bearer_token=TWITTER_BEARER_TOKEN,
                consumer_key=TWITTER_API_KEY,
                consumer_secret=TWITTER_API_SECRET,
                access_token=TWITTER_ACCESS_TOKEN,
                access_token_secret=TWITTER_ACCESS_SECRET,
                wait_on_rate_limit=True
            )

            # Test the connection
            self._test_connection()

            self._cache = {}
            self._cache_duration = timedelta(minutes=15)
            logger.info("Twitter API initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter API: {str(e)}", exc_info=True)
            raise

    def _test_connection(self):
        """Test the API connection with both authentication methods"""
        try:
            # Test OAuth 1.0a
            self.api.verify_credentials()
            logger.info("OAuth 1.0a authentication successful")
        except Exception as e:
            logger.warning(f"OAuth 1.0a authentication failed: {str(e)}")

        try:
            # Test OAuth 2.0
            self.client.get_me()
            logger.info("OAuth 2.0 authentication successful")
        except Exception as e:
            logger.warning(f"OAuth 2.0 authentication failed: {str(e)}")

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

            # Try OAuth 1.0a first
            try:
                logger.debug(f"Attempting OAuth 1.0a lookup for {username}")
                user = self.api.get_user(screen_name=username)
                if user:
                    result = (True, user.id)
                    self._set_in_cache(cache_key, result)
                    logger.info(f"Successfully verified Twitter account via OAuth 1.0a: {username}")
                    return result

            except TooManyRequests:
                logger.warning("OAuth 1.0a rate limited, falling back to OAuth 2.0")
                time.sleep(2)  # Small delay before retrying with OAuth 2.0

                try:
                    response = self.client.get_user(username=username)
                    if response and response.data:
                        result = (True, response.data.id)
                        self._set_in_cache(cache_key, result)
                        logger.info(f"Successfully verified Twitter account via OAuth 2.0: {username}")
                        return result

                except TooManyRequests:
                    logger.error("Both APIs rate limited")
                    raise
                except NotFound:
                    return False, None

            except NotFound:
                logger.warning(f"Twitter account {username} not found")
                return False, None

            except Exception as e:
                logger.error(f"Error in account verification: {str(e)}", exc_info=True)
                if "401" in str(e):
                    raise Unauthorized("Authentication failed")
                raise

            return False, None

        except TooManyRequests:
            logger.error("Rate limit reached for all API methods")
            raise
        except Exception as e:
            logger.error(f"Error in verify_account: {str(e)}", exc_info=True)
            raise

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

            # Try OAuth 1.0a first
            try:
                tweets = self.api.user_timeline(user_id=twitter_id, count=3)
                total_likes = sum(tweet.favorite_count for tweet in tweets)
                stats = {'likes': total_likes}
                self._set_in_cache(cache_key, stats)
                return stats

            except TooManyRequests:
                logger.warning("OAuth 1.0a rate limited for stats, trying OAuth 2.0")
                time.sleep(2)  # Small delay before retrying

                try:
                    tweets = self.client.get_users_tweets(
                        id=twitter_id,
                        max_results=3,
                        tweet_fields=['public_metrics']
                    )

                    if tweets and tweets.data:
                        total_likes = sum(tweet.public_metrics['like_count'] for tweet in tweets.data)
                        stats = {'likes': total_likes}
                        self._set_in_cache(cache_key, stats)
                        return stats
                    return {'likes': 0}

                except TooManyRequests:
                    logger.error("Both APIs rate limited for stats")
                    raise

            except Exception as e:
                logger.error(f"Error getting stats: {str(e)}", exc_info=True)
                raise

        except TooManyRequests:
            return {'error': 'Rate limit reached. Please try again later.'}
        except Exception as e:
            return {'error': str(e)}