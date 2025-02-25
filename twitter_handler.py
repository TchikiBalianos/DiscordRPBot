import tweepy
from config import *

class TwitterHandler:
    def __init__(self):
        try:
            auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
            auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
            self.api = tweepy.API(auth)
            self.client = tweepy.Client(
                consumer_key=TWITTER_API_KEY,
                consumer_secret=TWITTER_API_SECRET,
                access_token=TWITTER_ACCESS_TOKEN,
                access_token_secret=TWITTER_ACCESS_SECRET
            )
            self._test_connection()
        except Exception as e:
            print(f"Error initializing Twitter API: {e}")
            self.api = None
            self.client = None

    def _test_connection(self):
        try:
            self.api.verify_credentials()
            print("Twitter API connection successful")
        except Exception as e:
            print(f"Twitter API connection failed: {e}")
            raise

    async def get_user_activity(self, username):
        if not self.api:
            print("Twitter API not initialized")
            return None

        try:
            # Get user's recent tweets
            tweets = self.api.user_timeline(screen_name=username, count=10)

            activity = {
                'likes': 0,
                'retweets': 0,
                'comments': 0
            }

            for tweet in tweets:
                activity['likes'] += tweet.favorite_count
                activity['retweets'] += tweet.retweet_count
                # Getting reply count requires additional API calls in v1.1
                # This is a simplified version

            return activity
        except tweepy.TweepError as e:
            print(f"Error fetching Twitter activity for {username}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error fetching Twitter activity: {e}")
            return None