# Discord/Twitter Engagement Bot

A Discord bot that tracks user engagement across Discord and Twitter platforms, implementing a point system with gamification features.

## Features

- Track Discord activity (messages, voice chat)
- Track Twitter activity (likes, retweets, comments)
- Point system with various rewards
- Leaderboard system
- Rob command for interaction between users
- Regular data saving

## Commands

- `!points` - Check your current points
- `!leaderboard` - View the top 10 users
- `!rob @user` - Try to steal points from another user
- `!bothelp` - Show all available commands

## Setup

1. Set up environment variables:
   - DISCORD_TOKEN
   - TWITTER_API_KEY
   - TWITTER_API_SECRET
   - TWITTER_ACCESS_TOKEN
   - TWITTER_ACCESS_SECRET

2. Install requirements:
   ```bash
   pip install discord.py tweepy
   ```

3. Run the bot:
   ```bash
   python bot.py