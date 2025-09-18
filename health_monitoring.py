#!/usr/bin/env python3
"""
Health Monitoring System - Phase 4A
Système de surveillance avancé avec endpoint FastAPI, métriques et alertes
"""

import os
import sys
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import psutil
import threading
import time

# Import du bot Discord
try:
    from database_supabase import SupabaseDatabase
    from point_system import PointSystem  
    import discord
except ImportError as e:
    print(f"Warning: Could not import bot modules: {e}")

# Configuration logging avancé
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot_health.log', mode='a')
    ]
)
logger = logging.getLogger('HealthMonitor')

# FastAPI app
app = FastAPI(
    title="Discord RP Bot Health Monitor",
    description="Système de surveillance pour le bot Discord Thugz Life RP",
    version="4.0.0"
)

class HealthMonitor:
    """Moniteur de santé système complet"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.database = None
        self.bot_status = "initializing"
        self.last_check = None
        self.health_metrics = {
            "uptime": 0,
            "database_status": "unknown",
            "memory_usage": 0,
            "cpu_usage": 0,
            "active_connections": 0,
            "last_command_processed": None,
            "error_count": 0,
            "total_users": 0,
            "total_gangs": 0
        }
        
        # Initialiser la base de données
        try:
            self.database = SupabaseDatabase()
            logger.info("✅ Database connection initialized")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Récupérer les métriques système"""
        try:
            # Métriques système
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Uptime
            uptime_seconds = (datetime.now() - self.start_time).total_seconds()
            uptime_hours = round(uptime_seconds / 3600, 2)
            
            return {
                "uptime_hours": uptime_hours,
                "uptime_seconds": uptime_seconds,
                "memory_usage_percent": memory.percent,
                "memory_used_mb": round(memory.used / 1024 / 1024, 2),
                "memory_available_mb": round(memory.available / 1024 / 1024, 2),
                "cpu_usage_percent": cpu_percent,
                "disk_usage": psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {}
    
    async def check_database_health(self) -> Dict[str, Any]:
        """Vérifier la santé de la base de données avec métriques de résilience"""
        if not self.database:
            return {
                "status": "disconnected",
                "error": "Database not initialized",
                "response_time_ms": None,
                "connection_resilience": {
                    "status": "unknown",
                    "failures": 0,
                    "last_attempt": None
                }
            }
        
        try:
            start_time = time.time()
            
            # Test de connexion avec retry
            connection_status = self.database.get_connection_status()
            
            # Test de requête simple
            leaderboard = self.database.get_leaderboard(1)
            users_count = len(self.database.get_all_users()) if hasattr(self.database, 'get_all_users') else 0
            
            response_time = round((time.time() - start_time) * 1000, 2)
            
            # Déterminer le statut global
            if connection_status['connection_failures'] == 0:
                overall_status = "healthy"
            elif connection_status['connection_failures'] < 3:
                overall_status = "degraded"
            else:
                overall_status = "critical"
            
            return {
                "status": overall_status,
                "response_time_ms": response_time,
                "users_count": users_count,
                "tables_accessible": True,
                "last_check": datetime.now().isoformat(),
                "connection_resilience": {
                    "connected": connection_status['connected'],
                    "failures": connection_status['connection_failures'],
                    "last_attempt": connection_status['last_attempt'],
                    "is_reconnecting": connection_status['is_reconnecting'],
                    "max_retries": connection_status['max_retries'],
                    "status": connection_status['status']
                },
                "performance": {
                    "query_response_time_ms": response_time,
                    "connection_stable": connection_status['connection_failures'] == 0,
                    "auto_recovery_enabled": True
                }
            }
            
        except Exception as e:
            # En cas d'erreur, inclure les informations de résilience
            connection_status = self.database.get_connection_status() if self.database else {}
            
            return {
                "status": "error",
                "error": str(e),
                "response_time_ms": None,
                "last_check": datetime.now().isoformat(),
                "connection_resilience": connection_status,
                "auto_recovery_status": "attempting" if connection_status.get('is_reconnecting') else "failed"
            }
    
    async def get_bot_statistics(self) -> Dict[str, Any]:
        """Récupérer les statistiques du bot"""
        try:
            stats = {
                "total_users": 0,
                "total_gangs": 0,
                "active_prisoners": 0,
                "total_admin_actions": 0,
                "average_user_points": 0
            }
            
            if self.database:
                # Statistiques utilisateurs
                all_users = self.database.get_all_users() if hasattr(self.database, 'get_all_users') else []
                stats["total_users"] = len(all_users)
                
                # Statistiques gangs
                gangs = self.database.get_all_gangs() if hasattr(self.database, 'get_all_gangs') else []
                stats["total_gangs"] = len(gangs)
                
                # Prisonniers actifs (Justice System)
                prisoners = self.database.get_active_prisoners() if hasattr(self.database, 'get_active_prisoners') else []
                stats["active_prisoners"] = len(prisoners)
                
                # Actions admin récentes
                admin_actions = self.database.get_admin_actions(limit=100) if hasattr(self.database, 'get_admin_actions') else []
                stats["total_admin_actions"] = len(admin_actions)
                
                # Points moyens
                if all_users:
                    total_points = sum(user.get('points', 0) for user in all_users)
                    stats["average_user_points"] = round(total_points / len(all_users), 2)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting bot statistics: {e}")
            return {}
    
    async def perform_comprehensive_health_check(self) -> Dict[str, Any]:
        """Effectuer un check de santé complet"""
        logger.info("🔍 Performing comprehensive health check...")
        
        # Métriques système
        system_metrics = self.get_system_metrics()
        
        # Santé de la base de données
        db_health = await self.check_database_health()
        
        # Statistiques du bot
        bot_stats = await self.get_bot_statistics()
        
        # Status général
        overall_status = "healthy"
        issues = []
        
        # Vérifications critiques
        if db_health["status"] != "connected":
            overall_status = "unhealthy"
            issues.append("Database connection failed")
        
        if system_metrics.get("memory_usage_percent", 0) > 90:
            overall_status = "warning"
            issues.append("High memory usage")
        
        if system_metrics.get("cpu_usage_percent", 0) > 80:
            overall_status = "warning"
            issues.append("High CPU usage")
        
        self.last_check = datetime.now()
        
        return {
            "timestamp": self.last_check.isoformat(),
            "overall_status": overall_status,
            "issues": issues,
            "system": system_metrics,
            "database": db_health,
            "bot_statistics": bot_stats,
            "uptime": {
                "started_at": self.start_time.isoformat(),
                "running_for": str(datetime.now() - self.start_time)
            }
        }

# Instance globale du moniteur
health_monitor = HealthMonitor()

@app.get("/health/resilience")
async def connection_resilience():
    """Endpoint spécialisé pour la résilience de connexion"""
    try:
        if not health_monitor.database:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        connection_status = health_monitor.database.get_connection_status()
        
        # Test de performance de reconnexion
        start_time = time.time()
        test_success = health_monitor.database.is_connected()
        response_time = round((time.time() - start_time) * 1000, 2)
        
        resilience_data = {
            "connection_status": connection_status,
            "performance_test": {
                "response_time_ms": response_time,
                "connection_test_passed": test_success,
                "test_timestamp": datetime.now().isoformat()
            },
            "resilience_features": {
                "auto_retry_enabled": True,
                "exponential_backoff": True,
                "max_retries": connection_status.get('max_retries', 3),
                "degraded_mode_available": True
            },
            "health_assessment": {
                "status": connection_status.get('status', 'unknown'),
                "requires_attention": connection_status.get('connection_failures', 0) > 2,
                "auto_recovery_active": connection_status.get('is_reconnecting', False)
            }
        }
        
        # Déterminer le code de statut HTTP
        if connection_status.get('status') == 'critical':
            return JSONResponse(content=resilience_data, status_code=503)
        elif connection_status.get('status') == 'degraded':
            return JSONResponse(content=resilience_data, status_code=200)  # 200 car le service fonctionne
        else:
            return JSONResponse(content=resilience_data, status_code=200)
            
    except Exception as e:
        logger.error(f"Resilience check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Resilience check error: {str(e)}")

@app.get("/health")
async def health_endpoint():
    """Endpoint de santé basique pour Railway/UptimeRobot"""
    try:
        # Check rapide de la base de données
        if health_monitor.database:
            test_result = health_monitor.database.get_leaderboard(1)
            db_status = "connected"
        else:
            db_status = "disconnected"
        
        uptime = (datetime.now() - health_monitor.start_time).total_seconds()
        
        return JSONResponse({
            "status": "alive",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": uptime,
            "database": db_status,
            "version": "4.0.0"
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

@app.get("/health/detailed")
async def detailed_health():
    """Endpoint de santé détaillé avec toutes les métriques"""
    try:
        health_data = await health_monitor.perform_comprehensive_health_check()
        
        if health_data["overall_status"] == "unhealthy":
            return JSONResponse(content=health_data, status_code=503)
        elif health_data["overall_status"] == "warning":
            return JSONResponse(content=health_data, status_code=200)
        else:
            return JSONResponse(content=health_data, status_code=200)
            
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/metrics")
async def metrics_endpoint():
    """Endpoint pour les métriques Prometheus-style"""
    try:
        health_data = await health_monitor.perform_comprehensive_health_check()
        
        # Format métrique simple
        metrics = {
            "bot_uptime_seconds": health_data["system"]["uptime_seconds"],
            "bot_memory_usage_percent": health_data["system"]["memory_usage_percent"],
            "bot_cpu_usage_percent": health_data["system"]["cpu_usage_percent"],
            "bot_database_response_ms": health_data["database"].get("response_time_ms", 0),
            "bot_total_users": health_data["bot_statistics"]["total_users"],
            "bot_total_gangs": health_data["bot_statistics"]["total_gangs"],
            "bot_active_prisoners": health_data["bot_statistics"]["active_prisoners"]
        }
        
        return JSONResponse(metrics)
        
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def status_endpoint():
    """Endpoint de status pour monitoring externe"""
    try:
        return JSONResponse({
            "service": "Discord RP Bot",
            "status": "running",
            "version": "4.0.0",
            "environment": os.getenv("ENVIRONMENT", "production"),
            "timestamp": datetime.now().isoformat(),
            "uptime": str(datetime.now() - health_monitor.start_time)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def run_health_server(port: int = 8000):
    """Démarrer le serveur de monitoring"""
    # Sur Render, utiliser la variable PORT fournie par la plateforme
    render_port = os.getenv('PORT')
    if render_port:
        port = int(render_port)
        logger.info(f"🌐 Using Render PORT environment variable: {port}")
    else:
        logger.info(f"🌐 Using fallback port: {port}")
    
    logger.info(f"🌐 Starting health monitoring server on 0.0.0.0:{port}")
    
    try:
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=port, 
            log_level="info",
            access_log=True
        )
    except Exception as e:
        logger.error(f"Failed to start health server: {e}")

if __name__ == "__main__":
    # Démarrer le serveur de monitoring
    port = int(os.getenv("PORT", os.getenv("HEALTH_PORT", 8000)))
    run_health_server(port)
