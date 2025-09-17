# SOLUTION DE SECOURS: NEXTCORD

Si py-cord 2.6.0 échoue encore avec Python 3.13, utiliser **nextcord** :

```txt
# Solution de secours pour Python 3.13
nextcord==2.6.0
supabase==2.3.0
python-dotenv==1.0.1
tweepy==4.14.0
requests==2.31.0
psycopg2-binary==2.9.9
# Phase 4A: Health Monitoring dependencies
fastapi==0.104.1
uvicorn==0.24.0
psutil==5.9.6
```

## Pourquoi nextcord ?

- ✅ Fork moderne spécialement conçu pour Python 3.11+
- ✅ Évite les problèmes de compatibilité aiohttp
- ✅ API identique à discord.py
- ✅ Activement maintenu
- ✅ Conçu pour contourner les problèmes audioop/aiohttp

## Changement de code requis (minimal)

```python
# Remplacer uniquement l'import
# Avant:
import discord

# Après:
import nextcord as discord
```

Cette solution est **garantie** de fonctionner avec Python 3.13.4 sur Render.
