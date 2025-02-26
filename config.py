import os

# Discord Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')  # Remove default value for security
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is required")

# Twitter API Configuration
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

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

# Prison Configuration
PRISON_RATE = 0.3  # 30% chance of going to prison on failed robbery
PRISON_MIN_TIME = 300  # 5 minutes
PRISON_MAX_TIME = 1800  # 30 minutes
PRISON_ROLES = {
    "cuisinier": {"name": "👨‍🍳 Cuisinier", "reduction": 0.2},  # 20% reduction de peine
    "bibliothecaire": {"name": "📚 Bibliothécaire", "reduction": 0.15},
    "concierge": {"name": "🧹 Concierge", "reduction": 0.1}
}
PRISON_ACTIVITIES = {
    "exercice": {"name": "🏋️ Faire de l'exercice", "reduction": 60},  # 60 seconds reduction
    "lecture": {"name": "📖 Lire un livre", "reduction": 45},
    "meditation": {"name": "🧘 Méditer", "reduction": 30}
}

# Prison Escape Configuration
ESCAPE_ATTEMPT_COOLDOWN = 1800  # 30 minutes between attempts
ESCAPE_BASE_CHANCE = 0.3  # 30% base chance of successful escape
ESCAPE_FAILURE_EXTRA_TIME = 900  # 15 minutes added if caught
ESCAPE_SUCCESS_REWARD = 200  # Points earned for successful escape

# Tribunal Configuration
TRIBUNAL_VOTE_DURATION = 300  # 5 minutes
TRIBUNAL_MIN_VOTERS = 3
TRIBUNAL_ACQUIT_RATE = 0.6  # 60% des votes nécessaires pour être acquitté
TRIBUNAL_COOLDOWN = 3600  # 1 heure entre chaque demande
TRIBUNAL_COST = 500  # Coût en points pour demander un procès

# Revenge Configuration
REVENGE_SUCCESS_RATE = 0.6  # 60% success rate for revenge

# Work Configuration
WORK_COOLDOWN = 86400  # 24 hours in seconds
WORK_MIN_AMOUNT = 50
WORK_MAX_AMOUNT = 200

# Shop Configuration
SHOP_ITEMS = {
    "lockpick": {
        "name": "🔓 Kit de Crochetage",
        "price": 500,
        "description": "Augmente les chances de vol de 10%",
        "effect": {"rob_bonus": 0.1}
    },
    "fake_id": {
        "name": "📄 Faux Papiers",
        "price": 1000,
        "description": "Réduit de moitié le temps en prison",
        "effect": {"prison_reduction": 0.5}
    },
    "bulletproof": {
        "name": "🦺 Gilet Pare-balles",
        "price": 2000,
        "description": "50% de chances d'éviter la prison",
        "effect": {"prison_dodge": 0.5}
    },
    "avocat": {
        "name": "👨‍⚖️ Avocat Véreux",
        "price": 3000,
        "description": "Augmente de 20% les chances d'être acquitté au tribunal",
        "effect": {"tribunal_bonus": 0.2}
    }
}

# Heist Configuration
HEIST_MIN_PLAYERS = 2
HEIST_MAX_PLAYERS = 5
HEIST_PREPARATION_TIME = 60  # seconds to wait for other players
HEIST_MIN_REWARD = 1000
HEIST_MAX_REWARD = 5000
HEIST_SUCCESS_BASE_RATE = 0.3  # Base success rate, increases with more players

# Drug Deal Configuration
DRUG_DEAL_MIN_INVESTMENT = 100
DRUG_DEAL_MAX_INVESTMENT = 1000
DRUG_DEAL_SUCCESS_RATE = 0.6
DRUG_DEAL_PROFIT_MULTIPLIER = 2.5
DRUG_DEAL_COOLDOWN = 7200  # 2 hours

# Police Chase Configuration
CHASE_ESCAPE_RATE = 0.4
CHASE_MIN_LOSS = 100
CHASE_MAX_LOSS = 500
CHASE_COOLDOWN = 1800  # 30 minutes

# Combat Configuration
COMBAT_MIN_BET = 100
COMBAT_MAX_BET = 1000
COMBAT_DURATION = 60  # Seconds to accept challenge
COMBAT_MOVES = {
    "👊": {"name": "Punch", "damage": 25, "chance": 0.8},
    "🦶": {"name": "Kick", "damage": 35, "chance": 0.6},
    "🗡️": {"name": "Special", "damage": 50, "chance": 0.4}
}
COMBAT_BASE_HEALTH = 100

# Vote Reactions Configuration
VOTE_REACTIONS = {
    "✅": "yes",
    "❌": "no"
}
VOTE_DURATION = 300  # 5 minutes