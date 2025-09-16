#!/usr/bin/env python3
"""
Script de monitoring pour le bot
"""

import os
import time
import requests
from datetime import datetime
from database_supabase import SupabaseDatabase

def check_bot_status():
    """Vérifier le statut du bot"""
    try:
        # Vérifier la base de données
        db = SupabaseDatabase()
        
        if not db.is_connected():
            return {"status": "error", "message": "Database connection failed"}
        
        # Vérifier les données récentes
        users = db.get_leaderboard(5)
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "users_count": len(users),
            "top_user": users[0] if users else None
        }
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

def send_webhook_alert(webhook_url, message):
    """Envoyer une alerte webhook (Discord/Slack)"""
    try:
        payload = {
            "content": f"🚨 **Bot Alert**: {message}",
            "username": "Bot Monitor"
        }
        
        response = requests.post(webhook_url, json=payload)
        return response.status_code == 204
    
    except Exception as e:
        print(f"Failed to send webhook: {e}")
        return False

def main():
    """Monitoring principal"""
    status = check_bot_status()
    
    print(f"Bot Status: {status['status']}")
    print(f"Message: {status.get('message', 'OK')}")
    
    # Envoyer une alerte si erreur
    if status['status'] == 'error':
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        if webhook_url:
            send_webhook_alert(webhook_url, status['message'])

if __name__ == "__main__":
    main()