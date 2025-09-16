#!/usr/bin/env python3
"""
Test script pour vérifier les nouvelles configurations de cooldowns
selon les spécifications du TECH Brief
"""

from config import DAILY_LIMITS, COMMAND_COOLDOWNS

def test_cooldowns():
    """Test que les cooldowns correspondent aux spécifications du TECH Brief"""
    
    print("🔍 Test des cooldowns selon TECH Brief...")
    
    # Spécifications attendues du TECH Brief
    expected_cooldowns = {
        'work': 2 * 3600,      # 2 heures
        'steal': 4 * 3600,     # 4 heures  
        'fight': 6 * 3600,     # 6 heures
        'duel': 12 * 3600,     # 12 heures
        'gift': 1 * 3600,      # 1 heure
    }
    
    expected_limits = {
        'work': 8,     # max 8 times per day
        'steal': 5,    # max 5 attempts per day
        'fight': 3,    # max 3 fights per day
        'duel': 2,     # max 2 duels per day
        'gift': 10,    # reasonable limit for gifts
    }
    
    print("\n✅ Test des cooldowns:")
    for cmd, expected_sec in expected_cooldowns.items():
        actual = COMMAND_COOLDOWNS.get(cmd, 0)
        expected_hours = expected_sec // 3600
        actual_hours = actual // 3600
        
        if actual == expected_sec:
            print(f"  ✅ {cmd}: {actual_hours}h ✓")
        else:
            print(f"  ❌ {cmd}: {actual_hours}h (attendu: {expected_hours}h)")
    
    print("\n✅ Test des limites quotidiennes:")
    for cmd, expected_limit in expected_limits.items():
        actual = DAILY_LIMITS.get(cmd, 0)
        
        if actual == expected_limit:
            print(f"  ✅ {cmd}: {actual}x/jour ✓")
        else:
            print(f"  ❌ {cmd}: {actual}x/jour (attendu: {expected_limit}x/jour)")
    
    print("\n🆕 Nouvelles commandes ajoutées:")
    new_commands = ['steal', 'fight', 'duel', 'gift']
    for cmd in new_commands:
        cooldown = COMMAND_COOLDOWNS.get(cmd, 0)
        limit = DAILY_LIMITS.get(cmd, 0)
        print(f"  🆕 {cmd}: {cooldown//3600}h cooldown, {limit}x/jour")
    
    print("\n✅ Tests terminés!")

if __name__ == "__main__":
    test_cooldowns()
