"""
Système de logging avancé pour le bot Discord
Capture tous les événements, erreurs et performances
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import traceback
import sys


class StructuredLogger:
    """Logger structuré avec JSON et fichiers séparés"""
    
    def __init__(self, name: str, log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Logger principal
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Nettoyer les handlers existants
        self.logger.handlers.clear()
        
        # Format détaillé
        detailed_format = logging.Formatter(
            '[%(asctime)s] %(levelname)-8s [%(filename)s:%(lineno)d] %(funcName)s() - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler fichier TOUT
        all_handler = logging.FileHandler(self.log_dir / 'all.log', encoding='utf-8')
        all_handler.setLevel(logging.DEBUG)
        all_handler.setFormatter(detailed_format)
        self.logger.addHandler(all_handler)
        
        # Handler fichier ERREURS uniquement
        error_handler = logging.FileHandler(self.log_dir / 'errors.log', encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_format)
        self.logger.addHandler(error_handler)
        
        # Handler console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(detailed_format)
        self.logger.addHandler(console_handler)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log DEBUG"""
        self.logger.debug(message, extra={'data': kwargs} if kwargs else {})
    
    def info(self, message: str, **kwargs) -> None:
        """Log INFO"""
        self.logger.info(message, extra={'data': kwargs} if kwargs else {})
    
    def warning(self, message: str, **kwargs) -> None:
        """Log WARNING"""
        self.logger.warning(message, extra={'data': kwargs} if kwargs else {})
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        """Log ERROR avec traceback"""
        if exception:
            self.logger.error(f"{message}\n{traceback.format_exc()}", extra={'data': kwargs} if kwargs else {})
        else:
            self.logger.error(message, extra={'data': kwargs} if kwargs else {})
    
    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        """Log CRITICAL"""
        if exception:
            self.logger.critical(f"{message}\n{traceback.format_exc()}", extra={'data': kwargs} if kwargs else {})
        else:
            self.logger.critical(message, extra={'data': kwargs} if kwargs else {})
    
    def command_executed(self, command_name: str, user_id: str, success: bool, duration_ms: float, error: Optional[str] = None) -> None:
        """Log exécution de commande"""
        self.log_json({
            'type': 'command_execution',
            'command': command_name,
            'user_id': user_id,
            'success': success,
            'duration_ms': duration_ms,
            'error': error,
            'timestamp': datetime.now().isoformat()
        })
        
        if success:
            self.info(f"Command executed: {command_name} by {user_id} ({duration_ms:.2f}ms)")
        else:
            self.error(f"Command failed: {command_name} by {user_id} - {error}")
    
    def database_operation(self, operation: str, success: bool, duration_ms: float, error: Optional[str] = None, **kwargs) -> None:
        """Log opération base de données"""
        self.log_json({
            'type': 'database_operation',
            'operation': operation,
            'success': success,
            'duration_ms': duration_ms,
            'error': error,
            'details': kwargs,
            'timestamp': datetime.now().isoformat()
        })
        
        if success:
            self.debug(f"DB {operation} success ({duration_ms:.2f}ms): {kwargs}")
        else:
            self.error(f"DB {operation} failed ({duration_ms:.2f}ms): {error}", **kwargs)
    
    def api_call(self, service: str, endpoint: str, status_code: int, duration_ms: float, error: Optional[str] = None) -> None:
        """Log appel API"""
        self.log_json({
            'type': 'api_call',
            'service': service,
            'endpoint': endpoint,
            'status_code': status_code,
            'duration_ms': duration_ms,
            'error': error,
            'timestamp': datetime.now().isoformat()
        })
        
        if 200 <= status_code < 300:
            self.debug(f"API call: {service}/{endpoint} - {status_code} ({duration_ms:.2f}ms)")
        else:
            self.warning(f"API call: {service}/{endpoint} - {status_code} ({duration_ms:.2f}ms) - {error}")
    
    def log_json(self, data: Dict[str, Any]) -> None:
        """Sauvegarder un événement en JSON"""
        json_log = self.log_dir / 'events.jsonl'
        with open(json_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')


# Instances globales pour différents modules
bot_logger = StructuredLogger('DiscordBot')
database_logger = StructuredLogger('Database')
api_logger = StructuredLogger('API')
commands_logger = StructuredLogger('Commands')


def get_logger(name: str) -> StructuredLogger:
    """Obtenir un logger pour un module"""
    return StructuredLogger(name)
