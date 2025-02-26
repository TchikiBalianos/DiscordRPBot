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

            # Test the connection
            self._test_connection()

            self._cache = {}
            self._cache_duration = timedelta(minutes=15)
            logger.info("Twitter API initialization complete")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter API: {str(e)}", exc_info=True)
            raise

    def _test_connection(self):
        """Test the API connection with both authentication methods"""
        try:
            # Test OAuth 1.0a
            logger.info("Testing OAuth 1.0a authentication...")
            try:
                me_1 = self.api.verify_credentials()
                logger.info(f"✅ OAuth 1.0a authentication successful as @{me_1.screen_name}")
                logger.info("Account permissions verified")
            except Unauthorized as e:
                logger.error("❌ OAuth 1.0a authentication failed")
                logger.error(f"Error details: {str(e)}")
                logger.error("Please verify Access Token and Access Token Secret, and ensure Read+Write permissions")
            except Exception as e:
                logger.error(f"OAuth 1.0a error: {str(e)}", exc_info=True)

            # Test OAuth 2.0
            logger.info("Testing OAuth 2.0 authentication...")
            try:
                me_2 = self.client.get_me()
                if me_2 and me_2.data:
                    logger.info(f"✅ OAuth 2.0 authentication successful as ID: {me_2.data.id}")
                else:
                    logger.error("❌ OAuth 2.0 authentication failed: No user data returned")
                    logger.error("Please verify Bearer Token configuration")
            except Unauthorized as e:
                logger.error("❌ OAuth 2.0 authentication failed")
                logger.error(f"Error details: {str(e)}")
                logger.error("Please verify API Key, API Secret, and Bearer Token")
            except Exception as e:
                logger.error(f"OAuth 2.0 error: {str(e)}", exc_info=True)

        except Exception as e:
            logger.error(f"Error in connection test: {str(e)}", exc_info=True)
            raise RuntimeError("Failed to initialize Twitter API connection")

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

            # Try OAuth 2.0 first (newer API)
            try:
                logger.info(f"Attempting OAuth 2.0 lookup for {username}")
                response = self.client.get_user(username=username)

                if response and response.data:
                    result = (True, response.data.id)
                    self._set_in_cache(cache_key, result)
                    logger.info(f"Successfully verified Twitter account via OAuth 2.0: {username}")
                    return result

            except TooManyRequests:
                logger.warning("OAuth 2.0 rate limited, falling back to OAuth 1.0a")
                time.sleep(1)  # Small delay before retrying

                try:
                    logger.info(f"Attempting OAuth 1.0a lookup for {username}")
                    user = self.api.get_user(screen_name=username)
                    if user:
                        result = (True, user.id)
                        self._set_in_cache(cache_key, result)
                        logger.info(f"Successfully verified Twitter account via OAuth 1.0a: {username}")
                        return result

                except TooManyRequests:
                    logger.error("Both APIs rate limited")
                    raise
                except NotFound:
                    logger.warning(f"User {username} not found via OAuth 1.0a")
                    return False, None
                except Exception as e:
                    logger.error(f"OAuth 1.0a error: {str(e)}")
                    raise

            except NotFound:
                logger.warning(f"User {username} not found via OAuth 2.0")
                return False, None
            except Exception as e:
                logger.error(f"OAuth 2.0 error: {str(e)}")
                raise

            return False, None

        except Exception as e:
            logger.error(f"Error in verify_account: {str(e)}", exc_info=True)
            if isinstance(e, TooManyRequests):
                raise
            if "401" in str(e):
                raise Unauthorized("Authentication failed")
            return False, None

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
                logger.info(f"Attempting to get tweets via OAuth 2.0 for {twitter_id}")
                tweets = self.client.get_users_tweets(
                    id=twitter_id,
                    max_results=3,
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