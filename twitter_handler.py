import tweepy
from config import *
import logging

logger = logging.getLogger('EngagementBot')

class TwitterHandler:
    def __init__(self):
        try:
            logger.info("Initializing Twitter API...")
            # Log keys presence (not their values)
            logger.info(f"Twitter API Key present: {bool(TWITTER_API_KEY)}")
            logger.info(f"Twitter API Secret present: {bool(TWITTER_API_SECRET)}")
            logger.info(f"Twitter Access Token present: {bool(TWITTER_ACCESS_TOKEN)}")
            logger.info(f"Twitter Access Secret present: {bool(TWITTER_ACCESS_SECRET)}")

            self.client = tweepy.Client(
                consumer_key=TWITTER_API_KEY,
                consumer_secret=TWITTER_API_SECRET,
                access_token=TWITTER_ACCESS_TOKEN,
                access_token_secret=TWITTER_ACCESS_SECRET
            )
            self._test_connection()
            logger.info("Twitter API connection successful")
        except tweepy.errors.Unauthorized as e:
            logger.error(f"Twitter API authentication failed: {e}")
            logger.exception("Authentication error traceback:")
            self.client = None
        except Exception as e:
            logger.error(f"Error initializing Twitter API: {e}")
            logger.exception("Full traceback:")
            self.client = None

    def _test_connection(self):
        try:
            # Test with a simple API call
            me = self.client.get_me()
            if me.data:
                logger.info(f"Twitter API connection test successful - Connected as @{me.data.username}")
            else:
                logger.error("Twitter API connection test failed - Could not get user info")
                raise Exception("Failed to get user info")
        except tweepy.errors.Unauthorized as e:
            logger.error(f"Twitter API authentication test failed: {e}")
            logger.exception("Authentication test error traceback:")
            raise
        except Exception as e:
            logger.error(f"Twitter API connection test failed: {e}")
            logger.exception("Full traceback:")
            raise

    async def get_user_activity(self, username):
        if not self.client:
            logger.error("Twitter API not initialized - check your API credentials")
            raise ValueError("Configuration Twitter invalide. Veuillez contacter l'administrateur.")

        try:
            logger.info(f"Fetching Twitter activity for user {username}")

            # Get user ID first
            user = self.client.get_user(username=username)
            if not user.data:
                raise tweepy.errors.NotFound()

            user_id = user.data.id
            logger.info(f"Found Twitter user {username} with ID {user_id}")

            # Get recent tweets
            tweets = self.client.get_users_tweets(
                user_id,
                max_results=10,
                tweet_fields=['public_metrics']
            )

            if not tweets.data:
                # User exists but has no tweets
                logger.info(f"No tweets found for user {username}")
                return {
                    'likes': 0,
                    'retweets': 0,
                    'comments': 0
                }

            activity = {
                'likes': 0,
                'retweets': 0,
                'comments': 0
            }

            for tweet in tweets.data:
                metrics = tweet.public_metrics
                activity['likes'] += metrics.get('like_count', 0)
                activity['retweets'] += metrics.get('retweet_count', 0)
                activity['comments'] += metrics.get('reply_count', 0)

            logger.info(f"Successfully fetched activity for {username}: {activity}")
            return activity

        except tweepy.errors.NotFound:
            logger.error(f"Twitter user {username} not found")
            raise ValueError(f"Le compte Twitter @{username} n'existe pas.")

        except tweepy.errors.Unauthorized:
            logger.error(f"Unauthorized access to Twitter user {username}")
            raise ValueError(f"Le compte Twitter @{username} est privé ou inaccessible.")

        except tweepy.errors.TweepyException as e:
            logger.error(f"Tweepy error fetching Twitter activity for {username}: {e}")
            logger.exception("Full traceback:")
            raise ValueError("Une erreur est survenue lors de l'accès à Twitter. Réessayez plus tard.")

        except Exception as e:
            logger.error(f"Unexpected error fetching Twitter activity: {e}")
            logger.exception("Full traceback:")
            raise ValueError("Une erreur inattendue est survenue. Réessayez plus tard.")