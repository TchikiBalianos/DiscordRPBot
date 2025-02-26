import tweepy
from config import *
import logging
from tweepy.errors import TooManyRequests, NotFound, Unauthorized
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('TwitterTest')

def test_twitter_connection():
    try:
        logger.info("Testing Twitter API connection...")
        logger.info(f"Bearer Token present: {bool(TWITTER_BEARER_TOKEN)}")
        logger.info(f"API Key present: {bool(TWITTER_API_KEY)}")
        logger.info(f"API Secret present: {bool(TWITTER_API_SECRET)}")
        logger.info(f"Access Token present: {bool(TWITTER_ACCESS_TOKEN)}")
        logger.info(f"Access Secret present: {bool(TWITTER_ACCESS_SECRET)}")

        # Initialize with both OAuth 2.0 Bearer Token and OAuth 1.0a credentials
        client = tweepy.Client(
            bearer_token=TWITTER_BEARER_TOKEN,
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_SECRET,
            wait_on_rate_limit=True
        )

        try:
            # Test user lookup with specific account
            test_user = "Faroyevana"
            logger.info(f"Testing user lookup with @{test_user}")
            response = client.get_user(username=test_user)

            if response and response.data:
                logger.info(f"Successfully retrieved user info for @{test_user}")
                return True
            else:
                logger.error("Could not get user information")
                return False

        except Unauthorized as e:
            logger.error(f"Authentication failed: {e}")
            logger.error("Please verify your Twitter API credentials and permissions")
            return False
        except Exception as e:
            logger.error(f"Error testing connection: {e}")
            return False

    except Exception as e:
        logger.error(f"Unexpected error in test_twitter_connection: {e}")
        return False

if __name__ == "__main__":
    test_twitter_connection()