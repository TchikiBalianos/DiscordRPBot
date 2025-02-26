import random
from datetime import datetime
from config import *

class PointSystem:
    def __init__(self, database):
        self.db = database

    async def award_message_points(self, user_id):
        self.db.add_points(user_id, POINTS_MESSAGE)
        return POINTS_MESSAGE

    async def award_voice_points(self, user_id, minutes):
        points = int(minutes * POINTS_VOICE_PER_MINUTE)
        self.db.add_points(user_id, points)
        return points

    async def award_twitter_points(self, user_id, stats):
        """Award points for Twitter engagement"""
        total_points = 0
        
        # Points for likes
        like_points = stats['likes'] * POINTS_TWITTER_LIKE
        total_points += like_points
        
        # Points for retweets
        retweet_points = stats['retweets'] * POINTS_TWITTER_RT
        total_points += retweet_points
        
        # Points for replies
        reply_points = stats['replies'] * POINTS_TWITTER_COMMENT
        total_points += reply_points

        if total_points > 0:
            self.db.add_points(user_id, total_points)
            
        return total_points

    async def try_rob(self, robber_id, victim_id):
        now = datetime.now().timestamp()
        last_rob = self.db.get_rob_cooldown(robber_id)
        
        if now - last_rob < ROB_COOLDOWN:
            return False, "You must wait before attempting another robbery!"

        if random.random() < ROB_SUCCESS_RATE:
            amount = random.randint(ROB_MIN_AMOUNT, ROB_MAX_AMOUNT)
            victim_points = self.db.get_user_points(victim_id)
            
            if victim_points < amount:
                amount = victim_points

            if amount <= 0:
                return False, "The victim doesn't have enough points to steal!"

            self.db.add_points(victim_id, -amount)
            self.db.add_points(robber_id, amount)
            self.db.set_rob_cooldown(robber_id)
            return True, f"Successfully stole {amount} points!"
        else:
            self.db.set_rob_cooldown(robber_id)
            return False, "Robbery failed! Better luck next time!"
