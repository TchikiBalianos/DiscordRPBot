import tweepy
from config import (
    TWITTER_API_KEY, 
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_SECRET,
    TWITTER_BEARER_TOKEN,
    POINTS_TWITTER_LIKE,
    POINTS_TWITTER_RT,
    POINTS_TWITTER_COMMENT
)
import logging
from tweepy.errors import TooManyRequests, NotFound, Unauthorized
import time
from datetime import datetime, timedelta

logger = logging.getLogger('EngagementBot')

class TwitterHandler:
    def __init__(self):
        """Initialize Twitter API"""
        try:
            logger.info("Initializing Twitter API...")
            logger.info("Checking Twitter API credentials...")

            # Log credential status
            logger.debug("Checking Twitter API credentials status...")
            if not TWITTER_BEARER_TOKEN:
                logger.error("❌ Bearer Token is missing")
                raise ValueError("Bearer Token is required")

            if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
                logger.error("❌ One or more OAuth credentials are missing")
                raise ValueError("All OAuth credentials are required")

            # Initialize client with v2 API
            self.client = tweepy.Client(
                bearer_token=TWITTER_BEARER_TOKEN,
                consumer_key=TWITTER_API_KEY,
                consumer_secret=TWITTER_API_SECRET,
                access_token=TWITTER_ACCESS_TOKEN,
                access_token_secret=TWITTER_ACCESS_SECRET,
                wait_on_rate_limit=True
            )

            logger.info("✅ Twitter API initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize Twitter API: {str(e)}", exc_info=True)
            raise

    async def verify_account(self, username: str):
        """Verify Twitter account existence with enhanced validation"""
        try:
            username = username.lstrip('@').lower().strip()
            logger.info(f"Starting verification for Twitter account: @{username}")

            try:
                response = self.client.get_users(
                    usernames=[username],
                    user_fields=['id', 'username', 'public_metrics']
                )

                if response and hasattr(response, 'data') and response.data:
                    user = response.data[0]
                    logger.info(f"✅ Successfully found Twitter account: @{username}")
                    return True, user.id, user.public_metrics
                else:
                    logger.warning(f"❌ No data returned for @{username}")
                    return False, None, None

            except TooManyRequests as e:
                logger.error(f"Rate limit exceeded: {str(e)}")
                raise

            except Unauthorized as e:
                logger.error(f"Authentication failed: {str(e)}")
                raise

        except Exception as e:
            logger.error(f"Error in verify_account: {str(e)}")
            return False, None, None

    async def get_user_stats(self, twitter_id: str):
        """Get user engagement statistics with enhanced tracking"""
        try:
            logger.info(f"Fetching stats for Twitter ID: {twitter_id}")

            # Get recent tweets (last 7 days)
            tweets = self.client.get_users_tweets(
                id=twitter_id,
                max_results=100,
                tweet_fields=['public_metrics', 'created_at']
            )

            stats = {
                'likes': 0,
                'retweets': 0,
                'replies': 0,
                'total_engagement': 0,
                'points_earned': 0
            }

            if tweets and tweets.data:
                for tweet in tweets.data:
                    metrics = tweet.public_metrics

                    # Track each type of engagement
                    likes = metrics['like_count']
                    retweets = metrics['retweet_count']
                    replies = metrics['reply_count']

                    # Update stats
                    stats['likes'] += likes
                    stats['retweets'] += retweets
                    stats['replies'] += replies

                    # Calculate points earned
                    points = (
                        likes * POINTS_TWITTER_LIKE +
                        retweets * POINTS_TWITTER_RT +
                        replies * POINTS_TWITTER_COMMENT
                    )
                    stats['points_earned'] += points
                    stats['total_engagement'] = likes + retweets + replies

                logger.info(f"Successfully retrieved stats for user {twitter_id}: {stats}")
                return stats

            logger.warning(f"No tweets found for user {twitter_id}")
            return stats

        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}", exc_info=True)
            return {'error': str(e)}