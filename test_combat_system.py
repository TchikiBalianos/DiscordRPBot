import random
from config import EMOJI_POOL, COMBAT_MATRIX

print('=== Random Emoji Selection Test ===')
for round_num in range(3):
    selected_emojis = random.sample(EMOJI_POOL, 6)
    emojis_str = ' '.join(selected_emojis)
    print(f'Round {round_num+1}: {emojis_str}')

print()
print('=== Sample Combat Simulation ===')
selected_emojis = random.sample(EMOJI_POOL, 6)
emojis_str = ' '.join(selected_emojis)
print(f'Selected emojis: {emojis_str}')

# Simulate 5 random combats
for i in range(5):
    attacker_idx = random.randint(0, 5)
    defender_idx = random.randint(0, 5)
    result, messages = COMBAT_MATRIX[(attacker_idx, defender_idx)]
    message = random.choice(messages)
    print(f'  [{i+1}] Attacker picks {selected_emojis[attacker_idx]} vs Defender picks {selected_emojis[defender_idx]} -> {result.upper()}')

print()
print('✅ System ready for deployment!')
