import tweepy
from config import *
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('TwitterTest')

def test_twitter_connection():
    try:
        logger.info("Testing Twitter API connection...")
        logger.info(f"Twitter API Key present: {bool(TWITTER_API_KEY)}")
        logger.info(f"Twitter API Secret present: {bool(TWITTER_API_SECRET)}")
        logger.info(f"Twitter Access Token present: {bool(TWITTER_ACCESS_TOKEN)}")
        logger.info(f"Twitter Access Secret present: {bool(TWITTER_ACCESS_SECRET)}")

        client = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_SECRET
        )

        # Test the connection with get_me()
        me = client.get_me()
        if me.data:
            logger.info(f"Successfully connected as: @{me.data.username}")
            return True
        else:
            logger.error("Could not get user information")
            return False

    except tweepy.errors.Unauthorized as e:
        logger.error(f"Authentication failed: {e}")
        logger.error("Please verify in Twitter Developer Portal:")
        logger.error("1. App permissions are set to Read and Write")
        logger.error("2. OAuth 1.0a is enabled")
        logger.error("3. The tokens belong to the correct app")
        logger.error("4. The tokens are from the same app/project")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_twitter_connection()