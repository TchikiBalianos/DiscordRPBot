import tweepy
from config import *
import logging

logger = logging.getLogger('EngagementBot')

class TwitterHandler:
    def __init__(self):
        """Initialize Twitter API with basic functionality"""
        try:
            logger.info("Initializing Twitter API...")
            if not TWITTER_BEARER_TOKEN:
                logger.error("TWITTER_BEARER_TOKEN is missing")
                raise ValueError("TWITTER_BEARER_TOKEN is required")

            self.client = tweepy.Client(
                bearer_token=TWITTER_BEARER_TOKEN,
                wait_on_rate_limit=True
            )
            logger.info("Twitter API initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Twitter API: {e}")
            raise

    async def verify_account(self, username: str):
        """Verify if a Twitter account exists"""
        try:
            username = username.lstrip('@')
            logger.info(f"Verifying Twitter account: {username}")
            user = self.client.get_user(username=username)

            if user and user.data:
                logger.info(f"Successfully found Twitter user: {username}")
                return True, user.data.id
            else:
                logger.warning(f"Twitter user not found: {username}")
                return False, None

        except Exception as e:
            logger.error(f"Error verifying account {username}: {e}")
            return False, None

    async def get_user_stats(self, twitter_id: str):
        """Get user's basic Twitter stats"""
        try:
            logger.info(f"Getting stats for Twitter ID: {twitter_id}")

            # Get user's recent tweets
            tweets = self.client.get_users_tweets(
                id=twitter_id,
                max_results=5,
                tweet_fields=['public_metrics']
            )

            if not tweets or not tweets.data:
                logger.warning(f"No tweets found for user {twitter_id}")
                return {'likes': 0}

            # Calculate total likes
            total_likes = 0
            for tweet in tweets.data:
                if hasattr(tweet, 'public_metrics'):
                    total_likes += tweet.public_metrics.get('like_count', 0)
                    logger.debug(f"Tweet {tweet.id} has {tweet.public_metrics.get('like_count', 0)} likes")

            logger.info(f"Calculated total likes for {twitter_id}: {total_likes}")
            return {'likes': total_likes}

        except tweepy.errors.Unauthorized:
            logger.error("Unauthorized: Please check Twitter Bearer Token")
            return {'error': "Twitter API authentication failed"}
        except tweepy.errors.NotFound:
            logger.error(f"Twitter user {twitter_id} not found")
            return {'error': "Twitter user not found"}
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {'error': str(e)}