import tweepy
from config import TWITTER_BEARER_TOKEN
import logging
from tweepy.errors import TooManyRequests, NotFound

logger = logging.getLogger('EngagementBot')

class TwitterHandler:
    def __init__(self):
        try:
            self.client = tweepy.Client(
                bearer_token=TWITTER_BEARER_TOKEN,
                wait_on_rate_limit=True
            )
            logger.info("Twitter API initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter API: {e}")
            raise

    async def verify_account(self, username: str):
        try:
            username = username.lstrip('@')
            logger.info(f"Verifying Twitter account: {username}")

            try:
                user = self.client.get_user(username=username)
                if user and user.data:
                    logger.info(f"Successfully verified Twitter account: {username}")
                    return True, user.data.id
                return False, None
            except TooManyRequests:
                logger.error("Twitter API rate limit reached")
                return False, None
            except NotFound:
                logger.warning(f"Twitter account not found: {username}")
                return False, None

        except Exception as e:
            logger.error(f"Error verifying account {username}: {e}")
            return False, None

    async def get_user_stats(self, twitter_id: str):
        try:
            logger.info(f"Getting stats for Twitter ID: {twitter_id}")

            try:
                tweets = self.client.get_users_tweets(
                    id=twitter_id,
                    max_results=3,  # Reduced to minimize rate limit issues
                    tweet_fields=['public_metrics']
                )

                if not tweets.data:
                    logger.info("No tweets found")
                    return {'likes': 0}

                total_likes = sum(tweet.public_metrics['like_count'] for tweet in tweets.data)
                logger.info(f"Successfully retrieved stats. Total likes: {total_likes}")
                return {'likes': total_likes}

            except TooManyRequests:
                logger.error("Twitter API rate limit reached while getting stats")
                return {'error': 'Rate limit reached. Please try again later.'}

        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {'error': str(e)}