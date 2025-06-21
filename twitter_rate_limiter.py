import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger('EngagementBot')

class APIEndpoint(Enum):
    """Endpoints de l'API Twitter avec leurs limites"""
    GET_USERS = "get_users"
    GET_ME = "get_me"
    GET_USER_TWEETS = "get_user_tweets"
    SEARCH_TWEETS = "search_tweets"

@dataclass
class RateLimitInfo:
    """Informations de limite de taux pour un endpoint"""
    requests_per_window: int = 1  # 1 requête par fenêtre pour le plan gratuit
    window_minutes: int = 15      # Fenêtre de 15 minutes
    last_request_time: Optional[float] = None
    request_count: int = 0
    reset_time: Optional[float] = None

class TwitterRateLimiter:
    """Gestionnaire de rate limiting pour l'API Twitter gratuite"""
    
    def __init__(self):
        # Configuration pour le plan gratuit X API
        self.limits = {
            APIEndpoint.GET_USERS: RateLimitInfo(requests_per_window=1, window_minutes=15),
            APIEndpoint.GET_ME: RateLimitInfo(requests_per_window=1, window_minutes=15),
            APIEndpoint.GET_USER_TWEETS: RateLimitInfo(requests_per_window=1, window_minutes=15),
            APIEndpoint.SEARCH_TWEETS: RateLimitInfo(requests_per_window=1, window_minutes=15),
        }
        
        # Queue des requêtes en attente
        self.pending_requests = asyncio.Queue()
        
        # Tâche de traitement en arrière-plan
        self.processor_task = None
        self.running = False
        
        # Cache des résultats pour éviter les requêtes répétées
        self.cache = {}
        self.cache_duration = 300  # 5 minutes de cache
    
    async def start(self):
        """Démarrer le processeur de requêtes"""
        if self.running:
            return
        
        self.running = True
        self.processor_task = asyncio.create_task(self._process_requests())
        logger.info("Twitter rate limiter started")
    
    async def stop(self):
        """Arrêter le processeur de requêtes"""
        self.running = False
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        logger.info("Twitter rate limiter stopped")
    
    async def make_request(self, endpoint: APIEndpoint, request_func: Callable, *args, **kwargs) -> tuple[bool, Any]:
        """
        Faire une requête avec rate limiting
        
        Args:
            endpoint: Type d'endpoint API
            request_func: Fonction à appeler pour faire la requête
            *args, **kwargs: Arguments pour la fonction
            
        Returns:
            (success: bool, result: Any)
        """
        # Créer une clé de cache
        cache_key = self._generate_cache_key(endpoint, args, kwargs)
        
        # Vérifier le cache
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            logger.info(f"Returning cached result for {endpoint.value}")
            return True, cached_result
        
        # Créer un Future pour attendre le résultat
        result_future = asyncio.Future()
        
        # Ajouter à la queue
        request_item = {
            'endpoint': endpoint,
            'function': request_func,
            'args': args,
            'kwargs': kwargs,
            'cache_key': cache_key,
            'future': result_future,
            'timestamp': time.time()
        }
        
        await self.pending_requests.put(request_item)
        logger.info(f"Queued request for {endpoint.value}")
        
        # Attendre le résultat (avec timeout)
        try:
            return await asyncio.wait_for(result_future, timeout=300)  # 5 minutes timeout
        except asyncio.TimeoutError:
            logger.error(f"Request timeout for {endpoint.value}")
            return False, "Timeout de la requête Twitter"
    
    async def _process_requests(self):
        """Traiter les requêtes en queue en respectant les limites"""
        while self.running:
            try:
                # Attendre une requête (avec timeout pour permettre l'arrêt)
                try:
                    request_item = await asyncio.wait_for(
                        self.pending_requests.get(), 
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                endpoint = request_item['endpoint']
                
                # Vérifier si on peut faire la requête maintenant
                if not self._can_make_request(endpoint):
                    wait_time = self._get_wait_time(endpoint)
                    logger.info(f"Rate limit hit for {endpoint.value}, waiting {wait_time:.1f}s")
                    
                    # Remettre la requête en queue après attente
                    asyncio.create_task(self._requeue_after_delay(request_item, wait_time))
                    continue
                
                # Faire la requête
                await self._execute_request(request_item)
                
            except Exception as e:
                logger.error(f"Error in request processor: {e}", exc_info=True)
                await asyncio.sleep(1)
    
    async def _requeue_after_delay(self, request_item: dict, delay: float):
        """Remettre une requête en queue après un délai"""
        await asyncio.sleep(delay)
        if self.running:
            await self.pending_requests.put(request_item)
    
    async def _execute_request(self, request_item: dict):
        """Exécuter une requête"""
        try:
            endpoint = request_item['endpoint']
            request_func = request_item['function']
            args = request_item['args']
            kwargs = request_item['kwargs']
            cache_key = request_item['cache_key']
            result_future = request_item['future']
            
            # Mettre à jour les compteurs
            self._update_rate_limit_counters(endpoint)
            
            # Exécuter la requête
            logger.info(f"Executing request for {endpoint.value}")
            result = request_func(*args, **kwargs)
            
            # Mettre en cache
            self._set_cache(cache_key, result)
            
            # Retourner le résultat
            if not result_future.done():
                result_future.set_result((True, result))
            
            logger.info(f"Request completed successfully for {endpoint.value}")
            
        except Exception as e:
            logger.error(f"Error executing request: {e}", exc_info=True)
            if not request_item['future'].done():
                request_item['future'].set_result((False, f"Erreur API: {str(e)}"))
    
    def _can_make_request(self, endpoint: APIEndpoint) -> bool:
        """Vérifier si on peut faire une requête pour cet endpoint"""
        limit_info = self.limits[endpoint]
        current_time = time.time()
        
        # Si pas de requête précédente, on peut faire la requête
        if limit_info.last_request_time is None:
            return True
        
        # Calculer le temps écoulé depuis la dernière requête
        time_since_last = current_time - limit_info.last_request_time
        window_seconds = limit_info.window_minutes * 60
        
        # Si la fenêtre est écoulée, reset les compteurs
        if time_since_last >= window_seconds:
            limit_info.request_count = 0
            limit_info.reset_time = current_time + window_seconds
            return True
        
        # Vérifier si on a dépassé la limite
        return limit_info.request_count < limit_info.requests_per_window
    
    def _get_wait_time(self, endpoint: APIEndpoint) -> float:
        """Calculer le temps d'attente avant la prochaine requête possible"""
        limit_info = self.limits[endpoint]
        current_time = time.time()
        
        if limit_info.last_request_time is None:
            return 0
        
        window_seconds = limit_info.window_minutes * 60
        time_since_last = current_time - limit_info.last_request_time
        
        return max(0, window_seconds - time_since_last)
    
    def _update_rate_limit_counters(self, endpoint: APIEndpoint):
        """Mettre à jour les compteurs de rate limiting"""
        limit_info = self.limits[endpoint]
        current_time = time.time()
        
        limit_info.last_request_time = current_time
        limit_info.request_count += 1
        
        if limit_info.reset_time is None:
            limit_info.reset_time = current_time + (limit_info.window_minutes * 60)
    
    def _generate_cache_key(self, endpoint: APIEndpoint, args: tuple, kwargs: dict) -> str:
        """Générer une clé de cache pour la requête"""
        # Créer une clé basée sur l'endpoint et les paramètres
        key_parts = [endpoint.value]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return "|".join(key_parts)
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Récupérer un résultat du cache"""
        if cache_key in self.cache:
            cached_item = self.cache[cache_key]
            if time.time() - cached_item['timestamp'] < self.cache_duration:
                return cached_item['data']
            else:
                # Cache expiré, le supprimer
                del self.cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, data: Any):
        """Mettre un résultat en cache"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
        
        # Nettoyer le cache si trop grand
        if len(self.cache) > 100:
            self._cleanup_cache()
    
    def _cleanup_cache(self):
        """Nettoyer les anciennes entrées du cache"""
        current_time = time.time()
        expired_keys = [
            key for key, item in self.cache.items()
            if current_time - item['timestamp'] > self.cache_duration
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def get_status(self) -> dict:
        """Obtenir le statut du rate limiter"""
        status = {
            'running': self.running,
            'pending_requests': self.pending_requests.qsize(),
            'cache_entries': len(self.cache),
            'endpoints': {}
        }
        
        current_time = time.time()
        for endpoint, limit_info in self.limits.items():
            next_available = "Maintenant"
            if limit_info.last_request_time:
                wait_time = self._get_wait_time(endpoint)
                if wait_time > 0:
                    next_available = f"Dans {wait_time:.1f}s"
            
            status['endpoints'][endpoint.value] = {
                'requests_used': limit_info.request_count,
                'requests_limit': limit_info.requests_per_window,
                'window_minutes': limit_info.window_minutes,
                'next_available': next_available
            }
        
        return status