import tweepy
from config import *
import logging

logger = logging.getLogger('EngagementBot')

class TwitterHandler:
    def __init__(self):
        try:
            logger.info("Initializing Twitter API...")
            self.client = tweepy.Client(
                bearer_token=TWITTER_BEARER_TOKEN,
                wait_on_rate_limit=True
            )
            logger.info("Twitter API initialized")
        except Exception as e:
            logger.error(f"Error initializing Twitter API: {e}")
            raise

    async def verify_account(self, username: str):
        """Verify if a Twitter account exists"""
        try:
            username = username.lstrip('@')
            user = self.client.get_user(username=username)
            return bool(user.data), user.data.id if user.data else None
        except Exception as e:
            logger.error(f"Error verifying account {username}: {e}")
            return False, None

    async def get_user_stats(self, twitter_id: str):
        """Get user's basic Twitter stats"""
        try:
            tweets = self.client.get_users_tweets(
                id=twitter_id,
                max_results=5,
                tweet_fields=['public_metrics']
            )

            if not tweets.data:
                return {'likes': 0}

            total_likes = sum(tweet.public_metrics['like_count'] for tweet in tweets.data)
            return {'likes': total_likes}
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {'error': str(e)}