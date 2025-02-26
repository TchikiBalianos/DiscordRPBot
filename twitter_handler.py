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
            logger.info("Checking Twitter API credentials...")

            # Log credential status
            logger.debug("Checking Twitter API credentials status...")
            if not TWITTER_BEARER_TOKEN:
                logger.error("❌ Bearer Token is missing")
                raise ValueError("Bearer Token is required")

            if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
                logger.error("❌ One or more OAuth credentials are missing")
                raise ValueError("All OAuth credentials are required")

            # Initialize client with v2 API
            self.client = tweepy.Client(
                bearer_token=TWITTER_BEARER_TOKEN,
                consumer_key=TWITTER_API_KEY,
                consumer_secret=TWITTER_API_SECRET,
                access_token=TWITTER_ACCESS_TOKEN,
                access_token_secret=TWITTER_ACCESS_SECRET,
                wait_on_rate_limit=True
            )

            logger.info("✅ Twitter API initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize Twitter API: {str(e)}", exc_info=True)
            raise

    async def verify_account(self, username: str):
        """Verify Twitter account existence with detailed error handling"""
        try:
            # Clean up and normalize username
            username = username.lstrip('@').lower().strip()
            logger.info(f"Starting verification for Twitter account: @{username}")

            try:
                # Make API call with error tracking
                logger.debug(f"Making Twitter API call for username: @{username}")

                # First try with v2 API get_users
                response = self.client.get_users(
                    usernames=[username],
                    user_fields=['id', 'username', 'name']
                )

                logger.debug(f"Raw API Response for @{username}: {response}")

                if response and hasattr(response, 'data') and response.data:
                    user = response.data[0]
                    logger.info(f"✅ Successfully found Twitter account: @{username}")
                    logger.debug(f"User details - ID: {user.id}, Username: {user.username}")
                    return True, user.id
                else:
                    logger.warning(f"❌ No data returned for @{username}")
                    if hasattr(response, 'errors'):
                        logger.debug(f"API Errors: {response.errors}")
                    return False, None

            except TooManyRequests as e:
                logger.error(f"Rate limit exceeded: {str(e)}")
                logger.debug("Rate limit details:", exc_info=True)
                raise

            except Unauthorized as e:
                logger.error(f"Authentication failed: {str(e)}")
                logger.debug("Auth error details:", exc_info=True)
                raise

            except Exception as e:
                logger.error(f"Unexpected API error ({type(e).__name__}): {str(e)}")
                logger.debug("Full error details:", exc_info=True)
                return False, None

        except Exception as e:
            logger.error(f"Error in verify_account: {str(e)}")
            logger.debug("Stack trace:", exc_info=True)
            return False, None

    async def get_user_stats(self, twitter_id: str):
        """Get user statistics"""
        try:
            logger.info(f"Fetching stats for Twitter ID: {twitter_id}")
            tweets = self.client.get_users_tweets(
                id=twitter_id,
                max_results=10,
                tweet_fields=['public_metrics']
            )

            if tweets and tweets.data:
                total_likes = sum(tweet.public_metrics['like_count'] for tweet in tweets.data)
                logger.info(f"Successfully retrieved stats for user {twitter_id}")
                return {'likes': total_likes}

            logger.warning(f"No tweets found for user {twitter_id}")
            return {'likes': 0}

        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}", exc_info=True)
            return {'error': str(e)}