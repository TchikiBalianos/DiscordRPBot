import tweepy
import logging
import asyncio
from datetime import datetime
from config import (
    TWITTER_API_KEY, TWITTER_API_SECRET, 
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET, 
    TWITTER_BEARER_TOKEN, TWITTER_CONFIGURED
)
from twitter_rate_limiter import TwitterRateLimiter, APIEndpoint
from tweepy.errors import TooManyRequests, Unauthorized, Forbidden

logger = logging.getLogger('EngagementBot')

class TwitterHandler:
    """Gestionnaire Twitter avec rate limiting pour plan gratuit"""
    
    def __init__(self):
        self.client = None
        self.rate_limiter = TwitterRateLimiter()
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialiser le client Twitter"""
        try:
            if not TWITTER_CONFIGURED:
                logger.warning("Twitter not properly configured")
                return
            
            self.client = tweepy.Client(
                bearer_token=TWITTER_BEARER_TOKEN,
                consumer_key=TWITTER_API_KEY,
                consumer_secret=TWITTER_API_SECRET,
                access_token=TWITTER_ACCESS_TOKEN,
                access_token_secret=TWITTER_ACCESS_SECRET,
                wait_on_rate_limit=False  # On gère nous-mêmes le rate limiting
            )
            
            logger.info("Twitter client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {e}", exc_info=True)
            self.client = None
    
    async def start(self):
        """Démarrer le gestionnaire Twitter"""
        if self.rate_limiter:
            await self.rate_limiter.start()
            logger.info("Twitter handler started")
    
    async def stop(self):
        """Arrêter le gestionnaire Twitter"""
        if self.rate_limiter:
            await self.rate_limiter.stop()
            logger.info("Twitter handler stopped")
    
    def is_available(self) -> bool:
        """Vérifier si Twitter est disponible"""
        return self.client is not None and TWITTER_CONFIGURED
    
    async def verify_account(self, username: str) -> tuple[bool, dict]:
        """
        Vérifier un compte Twitter avec rate limiting
        
        Args:
            username: Nom d'utilisateur Twitter (sans @)
            
        Returns:
            (success: bool, data: dict)
        """
        if not self.is_available():
            return False, "Service Twitter indisponible"
        
        try:
            # Nettoyer le nom d'utilisateur
            username = username.replace('@', '').strip().lower()
            
            if not username:
                return False, "Nom d'utilisateur invalide"
            
            # Faire la requête avec rate limiting
            def make_request():
                return self.client.get_users(
                    usernames=[username],
                    user_fields=['id', 'username', 'name', 'public_metrics']
                )
            
            success, response = await self.rate_limiter.make_request(
                APIEndpoint.GET_USERS,
                make_request
            )
            
            if not success:
                return False, str(response)
            
            if response.data:
                user = response.data[0]
                return True, {
                    'id': user.id,
                    'username': user.username,
                    'name': user.name,
                    'followers_count': user.public_metrics.get('followers_count', 0),
                    'verified_at': datetime.now().isoformat()
                }
            else:
                return False, f"Compte Twitter '@{username}' introuvable"
                
        except TooManyRequests:
            return False, "Limite de requêtes Twitter atteinte. Réessayez dans 15 minutes."
        except Unauthorized:
            return False, "Erreur d'authentification Twitter"
        except Forbidden:
            return False, "Accès Twitter interdit"
        except Exception as e:
            logger.error(f"Error verifying Twitter account {username}: {e}", exc_info=True)
            return False, "Erreur lors de la vérification du compte"
    
    async def get_user_tweets(self, user_id: str, max_results: int = 5) -> tuple[bool, list]:
        """
        Récupérer les tweets d'un utilisateur
        
        Args:
            user_id: ID de l'utilisateur Twitter
            max_results: Nombre maximum de tweets à récupérer
            
        Returns:
            (success: bool, tweets: list)
        """
        if not self.is_available():
            return False, []
        
        try:
            def make_request():
                return self.client.get_users_tweets(
                    id=user_id,
                    max_results=min(max_results, 10),  # Limiter pour le plan gratuit
                    tweet_fields=['created_at', 'public_metrics']
                )
            
            success, response = await self.rate_limiter.make_request(
                APIEndpoint.GET_USER_TWEETS,
                make_request
            )
            
            if not success:
                return False, []
            
            if response.data:
                tweets = []
                for tweet in response.data:
                    tweets.append({
                        'id': tweet.id,
                        'text': tweet.text,
                        'created_at': tweet.created_at.isoformat() if tweet.created_at else None,
                        'public_metrics': tweet.public_metrics or {}
                    })
                return True, tweets
            else:
                return True, []
                
        except Exception as e:
            logger.error(f"Error getting user tweets: {e}", exc_info=True)
            return False, []
    
    async def health_check(self) -> tuple[bool, str]:
        """Vérifier l'état de santé de la connexion Twitter"""
        if not self.is_available():
            return False, "Client Twitter non initialisé"
        
        try:
            def make_request():
                return self.client.get_me()
            
            success, response = await self.rate_limiter.make_request(
                APIEndpoint.GET_ME,
                make_request
            )
            
            if success and response:
                return True, "Twitter API fonctionnelle"
            else:
                return False, f"Erreur de santé: {response}"
                
        except Exception as e:
            logger.error(f"Twitter health check failed: {e}", exc_info=True)
            return False, f"Erreur de santé: {str(e)}"
    
    def get_rate_limit_status(self) -> dict:
        """Obtenir le statut des limites de taux"""
        if not self.rate_limiter:
            return {"error": "Rate limiter non initialisé"}
        
        return self.rate_limiter.get_status()
    
    async def queue_info(self) -> dict:
        """Obtenir les informations sur la queue de requêtes"""
        if not self.rate_limiter:
            return {"error": "Rate limiter non initialisé"}
        
        status = self.get_rate_limit_status()
        return {
            "pending_requests": status.get('pending_requests', 0),
            "cache_entries": status.get('cache_entries', 0),
            "endpoints_status": status.get('endpoints', {})
        }