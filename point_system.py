import random
from datetime import datetime, timedelta
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

    async def try_rob(self, robber_id, victim_id):
        """Enhanced rob system with prison risk"""
        now = datetime.now().timestamp()

        # Check if robber is in prison
        prison_time = self.db.get_prison_time(robber_id)
        if prison_time > now:
            time_left = int(prison_time - now)
            return False, f"Tu es en prison! Temps restant: {time_left} secondes."

        # Check cooldown
        last_rob = self.db.get_rob_cooldown(robber_id)
        if now - last_rob < ROB_COOLDOWN:
            return False, "Tu dois attendre avant de tenter un autre vol!"

        # Calculate success chance
        if random.random() > ROB_SUCCESS_RATE:
            # Failed robbery - risk going to prison
            if random.random() < PRISON_RATE:
                prison_duration = random.randint(PRISON_MIN_TIME, PRISON_MAX_TIME)
                self.db.set_prison_time(robber_id, now + prison_duration)
                self.db.set_rob_cooldown(robber_id)
                return False, f"🚔 Tu t'es fait attraper! Direction la prison pour {prison_duration} secondes!"
            self.db.set_rob_cooldown(robber_id)
            return False, "Le vol a échoué! Plus de chance la prochaine fois!"

        # Successful robbery
        amount = random.randint(ROB_MIN_AMOUNT, ROB_MAX_AMOUNT)
        victim_points = self.db.get_user_points(victim_id)

        if victim_points < amount:
            amount = victim_points

        if amount <= 0:
            return False, "La victime n'a pas assez de points à voler!"

        self.db.add_points(victim_id, -amount)
        self.db.add_points(robber_id, amount)
        self.db.set_rob_cooldown(robber_id)
        self.db.set_last_robber(victim_id, robber_id)  # Track who robbed whom
        return True, f"Vol réussi! Tu as volé {amount} points! 💰"

    async def try_revenge(self, avenger_id):
        """Try to get revenge on your last robber"""
        last_robber = self.db.get_last_robber(avenger_id)
        if not last_robber:
            return False, "Personne ne t'a volé récemment!"

        # Higher success rate for revenge
        if random.random() < REVENGE_SUCCESS_RATE:
            amount = random.randint(ROB_MIN_AMOUNT * 2, ROB_MAX_AMOUNT * 2)
            robber_points = self.db.get_user_points(last_robber)

            if robber_points < amount:
                amount = robber_points

            if amount <= 0:
                return False, "Ton voleur n'a plus assez de points!"

            self.db.add_points(last_robber, -amount)
            self.db.add_points(avenger_id, amount)
            self.db.clear_last_robber(avenger_id)  # Reset revenge status
            return True, f"Vengeance accomplie! Tu as récupéré {amount} points! 🗡️"

        return False, "Ta tentative de vengeance a échoué!"

    async def daily_work(self, user_id):
        """Complete daily work for points"""
        now = datetime.now().timestamp()
        last_work = self.db.get_last_work(user_id)

        if now - last_work < WORK_COOLDOWN:
            return False, "Tu as déjà travaillé aujourd'hui!"

        # Random work reward
        amount = random.randint(WORK_MIN_AMOUNT, WORK_MAX_AMOUNT)
        self.db.add_points(user_id, amount)
        self.db.set_last_work(user_id, now)

        return True, f"Tu as gagné {amount} points en travaillant! 💼"

    async def get_monthly_leaderboard(self):
        """Get the monthly leaderboard"""
        return self.db.get_leaderboard()

    async def award_twitter_points(self, user_id, stats):
        """Award points for Twitter engagement"""
        total_points = 0

        # Points for likes
        like_points = stats['likes'] * POINTS_TWITTER_LIKE
        total_points += like_points

        # Points for retweets
        retweet_points = stats.get('retweets', 0) * POINTS_TWITTER_RT
        total_points += retweet_points

        # Points for replies
        reply_points = stats.get('replies', 0) * POINTS_TWITTER_COMMENT
        total_points += reply_points

        if total_points > 0:
            self.db.add_points(user_id, total_points)

        return total_points

    async def buy_item(self, user_id: str, item_id: str):
        """Buy an item from the shop"""
        if item_id not in SHOP_ITEMS:
            return False, "❌ Cet objet n'existe pas dans la boutique!"

        item = SHOP_ITEMS[item_id]
        user_points = self.db.get_user_points(user_id)

        if user_points < item['price']:
            return False, f"❌ Tu n'as pas assez de points! (Prix: {item['price']} points)"

        # Add item to user's inventory and remove points
        self.db.add_points(user_id, -item['price'])
        self.db.add_item_to_inventory(user_id, item_id)

        return True, f"✅ Tu as acheté {item['name']} pour {item['price']} points!"

    async def start_heist(self, leader_id: str):
        """Start a heist and wait for other players"""
        # Check if there's already an active heist
        active_heist = self.db.get_active_heist()
        if active_heist:
            return False, "❌ Un braquage est déjà en cours!"

        # Create new heist
        self.db.create_heist(leader_id)
        return True, "🚗 Braquage lancé! Utilisez !joinheist pour participer!"

    async def join_heist(self, user_id: str):
        """Join an active heist"""
        heist = self.db.get_active_heist()
        if not heist:
            return False, "❌ Aucun braquage en cours!"

        if user_id in heist['participants']:
            return False, "❌ Tu participes déjà au braquage!"

        if len(heist['participants']) >= HEIST_MAX_PLAYERS:
            return False, "❌ L'équipe est déjà complète!"

        self.db.add_heist_participant(user_id)
        return True, "✅ Tu as rejoint le braquage!"

    async def start_drug_deal(self, user_id: str, investment: int):
        """Start a drug deal with investment"""
        if investment < DRUG_DEAL_MIN_INVESTMENT or investment > DRUG_DEAL_MAX_INVESTMENT:
            return False, f"❌ L'investissement doit être entre {DRUG_DEAL_MIN_INVESTMENT} et {DRUG_DEAL_MAX_INVESTMENT} points!"

        last_deal = self.db.get_drug_deal_cooldown(user_id)
        now = datetime.now().timestamp()

        if now - last_deal < DRUG_DEAL_COOLDOWN:
            remaining = int(DRUG_DEAL_COOLDOWN - (now - last_deal))
            return False, f"⏳ Tu dois attendre {remaining} secondes avant de refaire un deal!"

        user_points = self.db.get_user_points(user_id)
        if user_points < investment:
            return False, "❌ Tu n'as pas assez de points!"

        # Remove investment
        self.db.add_points(user_id, -investment)

        # Calculate success and profit
        if random.random() < DRUG_DEAL_SUCCESS_RATE:
            profit = int(investment * DRUG_DEAL_PROFIT_MULTIPLIER)
            self.db.add_points(user_id, profit)
            self.db.set_drug_deal_cooldown(user_id)
            return True, f"💊 Deal réussi! Tu as gagné {profit} points!"
        else:
            self.db.set_drug_deal_cooldown(user_id)
            return False, "🚔 La police a saisi ta marchandise! Tu as perdu ton investissement!"

    async def try_escape_police(self, user_id: str):
        """Try to escape from police"""
        last_chase = self.db.get_chase_cooldown(user_id)
        now = datetime.now().timestamp()

        if now - last_chase < CHASE_COOLDOWN:
            remaining = int(CHASE_COOLDOWN - (now - last_chase))
            return False, f"⏳ Tu dois attendre {remaining} secondes avant de retenter une course poursuite!"

        self.db.set_chase_cooldown(user_id)

        if random.random() < CHASE_ESCAPE_RATE:
            reward = random.randint(CHASE_MIN_LOSS, CHASE_MAX_LOSS)
            self.db.add_points(user_id, reward)
            return True, f"🏎️ Tu as semé la police et récupéré {reward} points du butin!"
        else:
            loss = random.randint(CHASE_MIN_LOSS, CHASE_MAX_LOSS)
            self.db.add_points(user_id, -loss)
            return False, f"🚓 La police t'a rattrapé! Tu as perdu {loss} points en amende!"

    async def assign_prison_role(self, user_id: str):
        """Randomly assign a prison role when sent to prison"""
        role = random.choice(list(PRISON_ROLES.keys()))
        self.db.set_prison_role(user_id, role)
        return PRISON_ROLES[role]['name']

    async def do_prison_activity(self, user_id: str, activity: str):
        """Do an activity in prison to reduce sentence"""
        now = datetime.now().timestamp()
        prison_time = self.db.get_prison_time(user_id)

        if prison_time <= now:
            return False, "Tu n'es pas en prison!"

        if activity not in PRISON_ACTIVITIES:
            return False, "❌ Cette activité n'existe pas!"

        # Check cooldown
        last_activity = self.db.get_last_prison_activity(user_id)
        if now - last_activity < 300:  # 5 minutes cooldown
            return False, "⏳ Tu dois attendre avant de faire une autre activité!"

        # Calculate reduction
        base_reduction = PRISON_ACTIVITIES[activity]['reduction']
        role = self.db.get_prison_role(user_id)
        if role:
            role_bonus = PRISON_ROLES[role]['reduction']
            reduction = int(base_reduction * (1 + role_bonus))
        else:
            reduction = base_reduction

        # Apply reduction
        new_time = max(now, prison_time - reduction)
        self.db.set_prison_time(user_id, new_time)
        self.db.set_last_prison_activity(user_id, now)

        # Return remaining time
        remaining = int(new_time - now)
        return True, f"✅ Tu as fait {PRISON_ACTIVITIES[activity]['name']} et réduit ta peine de {reduction} secondes!\nTemps restant: {remaining} secondes"

    async def get_prison_status(self, user_id: str):
        """Get user's prison status"""
        now = datetime.now().timestamp()
        prison_time = self.db.get_prison_time(user_id)
        role = self.db.get_prison_role(user_id)

        if prison_time <= now:
            return None

        status = {
            'time_left': int(prison_time - now),
            'role': PRISON_ROLES[role]['name'] if role else None,
            'role_bonus': f"{int(PRISON_ROLES[role]['reduction']*100)}%" if role else None
        }
        return status

    async def request_trial(self, user_id: str, plea: str):
        """Request a trial with a plea"""
        now = datetime.now().timestamp()

        # Check if in prison
        prison_time = self.db.get_prison_time(user_id)
        if prison_time <= now:
            return False, "Tu n'es pas en prison!"

        # Check cooldown
        last_trial = self.db.get_trial_cooldown(user_id)
        if now - last_trial < TRIBUNAL_COOLDOWN:
            return False, "⏳ Tu dois attendre avant de demander un autre procès!"

        # Check points
        points = self.db.get_user_points(user_id)
        if points < TRIBUNAL_COST:
            return False, f"❌ Tu n'as pas assez de points! (Coût: {TRIBUNAL_COST} points)"

        # Create trial
        self.db.create_trial(user_id, plea, now + TRIBUNAL_VOTE_DURATION)
        self.db.add_points(user_id, -TRIBUNAL_COST)
        self.db.set_trial_cooldown(user_id, now)

        return True, "⚖️ Ton procès commence! Les membres vont voter pendant 5 minutes!"

    async def vote_trial(self, voter_id: str, defendant_id: str, vote: bool):
        """Vote in an active trial"""
        trial = self.db.get_active_trial(defendant_id)
        if not trial:
            return False, "❌ Aucun procès en cours pour ce membre!"

        if voter_id == defendant_id:
            return False, "❌ Tu ne peux pas voter pour ton propre procès!"

        if voter_id in trial['votes']:
            return False, "❌ Tu as déjà voté!"

        # Record vote
        self.db.add_trial_vote(defendant_id, voter_id, vote)

        # Check if trial is over
        votes = self.db.get_trial_votes(defendant_id)
        if len(votes) >= TRIBUNAL_MIN_VOTERS:
            return await self.conclude_trial(defendant_id)

        return True, "✅ Vote enregistré!"

    async def conclude_trial(self, user_id: str):
        """Conclude a trial based on votes"""
        trial = self.db.get_active_trial(user_id)
        if not trial:
            return False, "❌ Aucun procès en cours!"

        votes = trial['votes']
        total_votes = len(votes)
        positive_votes = sum(1 for v in votes.values() if v)
        acquittal_rate = positive_votes / total_votes if total_votes > 0 else 0

        # Check if player has lawyer bonus
        inventory = self.db.get_inventory(user_id)
        lawyer_bonus = 0.2 if 'avocat' in inventory else 0
        acquittal_rate += lawyer_bonus

        if acquittal_rate >= TRIBUNAL_ACQUIT_RATE:
            self.db.set_prison_time(user_id, 0)  # Free from prison
            self.db.clear_active_trial(user_id)
            return True, "🎉 Le tribunal t'a acquitté! Tu es libre!"
        else:
            self.db.clear_active_trial(user_id)
            return False, "😔 Le tribunal t'a jugé coupable! Tu restes en prison!"
            
    async def try_escape_prison(self, user_id: str):
        """Try to escape from prison with risks"""
        now = datetime.now().timestamp()
        prison_time = self.db.get_prison_time(user_id)

        if prison_time <= now:
            return False, "Tu n'es pas en prison!"

        last_escape = self.db.get_escape_cooldown(user_id)
        if now - last_escape < ESCAPE_ATTEMPT_COOLDOWN:
            remaining = int(ESCAPE_ATTEMPT_COOLDOWN - (now - last_escape))
            return False, f"⏳ Tu dois attendre {remaining} secondes avant de retenter une évasion!"

        # Calculate escape chance
        escape_chance = ESCAPE_BASE_CHANCE
        inventory = self.db.get_inventory(user_id)
        if "lockpick" in inventory:
            escape_chance += 0.2  # +20% with lockpick

        self.db.set_escape_cooldown(user_id, now)

        if random.random() < escape_chance:
            self.db.set_prison_time(user_id, 0)  # Free from prison
            self.db.add_points(user_id, ESCAPE_SUCCESS_REWARD)
            return True, f"🏃 Tu t'es évadé avec succès! Tu as gagné {ESCAPE_SUCCESS_REWARD} points!"
        else:
            # Failed escape adds more prison time
            new_time = prison_time + ESCAPE_FAILURE_EXTRA_TIME
            self.db.set_prison_time(user_id, new_time)
            return False, f"🚔 Tentative d'évasion échouée! Ta peine est prolongée de {ESCAPE_FAILURE_EXTRA_TIME//60} minutes!"

    async def start_combat(self, challenger_id: str, target_id: str, bet: int):
        """Start a combat between two players"""
        if bet < COMBAT_MIN_BET or bet > COMBAT_MAX_BET:
            return False, f"❌ Le pari doit être entre {COMBAT_MIN_BET} et {COMBAT_MAX_BET} points!"

        challenger_points = self.db.get_user_points(challenger_id)
        target_points = self.db.get_user_points(target_id)

        if challenger_points < bet or target_points < bet:
            return False, "❌ Un des joueurs n'a pas assez de points!"

        combat_data = {
            'challenger': challenger_id,
            'target': target_id,
            'bet': bet,
            'start_time': datetime.now().timestamp(),
            'accepted': False,
            'health': {
                challenger_id: COMBAT_BASE_HEALTH,
                target_id: COMBAT_BASE_HEALTH
            },
            'moves': []
        }

        self.db.create_combat(combat_data)
        return True, f"⚔️ Combat proposé! Mise: {bet} points\nUtilisez les réactions pour combattre!"

    async def process_combat_move(self, combat_id: str, user_id: str, move: str):
        """Process a combat move"""
        combat = self.db.get_combat(combat_id)
        if not combat:
            return False, "❌ Combat non trouvé!"

        if user_id not in [combat['challenger'], combat['target']]:
            return False, "❌ Tu ne participes pas à ce combat!"

        move_data = COMBAT_MOVES.get(move)
        if not move_data:
            return False, "❌ Coup invalide!"

        # Calculate damage
        if random.random() < move_data['chance']:
            opponent_id = combat['target'] if user_id == combat['challenger'] else combat['challenger']
            damage = move_data['damage']
            combat['health'][opponent_id] -= damage
            combat['moves'].append({
                'user': user_id,
                'move': move,
                'damage': damage
            })

            self.db.update_combat(combat_id, combat)

            # Check if combat is over
            if combat['health'][opponent_id] <= 0:
                # Winner gets the bet
                self.db.add_points(user_id, combat['bet'] * 2)
                self.db.add_points(opponent_id, -combat['bet'])
                self.db.end_combat(combat_id)
                return True, f"🏆 {move_data['name']} fatal! Combat terminé! Tu as gagné {combat['bet']} points!"

            return True, f"💥 {move_data['name']} inflige {damage} dégâts!"
        else:
            return True, f"😅 {move_data['name']} raté!"