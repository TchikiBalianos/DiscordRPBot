import os

# Daily Command Limits Configuration
DAILY_LIMITS = {
    "rob": 3,        # 3 vols par jour
    "deal": 5,       # 5 deals par jour
    "heist": 2,      # 2 braquages par jour
    "combat": 5,     # 5 combats par jour
    "escape": 2,     # 2 tentatives d'évasion par jour
    "revenge": 1,    # 1 vengeance par jour
    "work": 1,       # 1 travail par jour
    "roulette": 10,  # 10 parties de roulette par jour
    "race": 15,      # 15 courses par jour
    "blackjack": 20, # 20 parties de blackjack par jour
    "treasure": 5,   # 5 chasses au trésor par jour
    "dice": 10       # 10 duels de dés par jour
}

# Russian Roulette Configuration
ROULETTE_MIN_BET = 100
ROULETTE_MAX_BET = 1000
ROULETTE_MULTIPLIER = 6  # 6x la mise si survie
ROULETTE_COOLDOWN = 14400  # 4 heures (augmenté de 2h à 4h)
ROULETTE_LOSS_PENALTY = 0.8  # Perd 80% de points supplémentaires en cas de mort (augmenté de 50% à 80%)

# Lottery Configuration
LOTTERY_TICKET_PRICE = 100
LOTTERY_DRAW_INTERVAL = 86400  # Tirage quotidien
LOTTERY_JACKPOT_BASE = 5000   # Cagnotte de base
LOTTERY_MAX_TICKETS = 5       # Maximum 5 tickets par personne

# Racing Configuration
RACE_MIN_BET = 50
RACE_MAX_BET = 500
RACE_COOLDOWN = 7200  # 2 heures (augmenté de 1h à 2h)
RACE_HORSES = {
    "1": {"name": "🐎 Flash", "odds": 2.0, "risk": 0.2},  # 20% de chance de se blesser (augmenté de 10% à 20%)
    "2": {"name": "🐎 Thunder", "odds": 3.0, "risk": 0.25},
    "3": {"name": "🐎 Shadow", "odds": 4.0, "risk": 0.3},
    "4": {"name": "🐎 Lucky", "odds": 5.0, "risk": 0.35}
}
RACE_INJURY_MULTIPLIER = 2.0  # Perte x2 si le cheval se blesse (augmenté de 1.5 à 2.0)

# Blackjack Configuration
BLACKJACK_MIN_BET = 100
BLACKJACK_MAX_BET = 2000
BLACKJACK_COOLDOWN = 7200  # 2 heures (augmenté de 30min à 2h)
BLACKJACK_STREAK_PENALTY = True  # Active les malus progressifs sur les pertes consécutives
BLACKJACK_MAX_STREAK_PENALTY = 0.5  # Jusqu'à 50% de perte supplémentaire après une série de défaites

# Treasure Hunt Configuration 
TREASURE_COOLDOWN = 10800  # 3 heures (augmenté de 1h à 3h)
TREASURE_MIN_REWARD = 200
TREASURE_MAX_REWARD = 1000
TREASURE_HINTS = {
    "prison": "🏢 Dans les cellules",
    "garden": "🌳 Dans le jardin",
    "kitchen": "🍳 Dans la cuisine",
    "library": "📚 Dans la bibliothèque",
    "gym": "🏋️ Dans la salle de sport"
}
TREASURE_TRAP_CHANCE = 0.4  # 40% de chance de tomber dans un piège (augmenté de 30% à 40%)
TREASURE_TRAP_LOSS = 0.7   # Perd 70% de la récompense potentielle si piège (augmenté de 50% à 70%)

# Dice Duel Configuration
DICE_MIN_BET = 50
DICE_MAX_BET = 500
DICE_COOLDOWN = 1800  # 30 minutes (augmenté de 5min à 30min)
DICE_BONUS_MULTIPLIER = 1.5  # 50% bonus pour dés identiques
DICE_LOSING_STREAK_PENALTY = 0.3  # Perd 30% supplémentaire après 3 pertes consécutives (augmenté de 20% à 30%)

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

# Narration Configuration
COMMAND_NARRATIONS = {
    "rob": [
        "🦹 Tel un voleur dans la nuit, {user} se faufile silencieusement derrière {target}...",
        "🎭 Masqué et déterminé, {user} prépare son coup contre {target}...",
        "🌙 Profitant de l'obscurité, {user} suit discrètement {target} dans une ruelle sombre..."
    ],
    "heist": [
        "🏦 La bande de {user} se réunit devant la banque, vérifiant une dernière fois leur équipement...",
        "💰 Le plan est en place. {user} et son équipe enfilent leurs masques...",
        "🚓 Les alarmes retentissent alors que {user} et sa crew forcent l'entrée du coffre..."
    ],
    "combat": [
        "⚔️ Une tension électrique remplit l'air alors que {user} défie {target} en duel...",
        "👊 La foule se rassemble en cercle autour de {user} et {target}...",
        "🥊 {user} et {target} se toisent du regard, prêts à en découdre..."
    ],
    "roulette": [
        "🎲 Les mains tremblantes, {user} fait tourner le barillet...",
        "🔫 Un silence de mort règne dans la salle alors que {user} saisit l'arme...",
        "💀 Les spectateurs retiennent leur souffle pendant que {user} joue sa vie..."
    ],
    "race": [
        "🏇 Les chevaux s'ébrouent nerveusement dans leurs stalles...",
        "🐎 La tension monte sur l'hippodrome alors que les jockeys prennent position...",
        "🎪 La foule hurle d'excitation à l'approche du départ..."
    ],
    "escape": [
        "🏃 Profitant de la relève des gardes, {user} commence son évasion...",
        "🔒 Après des semaines de préparation, {user} met son plan à exécution...",
        "⛓️ Les barreaux sciés, {user} attend le moment propice..."
    ],
    "deal": [
        "🕶️ Dans une ruelle sombre, {user} attend nerveusement son contact...",
        "💼 La mallette à la main, {user} vérifie que personne ne le suit...",
        "🌃 Le deal est prêt, {user} espère que tout se passera bien..."
    ]
}

# Shop Configuration (New Shop Items)
SHOP_ITEMS_NEW = {
    "thugz_nft": {
        "name": "🎨 NFT Thugz Original",
        "description": "NFT ultra rare de la collection Thugz - Pièce unique!",
        "price": 100000,
        "quantity": 1,
        "type": "collectible"
    },
    "thugzblock_nft": {
        "name": "🖼️ NFT ThugzBlock",
        "description": "NFT de la collection ThugzBlock - Édition limitée",
        "price": 25000,
        "quantity": 30,
        "type": "collectible"
    },
    "gift_card": {
        "name": "💳 Carte Cadeau 10$",
        "description": "Carte cadeau d'une valeur de 10$",
        "price": 15000,
        "quantity": 2,
        "type": "reward"
    },
    "tech_gift": {
        "name": "📱 Cadeau High-Tech",
        "description": "Gadget technologique d'une valeur de 30€",
        "price": 40000,
        "quantity": 1,
        "type": "reward"
    },
    "whitelist": {
        "name": "⭐ Whitelist VIP",
        "description": "Accès prioritaire aux futures collections",
        "price": 50000,
        "quantity": 10,
        "type": "access"
    },
    "dlz_currency": {
        "name": "💎 $DLZ",
        "description": "100 $DLZ - La crypto des gangsters",
        "price": 10000,
        "quantity": 50,
        "type": "currency"
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