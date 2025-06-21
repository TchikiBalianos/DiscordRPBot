#!/usr/bin/env python3
"""
Health check endpoint pour Railway
"""

import os
import asyncio
from database_supabase import SupabaseDatabase

async def health_check():
    """Vérifier la santé du bot"""
    try:
        # Vérifier la base de données
        db = SupabaseDatabase()
        if not db.is_connected():
            return False, "Database connection failed"
        
        # Test simple
        users = db.get_leaderboard(1)
        
        return True, "Bot is healthy"
    
    except Exception as e:
        return False, f"Health check failed: {str(e)}"

def main():
    """Main health check"""
    is_healthy, message = asyncio.run(health_check())
    
    if is_healthy:
        print(f"✅ {message}")
        exit(0)
    else:
        print(f"❌ {message}")
        exit(1)

if __name__ == "__main__":
    main()