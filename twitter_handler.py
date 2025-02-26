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
        """Initialize Twitter API"""
        try:
            logger.info("Initializing Twitter API...")

            # Create a simple client with just the bearer token for v2 API
            self.client = tweepy.Client(
                bearer_token=TWITTER_BEARER_TOKEN,
                wait_on_rate_limit=True
            )

            logger.info("Twitter API initialization complete")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter API: {str(e)}", exc_info=True)
            raise

    async def verify_account(self, username: str):
        """Simple Twitter account verification using v2 API"""
        try:
            # Clean up username
            username = username.lstrip('@').lower().strip()
            logger.info(f"Verifying Twitter account: @{username}")

            try:
                # Make a simple v2 API call
                logger.debug(f"Making API call for @{username}")
                response = self.client.get_users(usernames=[username])

                # Log full response for debugging
                logger.debug(f"API Response for @{username}: {response}")

                if response and response.data and len(response.data) > 0:
                    user_id = response.data[0].id
                    user_name = response.data[0].username
                    logger.info(f"✅ Found Twitter account: @{user_name} (ID: {user_id})")
                    return True, user_id
                else:
                    logger.warning(f"❌ Account not found: @{username}")
                    return False, None

            except TooManyRequests as e:
                logger.error(f"Rate limit reached: {str(e)}")
                raise
            except Unauthorized as e:
                logger.error(f"Authentication failed: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"API error: {type(e).__name__}: {str(e)}")
                return False, None

        except Exception as e:
            logger.error(f"Error in verify_account: {str(e)}", exc_info=True)
            return False, None

    async def get_user_stats(self, twitter_id: str):
        """Get user statistics"""
        try:
            tweets = self.client.get_users_tweets(
                id=twitter_id,
                max_results=10,
                tweet_fields=['public_metrics']
            )

            if tweets and tweets.data:
                total_likes = sum(tweet.public_metrics['like_count'] for tweet in tweets.data)
                return {'likes': total_likes}

            return {'likes': 0}

        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}", exc_info=True)
            return {'error': str(e)}