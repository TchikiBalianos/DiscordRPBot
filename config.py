import os

# Discord Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')  # Remove default value for security
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is required")

# Twitter API Configuration
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY', 'your-twitter-api-key')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET', 'your-twitter-api-secret')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN', 'your-twitter-bearer-token')

# Points Configuration
POINTS_VOICE_PER_MINUTE = 1
POINTS_MESSAGE = 2
POINTS_TWITTER_LIKE = 3
POINTS_TWITTER_RT = 5
POINTS_TWITTER_COMMENT = 4

# Rob Configuration
ROB_COOLDOWN = 3600  # 1 hour in seconds
ROB_SUCCESS_RATE = 0.4
ROB_MIN_AMOUNT = 10
ROB_MAX_AMOUNT = 100