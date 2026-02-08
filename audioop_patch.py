#!/usr/bin/env python3
"""
MONKEY PATCH AUDIOOP + IMGHDR - Solution ultime pour Python 3.13
Ce patch désactive complètement audioop et imghdr avant que les bibliothèques ne les importent
"""

import sys
import logging

logger = logging.getLogger('compatibility_patch')

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

class MockImghdr:
    """Mock imghdr module pour remplacer les fonctions de détection d'images"""
    
    def what(self, file, h=None):
        """Mock de imghdr.what - détecte le format d'image"""
        logger.warning("imghdr.what appelé mais désactivé (Python 3.13 compatibility)")
        # Retourne None par défaut (image non reconnue)
        # Les bibliothèques gèrent généralement ce cas
        return None
    
    def __getattr__(self, name):
        """Retourne une fonction mock pour tous les autres attributs imghdr"""
        def mock_function(*args, **kwargs):
            logger.warning(f"imghdr.{name} appelé mais désactivé (Python 3.13 compatibility)")
            return None
        
        return mock_function

def patch_audioop():
    """Installe le patch audioop avant tout import Discord"""
    logger.info("[+] Installation du patch audioop pour Python 3.13...")
    
    # Créer un module audioop mock
    mock_audioop = MockAudioop()
    
    # L'injecter dans sys.modules
    sys.modules['audioop'] = mock_audioop
    
    logger.info("[OK] Patch audioop installe avec succes")
    print("[PATCH] AUDIOOP PATCH: Module mock installe pour Python 3.13 compatibility")

def patch_imghdr():
    """Installe le patch imghdr avant tout import Tweepy"""
    logger.info("[+] Installation du patch imghdr pour Python 3.13...")
    
    # Créer un module imghdr mock
    mock_imghdr = MockImghdr()
    
    # L'injecter dans sys.modules
    sys.modules['imghdr'] = mock_imghdr
    
    logger.info("[OK] Patch imghdr installe avec succes")
    print("[PATCH] IMGHDR PATCH: Module mock installe pour Python 3.13 compatibility")

def patch_all():
    """Installe tous les patches de compatibilité Python 3.13"""
    patch_audioop()
    patch_imghdr()

# Auto-patch si ce module est importé
if __name__ == "__main__":
    patch_all()
else:
    # Auto-patch lors de l'import
    patch_all()
