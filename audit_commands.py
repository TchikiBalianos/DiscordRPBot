#!/usr/bin/env python3
"""
Script d'audit des commandes pour internationalisation
Analyse toutes les commandes existantes et identifie le besoin d'aliases français
"""

import re

def audit_commands():
    """Analyse le fichier commands.py pour extraire toutes les commandes et leurs aliases"""
    
    print("🔍 Audit des commandes existantes...\n")
    
    # Lire le fichier commands.py
    with open('commands.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern pour extraire les commandes
    pattern = r"@commands\.command\(name='([^']+)'(?:, aliases=\[([^\]]+)\])?\)"
    matches = re.findall(pattern, content)
    
    commands_data = []
    
    for match in matches:
        command_name = match[0]
        aliases_str = match[1]
        
        # Parser les aliases
        aliases = []
        if aliases_str:
            # Nettoyer et extraire les aliases
            aliases_clean = re.findall(r"'([^']+)'", aliases_str)
            aliases = aliases_clean
        
        commands_data.append({
            'name': command_name,
            'aliases': aliases,
            'has_french': any('é' in alias or 'è' in alias or 'à' in alias or 'ç' in alias or 
                             alias in ['travail', 'cadeau', 'vengeance', 'classement', 
                                     'braquage', 'rejoindre', 'bagarre', 'boutique', 'acheter',
                                     'aide', 'commandes', 'solde', 'argent', 'boulot', 'job',
                                     'voler', 'cambrioler', 'bataille', 'duel_honneur', 'statut',
                                     'cellule', 'activite', 'action', 'faire', 'proces', 'cour',
                                     'justice', 'inventaire', 'inv', 'objets', 'echanger', 
                                     'troquer', 'echange', 'ajouterpoints', 'donnerpoints',
                                     'retirerpoints', 'enleverpoints', 'liertwitter', 
                                     'connecttwitter', 'statustwitter', 'statut_x', 'queuetwitter',
                                     'file_x', 'deconnectertwitter', 'delier_x', 'arreter',
                                     'arreter_suspect', 'caution', 'payer_caution', 'visiter',
                                     'visite_prison', 'plaider', 'supplier', 'travail_prison',
                                     'bosser_prison']
                             for alias in aliases)
        })
    
    # Afficher le rapport
    print("📊 Rapport d'audit des commandes:\n")
    
    needs_french = []
    has_french = []
    
    for cmd in commands_data:
        status = "✅ A des aliases FR" if cmd['has_french'] else "❌ Pas d'alias FR"
        aliases_str = f"[{', '.join(cmd['aliases'])}]" if cmd['aliases'] else "[]"
        
        print(f"  {status} | !{cmd['name']} {aliases_str}")
        
        if cmd['has_french']:
            has_french.append(cmd)
        else:
            needs_french.append(cmd)
    
    print(f"\n📈 Statistiques:")
    print(f"  Total commandes: {len(commands_data)}")
    print(f"  Avec aliases FR: {len(has_french)}")
    print(f"  Sans aliases FR: {len(needs_french)}")
    print(f"  Couverture: {len(has_french)/len(commands_data)*100:.1f}%")
    
    print(f"\n🔧 Commandes nécessitant des aliases français:")
    for cmd in needs_french:
        # Suggestions d'aliases français
        suggestions = get_french_suggestions(cmd['name'])
        print(f"  !{cmd['name']} → {suggestions}")
    
    return commands_data, needs_french

def get_french_suggestions(command_name):
    """Suggère des aliases français pour une commande anglaise"""
    
    suggestions_map = {
        'debug': ['debug'],  # Garde debug
        'ping': ['ping'],    # Garde ping
        'help': ['aide', 'commandes'],
        'points': ['points', 'solde'],
        'work': ['travail', 'boulot'],  # Déjà présent
        'steal': ['voler', 'rob'],      # Déjà présent
        'gift': ['cadeau', 'donner'],   # Déjà présent
        'revenge': ['vengeance'],       # Déjà présent
        'leaderboard': ['classement', 'top'],  # Déjà présent
        'heist': ['braquage', 'casse'], # Déjà présent
        'joinheist': ['rejoindre'],     # Déjà présent
        'combat': ['combat', 'bataille'],
        'fight': ['bagarre', 'combattre'],  # Déjà présent
        'duel': ['duel'],
        'prison': ['prison', 'statut'],
        'activity': ['activite', 'action'],
        'tribunal': ['tribunal', 'proces'],
        'shop': ['boutique', 'magasin'],    # Déjà présent
        'buy': ['acheter', 'achat'],        # Déjà présent
        'inventory': ['inventaire', 'inv'],
        'trade': ['echanger', 'troquer']
    }
    
    return suggestions_map.get(command_name, [f'{command_name}_fr'])

if __name__ == "__main__":
    audit_commands()
