import tweepy
from config import *
import logging
from datetime import datetime

logger = logging.getLogger('EngagementBot')

class TwitterHandler:
    def __init__(self):
        """Initialize Twitter API with basic functionality"""
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

    async def verify_account(self, username: str) -> tuple[bool, str]:
        """Verify if a Twitter account exists"""
        try:
            username = username.lstrip('@')
            logger.info(f"Verifying Twitter account: {username}")

            response = self.client.get_user(
                username=username,
                user_fields=['public_metrics']
            )

            if response and response.data:
                user_id = response.data.id
                logger.info(f"Found Twitter user: {username} with ID: {user_id}")
                return True, user_id
            else:
                logger.warning(f"No data returned for username: {username}")
                return False, None

        except Exception as e:
            logger.error(f"Error in verify_account: {e}", exc_info=True)
            return False, None

    async def get_user_stats(self, twitter_id: str, days: int = 7) -> dict:
        """Get user's Twitter stats for the last X days"""
        try:
            logger.info(f"Getting stats for Twitter ID: {twitter_id}")

            # Get user's recent tweets
            logger.info("Fetching tweets...")
            tweets = self.client.get_users_tweets(
                id=twitter_id,
                max_results=10,  # Reduced for testing
                tweet_fields=['public_metrics']
            )

            logger.info(f"Tweets response: {tweets}")

            # Initialize stats
            stats = {
                'likes': 0,
                'retweets': 0,
                'replies': 0,
                'tweets': 0,
                'engagement_rate': 0.0
            }

            if not tweets or not tweets.data:
                logger.warning(f"No tweets found for user {twitter_id}")
                return stats

            # Calculate engagement
            for tweet in tweets.data:
                logger.info(f"Processing tweet: {tweet.id}")
                stats['tweets'] += 1
                metrics = tweet.public_metrics
                stats['likes'] += metrics.get('like_count', 0)
                stats['retweets'] += metrics.get('retweet_count', 0)
                stats['replies'] += metrics.get('reply_count', 0)

            # Calculate engagement rate
            total_engagements = stats['likes'] + stats['retweets'] + stats['replies']
            if stats['tweets'] > 0:
                stats['engagement_rate'] = round(total_engagements / stats['tweets'], 2)

            logger.info(f"Final stats for {twitter_id}: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error in get_user_stats: {e}", exc_info=True)
            return {'error': str(e)}