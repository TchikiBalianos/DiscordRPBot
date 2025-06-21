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

def validate_oauth1_tokens():
    """Validate that OAuth 1.0a tokens are present and well-formed"""
    missing = []
    if not TWITTER_API_KEY:
        missing.append("API Key")
    if not TWITTER_API_SECRET:
        missing.append("API Secret")
    if not TWITTER_ACCESS_TOKEN:
        missing.append("Access Token")
    if not TWITTER_ACCESS_SECRET:
        missing.append("Access Secret")

    if missing:
        logger.error(f"Missing OAuth 1.0a tokens: {', '.join(missing)}")
        return False
    return True

def test_oauth1_tokens():
    """Test OAuth 1.0a tokens individually"""
    logger.info("\nTesting OAuth 1.0a authentication...")

    if not validate_oauth1_tokens():
        return False

    try:
        # Initialize OAuth 1.0a
        auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
        auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
        api = tweepy.API(auth)

        # Test authentication
        me = api.verify_credentials()
        logger.info("✅ OAuth 1.0a authentication successful")
        logger.info(f"Authenticated as: @{me.screen_name}")
        return True
    except Unauthorized as e:
        logger.error("❌ OAuth 1.0a authentication failed")
        logger.error(f"Error: {str(e)}")
        logger.error("Please verify in Twitter Developer Portal:")
        logger.error("1. App permissions are set to 'Read and Write'")
        logger.error("2. The Access Token and Secret are newly generated")
        logger.error("3. The API Key and Secret are correct")
        return False
    except Exception as e:
        logger.error(f"❌ OAuth 1.0a error: {str(e)}")
        return False

def test_bearer_token():
    """Test Bearer Token authentication"""
    logger.info("\nTesting Bearer Token authentication...")

    if not TWITTER_BEARER_TOKEN:
        logger.error("❌ Bearer Token is missing")
        return False

    if not TWITTER_BEARER_TOKEN.startswith('AAAA'):
        logger.error("❌ Bearer Token appears invalid (should start with 'AAAA')")
        return False

    try:
        # Test Bearer Token only, using a simpler endpoint
        client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)

        # Try to get a single tweet from Twitter's official account
        # This endpoint typically has higher rate limits
        response = client.get_user(id=783214)  # Twitter's official account ID

        if response and response.data:
            logger.info("✅ Bearer Token authentication successful")
            logger.info(f"Successfully retrieved Twitter account info")
            return True
        else:
            logger.error("❌ Bearer Token authentication failed: No data returned")
            return False
    except TooManyRequests:
        logger.warning("⚠️ Rate limit reached while testing Bearer Token")
        logger.warning("This usually means the token is valid but we need to wait")
        # Consider it a success since this means the token is valid
        return True
    except Unauthorized as e:
        logger.error("❌ Bearer Token authentication failed")
        logger.error(f"Error: {str(e)}")
        logger.error("Please regenerate your Bearer Token in the Twitter Developer Portal")
        return False
    except Exception as e:
        logger.error(f"❌ Bearer Token error: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting Twitter API authentication tests...")

    # Test each authentication method separately
    oauth1_success = test_oauth1_tokens()
    bearer_success = test_bearer_token()

    # Summary
    logger.info("\nAuthentication Test Results:")
    logger.info(f"OAuth 1.0a (API + Access Tokens): {'✅ Working' if oauth1_success else '❌ Failed'}")
    logger.info(f"Bearer Token: {'✅ Working' if bearer_success else '❌ Failed'}")

    if not (oauth1_success or bearer_success):
        logger.error("\n❌ All authentication methods failed")
        logger.error("Please regenerate all tokens in the Twitter Developer Portal")
        exit(1)