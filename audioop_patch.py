#!/usr/bin/env python3
"""
MONKEY PATCH AUDIOOP - Solution ultime pour Python 3.13
Ce patch désactive complètement audioop avant que Discord/nextcord ne l'importe
"""

import sys
import logging

logger = logging.getLogger('audioop_patch')

class MockAudioop:
    """Mock audioop module pour remplacer les fonctions audio"""
    
    def __getattr__(self, name):
        """Retourne une fonction mock pour tous les attributs audioop"""
        def mock_function(*args, **kwargs):
            logger.warning(f"audioop.{name} appelé mais désactivé (Python 3.13 compatibility)")
            # Retourner des valeurs par défaut selon la fonction
            if name in ['mul', 'add', 'bias']:
                return b''  # Retourner bytes vide pour fonctions audio
            elif name in ['max', 'avg', 'maxpp', 'avgpp']:
                return 0  # Retourner 0 pour fonctions de mesure
            elif name in ['rms']:
                return 0  # RMS value
            elif name in ['findmax', 'findfit']:
                return (0, 0)  # Tuple pour fonctions de recherche
            else:
                return None  # Valeur par défaut
        
        return mock_function

def patch_audioop():
    """Installe le patch audioop avant tout import Discord"""
    logger.info("🔧 Installation du patch audioop pour Python 3.13...")
    
    # Créer un module audioop mock
    mock_audioop = MockAudioop()
    
    # L'injecter dans sys.modules
    sys.modules['audioop'] = mock_audioop
    
    logger.info("✅ Patch audioop installé avec succès")
    print("🎯 AUDIOOP PATCH: Module mock installé pour Python 3.13 compatibility")

# Auto-patch si ce module est importé
if __name__ == "__main__":
    patch_audioop()
else:
    # Auto-patch lors de l'import
    patch_audioop()
