import tweepy
from config import *
import logging
from tweepy.errors import TooManyRequests, NotFound, Unauthorized
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TwitterTest')

def test_oauth1_tokens():
    """Test OAuth 1.0a tokens individually"""
    logger.info("\nTesting OAuth 1.0a tokens...")

    # Log tokens (first 4 chars only)
    logger.info(f"API Key starts with: {TWITTER_API_KEY[:4]}...")
    logger.info(f"Access Token starts with: {TWITTER_ACCESS_TOKEN[:4]}...")

    try:
        auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
        auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
        api = tweepy.API(auth)

        me = api.verify_credentials()
        logger.info("✅ OAuth 1.0a Verification successful")
        logger.info(f"Authenticated as: @{me.screen_name}")
        return True
    except Unauthorized as e:
        logger.error("❌ OAuth 1.0a Verification failed")
        logger.error(f"Error: {str(e)}")
        logger.error("Solution: Please verify that you have:")
        logger.error("1. Generated new OAuth 1.0a tokens (not copying old ones)")
        logger.error("2. Correctly copied both Consumer Keys (API Key + Secret)")
        logger.error("3. Correctly copied both Access Tokens")
        logger.error("4. Enabled Read+Write permissions in app settings")
        return False

def test_oauth2_bearer():
    """Test OAuth 2.0 Bearer Token"""
    logger.info("\nTesting OAuth 2.0 Bearer Token...")

    # Log token (first 4 chars only)
    logger.info(f"Bearer Token starts with: {TWITTER_BEARER_TOKEN[:4]}...")

    try:
        client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)
        me = client.get_me()

        if me and me.data:
            logger.info("✅ Bearer Token Verification successful")
            logger.info(f"Account ID: {me.data.id}")
            return True
        else:
            logger.error("❌ Bearer Token verification failed: No data returned")
            return False
    except Unauthorized as e:
        logger.error("❌ Bearer Token verification failed")
        logger.error(f"Error: {str(e)}")
        logger.error("Solution: Please verify that you have:")
        logger.error("1. Generated a new Bearer Token (not copying old one)")
        logger.error("2. Correctly copied the entire Bearer Token")
        logger.error("3. Bearer Token starts with 'AAAA...'")
        return False

if __name__ == "__main__":
    logger.info("Starting detailed Twitter API verification...")

    # Test each authentication method separately
    oauth1_success = test_oauth1_tokens()
    oauth2_success = test_oauth2_bearer()

    # Summary
    logger.info("\nAuthentication Test Summary:")
    logger.info(f"OAuth 1.0a (API Key + Access Token): {'✅ Working' if oauth1_success else '❌ Failed'}")
    logger.info(f"OAuth 2.0 (Bearer Token): {'✅ Working' if oauth2_success else '❌ Failed'}")

    if not (oauth1_success or oauth2_success):
        logger.error("\n❌ All authentication methods failed.")
        logger.error("Please verify all tokens have been correctly regenerated and copied.")
        exit(1)