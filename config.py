import os

# Configuration Twitter
TWITTER_CONFIGURED = True  # ou False si Twitter n'est pas configuré

# Twitter API Configuration (get from environment variables)
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY', '')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET', '')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN', '')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET', '')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN', '')

# Twitter Points Configuration
POINTS_TWITTER_LIKE = 5
POINTS_TWITTER_RT = 10
POINTS_TWITTER_COMMENT = 15

# === DATABASE RESILIENCE CONFIGURATION (Phase 4C) ===
DATABASE_RESILIENCE_CONFIG = {
    "max_retries": 3,              # Nombre maximum de tentatives de reconnexion
    "base_delay": 1.0,             # Délai de base en secondes pour l'exponential backoff
    "max_delay": 30.0,             # Délai maximum entre les tentatives
    "connection_timeout": 10.0,     # Timeout pour les requêtes individuelles
    "health_check_interval": 300,   # Intervalle de vérification de santé (5 minutes)
    "enable_degraded_mode": True,   # Activer le mode dégradé en cas d'échec
    "log_connection_issues": True,  # Logger les problèmes de connexion
    "auto_reconnect": True,         # Reconnexion automatique activée
    "jitter_enabled": True,         # Ajouter du jitter pour éviter thundering herd
    "circuit_breaker": {
        "failure_threshold": 5,     # Seuil d'échecs pour ouvrir le circuit
        "recovery_timeout": 60,     # Timeout avant tentative de récupération
        "half_open_max_calls": 3    # Appels max en mode semi-ouvert
    }
}

# Daily Command Limits Configuration (selon TECH Brief specs)
DAILY_LIMITS = {
    "rob": 5,        # 5 vols par jour (steal selon brief)
    "steal": 5,      # 5 vols par jour (nouvelle commande)
    "deal": 5,       # 5 deals par jour
    "heist": 2,      # 2 braquages par jour
    "combat": 5,     # 5 combats par jour (combat général)
    "fight": 3,      # 3 combats par jour (fight selon brief)
    "duel": 2,       # 2 duels par jour (duel selon brief)
    "escape": 2,     # 2 tentatives d'évasion par jour
    "revenge": 1,    # 1 vengeance par jour
    "work": 8,       # 8 travaux par jour (selon brief: max 8 times per day)
    "gift": 10,      # 10 cadeaux par jour (nouvelle commande)
    "roulette": 10,  # 10 parties de roulette par jour
    "race": 15,      # 15 courses par jour
    "blackjack": 20, # 20 parties de blackjack par jour
    "treasure": 5,   # 5 chasses au trésor par jour
    "dice": 10       # 10 duels de dés par jour
}

# Command Cooldowns Configuration (selon TECH Brief specs)
COMMAND_COOLDOWNS = {
    "work": 2 * 3600,      # 2 heures entre chaque !work
    "steal": 4 * 3600,     # 4 heures entre chaque !steal
    "rob": 4 * 3600,       # 4 heures entre chaque !rob (compatibilité)
    "fight": 6 * 3600,     # 6 heures entre chaque !fight
    "duel": 12 * 3600,     # 12 heures entre chaque !duel
    "gift": 1 * 3600,      # 1 heure entre chaque !gift
    "combat": 3 * 3600,    # 3 heures entre chaque !combat (général)
    "arrest": 1 * 3600,    # 1 heure entre chaque arrestation
    "bail": 30 * 60,       # 30 minutes entre tentatives de caution
    "visit": 2 * 3600,     # 2 heures entre visites en prison
}

# Justice System Configuration (nouveau selon TECH Brief)
JUSTICE_CONFIG = {
    "arrest_cost": 500,           # Coût pour arrêter quelqu'un
    "min_arrest_points": 1000,    # Points minimum pour pouvoir arrêter
    "base_bail_amount": 2000,     # Montant de base pour la caution
    "bail_multiplier": 1.5,       # Multiplicateur selon la gravité
    "bail_cost_multiplier": 1.5,  # Alias pour compatibilité tests
    "max_prison_time": 24 * 3600, # Temps de prison maximum (24h)
    "min_prison_time": 1 * 3600,  # Temps de prison minimum (1h)
    "min_sentence_hours": 1,      # Alias pour compatibilité tests (heures)
    "max_sentence_hours": 24,     # Alias pour compatibilité tests (heures)
    "prison_work_reward": 50,     # Points gagnés par heure de travail en prison
    "visit_cost": 100,            # Coût pour visiter en prison
    "plea_success_rate": 0.3,     # 30% de chance de succès pour plaider
}

# Administration System Configuration (nouveau selon TECH Brief)
ADMIN_CONFIG = {
    "max_items_per_action": 10,    # Maximum d'items par commande admin
    "restricted_items": [          # Items nécessitant permissions spéciales
        "vip_pass", "mod_tools", "admin_badge", "server_boosts"
    ],
    "user_roles_hierarchy": [      # Hiérarchie des rôles utilisateurs (ordre croissant)
        "member", "trusted", "vip", "helper", "moderator", "admin"
    ],
    "promotable_roles": [          # Rôles que les admins peuvent promouvoir
        "trusted", "vip", "helper"
    ],
    "demotable_roles": [           # Rôles que les admins peuvent rétrograder
        "trusted", "vip", "helper", "moderator"
    ],
    "admin_action_log": True,      # Logger toutes les actions admin
    "require_reason": True,        # Exiger une raison pour promote/demote
}

# Advanced Gang Wars Configuration (Phase 4B selon TECH Brief)
ADVANCED_GANG_CONFIG = {
    "alliance_cost": 5000,         # Coût pour proposer une alliance
    "max_alliances": 3,            # Maximum 3 alliances par gang
    "alliance_duration": 7 * 24 * 3600,  # Alliance dure 7 jours
    "territory_claim_cost": 10000, # Coût pour revendiquer un territoire
    "territory_defense_bonus": 1.2, # Bonus 20% pour défendre son territoire
    "asset_types": [               # Types d'assets de gang disponibles
        "weapons_cache", "safe_house", "drug_lab", "money_laundry", 
        "security_system", "recruitment_center", "training_facility"
    ],
    "asset_costs": {               # Coûts des différents assets
        "weapons_cache": 15000,    # Cache d'armes
        "safe_house": 25000,       # Planque sécurisée
        "drug_lab": 30000,         # Laboratoire de drogue
        "money_laundry": 20000,    # Blanchiment d'argent
        "security_system": 12000,  # Système de sécurité
        "recruitment_center": 8000, # Centre de recrutement
        "training_facility": 18000  # Centre d'entraînement
    },
    "asset_benefits": {            # Bénéfices des assets
        "weapons_cache": {"gang_war_bonus": 1.3, "description": "Bonus 30% en guerre"},
        "safe_house": {"protection": 0.8, "description": "Protection 80% contre vols"},
        "drug_lab": {"daily_income": 500, "description": "500 DLZ/jour passif"},
        "money_laundry": {"tax_reduction": 0.5, "description": "50% moins de taxes"},
        "security_system": {"intel_bonus": 1.5, "description": "Intel 50% meilleur"},
        "recruitment_center": {"recruit_bonus": 2.0, "description": "Recrutement 2x plus rapide"},
        "training_facility": {"member_bonus": 1.1, "description": "Membres 10% plus forts"}
    },
    "reputation_system": {         # Système de réputation de gang
        "min_reputation": -100,    # Réputation minimum
        "max_reputation": 100,     # Réputation maximum
        "war_victory_bonus": 10,   # Bonus pour victoire en guerre
        "war_defeat_penalty": -5,  # Pénalité pour défaite
        "alliance_bonus": 3,       # Bonus pour nouvelle alliance
        "territory_bonus": 5,      # Bonus pour nouveau territoire
        "asset_bonus": 2           # Bonus pour nouvel asset
    },
    "territories": [               # Territoires disponibles
        "downtown", "harbor", "industrial", "suburbs", "airport",
        "casino_district", "financial_center", "underground", "market_square"
    ],
    "territory_benefits": {        # Bénéfices par territoire
        "downtown": {"daily_income": 800, "prestige": 5},
        "harbor": {"smuggling_bonus": 1.4, "prestige": 3},
        "industrial": {"asset_discount": 0.8, "prestige": 2},
        "suburbs": {"recruitment_bonus": 1.3, "prestige": 1},
        "airport": {"international_bonus": 1.5, "prestige": 4},
        "casino_district": {"gambling_bonus": 1.6, "prestige": 6},
        "financial_center": {"money_bonus": 1.8, "prestige": 8},
        "underground": {"stealth_bonus": 1.7, "prestige": 3},
        "market_square": {"trade_bonus": 1.4, "prestige": 4}
    }
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
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
# if not DISCORD_TOKEN:
#     raise ValueError("DISCORD_TOKEN is required")



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
        "🌙 Profitant de l'obscurité, {user} suit discrètement {target} dans une ruelle sombre...",
        "🕵️ Avec la précision d'un professionnel, {user} cible {target}...",
        "💨 Dans un élan foudroyant, {user} s'en prend à {target}...",
        "🎯 L'occasion parfaite se présente... {user} attaque {target}...",
        "🏃 {user} repère {target} seul et enclenche son plan...",
        "😈 D'un geste rapide, {user} prive {target} de son argent..."
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


# ============================================
# 🔐 SECURITY & PERMISSIONS CONFIGURATION
# ============================================

# Propriétaire du bot (ID Discord)
OWNER_ID = 250313844554072064

# Staff approuvés (whitelist d'IDs - PAS de rôles spécialisés)
# Le propriétaire est automatiquement reconnu, pas besoin de l'ajouter ici
APPROVED_STAFF_IDS = [
    # Ajouter les IDs des modérateurs approuvés si besoin
    # 123456789,
]

# Serveurs de confiance pour commandes sensibles
# Les commandes critiques ne sont exécutables que depuis ces serveurs
TRUSTED_GUILD_IDS = []  # À remplir avec vos serveurs approuvés

# === Limites de Modification de Points (Staff Commands) ===
STAFF_EDITPOINTS_DAILY_LIMIT = 10  # Max 10 modifications de points par jour
STAFF_EDITPOINTS_MAX_ADD = 10000  # Max 10k points par ajout
STAFF_EDITPOINTS_MAX_REMOVE = 1000000  # Max 1M points par retrait
STAFF_EDITPOINTS_MIN_PER_CHANGE = 1  # Min 1 point par modification

# === Limites de Modification d'Items ===
STAFF_EDITITEM_DAILY_LIMIT = 20  # Max 20 modifications d'items par jour
STAFF_EDITITEM_GUILD_LIMIT = 100  # Max 100 items totaux par serveur

# === Limites de Commandes Admin ===
ADMIN_ACTION_RATE_LIMIT = 5  # Max 5 actions admin par 10 secondes

# === Paramètres d'Audit ===
ENABLE_AUDIT_LOGGING = True  # Activer les logs d'audit complets
AUDIT_LOG_CRITICAL_ONLY = False  # False = log tout, True = log seulement actions critiques
AUDIT_LOG_RETENTION_DAYS = 90  # Garder les logs d'audit pendant 90 jours

# === Whitelist de Commandes par Serveur ===
# Si activé, seules ces commandes sont disponibles sur serveurs non approuvés
RESTRICTED_COMMANDS_ON_UNTRUSTED_SERVERS = {
    "addpoints": True,      # Commande critiques
    "removepoints": True,   # Commande critiques
    "additem": True,        # Commande critiques
    "removeitem": True,     # Commande critiques
}

# === Combat Moves ===
# Emojis utilisés pour les réactions de combat
COMBAT_MOVES = ['⚔️', '🛡️', '🤜']  # Attaque, Défense, Puissant
COMBAT_MOVE_NAMES = {
    '⚔️': 'Attaque rapide',
    '🛡️': 'Défense',
    '🤜': 'Coup puissant'
}

# === Combat Configuration ===
COMBAT_REACTION_TIMEOUT = 300  # 5 minutes en secondes
COMBAT_FIRST_MOVE_TIMEOUT = 60  # 1 minute pour choisir son premier coup
COMBAT_ROUNDS = 1  # Nombre de rounds de combat
COMBAT_MIN_BET = 50
COMBAT_MAX_BET = 10000

# Logique des coups (qui bat quoi):
# Attaque < Défense < Puissance < Attaque
COMBAT_MOVE_RESULTS = {
    ('⚔️', '⚔️'): ('tie', 'Les deux attaques se heurtent de plein fouet!'),
    ('⚔️', '🛡️'): ('lose', 'La défense stoppe net l\'attaque!'),
    ('⚔️', '🤜'): ('lose', 'Le coup puissant transperce l\'attaque!'),
    ('🛡️', '⚔️'): ('win', 'Votre défense neutralise l\'attaque!'),
    ('🛡️', '🛡️'): ('tie', 'Les deux se défendent! Impasse totale...'),
    ('🛡️', '🤜'): ('lose', 'Le coup puissant brise la défense!'),
    ('🤜', '⚔️'): ('win', 'Votre coup puissant crève la défense!'),
    ('🤜', '🛡️'): ('win', 'Même la défense échoue contre cette puissance!'),
    ('🤜', '🤜'): ('tie', 'Les deux coups puissants s\'annulent!'),
}

# === Heist Configuration ===
# Paramètres pour les braquages collectifs
HEIST_MIN_REWARD = 500
HEIST_MAX_REWARD = 2000
HEIST_MAX_PARTICIPANTS = 5
HEIST_SUCCESS_RATE = 0.65  # 65% de chance de succès

# === Debug Mode ===
# ⚠️ À désactiver en production!
DEBUG_PERMISSIONS = False  # Si True, affiche les checks de permissions en console