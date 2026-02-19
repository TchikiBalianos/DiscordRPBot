"""
🔐 SECURE PERMISSIONS SYSTEM
Système de permissions robuste et audité pour le bot Discord.
"""

import logging
from datetime import datetime
from functools import wraps
from nextcord.ext import commands


logger = logging.getLogger('EngagementBot')


class PermissionLevel:
    """Niveaux de permission du système"""
    PUBLIC = 0          # N'importe qui
    MEMBER = 1          # Membres du serveur
    MODERATED = 2       # Soumis à cooldown/limites
    ADMIN = 3           # Admin du serveur
    STAFF = 4           # Staff approuvé (whitelist)
    OWNER = 5           # Propriétaire du bot uniquement


class AuditLogger:
    """Logger les actions sensibles pour audit"""
    
    @staticmethod
    def log_admin_action(user_id, action, target_user=None, amount=None, details=None):
        """Enregistrer une action administrative sensible"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "action": action,
            "target_user": target_user,
            "amount": amount,
            "details": details or {}
        }
        logger.critical(f"[AUDIT_ADMIN] {entry}")
    
    @staticmethod
    def log_staff_action(user_id, action, details=None):
        """Enregistrer une action staff"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "action": action,
            "details": details or {}
        }
        logger.warning(f"[AUDIT_STAFF] {entry}")


def get_permission_level(ctx) -> int:
    """
    Déterminer le niveau de permission de l'utilisateur
    Retourne un PermissionLevel
    """
    # Importer ici pour éviter circular imports
    from config import OWNER_ID, APPROVED_STAFF_IDS
    
    # Niveau OWNER
    if ctx.author.id == OWNER_ID:
        return PermissionLevel.OWNER
    
    # Niveau STAFF (whitelist)
    if ctx.author.id in APPROVED_STAFF_IDS:
        return PermissionLevel.STAFF
    
    # Niveau ADMIN (administrateur Discord)
    if ctx.author.guild_permissions.administrator:
        return PermissionLevel.ADMIN
    
    # Niveau MEMBER
    if ctx.guild is not None:
        return PermissionLevel.MEMBER
    
    return PermissionLevel.PUBLIC


def require_permission_level(required_level: int):
    """
    Décorateur qui exige un certain niveau de permission
    
    Usage:
        @require_permission_level(PermissionLevel.OWNER)
        async def critical_command(ctx):
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            user_level = get_permission_level(ctx)
            
            if user_level < required_level:
                level_names = {
                    PermissionLevel.PUBLIC: "Public",
                    PermissionLevel.MEMBER: "Membre",
                    PermissionLevel.MODERATED: "Modéré",
                    PermissionLevel.ADMIN: "Administrateur",
                    PermissionLevel.STAFF: "Staff",
                    PermissionLevel.OWNER: "Propriétaire",
                }
                required_name = level_names.get(required_level, "Inconnu")
                await ctx.send(f"❌ Permission refusée. Niveau requis: **{required_name}**")
                logger.warning(f"Permission denied for {ctx.author} (level {user_level}) to execute {func.__name__}")
                return
            
            # Log actions sensibles
            if required_level >= PermissionLevel.STAFF:
                command_name = ctx.command.name if hasattr(ctx, 'command') and ctx.command else func.__name__
                AuditLogger.log_staff_action(ctx.author.id, f"Executed {command_name}")
            
            if required_level == PermissionLevel.OWNER:
                command_name = ctx.command.name if hasattr(ctx, 'command') and ctx.command else func.__name__
                AuditLogger.log_admin_action(ctx.author.id, f"Executed SENSITIVE command: {command_name}")
            
            return await func(self, ctx, *args, **kwargs)
        
        return commands.check(lambda ctx: get_permission_level(ctx) >= required_level)(wrapper)
    
    return decorator


# === Décorateurs simplifiés ===

def is_owner_only():
    """Strict: Propriétaire du bot uniquement"""
    return require_permission_level(PermissionLevel.OWNER)


def is_staff_or_owner():
    """Staff approuvé ou propriétaire"""
    return require_permission_level(PermissionLevel.STAFF)


def is_admin_or_owner():
    """Admin serveur ou propriétaire"""
    return require_permission_level(PermissionLevel.ADMIN)


def require_audit_log(action_description: str, require_amount=False):
    """
    Décorateur qui log automatiquement les actions sensibles
    
    Usage:
        @require_audit_log("Modified user points", require_amount=True)
        async def admin_command(ctx, user, amount):
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            # Chercher 'amount' dans les args ou kwargs
            amount = kwargs.get('amount', None)
            for arg in args:
                if isinstance(arg, int) and require_amount and amount is None:
                    amount = arg
                    break
            
            # Log l'action
            target_user = args[0].id if args and hasattr(args[0], 'id') else None
            AuditLogger.log_admin_action(
                ctx.author.id,
                action_description,
                target_user=target_user,
                amount=amount,
                details={"guild": ctx.guild.id if ctx.guild else None}
            )
            
            return await func(self, ctx, *args, **kwargs)
        
        return wrapper
    
    return decorator


def rate_limit_admin_action(max_per_day=10):
    """
    Limiter les actions admin sensibles
    
    Usage:
        @rate_limit_admin_action(max_per_day=10)
        async def admin_command(ctx):
            pass
    """
    def decorator(func):
        # Cache des actions: {user_id: [(timestamp, count)]}
        if not hasattr(decorator, '_action_cache'):
            decorator._action_cache = {}
        
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            from datetime import datetime, date

            user_id = str(ctx.author.id)
            action_name = func.__name__

            # Priorité au rate-limiting persistant via la DB (survit aux redémarrages)
            db = getattr(getattr(self, 'points', None), 'database', None)
            if db and hasattr(db, 'get_daily_commands') and hasattr(db, 'increment_daily_command'):
                today = date.today().isoformat()
                cmd_key = f"admin_{action_name}"
                commands = db.get_daily_commands(user_id, today) or {}
                if commands.get(cmd_key, 0) >= max_per_day:
                    await ctx.send(f"❌ Limite quotidienne atteinte pour cette action ({max_per_day}/jour)")
                    logger.warning(f"Rate limit hit (DB) for {user_id} on {action_name}")
                    return
                db.increment_daily_command(user_id, cmd_key, today)
            else:
                # Fallback : cache en mémoire (réinitialisé au redémarrage)
                now = datetime.now()
                key = f"{user_id}_{action_name}"
                cache = decorator._action_cache.get(key, [])
                cache = [(ts, cnt) for ts, cnt in cache if (now - ts).days < 1]
                if sum(cnt for _, cnt in cache) >= max_per_day:
                    await ctx.send(f"❌ Limite quotidienne atteinte pour cette action ({max_per_day}/jour)")
                    logger.warning(f"Rate limit hit (memory) for {user_id} on {action_name}")
                    return
                cache.append((now, 1))
                decorator._action_cache[key] = cache

            return await func(self, ctx, *args, **kwargs)
        
        return wrapper
    
    return decorator


# === Validation des montants ===

def validate_amount(max_amount=None, min_amount=1):
    """
    Décorateur pour valider les montants de points
    
    Usage:
        @validate_amount(max_amount=10000)
        async def admin_command(ctx, user, amount: int):
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            # Chercher 'amount' dans les args ou kwargs
            amount = kwargs.get('amount', None)
            if amount is None:
                for arg in args:
                    if isinstance(arg, int):
                        amount = arg
                        break
            
            if amount is None:
                await ctx.send("❌ Montant non spécifié")
                return
            
            if amount < min_amount:
                await ctx.send(f"❌ Le montant doit être >= {min_amount}")
                return
            
            if max_amount and amount > max_amount:
                await ctx.send(f"❌ Le montant ne peut pas dépasser {max_amount}")
                return
            
            return await func(self, ctx, *args, **kwargs)
        
        return wrapper
    
    return decorator
