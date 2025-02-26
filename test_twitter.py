import tweepy
from config import *
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('TwitterTest')

def test_twitter_connection():
    try:
        logger.info("Testing Twitter API connection...")
        logger.info(f"Bearer Token present: {bool(TWITTER_BEARER_TOKEN)}")

        if not TWITTER_BEARER_TOKEN:
            logger.error("Bearer Token is missing")
            return False

        client = tweepy.Client(
            bearer_token=TWITTER_BEARER_TOKEN,
            wait_on_rate_limit=True
        )

        # Test the connection with get_me()
        response = client.get_user(username="X")
        if response and response.data:
            logger.info(f"Successfully retrieved user info for @X")
            return True
        else:
            logger.error("Could not get user information")
            return False

    except tweepy.errors.Unauthorized as e:
        logger.error(f"Authentication failed: {e}")
        logger.error("Please verify in Twitter Developer Portal:")
        logger.error("1. Your Bearer Token is valid")
        logger.error("2. Your app has User.Read permission")
        logger.error("3. The Bearer Token hasn't expired")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_twitter_connection()