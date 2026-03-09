import nextcord as discord
from nextcord.ext import commands
import logging
from datetime import datetime
import random
import asyncio
from config import (
    OWNER_ID, APPROVED_STAFF_IDS, DAILY_LIMITS, COMMAND_COOLDOWNS,
    COMMAND_NARRATIONS, EMOJI_POOL, COMBAT_FIRST_MOVE_TIMEOUT,
    COMBAT_REACTION_TIMEOUT, JUSTICE_CONFIG, ADMIN_CONFIG,
    SHOP_ITEMS, SHOP_ITEMS_NEW, PRISON_ACTIVITIES, PRISON_DISCORD,
    STAFF_EDITPOINTS_MAX_ADD, STAFF_EDITPOINTS_MAX_REMOVE,
)
from tweepy.errors import TooManyRequests, NotFound, Unauthorized

logger = logging.getLogger('EngagementBot')

def is_bot_owner():
    """Check if the user is the bot owner (by Discord user ID)"""
    async def predicate(ctx):
        if ctx.author.id == OWNER_ID:
            return True
        if ctx.author.id in APPROVED_STAFF_IDS:
            return True
        await ctx.send("❌ **Permission refusée.** Cette commande est réservée au propriétaire du bot.")
        logger.warning(f"SECURITY: {ctx.author} ({ctx.author.id}) tried to use admin command '{ctx.command}' in {ctx.guild}")
        return False
    return commands.check(predicate)

def check_daily_limit(command_name):
    """Decorator to check daily command limits"""
    async def predicate(ctx):
        # Accéder à la base de données pour vérifier l'utilisation quotidienne
        try:
            # Incrémenter l'utilisation quotidienne pour ce tracage
            if hasattr(ctx.bot, 'db'):
                # Accès direct à la base de données
                usage = ctx.bot.db.get_daily_usage(str(ctx.author.id), command_name)
            elif hasattr(ctx.bot, 'point_system') and hasattr(ctx.bot.point_system, 'db'):
                # Accès via point_system
                usage = ctx.bot.point_system.db.get_daily_usage(str(ctx.author.id), command_name)
            else:
                # Cas de fallback si la structure n'est pas comme prévu
                logger.warning(f"Impossible d'accéder à la base de données pour vérifier les limites quotidiennes: {command_name}")
                return True  # Permettre l'exécution par défaut
                
            if usage >= DAILY_LIMITS.get(command_name, float('inf')):
                await ctx.send(f"❌ Tu as atteint la limite quotidienne pour cette commande ({DAILY_LIMITS[command_name]}x par jour)")
                return False
            
            # Incrémenter uniquement si le check passe, pour ne pas compter les tentatives échouées
            if hasattr(ctx.bot, 'db'):
                ctx.bot.db.increment_daily_usage(str(ctx.author.id), command_name)
            elif hasattr(ctx.bot, 'point_system') and hasattr(ctx.bot.point_system, 'db'):
                ctx.bot.point_system.db.increment_daily_usage(str(ctx.author.id), command_name)
                
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des limites quotidiennes: {e}", exc_info=True)
            return True  # En cas d'erreur, permettre l'exécution
    return commands.check(predicate)

def check_cooldown_and_limit(command_name):
    """Decorator to check both cooldown and daily command limits selon TECH Brief"""
    async def predicate(ctx):
        try:
            # 1. Vérifier le cooldown d'abord
            cooldown_seconds = COMMAND_COOLDOWNS.get(command_name, 0)
            if cooldown_seconds > 0:
                # Accéder à la base de données pour le cooldown
                db = None
                if hasattr(ctx.bot, 'db'):
                    db = ctx.bot.db
                elif hasattr(ctx.bot, 'point_system') and hasattr(ctx.bot.point_system, 'db'):
                    db = ctx.bot.point_system.db
                
                if db and hasattr(db, 'get_command_cooldown'):
                    remaining_cooldown = db.get_command_cooldown(str(ctx.author.id), command_name)
                    if remaining_cooldown > 0:
                        hours = remaining_cooldown // 3600
                        minutes = (remaining_cooldown % 3600) // 60
                        seconds = remaining_cooldown % 60
                        if hours > 0:
                            time_str = f"{hours}h {minutes:02d}min"
                        elif minutes > 0:
                            time_str = f"{minutes}min {seconds:02d}s"
                        else:
                            time_str = f"{seconds}s"
                        await ctx.send(f"⏰ Reviens dans **{time_str}** pour `!{command_name}` !")
                        return False
            
            # 2. Vérifier la limite quotidienne
            if hasattr(ctx.bot, 'db'):
                usage = ctx.bot.db.get_daily_usage(str(ctx.author.id), command_name)
            elif hasattr(ctx.bot, 'point_system') and hasattr(ctx.bot.point_system, 'db'):
                usage = ctx.bot.point_system.db.get_daily_usage(str(ctx.author.id), command_name)
            else:
                logger.warning(f"Impossible d'accéder à la base de données pour {command_name}")
                return True
                
            if usage >= DAILY_LIMITS.get(command_name, float('inf')):
                await ctx.send(f"❌ Tu as atteint la limite quotidienne pour cette commande ({DAILY_LIMITS[command_name]}x par jour)")
                return False
            
            # 3. Si tout est OK, enregistrer l'utilisation et définir le nouveau cooldown
            if hasattr(ctx.bot, 'db'):
                ctx.bot.db.increment_daily_usage(str(ctx.author.id), command_name)
                if cooldown_seconds > 0 and hasattr(ctx.bot.db, 'set_command_cooldown'):
                    ctx.bot.db.set_command_cooldown(str(ctx.author.id), command_name, cooldown_seconds)
            elif hasattr(ctx.bot, 'point_system') and hasattr(ctx.bot.point_system, 'db'):
                ctx.bot.point_system.db.increment_daily_usage(str(ctx.author.id), command_name)
                if cooldown_seconds > 0 and hasattr(ctx.bot.point_system.db, 'set_command_cooldown'):
                    ctx.bot.point_system.db.set_command_cooldown(str(ctx.author.id), command_name, cooldown_seconds)
                
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des cooldowns/limites: {e}", exc_info=True)
            return True
    return commands.check(predicate)

class Commands(commands.Cog):
    """Commands cog containing all bot commands"""

    def __init__(self, bot, point_system, twitter_handler):
        """Initialize the Commands cog"""
        super().__init__()  # Important: Call the parent class's __init__
        self.bot = bot
        self.points = point_system
        self.twitter = twitter_handler
        logger.info("Commands cog initialized")
        # Log all commands that will be registered
        logger.info(f"Commands being registered: {[method for method in dir(self) if method.endswith('_command')]}")
        # Start prison auto-release task
        self._prison_monitor_task = self.bot.loop.create_task(self._prison_monitor_loop())

    async def _prison_monitor_loop(self):
        """Background task: libère automatiquement les prisonniers dont la peine est finie."""
        await self.bot.wait_until_ready()
        interval = PRISON_DISCORD.get("auto_release_check", 60)
        while not self.bot.is_closed():
            try:
                await self._check_auto_releases()
            except Exception as e:
                logger.error(f"Prison monitor error: {e}")
            await asyncio.sleep(interval)

    # ══════════════════════════════════════════════════════════════
    # ══  SYSTÈME D'ITEMS — MOTEUR D'EFFETS                     ══
    # ══════════════════════════════════════════════════════════════

    def _get_item_bonus(self, user_id: str, trigger: str, effect_key: str) -> float:
        """Calcule le bonus cumulé des items d'un joueur pour un trigger donné.
        Ex: _get_item_bonus(uid, 'steal', 'rob_bonus') → 0.25 si lockpick + pied_de_biche
        Ne consomme rien, juste lecture."""
        try:
            inv = self.points.db.get_inventory(user_id)
            if not inv:
                return 0.0
            total = 0.0
            for item_id in set(inv):  # set pour éviter double comptage
                item_cfg = SHOP_ITEMS.get(item_id)
                if not item_cfg:
                    continue
                triggers = item_cfg.get("triggers", [])
                if trigger in triggers or "all" in triggers:
                    total += item_cfg.get("effect", {}).get(effect_key, 0.0)
            return total
        except Exception as e:
            logger.error(f"Error in _get_item_bonus: {e}")
            return 0.0

    def _has_item_effect(self, user_id: str, trigger: str, effect_key: str) -> bool:
        """Vérifie si le joueur a un item avec un effet booléen pour ce trigger.
        Ex: _has_item_effect(uid, 'wesh', 'heal_wesh') → True si potion_soin"""
        try:
            inv = self.points.db.get_inventory(user_id)
            if not inv:
                return False
            for item_id in inv:
                item_cfg = SHOP_ITEMS.get(item_id)
                if not item_cfg:
                    continue
                triggers = item_cfg.get("triggers", [])
                if trigger in triggers or "all" in triggers:
                    if item_cfg.get("effect", {}).get(effect_key):
                        return True
            return False
        except Exception as e:
            logger.error(f"Error in _has_item_effect: {e}")
            return False

    def _consume_item(self, user_id: str, trigger: str, effect_key: str) -> str:
        """Consomme (retire) le premier item consommable qui match le trigger+effect.
        Retourne le nom de l'item consommé, ou '' si rien."""
        try:
            inv = self.points.db.get_inventory(user_id)
            if not inv:
                return ""
            for item_id in inv:
                item_cfg = SHOP_ITEMS.get(item_id)
                if not item_cfg:
                    continue
                if not item_cfg.get("consumable", False):
                    continue
                triggers = item_cfg.get("triggers", [])
                if trigger in triggers or "all" in triggers:
                    if item_cfg.get("effect", {}).get(effect_key):
                        self.points.db.remove_item(user_id, item_id)
                        return item_cfg.get("name", item_id)
            return ""
        except Exception as e:
            logger.error(f"Error in _consume_item: {e}")
            return ""

    def _find_defense_item(self, user_id: str, trigger: str) -> dict:
        """Cherche un item défensif chez un joueur. Retourne {item_id, item_cfg} ou {}."""
        try:
            inv = self.points.db.get_inventory(user_id)
            if not inv:
                return {}
            for item_id in inv:
                item_cfg = SHOP_ITEMS.get(item_id)
                if not item_cfg:
                    continue
                triggers = item_cfg.get("triggers", [])
                if trigger in triggers:
                    return {"item_id": item_id, "cfg": item_cfg}
            return {}
        except Exception as e:
            logger.error(f"Error in _find_defense_item: {e}")
            return {}

    # ══════════════════════════════════════════════════════════════
    # ══  SYSTÈME PRISON — GESTION DES RÔLES DISCORD            ══
    # ══════════════════════════════════════════════════════════════

    async def _get_or_create_prison_role(self, guild):
        """Récupère ou crée le rôle Prisonnier."""
        role_name = PRISON_DISCORD.get("role_name", "🔒 Prisonnier")
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            try:
                role = await guild.create_role(
                    name=role_name,
                    color=discord.Color.dark_grey(),
                    reason="Thugz Bot — Rôle prison auto-créé"
                )
                logger.info(f"Created prison role: {role_name} in {guild.name}")
            except Exception as e:
                logger.error(f"Failed to create prison role: {e}")
                return None
        return role

    async def _get_or_create_prison_channel(self, guild):
        """Récupère ou crée le channel prison avec les bonnes permissions."""
        channel_name = PRISON_DISCORD.get("channel_name", "prison")
        channel = discord.utils.get(guild.text_channels, name=channel_name)
        if channel:
            return channel

        try:
            # Créer la catégorie si elle n'existe pas
            cat_name = PRISON_DISCORD.get("category_name", "THUGZ JUSTICE")
            category = discord.utils.get(guild.categories, name=cat_name)
            if not category:
                category = await guild.create_category(cat_name)

            prison_role = await self._get_or_create_prison_role(guild)

            # Permissions: personne ne voit sauf les prisonniers et le bot
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    view_channel=False, send_messages=False
                ),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, manage_messages=True
                ),
            }
            if prison_role:
                overwrites[prison_role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True,
                    add_reactions=True
                )

            channel = await guild.create_text_channel(
                channel_name, category=category, overwrites=overwrites,
                topic="🔒 Cellule de prison — Seuls les prisonniers peuvent parler ici."
            )
            logger.info(f"Created prison channel: #{channel_name} in {guild.name}")
            return channel
        except Exception as e:
            logger.error(f"Failed to create prison channel: {e}")
            return None

    async def _imprison_member(self, member, duration_seconds, reason="N/A"):
        """Emprisonne un membre: sauvegarde ses rôles, les retire, ajoute le rôle prisonnier."""
        try:
            guild = member.guild
            user_id = str(member.id)
            prison_role = await self._get_or_create_prison_role(guild)
            if not prison_role:
                return False

            # Sauvegarder les rôles actuels (sauf @everyone et le rôle prisonnier)
            saved_roles = [r.id for r in member.roles if r != guild.default_role and r != prison_role]
            try:
                roles_data = self.points.database.load_bot_state("saved_roles") or {}
                roles_data[user_id] = saved_roles
                self.points.database.save_bot_state("saved_roles", roles_data)
            except Exception as e:
                logger.error(f"Failed to save roles: {e}")

            # Retirer tous les rôles (sauf @everyone)
            try:
                roles_to_remove = [r for r in member.roles if r != guild.default_role and r.is_assignable()]
                if roles_to_remove:
                    await member.remove_roles(*roles_to_remove, reason=f"Prison: {reason}")
            except Exception as e:
                logger.error(f"Failed to remove roles: {e}")

            # Ajouter le rôle prisonnier
            try:
                await member.add_roles(prison_role, reason=f"Prison: {reason}")
            except Exception as e:
                logger.error(f"Failed to add prison role: {e}")

            # Enregistrer en DB
            import time as _time
            release_time = _time.time() + duration_seconds
            self.points.database.set_prison_time(user_id, release_time)

            # Log la transaction
            self.points.add_points(user_id, 0, f"PRISON: {reason} ({duration_seconds//60}min)")

            return True
        except Exception as e:
            logger.error(f"Error in _imprison_member: {e}", exc_info=True)
            return False

    async def _release_member(self, member):
        """Libère un prisonnier: retire le rôle prison, restaure ses anciens rôles."""
        try:
            guild = member.guild
            user_id = str(member.id)
            prison_role = await self._get_or_create_prison_role(guild)

            # Retirer le rôle prisonnier
            if prison_role and prison_role in member.roles:
                try:
                    await member.remove_roles(prison_role, reason="Libération de prison")
                except Exception as e:
                    logger.error(f"Failed to remove prison role: {e}")

            # Restaurer les anciens rôles
            try:
                roles_data = self.points.database.load_bot_state("saved_roles") or {}
                saved_role_ids = roles_data.get(user_id, [])
                if saved_role_ids:
                    roles_to_add = []
                    for role_id in saved_role_ids:
                        role = guild.get_role(role_id)
                        if role and role.is_assignable():
                            roles_to_add.append(role)
                    if roles_to_add:
                        await member.add_roles(*roles_to_add, reason="Sortie de prison — rôles restaurés")

                    # Nettoyer la sauvegarde
                    del roles_data[user_id]
                    self.points.database.save_bot_state("saved_roles", roles_data)
            except Exception as e:
                logger.error(f"Failed to restore roles: {e}")

            # Nettoyer en DB
            self.points.database.remove_prison_time(user_id)

            # Log
            self.points.add_points(user_id, 0, "LIBERATION de prison")

            return True
        except Exception as e:
            logger.error(f"Error in _release_member: {e}", exc_info=True)
            return False

    async def _check_auto_releases(self):
        """Vérifie et libère automatiquement les prisonniers dont la peine est finie."""
        try:
            import time as _time
            now = _time.time()
            for guild in self.bot.guilds:
                prison_role = discord.utils.get(guild.roles, name=PRISON_DISCORD.get("role_name", "🔒 Prisonnier"))
                if not prison_role:
                    continue
                for member in prison_role.members:
                    user_id = str(member.id)
                    release_time = self.points.database.get_prison_time(user_id)
                    if release_time and float(release_time) <= now:
                        await self._release_member(member)
                        # Annonce
                        prison_channel = await self._get_or_create_prison_channel(guild)
                        if prison_channel:
                            await prison_channel.send(f"🔓 **{member.display_name}** a purgé sa peine et est libre !")
                        logger.info(f"Auto-released {member.display_name} from prison")
        except Exception as e:
            logger.error(f"Error in auto-release check: {e}")

    def _is_prison_channel(self, ctx):
        """Vérifie si on est dans le channel prison."""
        return ctx.channel.name == PRISON_DISCORD.get("channel_name", "prison")

    async def _get_user_history(self, user_id):
        """Récupère l'historique complet d'un joueur depuis point_transactions."""
        try:
            db = self.points.database
            if not db.is_connected():
                return {}
            result = db.supabase.table('point_transactions').select('*').eq('user_id', user_id).order('timestamp', desc=True).limit(100).execute()
            if not result.data:
                return {"total_actions": 0, "crimes": 0, "work": 0, "prison": 0, "deals": 0, "gambling": 0}

            stats = {"total_actions": len(result.data), "crimes": 0, "work": 0, "prison": 0, "deals": 0, "gambling": 0, "ken": 0, "wesh": 0}
            for tx in result.data:
                reason = (tx.get('reason', '') or '').lower()
                if any(w in reason for w in ['steal', 'rob', 'vol', 'pickpocket', 'carjack', 'braquage']):
                    stats["crimes"] += 1
                elif any(w in reason for w in ['work', 'travail', 'boulot']):
                    stats["work"] += 1
                elif any(w in reason for w in ['prison', 'libera', 'arrest']):
                    stats["prison"] += 1
                elif any(w in reason for w in ['deal', 'dealer', 'trafic']):
                    stats["deals"] += 1
                elif any(w in reason for w in ['casino', 'loto', 'roulette']):
                    stats["gambling"] += 1
                elif 'ken' in reason:
                    stats["ken"] += 1
                elif 'wesh' in reason:
                    stats["wesh"] += 1
            return stats
        except Exception as e:
            logger.error(f"Error getting user history: {e}")
            return {"total_actions": 0, "crimes": 0, "work": 0, "prison": 0}

    async def _safe_send(self, ctx, embed=None, content=None):
        """Envoie un embed, fallback en texte si pas la permission (403). Retourne le message."""
        try:
            if embed:
                return await ctx.send(embed=embed, content=content)
            elif content:
                return await ctx.send(content)
        except discord.errors.Forbidden:
            # Pas la permission d'envoyer des embeds → fallback texte
            fallback = content or ""
            if embed:
                if embed.title:
                    fallback += f"**{embed.title}**\n"
                if embed.description:
                    fallback += f"{embed.description}\n"
                for field in embed.fields:
                    fallback += f"\n**{field.name}**\n{field.value}\n"
                if embed.footer and embed.footer.text:
                    fallback += f"\n_{embed.footer.text}_"
            if fallback:
                return await ctx.send(fallback[:2000])
            else:
                await ctx.send("(Le bot n'a pas la permission Embed Links. Demande à un admin de l'activer.)")

    @commands.command(name='debug')
    @is_bot_owner()
    async def debug_command(self, ctx):
        """[OWNER] Debug command to check registered commands"""
        try:
            # Get all registered commands
            all_commands = sorted([c.name for c in self.bot.commands])
            cog_commands = sorted([c.name for c in self.get_commands()])

            embed = discord.Embed(
                title="🔧 Debug Information",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="Bot Commands",
                value=f"Total: {len(all_commands)}\n" + "\n".join(all_commands),
                inline=False
            )

            embed.add_field(
                name="Cog Commands",
                value=f"Total: {len(cog_commands)}\n" + "\n".join(cog_commands),
                inline=False
            )

            await self._safe_send(ctx, embed=embed)
            logger.info(f"Debug command executed by {ctx.author}")

        except Exception as e:
            logger.error(f"Error in debug command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='ping')
    async def ping_command(self, ctx):
        """Simple ping command to test bot responsiveness"""
        try:
            logger.info(f"Ping command received from {ctx.author} in channel {ctx.channel.name}")

            # Calculate bot latency
            latency = round(self.bot.latency * 1000)

            # Send response with more information
            await ctx.send(f"Pong! ✅ Latence : {latency}ms\nLe bot fonctionne correctement.")

            # Log available commands
            all_commands = [c.name for c in self.bot.commands]
            logger.info(f"Available commands when ping was executed: {all_commands}")
            logger.info(f"Ping command executed successfully for {ctx.author}")
        except Exception as e:
            logger.error(f"Error in ping command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='help', aliases=['commands', 'bothelp', 'aide', 'commandes'])
    async def help_command(self, ctx, cmd_name: str = None):
        """Show all available commands / Afficher toutes les commandes disponibles"""
        try:
            if cmd_name:
                return await self._help_single(ctx, cmd_name)

            HELP_DATA = {
                "💰 Économie": [
                    ("`!work`", "Travailler pour gagner de l'argent", "2h cooldown, 8x/jour"),
                    ("`!points [@user]`", "Voir ton solde (ou celui d'un autre)", None),
                    ("`!leaderboard`", "Classement des plus riches", None),
                    ("`!shop`", "Afficher la boutique (+ 10 nouveaux items !)", None),
                    ("`!buy <item>`", "Acheter un objet de la boutique", None),
                    ("`!inventory`", "Voir ton inventaire d'objets", None),
                    ("`!trade @user <item>`", "Proposer un échange d'objet", None),
                    ("`!gift @user <montant>`", "Donner de l'argent", "1h cooldown, 10x/jour"),
                    ("`!mendier`", "Faire la manche (low risk)", "15min cooldown"),
                    ("`!fouiller`", "Chercher du cash/items dans les environs", "1h cooldown"),
                    ("`!loto`", "Acheter un ticket à gratter (100 💵)", "2h cooldown"),
                ],
                "🦹 Crimes": [
                    ("`!steal @user`", "Voler un joueur (risque prison)", "4h cooldown, 5x/jour"),
                    ("`!pickpocket @user`", "Faire les poches discrètement (petit gain)", "30min cd, 8x/jour"),
                    ("`!heist`", "Lancer un braquage en groupe", "2x/jour"),
                    ("`!joinheist`", "Rejoindre un braquage en cours", None),
                    ("`!carjack`", "Voler une voiture ! (gros risque/gain)", "6h cooldown, 2x/jour"),
                    ("`!dealer`", "Deal de rue (attention aux stups)", "3h cooldown, 3x/jour"),
                    ("`!revenge`", "Se venger de ton dernier voleur", "1x/jour"),
                ],
                "⚔️ Combat & Embrouilles": [
                    ("`!fight @user [mise]`", "Se battre avec quelqu'un", "6h cooldown, 3x/jour"),
                    ("`!duel @user <mise>`", "Duel d'honneur (mise obligatoire)", "12h cooldown, 2x/jour"),
                    ("`!combat @user <mise>`", "Combat général", "3h cooldown, 5x/jour"),
                    ("`!insulter @user`", "Clash quelqu'un pour du respect", "20min cooldown, 5x/jour"),
                ],
                "🎨 Street Life": [
                    ("`!wesh`", "🌀 ÉVÉNEMENT RANDOM WTF !! (bons ou mauvais)", "1h cooldown, 3x/jour"),
                    ("`!graffiti`", "Tagger un mur pour du respect", "45min cooldown, 5x/jour"),
                    ("`!casino <mise>`", "Jouer au casino du quartier (min 50 💵)", "30min cd, 5x/jour"),
                    ("`!ken @user [montant]`", "Proposition coquine (PG-13, consentement)", None),
                ],
                "🏢 Prison & Justice": [
                    ("`!prison [@user]`", "Voir ton statut en prison", None),
                    ("`!activity [nom]`", "Activité en prison (réduit la peine)", None),
                    ("`!tribunal <plaidoyer>`", "Demander un procès (vote) — 500 💵", None),
                    ("`!bail [montant]`", "Payer ta caution", "30min cooldown"),
                    ("`!plead <texte>`", "Plaider ta cause", None),
                    ("`!prisonwork`", "Bosser en prison", None),
                    ("`!visit @user <msg>`", "Visiter un prisonnier (100 💵)", "2h cooldown"),
                    ("`!arrest @user <raison>`", "Arrêter quelqu'un (500 💵)", "1h cooldown"),
                ],
                "🔫 Gangs": [
                    ("`!gang`", "Infos de ton gang", None),
                    ("`!gang create <nom>`", "Créer un gang", None),
                    ("`!gang info <nom>`", "Infos sur un gang", None),
                    ("`!gang alliance`", "Gérer les alliances", None),
                    ("`!gang territory`", "Gérer les territoires", None),
                    ("`!gang asset`", "Gérer les actifs", None),
                    ("`!war`", "Guerres en cours", None),
                    ("`!territory`", "Carte des territoires", None),
                ],
                "👤 Profil": [
                    ("`!profil [@user]`", "Profil complet + surnom gangster", None),
                ],
                "💀 Galère / Dettes": [
                    ("`!vendrecul`", "Vendre son corps pour survivre...", "30min cd, 5x/jour"),
                    ("`!vendreslip`", "Vendre ton slip (oui oui)", "20min cd, 5x/jour"),
                    ("`!vendredigite`", "Vendre ta dignité", "15min cd, 8x/jour"),
                    ("`!pret @user <montant>`", "Demander un prêt", "1h cd, 3x/jour"),
                    ("`!rembourser @user <montant>`", "Récupérer ton prêt (à tout moment)", None),
                    ("`!dette`", "Voir tes dettes", None),
                    ("`!faillite`", "Déclarer faillite (reset total)", None),
                ],
                "📌 Divers": [
                    ("`!ping`", "Tester si le bot répond", None),
                    ("`!help [commande]`", "Afficher cette aide", None),
                ],
            }

            if ctx.author.id == OWNER_ID or ctx.author.id in APPROVED_STAFF_IDS:
                HELP_DATA["⚡ Admin"] = [
                    ("`!addpoints @user <montant>`", "Ajouter des points", None),
                    ("`!removepoints @user <montant>`", "Retirer des points", None),
                    ("`!resetcooldowns [@user]`", "Reset cooldowns", None),
                    ("`!additem @user <item>`", "Donner un item", None),
                    ("`!removeitem @user <item>`", "Retirer un item", None),
                    ("`!promote @user`", "Promouvoir", None),
                    ("`!demote @user`", "Rétrograder", None),
                    ("`!debug`", "Debug", None),
                ]

            embeds = []
            title_embed = discord.Embed(
                title="🦹 Thugz Life — Commandes",
                description="Tape `!help <commande>` pour les détails.\nAliases FR: `!voler`=`!steal`, `!travail`=`!work`, etc.",
                color=0xFF4500
            )

            for category, cmds in HELP_DATA.items():
                lines = []
                for cmd_syntax, desc, note in cmds:
                    line = f"{cmd_syntax} — {desc}"
                    if note:
                        line += f" *({note})*"
                    lines.append(line)
                field_value = "\n".join(lines)
                # Discord field limit = 1024 chars, truncate if needed
                if len(field_value) > 1020:
                    field_value = field_value[:1020] + "..."
                title_embed.add_field(name=category, value=field_value, inline=False)

            await self._safe_send(ctx, embed=title_embed)
            logger.info(f"Help command executed for {ctx.author}")
        except Exception as e:
            logger.error(f"Error in help command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    async def _help_single(self, ctx, cmd_name: str):
        """Show detailed help for a single command"""
        cmd = self.bot.get_command(cmd_name)
        if not cmd:
            await ctx.send(f"❌ Commande `{cmd_name}` introuvable. Tape `!help` pour la liste.")
            return
        embed = discord.Embed(title=f"📖 !{cmd.name}", description=cmd.help or "Pas de description.", color=0xFF4500)
        if cmd.aliases:
            embed.add_field(name="Aliases", value=", ".join([f"`!{a}`" for a in cmd.aliases]), inline=False)
        cooldown_val = COMMAND_COOLDOWNS.get(cmd.name, 0)
        if cooldown_val > 0:
            h = cooldown_val // 3600
            m = (cooldown_val % 3600) // 60
            embed.add_field(name="⏰ Cooldown", value=f"{h}h {m}min" if h else f"{m}min", inline=True)
        daily = DAILY_LIMITS.get(cmd.name)
        if daily:
            embed.add_field(name="📊 Limite/jour", value=f"{daily}x", inline=True)
        await self._safe_send(ctx, embed=embed)

    @commands.command(name='points', aliases=['money', 'balance', 'solde', 'argent'])
    async def points_command(self, ctx, member: discord.Member = None):
        """Check your points or another member's points / Vérifier tes points ou ceux d'un autre membre"""
        try:
            target = member or ctx.author
            points = self.points.db.get_user_points(str(target.id))

            if target == ctx.author:
                await ctx.send(f"💰 Tu as **{points}** points!")
            else:
                await ctx.send(f"💰 {target.name} a **{points}** points!")
        except Exception as e:
            logger.error(f"Error in points command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='work', aliases=['travail', 'boulot', 'job'])
    @check_cooldown_and_limit('work')
    async def work_command(self, ctx):
        """Do your daily work (TECH Brief: 2h cooldown, max 8x/day) / Faire ton travail quotidien"""
        try:
            success, message = await self.points.daily_work(str(ctx.author.id))
            await ctx.send(message)
        except Exception as e:
            logger.error(f"Error in work command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='steal', aliases=['rob', 'voler', 'cambrioler'])
    @check_cooldown_and_limit('steal')
    async def steal_command(self, ctx, target: discord.Member = None):
        """Voler un autre membre — tes items augmentent tes chances, mais la victime peut avoir un gilet !"""
        try:
            if not target:
                await ctx.send("❌ Mentionne la personne que tu veux voler! `!steal @user`")
                return
            if target.id == ctx.author.id:
                await ctx.send("❌ Tu ne peux pas te voler toi-même!")
                return

            user_id = str(ctx.author.id)
            target_id = str(target.id)
            name = ctx.author.display_name
            target_name = target.display_name

            narration = random.choice(COMMAND_NARRATIONS['rob']).format(user=name, target=target_name)
            await ctx.send(narration)
            await asyncio.sleep(2)

            # ── CHECK ITEMS DÉFENSIFS DE LA VICTIME ──
            # Kevlar → bloque 100% + envoie voleur en prison
            defense = self._find_defense_item(target_id, "defense_steal")
            if defense:
                d_cfg = defense["cfg"]
                d_effect = d_cfg.get("effect", {})

                # KEVLAR: full block + prison pour le voleur
                if d_effect.get("full_block"):
                    counter_prison = d_effect.get("counter_prison", 1800)
                    if d_cfg.get("consumable"):
                        self.points.db.remove_item(target_id, defense["item_id"])
                    import time as _time
                    self.points.database.set_prison_time(user_id, _time.time() + counter_prison)
                    mins = counter_prison // 60
                    await ctx.send(
                        f"🛡️💥 **CONTRE-ATTAQUE !** {target_name} portait un **{d_cfg['name']}** !\n"
                        f"Le vol est bloqué à 100% et TU te retrouves en prison pour **{mins} min** ! 🚔\n"
                        f"*({d_cfg['name']} consommé)*"
                    )
                    return

                # GILET PARE-BALLES: reversal — le vol se retourne contre le voleur
                reversal = d_effect.get("reversal_chance", 0)
                if reversal > 0 and random.random() < reversal:
                    # Le vol se retourne !
                    steal_amount = random.randint(100, 500)
                    attacker_points = int(self.points.get_user_points(user_id))
                    steal_amount = min(steal_amount, attacker_points)
                    if steal_amount > 0:
                        self.points.remove_points(user_id, steal_amount)
                        self.points.add_points(target_id, steal_amount, "Vol retourné (gilet)")
                    if d_cfg.get("consumable"):
                        self.points.db.remove_item(target_id, defense["item_id"])
                    await ctx.send(
                        f"🦺💥 **RETOURNEMENT !** {target_name} avait un **{d_cfg['name']}** !\n"
                        f"Le vol se retourne contre toi ! {target_name} te prend **{steal_amount}** 💵 !\n"
                        f"*({d_cfg['name']} consommé)*"
                    )
                    return

            # ── CALCUL DES BONUS D'ATTAQUE ──
            rob_bonus = self._get_item_bonus(user_id, "steal", "rob_bonus")
            luck_bonus = self._get_item_bonus(user_id, "steal", "global_luck")
            total_bonus = rob_bonus + luck_bonus  # ex: 0.15 + 0.10 = 0.25

            # Try to rob (on modifie la chance de succès via les items)
            success, amount = await self.points.try_rob(user_id, target_id, target_name)

            # Si le vol échoue naturellement, les items offensifs donnent une 2e chance
            if not success and amount == -3 and total_bonus > 0:
                if random.random() < total_bonus:
                    # Les items sauvent le vol !
                    success = True
                    amount = random.randint(50, 300)
                    target_pts = int(self.points.get_user_points(target_id))
                    amount = min(amount, target_pts)
                    if amount > 0:
                        self.points.remove_points(target_id, amount)
                        self.points.add_points(user_id, amount, f"Vol (item bonus)")

            # ── RÉSULTAT ──
            if success and amount > 0:
                item_msg = ""
                if total_bonus > 0:
                    item_msg = "\n🔓 *Tes items t'ont aidé !*"
                msgs = [
                    f"✅ Vol réussi ! Tu as volé **{amount}** 💵 à {target_name} !{item_msg}",
                    f"✅ Butin acquis ! {target_name} perd **{amount}** 💵...{item_msg}",
                    f"✅ Parfait ! **{amount}** 💵 subtilisés à {target_name} !{item_msg}",
                ]
                await ctx.send(random.choice(msgs))
            else:
                if amount == -1:
                    await ctx.send("❌ L'utilisateur n'existe pas dans la base de données.")
                elif amount == -2:
                    await ctx.send("❌ La victime n'a pas assez de points pour valoir le coup!")
                elif amount == -3:
                    # Vol échoué — check cagoule (stealth) pour éviter conséquences
                    stealth = self._get_item_bonus(user_id, "steal", "stealth_on_fail")
                    if stealth > 0 and random.random() < stealth:
                        await ctx.send(
                            f"❌ Le vol a échoué... mais ta 🎭 **Cagoule** t'a permis de fuir sans être identifié !"
                            f"\nPas de conséquences cette fois."
                        )
                    else:
                        fails = [
                            f"❌ Le vol a échoué ! {target_name} s'est défendu !",
                            f"❌ Raté ! {target_name} a senti le coup venir...",
                            f"❌ Échec ! {target_name} était sur ses gardes...",
                        ]
                        await ctx.send(random.choice(fails))
                else:
                    await ctx.send("❌ Une erreur s'est produite lors du vol.")
        except Exception as e:
            logger.error(f"Error in steal command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='gift', aliases=['cadeau', 'give'])
    @check_cooldown_and_limit('gift')
    async def gift_command(self, ctx, target: discord.Member = None, amount: int = None):
        """Give points to another member (TECH Brief: 1h cooldown, max 10x/day)"""
        try:
            if not target or amount is None:
                await ctx.send("❌ Usage: `!gift @user <montant>` - Exemple: `!gift @user 100`")
                return

            if target.id == ctx.author.id:
                await ctx.send("❌ Tu ne peux pas te faire un cadeau à toi-même!")
                return

            if amount <= 0:
                await ctx.send("❌ Le montant doit être positif!")
                return

            if amount > 1000:
                await ctx.send("❌ Tu ne peux pas donner plus de 1000 points à la fois!")
                return

            # Vérifier si l'utilisateur a assez de points
            sender_points = self.points.db.get_user_points(str(ctx.author.id))
            if sender_points < amount:
                await ctx.send(f"❌ Tu n'as que {sender_points} points! Tu ne peux pas donner {amount} points.")
                return

            # Effectuer le transfert
            success_remove = self.points.remove_points(str(ctx.author.id), amount)
            if success_remove:
                self.points.add_points(str(target.id), amount, f"Cadeau de {ctx.author.name}")
                
                embed = discord.Embed(
                    title="🎁 Cadeau envoyé!",
                    description=f"{ctx.author.mention} a donné **{amount} points** à {target.mention}!",
                    color=0x00FF00
                )
                embed.add_field(name="Expéditeur", value=ctx.author.name, inline=True)
                embed.add_field(name="Destinataire", value=target.name, inline=True)
                embed.add_field(name="Montant", value=f"{amount} points", inline=True)
                
                await self._safe_send(ctx, embed=embed)
                
                # Log de l'activité
                logger.info(f"Gift: {ctx.author.name} gave {amount} points to {target.name}")
            else:
                await ctx.send("❌ Erreur lors du transfert des points.")

        except Exception as e:
            logger.error(f"Error in gift command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='revenge', aliases=['vengeance'])
    @check_daily_limit('revenge')
    async def revenge_command(self, ctx):
        """Get revenge on your last robber"""
        try:
            success, message = await self.points.try_revenge(str(ctx.author.id))
            await ctx.send(message)
        except Exception as e:
            logger.error(f"Error in revenge command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='leaderboard', aliases=['classement', 'top'])
    async def leaderboard_command(self, ctx):
        """Classement des plus riches du serveur"""
        try:
            leaderboard = await self.points.get_monthly_leaderboard()

            if not leaderboard:
                await ctx.send("📊 Aucun joueur dans le classement pour l'instant. Tape `!work` pour commencer !")
                return

            embed = discord.Embed(
                title="🏆 Classement des Thugz",
                description="Les plus grands gangsters :",
                color=discord.Color.gold()
            )

            medals = ["🥇", "🥈", "🥉"]
            for i, user_data in enumerate(leaderboard[:10], 1):
                try:
                    user_id = str(user_data.get('user_id', ''))
                    points = user_data.get('points', 0)
                    # Try to get member name, fallback to ID
                    try:
                        member = await ctx.guild.fetch_member(int(user_id))
                        name = member.display_name
                    except Exception:
                        name = user_data.get('username', f"Joueur #{user_id[-4:]}")
                    medal = medals[i-1] if i <= 3 else f"**{i}.**"
                    embed.add_field(
                        name=f"{medal} {name}",
                        value=f"💰 **{points:,}** 💵",
                        inline=False
                    )
                except Exception:
                    continue

            embed.set_footer(text=f"Classement — {datetime.now().strftime('%B %Y')}")
            await self._safe_send(ctx, embed=embed)
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='heist', aliases=['braquage'])
    @check_daily_limit('heist')
    async def heist_command(self, ctx):
        """Start a heist"""
        try:
            # Get random narration for heist
            narration = random.choice(COMMAND_NARRATIONS['heist']).format(user=ctx.author.name)
            await ctx.send(narration)

            # Wait for tension
            await asyncio.sleep(2)

            success, message = await self.points.start_heist(str(ctx.author.id))
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in heist command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='joinheist', aliases=['rejoindre'])
    async def join_heist_command(self, ctx):
        """Join an active heist"""
        try:
            success, message = await self.points.join_heist(str(ctx.author.id))
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in join_heist command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='combat', aliases=['bataille', 'fight_general'])
    @check_cooldown_and_limit('combat')
    async def combat_command(self, ctx, target: discord.Member = None, bet: int = None):
        """Start a general combat with another member (3h cooldown, max 5x/day)"""
        try:
            if not target or not bet:
                await ctx.send("Usage: !combat @user <mise>")
                return

            if target.id == ctx.author.id:
                await ctx.send("Tu ne peux pas te battre contre toi-meme!")
                return

            # Get random narration for combat
            narration = random.choice(COMMAND_NARRATIONS['combat']).format(
                user=ctx.author.name,
                target=target.name
            )
            await ctx.send(narration)
            await asyncio.sleep(2)

            # Initialize combat
            success, message, combat_info = await self.points.start_combat(str(ctx.author.id), str(target.id), bet)
            if not success:
                await ctx.send(message)
                return
            
            # Select 6 random emojis for this combat
            selected_emojis = random.sample(EMOJI_POOL, 6)
            emoji_display = " ".join(selected_emojis)
            
            # Step 1: Attacker chooses move
            attacker_msg = await ctx.send(
                f"{ctx.author.mention}, choisissez votre coup:\n"
                f"{emoji_display}\n"
                f"⏱️ 1 minute pour choisir!"
            )
            for emoji in selected_emojis:
                await attacker_msg.add_reaction(emoji)
            
            # Wait for attacker reaction
            try:
                attacker_reaction = await self.bot.wait_for(
                    'reaction_add',
                    timeout=COMBAT_FIRST_MOVE_TIMEOUT,
                    check=lambda r, u: (u.id == ctx.author.id and 
                                       str(r.emoji) in selected_emojis and 
                                       r.message.id == attacker_msg.id)
                )
                # Convert emoji to index
                attacker_emoji = str(attacker_reaction[0].emoji)
                attacker_idx = selected_emojis.index(attacker_emoji)
                await ctx.send(f"✅ {ctx.author.mention} a choisi: {attacker_emoji}")
            except asyncio.TimeoutError:
                await ctx.send(f"⏱️ TIMEOUT! {ctx.author.mention} n'a pas choisi à temps. Combat annulé!")
                return
            
            await asyncio.sleep(1)
            
            # Step 2: Defender must react within 5 minutes
            defender_msg = await ctx.send(
                f"{target.mention}, défendez-vous dans les 5 MINUTES!\n"
                f"{emoji_display}\n"
                f"⏱️ 5 minutes pour réagir!"
            )
            for emoji in selected_emojis:
                await defender_msg.add_reaction(emoji)
            
            # Wait for defender reaction with 5 minute timeout
            try:
                defender_reaction = await self.bot.wait_for(
                    'reaction_add',
                    timeout=COMBAT_REACTION_TIMEOUT,
                    check=lambda r, u: (u.id == target.id and 
                                       str(r.emoji) in selected_emojis and 
                                       r.message.id == defender_msg.id)
                )
                # Convert emoji to index
                defender_emoji = str(defender_reaction[0].emoji)
                defender_idx = selected_emojis.index(defender_emoji)
                await ctx.send(f"✅ {target.mention} a riposté: {defender_emoji}")
            except asyncio.TimeoutError:
                # Defender loses
                await ctx.send(f"⏱️ TIMEOUT! {target.mention} n'a pas réagi à temps! 💀\n"
                              f"{ctx.author.mention} remporte le combat et gagne **{bet}** points!")
                self.points.database.remove_points(str(target.id), bet)
                self.points.database.add_points(str(ctx.author.id), bet)
                return
            
            # Evaluate moves with indices
            result, move_description = await self.points.evaluate_combat_moves(attacker_idx, defender_idx, selected_emojis)
            
            await ctx.send(f"\n{move_description}")
            await asyncio.sleep(2)
            
            # Apply results (win = attacker wins, lose = attacker loses)
            if result == 'win':
                # ATTACKER WINS
                self.points.database.add_points(str(ctx.author.id), bet)
                self.points.database.remove_points(str(target.id), bet)
                await ctx.send(f"{ctx.author.mention} GAGNE! +{bet}")
            elif result == 'lose':
                # DEFENDER WINS
                self.points.database.add_points(str(target.id), bet)
                self.points.database.remove_points(str(ctx.author.id), bet)
                await ctx.send(f"{target.mention} GAGNE! +{bet}")
            else:
                # TIE
                self.points.database.add_points(str(ctx.author.id), bet)
                self.points.database.add_points(str(target.id), bet)
                await ctx.send(f"EGALITE! Chacun garde son argent")

        except Exception as e:
            logger.error(f"Error in combat command: {e}", exc_info=True)
            await ctx.send("Une erreur est survenue.")

    @commands.command(name='fight', aliases=['bagarre'])
    @check_cooldown_and_limit('fight')
    async def fight_command(self, ctx, target: discord.Member = None, bet: int = None):
        """Fight another member with interactive reactions (6h cooldown, max 3x/day)"""
        try:
            if not target:
                await ctx.send("Usage: !fight @user [mise]")
                return

            if target.id == ctx.author.id:
                await ctx.send("Tu ne peux pas te battre contre toi-meme!")
                return

            # Default bet
            if bet is None:
                bet = 100

            # Initialize combat
            success, message, combat_info = await self.points.start_combat(str(ctx.author.id), str(target.id), bet)
            if not success:
                await ctx.send(message)
                return
            
            # Announce the fight
            await ctx.send(f"⚔️ {ctx.author.mention} defie {target.mention} en combat singulier!")
            await asyncio.sleep(1)
            
            # Select 6 random emojis for this combat
            selected_emojis = random.sample(EMOJI_POOL, 6)
            emoji_display = " ".join(selected_emojis)
            
            # Step 1: Attacker chooses move
            attacker_msg = await ctx.send(
                f"{ctx.author.mention}, choisissez votre coup:\n"
                f"{emoji_display}\n"
                f"⏱️ 1 minute pour choisir!"
            )
            for emoji in selected_emojis:
                await attacker_msg.add_reaction(emoji)
            
            # Wait for attacker reaction
            try:
                attacker_reaction = await self.bot.wait_for(
                    'reaction_add',
                    timeout=COMBAT_FIRST_MOVE_TIMEOUT,
                    check=lambda r, u: (u.id == ctx.author.id and 
                                       str(r.emoji) in selected_emojis and 
                                       r.message.id == attacker_msg.id)
                )
                # Convert emoji to index
                attacker_emoji = str(attacker_reaction[0].emoji)
                attacker_idx = selected_emojis.index(attacker_emoji)
                await ctx.send(f"✅ {ctx.author.mention} a choisi: {attacker_emoji}")
            except asyncio.TimeoutError:
                await ctx.send(f"⏱️ TIMEOUT! {ctx.author.mention} n'a pas choisi à temps. Combat annulé!")
                return
            
            await asyncio.sleep(1)
            
            # Step 2: Defender must react within 5 minutes
            defender_msg = await ctx.send(
                f"{target.mention}, défendez-vous dans les 5 MINUTES!\n"
                f"{emoji_display}\n"
                f"⏱️ 5 minutes pour réagir!"
            )
            for emoji in selected_emojis:
                await defender_msg.add_reaction(emoji)
            
            # Wait for defender reaction with 5 minute timeout
            try:
                defender_reaction = await self.bot.wait_for(
                    'reaction_add',
                    timeout=COMBAT_REACTION_TIMEOUT,
                    check=lambda r, u: (u.id == target.id and 
                                       str(r.emoji) in selected_emojis and 
                                       r.message.id == defender_msg.id)
                )
                # Convert emoji to index
                defender_emoji = str(defender_reaction[0].emoji)
                defender_idx = selected_emojis.index(defender_emoji)
                await ctx.send(f"✅ {target.mention} a riposté: {defender_emoji}")
            except asyncio.TimeoutError:
                # Defender loses
                await ctx.send(f"⏱️ TIMEOUT! {target.mention} n'a pas réagi à temps! 💀\n"
                              f"{ctx.author.mention} remporte le combat et gagne **{bet}** points!")
                self.points.database.remove_points(str(target.id), bet)
                self.points.database.add_points(str(ctx.author.id), bet)
                return
            
            # Evaluate moves with indices
            result, move_description = await self.points.evaluate_combat_moves(attacker_idx, defender_idx, selected_emojis)
            
            await ctx.send(f"\n{move_description}")
            await asyncio.sleep(2)
            
            # Apply results (win = attacker wins, lose = attacker loses)
            if result == 'win':
                # ATTACKER WINS
                self.points.database.add_points(str(ctx.author.id), bet)
                self.points.database.remove_points(str(target.id), bet)
                await ctx.send(f"{ctx.author.mention} GAGNE! +{bet}")
            elif result == 'lose':
                # DEFENDER WINS
                self.points.database.add_points(str(target.id), bet)
                self.points.database.remove_points(str(ctx.author.id), bet)
                await ctx.send(f"{target.mention} GAGNE! +{bet}")
            else:
                # TIE
                self.points.database.add_points(str(ctx.author.id), bet)
                self.points.database.add_points(str(target.id), bet)
                await ctx.send(f"EGALITE! Chacun garde son argent")

        except Exception as e:
            logger.error(f"Error in fight command: {e}", exc_info=True)
            await ctx.send("Une erreur est survenue.")

    @commands.command(name='duel', aliases=['duel_honneur'])
    @check_cooldown_and_limit('duel')
    async def duel_command(self, ctx, target: discord.Member = None, bet: int = None):
        """Challenge someone to an honor duel (TECH Brief: 12h cooldown, max 2x/day) / Défier en duel d'honneur"""
        try:
            if not target or not bet:
                await ctx.send("❌ Usage: !duel @user <mise> - Duel d'honneur avec mise obligatoire!")
                return

            if target.id == ctx.author.id:
                await ctx.send("❌ Tu ne peux pas te défier toi-même en duel!")
                return

            if bet < 200:
                await ctx.send("❌ La mise minimale pour un duel d'honneur est de 200 points!")
                return

            await ctx.send(f"🤺 {ctx.author.mention} défie {target.mention} en DUEL D'HONNEUR pour {bet} points!")
            await ctx.send("*Les duels sont des combats prestigieux avec des enjeux élevés...*")
            await asyncio.sleep(2)

            success, message, combat_info = await self.points.start_combat(str(ctx.author.id), str(target.id), bet)
            if success:
                await ctx.send("✅ Duel accepté! Le combat commencera bientôt...")
            else:
                await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in duel command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='prison', aliases=['status', 'statut', 'cellule'])
    async def prison_status_command(self, ctx, member: discord.Member = None):
        """Vérifier le statut de prison d'un joueur"""
        try:
            target = member or ctx.author
            user_id = str(target.id)
            prison_role = discord.utils.get(ctx.guild.roles, name=PRISON_DISCORD.get("role_name", "🔒 Prisonnier"))
            is_imprisoned = prison_role and prison_role in target.roles

            if not is_imprisoned:
                await ctx.send(f"✅ **{target.display_name}** est libre !")
                return

            # Temps restant
            import time as _time
            release_time = self.points.database.get_prison_time(user_id)
            remaining = max(0, int(float(release_time or 0) - _time.time())) if release_time else 0
            hours = remaining // 3600
            mins = (remaining % 3600) // 60
            time_str = f"{hours}h {mins:02d}min" if hours else f"{mins}min"

            bail_amount = int(JUSTICE_CONFIG['base_bail_amount'] * JUSTICE_CONFIG['bail_multiplier'])

            embed = discord.Embed(
                title=f"🔒 {target.display_name} — EN PRISON",
                description="Enfermé(e) dans les cellules du serveur.",
                color=discord.Color.dark_grey()
            )
            embed.set_thumbnail(url=target.display_avatar.url)
            embed.add_field(name="⏰ Temps restant", value=f"**{time_str}**", inline=True)
            embed.add_field(name="💰 Caution", value=f"**{bail_amount:,}** 💵", inline=True)
            embed.add_field(name="📋 Commandes dispo", value=(
                "`!activity` — Réduire ta peine\n"
                "`!prisonwork` — Bosser en prison\n"
                "`!bail` — Payer ta caution\n"
                "`!tribunal` — Demander un procès\n"
                "`!plead` — Plaider ta cause"
            ), inline=False)

            await self._safe_send(ctx, embed=embed)

        except Exception as e:
            logger.error(f"Error in prison status command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='activity', aliases=['activite', 'action', 'faire'])
    async def prison_activity_command(self, ctx, activity_name: str = None):
        """Activité en prison — UNIQUEMENT dans le channel prison"""
        # Check: doit être en prison
        prison_role = discord.utils.get(ctx.guild.roles, name=PRISON_DISCORD.get("role_name", "🔒 Prisonnier"))
        if not prison_role or prison_role not in ctx.author.roles:
            await ctx.send("❌ Tu n'es pas en prison ! Cette commande est réservée aux prisonniers.")
            return
        try:
            if not activity_name:
                embed = discord.Embed(
                    title="🏢 Activités Prison",
                    description="Liste des activités disponibles:",
                    color=discord.Color.blue()
                )

                for act_id, activity in PRISON_ACTIVITIES.items():
                    embed.add_field(
                        name=activity['name'],
                        value=f"Réduction: {activity['reduction']} secondes\nID: `{act_id}`",
                        inline=False
                    )

                await self._safe_send(ctx, embed=embed)
                return

            success, message = await self.points.do_prison_activity(str(ctx.author.id), activity_name)
            await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in prison activity command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='tribunal', aliases=['proces', 'cour', 'justice'])
    async def tribunal_command(self, ctx, *, plea: str = None):
        """Request a trial with a plea / Demander un procès avec plaidoyer"""
        try:
            if not plea:
                await ctx.send("❌ Tu dois inclure un plaidoyer! Exemple: `!tribunal Je suis innocent!`")
                return

            success, message = await self.points.request_trial(str(ctx.author.id), plea)
            if success:
                trial_msg = await ctx.send(message)
                await trial_msg.add_reaction("✅")
                await trial_msg.add_reaction("❌")
            else:
                await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in tribunal command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    # === NOUVELLES COMMANDES JUSTICE SYSTEM (TECH Brief) ===

    @commands.command(name='arrest', aliases=['arreter', 'arreter_suspect'])
    @commands.cooldown(1, COMMAND_COOLDOWNS.get("arrest", 3600), commands.BucketType.user)
    async def arrest_command(self, ctx, target: discord.Member, *, reason: str):
        """Arrêter quelqu'un et l'envoyer en prison (rôles Discord gérés)"""
        try:
            if target == ctx.author:
                await ctx.send("❌ Tu ne peux pas t'arrêter toi-même!")
                return
            if target.bot:
                await ctx.send("❌ Tu ne peux pas arrêter un bot!")
                return

            arrester_data = self.points.database.get_user_data(str(ctx.author.id))
            if arrester_data['points'] < JUSTICE_CONFIG['min_arrest_points']:
                await ctx.send(f"❌ Il te faut au moins {JUSTICE_CONFIG['min_arrest_points']} 💵 pour arrêter quelqu'un!")
                return

            # Vérifier si déjà en prison
            prison_role = await self._get_or_create_prison_role(ctx.guild)
            if prison_role and prison_role in target.roles:
                await ctx.send(f"❌ {target.display_name} est déjà en prison!")
                return

            # Calculer le temps de prison (1h à 24h)
            base_time = JUSTICE_CONFIG['min_prison_time']
            target_data = self.points.database.get_user_data(str(target.id))
            time_multiplier = min(target_data.get('points', 0) / 5000, 3.0)
            prison_time = max(base_time, int(base_time * max(1, time_multiplier)))
            prison_time = min(prison_time, JUSTICE_CONFIG['max_prison_time'])

            # Payer le coût d'arrestation
            self.points.remove_points(str(ctx.author.id), JUSTICE_CONFIG['arrest_cost'])

            # EMPRISONNER (rôles Discord + DB)
            success = await self._imprison_member(target, prison_time, reason)
            if not success:
                await ctx.send("❌ Échec de l'arrestation (erreur de permissions Discord).")
                return

            hours = prison_time // 3600
            mins = (prison_time % 3600) // 60
            time_str = f"{hours}h {mins:02d}min" if hours else f"{mins}min"
            bail_amount = int(JUSTICE_CONFIG['base_bail_amount'] * JUSTICE_CONFIG['bail_multiplier'])

            embed = discord.Embed(
                title="🚔 ARRESTATION !",
                description=f"**{target.display_name}** a été arrêté(e) et envoyé(e) en prison !",
                color=discord.Color.red()
            )
            embed.add_field(name="👮 Arrêté par", value=ctx.author.display_name, inline=True)
            embed.add_field(name="📝 Motif", value=reason, inline=True)
            embed.add_field(name="⏰ Durée", value=time_str, inline=True)
            embed.add_field(name="💰 Caution", value=f"{bail_amount:,} 💵", inline=True)
            embed.add_field(name="🔒 Effets", value="Rôles retirés, accès limité au channel prison uniquement", inline=False)
            await self._safe_send(ctx, embed=embed)

            # Annonce dans le channel prison
            prison_channel = await self._get_or_create_prison_channel(ctx.guild)
            if prison_channel:
                await prison_channel.send(
                    f"🚔 **NOUVEAU PRISONNIER** — {target.mention} vient d'arriver !\n"
                    f"📝 Motif: {reason}\n⏰ Peine: {time_str}\n"
                    f"Utilise `!activity` pour réduire ta peine ou `!bail` pour payer ta caution."
                )

            # DM à la cible
            try:
                await target.send(f"🚔 Tu as été arrêté(e) par **{ctx.author.display_name}** pour: {reason}\nPeine: {time_str}\nTape `!bail` pour payer ta caution ou `!activity` pour réduire ta peine!")
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error in arrest command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite lors de l'arrestation.")

    @commands.command(name='bail', aliases=['caution', 'payer_caution'])
    @check_cooldown_and_limit('bail')
    async def bail_command(self, ctx, amount: int = None):
        """Payer ta caution pour sortir de prison (restaure tes rôles)"""
        try:
            user_id = str(ctx.author.id)
            prison_role = await self._get_or_create_prison_role(ctx.guild)

            if not prison_role or prison_role not in ctx.author.roles:
                await ctx.send("❌ Tu n'es pas en prison!")
                return

            bail_amount = amount or int(JUSTICE_CONFIG['base_bail_amount'] * JUSTICE_CONFIG['bail_multiplier'])
            current_points = int(self.points.get_user_data(user_id).get('points', 0))

            if current_points < bail_amount:
                await ctx.send(f"❌ La caution est de **{bail_amount:,}** 💵 et tu n'as que **{current_points:,}** 💵.")
                return

            # Payer et libérer
            self.points.remove_points(user_id, bail_amount)
            success = await self._release_member(ctx.author)

            if success:
                await ctx.send(
                    f"🔓 **LIBÉRÉ(E) !** {ctx.author.display_name} a payé sa caution de **{bail_amount:,}** 💵 et est libre !\n"
                    f"Tes rôles ont été restaurés."
                )
            else:
                await ctx.send("❌ Erreur lors de la libération. Contacte un admin.")

        except Exception as e:
            logger.error(f"Error in bail command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='visit', aliases=['visiter', 'visite_prison'])
    @check_cooldown_and_limit('visit')
    async def visit_command(self, ctx, target: discord.Member = None, *, message: str = ""):
        """Visiter un prisonnier — tu payes + le prisonnier doit accepter ta visite"""
        try:
            if not target:
                await ctx.send("❌ Usage: `!visit @prisonnier Ton message`")
                return

            user_id = str(ctx.author.id)
            target_id = str(target.id)
            visit_cost = JUSTICE_CONFIG.get('visit_cost', 100)

            # Vérifier que la cible est en prison
            prison_role = await self._get_or_create_prison_role(ctx.guild)
            if not prison_role or prison_role not in target.roles:
                await ctx.send(f"❌ {target.display_name} n'est pas en prison!")
                return

            # Vérifier les fonds
            current_points = int(self.points.get_user_data(user_id).get('points', 0))
            if current_points < visit_cost:
                await ctx.send(f"❌ Une visite coûte **{visit_cost}** 💵 et tu n'as que **{current_points:,}** 💵.")
                return

            # Demander l'accord du prisonnier
            prison_channel = await self._get_or_create_prison_channel(ctx.guild)
            if not prison_channel:
                await ctx.send("❌ Pas de channel prison trouvé.")
                return

            request_msg = await prison_channel.send(
                f"🔔 **DEMANDE DE VISITE**\n"
                f"{ctx.author.display_name} veut te rendre visite, {target.mention} !\n"
                f"{'Message: *' + message + '*' if message else ''}\n\n"
                f"Réagis ✅ pour accepter ou ❌ pour refuser."
            )
            await request_msg.add_reaction("✅")
            await request_msg.add_reaction("❌")

            def check(reaction, user):
                return user.id == target.id and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == request_msg.id

            try:
                reaction, _ = await self.bot.wait_for('reaction_add', check=check, timeout=120)
            except asyncio.TimeoutError:
                await prison_channel.send(f"⏰ {target.display_name} n'a pas répondu. Visite annulée.")
                return

            if str(reaction.emoji) == "❌":
                await prison_channel.send(f"❌ {target.display_name} refuse la visite.")
                return

            # Payer et autoriser la visite (accès temporaire au channel prison)
            self.points.remove_points(user_id, visit_cost)

            # Donner accès temporaire au visiteur
            try:
                await prison_channel.set_permissions(ctx.author, view_channel=True, send_messages=True)
            except Exception:
                pass

            await prison_channel.send(
                f"✅ **VISITE ACCEPTÉE** — {ctx.author.display_name} entre dans la prison.\n"
                f"{'📝 Message: *' + message + '*' if message else ''}\n"
                f"💰 Coût: **{visit_cost}** 💵\n\n"
                f"⏰ La visite dure **5 minutes**. Parlez vite !"
            )

            # Retirer l'accès après 5 minutes
            await asyncio.sleep(300)
            try:
                await prison_channel.set_permissions(ctx.author, overwrite=None)
            except Exception:
                pass
            await prison_channel.send(f"🔒 La visite de {ctx.author.display_name} est terminée.")

        except Exception as e:
            logger.error(f"Error in visit command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='plead', aliases=['plaider', 'supplier'])
    async def plead_command(self, ctx, *, plea_text: str):
        """Submit a plea to reduce prison sentence / Plaider pour réduire sa peine de prison"""
        try:
            # Vérifier si l'utilisateur est en prison
            prison_status = self.points.database.get_prison_status(str(ctx.author.id))
            if not prison_status:
                await ctx.send("❌ Tu n'es pas en prison! Tu ne peux plaider que si tu es emprisonné.")
                return
            
            # Soumettre le plaidoyer
            success = self.points.database.submit_plea(str(ctx.author.id), plea_text)
            
            if success:
                # Chance de succès du plaidoyer
                import random
                success_roll = random.random()
                
                embed = discord.Embed(
                    title="⚖️ Plaidoyer Soumis",
                    description="Ton plaidoyer a été entendu par le tribunal...",
                    color=discord.Color.gold()
                )
                embed.add_field(name="📝 Ton plaidoyer", value=plea_text, inline=False)
                
                if success_roll < JUSTICE_CONFIG['plea_success_rate']:
                    # Succès du plaidoyer - réduire la peine
                    time_reduction = prison_status['time_left'] // 3  # Réduction de 1/3
                    
                    # Mettre à jour la sentence (simulation - à adapter selon votre système)
                    embed.add_field(name="✅ Verdict", value="Plaidoyer accepté!", inline=True)
                    embed.add_field(name="⏰ Réduction", value=f"{time_reduction//60} minutes", inline=True)
                    embed.color = discord.Color.green()
                    
                    # TODO: Implémenter la réduction réelle du temps de prison
                    
                else:
                    # Échec du plaidoyer
                    embed.add_field(name="❌ Verdict", value="Plaidoyer rejeté", inline=True)
                    embed.add_field(name="📢 Tribunal", value="Ta peine reste inchangée", inline=True)
                    embed.color = discord.Color.red()
                
                await self._safe_send(ctx, embed=embed)
            else:
                await ctx.send("❌ Échec de la soumission du plaidoyer. Réessaie plus tard.")

        except Exception as e:
            logger.error(f"Error in plead command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite lors du plaidoyer.")

    @commands.command(name='prisonwork', aliases=['travail_prison', 'bosser_prison'])
    @commands.cooldown(1, 3600, commands.BucketType.user)  # 1 fois par heure
    async def prisonwork_command(self, ctx):
        """Work in prison to earn points and reduce sentence / Travailler en prison pour gagner des points et réduire sa peine"""
        try:
            # Vérifier si l'utilisateur est en prison
            prison_status = self.points.database.get_prison_status(str(ctx.author.id))
            if not prison_status:
                await ctx.send("❌ Tu n'es pas en prison! Tu ne peux travailler qu'en étant emprisonné.")
                return
            
            # Effectuer le travail en prison
            success, points_earned = self.points.database.do_prison_work(str(ctx.author.id))
            
            if success:
                embed = discord.Embed(
                    title="🔨 Travail en Prison",
                    description="Tu as travaillé dur pendant ton emprisonnement!",
                    color=discord.Color.orange()
                )
                embed.add_field(name="💰 Points gagnés", value=f"+{points_earned} points", inline=True)
                embed.add_field(name="⏰ Temps réduit", value="30 minutes", inline=True)
                embed.add_field(name="📈 Comportement", value="Exemplaire", inline=True)
                embed.add_field(name="💡 Info", value="Tu peux travailler une fois par heure", inline=False)
                
                await self._safe_send(ctx, embed=embed)
            else:
                await ctx.send("❌ Impossible de travailler maintenant. Réessaie plus tard.")

        except Exception as e:
            logger.error(f"Error in prisonwork command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite pendant le travail en prison.")

    # === FIN COMMANDES JUSTICE SYSTEM ===

    @commands.command(name='shop', aliases=['boutique'])
    async def shop_command(self, ctx):
        """Show the shop items"""
        try:
            embed = discord.Embed(
                title="🏪 Boutique du Crime",
                description="Utilise !buy <item> pour acheter un objet",
                color=discord.Color.gold()
            )

            # Add regular items
            for item_id, item in SHOP_ITEMS.items():
                embed.add_field(
                    name=f"{item['name']} - {item['price']} points",
                    value=f"{item['description']}\nID: `{item_id}`",
                    inline=False
                )

            # Add special items if available
            if SHOP_ITEMS_NEW:
                embed.add_field(
                    name="🌟 Items Spéciaux",
                    value="Collection unique et limitée:",
                    inline=False
                )

                for item_id, item in SHOP_ITEMS_NEW.items():
                    quantity_text = f"(Reste: {item['quantity']})" if item['quantity'] > 0 else "(SOLD OUT)"
                    embed.add_field(
                        name=f"{item['name']} - {item['price']} points {quantity_text}",
                        value=f"{item['description']}\nID: `{item_id}`",
                        inline=False
                    )

            await self._safe_send(ctx, embed=embed)
            logger.info(f"Shop displayed to {ctx.author}")
        except Exception as e:
            logger.error(f"Error in shop command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='buy', aliases=['acheter'])
    async def buy_command(self, ctx, item_id: str = None):
        """Buy an item from the shop"""
        try:
            if not item_id:
                await ctx.send("❌ Spécifie l'objet à acheter! Exemple: `!buy lockpick`")
                return

            success, message = await self.points.buy_item(str(ctx.author.id), item_id)
            await ctx.send(message)
        except Exception as e:
            logger.error(f"Error in buy command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='inventory', aliases=['inventaire', 'inv', 'objets'])
    async def inventory(self, ctx):
        """Show your inventory / Affiche l'inventaire de l'utilisateur."""
        inv = self.points.db.get_inventory(str(ctx.author.id))
        if not inv:
            await ctx.send("Votre inventaire est vide.")
        else:
            items = "\n".join(f"- {item_id}" for item_id in inv)
            await ctx.send(f"**Votre inventaire :**\n{items}")

    @commands.command(name='trade', aliases=['echanger', 'troquer', 'echange'])
    async def trade(self, ctx, member: discord.Member, my_item_id: str):
        """Trade an item with another player / Propose un échange d'objet à un autre joueur."""
        author_id = str(ctx.author.id)
        target_id = str(member.id)
        db = self.points.db

        # Vérifie que l'auteur possède bien l'objet proposé
        if my_item_id not in db.get_inventory(author_id):
            await ctx.send("Vous ne possédez pas cet objet.")
            return
        if author_id == target_id:
            await ctx.send("Vous ne pouvez pas échanger avec vous-même.")
            return

        # Demande à B quel objet il souhaite proposer en échange
        await ctx.send(
            f"{member.mention}, {ctx.author.display_name} souhaite échanger son objet `{my_item_id}` avec vous.\n"
            "Réponds avec l'identifiant de l'objet de ton inventaire que tu proposes en échange, ou 'annuler' pour refuser.\n"
            f"Ton inventaire : {', '.join(db.get_inventory(target_id)) or 'vide'}"
        )

        def check_item(m):
            return m.author.id == member.id and m.channel == ctx.channel

        try:
            msg = await ctx.bot.wait_for("message", check=check_item, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send("Échange annulé (temps écoulé).")
            return

        # Si B annule
        if msg.content.lower() == "annuler":
            await ctx.send("Échange annulé.")
            return

        their_item_id = msg.content.strip()

        # Vérifie que B possède bien l'objet proposé
        if their_item_id not in db.get_inventory(target_id):
            await ctx.send(f"{member.display_name} ne possède pas cet objet. Échange annulé.")
            return

        # Demande à A de confirmer l'échange
        await ctx.send(
            f"{ctx.author.mention}, {member.display_name} propose d'échanger son objet `{their_item_id}` contre ton `{my_item_id}`.\n"
            "Réponds 'oui' pour accepter, 'non' pour refuser."
        )

        def check_confirm(m):
            return m.author.id == ctx.author.id and m.channel == ctx.channel and m.content.lower() in ["oui", "non"]

        try:
            confirm_msg = await ctx.bot.wait_for("message", check=check_confirm, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("Échange annulé (temps écoulé).")
            return

        if confirm_msg.content.lower() == "oui":
            # Retire les objets des inventaires respectifs et les ajoute à l'autre
            db.remove_item_from_inventory(author_id, my_item_id)
            db.add_item_to_inventory(target_id, my_item_id)
            db.remove_item_from_inventory(target_id, their_item_id)
            db.add_item_to_inventory(author_id, their_item_id)
            await ctx.send(
                f"Échange réussi ! `{my_item_id}` a été échangé contre `{their_item_id}` entre {ctx.author.display_name} et {member.display_name}."
            )
        else:
            await ctx.send("Échange refusé.")

    @commands.command(name='addpoints', aliases=['ajouterpoints', 'donnerpoints'])
    @is_bot_owner()
    async def add_points(self, ctx, member: discord.Member = None, amount: int = None):
        """[OWNER] Ajouter des points à un membre"""
        try:
            if not member or amount is None:
                await ctx.send("❌ Usage: !addpoints @user <montant>")
                return

            if amount <= 0:
                await ctx.send("❌ Le montant doit être positif!")
                return

            if amount > STAFF_EDITPOINTS_MAX_ADD:
                await ctx.send(f"❌ Limite maximale: {STAFF_EDITPOINTS_MAX_ADD} points par ajout!")
                return

            self.points.db.add_points(str(member.id), amount)
            await ctx.send(f"✅ {amount} points ajoutés à {member.name}!")
            logger.warning(f"AUDIT: Owner {ctx.author} ({ctx.author.id}) added {amount} points to {member} ({member.id})")
        except Exception as e:
            logger.error(f"Error in add_points command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='removepoints', aliases=['retirerpoints', 'enleverpoints'])
    @is_bot_owner()
    async def remove_points(self, ctx, member: discord.Member = None, amount: int = None):
        """[OWNER] Retirer des points à un membre"""
        try:
            if not member or amount is None:
                await ctx.send("❌ Usage: !removepoints @user <montant>")
                return

            if amount <= 0:
                await ctx.send("❌ Le montant doit être positif!")
                return

            if amount > STAFF_EDITPOINTS_MAX_REMOVE:
                await ctx.send(f"❌ Limite maximale: {STAFF_EDITPOINTS_MAX_REMOVE} points par retrait!")
                return

            current_points = self.points.db.get_user_points(str(member.id))
            if current_points < amount:
                amount = current_points

            self.points.db.add_points(str(member.id), -amount)
            await ctx.send(f"✅ {amount} points retirés à {member.name}!")
            logger.warning(f"AUDIT: Owner {ctx.author} ({ctx.author.id}) removed {amount} points from {member} ({member.id})")
        except Exception as e:
            logger.error(f"Error in remove_points command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='resetcooldowns', aliases=['resetcd', 'resetlimits'])
    @is_bot_owner()
    async def reset_cooldowns(self, ctx, target: discord.Member = None):
        """[OWNER] Reset tous les cooldowns et limites quotidiennes d'un utilisateur"""
        try:
            member = target or ctx.author
            user_id = str(member.id)
            db = self.points.db

            reset_count = 0

            # 1. Supprimer tous les cooldowns de commandes
            if hasattr(db, 'supabase') and hasattr(db, 'is_connected') and db.is_connected():
                # Reset cooldowns
                try:
                    db.supabase.table('user_cooldowns').delete().eq('user_id', user_id).execute()
                    reset_count += 1
                except Exception as e:
                    logger.warning(f"Error resetting cooldowns: {e}")

                # Reset daily usage
                today = datetime.now().date().isoformat()
                try:
                    db.supabase.table('command_usage').delete().eq('user_id', user_id).eq('date', today).execute()
                    reset_count += 1
                except Exception as e:
                    logger.warning(f"Error resetting daily usage: {e}")
            elif hasattr(db, 'data'):
                # Fallback JSON database
                if 'cooldowns' in db.data:
                    keys_to_remove = [k for k in db.data['cooldowns'] if user_id in str(db.data['cooldowns'].get(k, {}))]
                    for k in keys_to_remove:
                        if user_id in db.data['cooldowns'].get(k, {}):
                            del db.data['cooldowns'][k][user_id]
                            reset_count += 1
                if 'daily_usage' in db.data and user_id in db.data['daily_usage']:
                    del db.data['daily_usage'][user_id]
                    reset_count += 1
                db.save()

            embed = discord.Embed(
                title="🔄 Cooldowns & Limites Reset",
                description=f"Tous les cooldowns et limites quotidiennes de **{member.display_name}** ont été réinitialisés.",
                color=0x00FF00
            )
            embed.add_field(name="Utilisateur", value=f"{member.mention}", inline=True)
            embed.add_field(name="Resets effectués", value=f"{reset_count}", inline=True)
            await self._safe_send(ctx, embed=embed)
            logger.warning(f"AUDIT: Owner {ctx.author} ({ctx.author.id}) reset cooldowns for {member} ({member.id})")

        except Exception as e:
            logger.error(f"Error in reset_cooldowns: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite lors du reset.")

    # === NOUVELLES COMMANDES ADMIN AVANCÉES (TECH Brief Phase 3B) ===

    @commands.command(name='additem', aliases=['ajouteritem', 'donneritem'])
    @is_bot_owner()
    async def admin_add_item(self, ctx, member: discord.Member = None, item_id: str = None, quantity: int = 1, *, reason: str = ""):
        """[OWNER] Ajouter objet(s) à l'inventaire d'un utilisateur"""
        try:
            if not member or not item_id:
                await ctx.send("❌ Usage: !additem @user <item_id> [quantité] [raison]")
                return

            if quantity <= 0 or quantity > ADMIN_CONFIG['max_items_per_action']:
                await ctx.send(f"❌ Quantité invalide! Maximum {ADMIN_CONFIG['max_items_per_action']} par action.")
                return

            # Vérifier si l'item nécessite des permissions spéciales
            if item_id in ADMIN_CONFIG['restricted_items'] and not ctx.author.guild_permissions.administrator:
                await ctx.send(f"❌ L'item '{item_id}' nécessite des permissions d'administrateur!")
                return

            # Ajouter les items
            success = self.points.database.admin_add_item(
                str(ctx.author.id), 
                str(member.id), 
                item_id, 
                quantity, 
                reason
            )

            if success:
                embed = discord.Embed(
                    title="📦 Items Ajoutés",
                    description=f"**{quantity}x {item_id}** ajouté(s) à l'inventaire de {member.display_name}",
                    color=discord.Color.green()
                )
                embed.add_field(name="👤 Administrateur", value=ctx.author.display_name, inline=True)
                embed.add_field(name="🎯 Cible", value=member.display_name, inline=True)
                embed.add_field(name="📝 Quantité", value=f"{quantity}x", inline=True)
                
                if reason:
                    embed.add_field(name="📋 Raison", value=reason, inline=False)
                
                await self._safe_send(ctx, embed=embed)
                
                # Notification à l'utilisateur cible
                try:
                    await member.send(f"🎁 Tu as reçu **{quantity}x {item_id}** de la part de l'administration!\nRaison: {reason or 'Non spécifiée'}")
                except:
                    pass  # Si les DM sont fermés
            else:
                await ctx.send("❌ Échec de l'ajout d'items. Vérifiez les logs.")

        except Exception as e:
            logger.error(f"Error in admin_add_item command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='removeitem', aliases=['retireritem', 'enleveritem'])
    @is_bot_owner()
    async def admin_remove_item(self, ctx, member: discord.Member = None, item_id: str = None, quantity: int = 1, *, reason: str = ""):
        """[OWNER] Retirer objet(s) de l'inventaire d'un utilisateur"""
        try:
            if not member or not item_id:
                await ctx.send("❌ Usage: !removeitem @user <item_id> [quantité] [raison]")
                return

            if quantity <= 0 or quantity > ADMIN_CONFIG['max_items_per_action']:
                await ctx.send(f"❌ Quantité invalide! Maximum {ADMIN_CONFIG['max_items_per_action']} par action.")
                return

            # Vérifier l'inventaire actuel
            current_inventory = self.points.database.get_inventory(str(member.id))
            current_count = current_inventory.count(item_id)
            
            if current_count == 0:
                await ctx.send(f"❌ {member.display_name} ne possède pas d'item '{item_id}'!")
                return

            # Retirer les items
            success, items_removed = self.points.database.admin_remove_item(
                str(ctx.author.id), 
                str(member.id), 
                item_id, 
                quantity, 
                reason
            )

            if success:
                embed = discord.Embed(
                    title="📦 Items Retirés",
                    description=f"**{items_removed}x {item_id}** retiré(s) de l'inventaire de {member.display_name}",
                    color=discord.Color.orange()
                )
                embed.add_field(name="👤 Administrateur", value=ctx.author.display_name, inline=True)
                embed.add_field(name="🎯 Cible", value=member.display_name, inline=True)
                embed.add_field(name="📝 Quantité", value=f"{items_removed}x (demandé: {quantity}x)", inline=True)
                
                if reason:
                    embed.add_field(name="📋 Raison", value=reason, inline=False)
                
                await self._safe_send(ctx, embed=embed)
                
                # Notification à l'utilisateur cible
                try:
                    await member.send(f"⚠️ **{items_removed}x {item_id}** ont été retirés de ton inventaire par l'administration.\nRaison: {reason or 'Non spécifiée'}")
                except:
                    pass  # Si les DM sont fermés
            else:
                await ctx.send("❌ Échec du retrait d'items. Vérifiez les logs.")

        except Exception as e:
            logger.error(f"Error in admin_remove_item command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='promote', aliases=['promouvoir', 'upgrader'])
    @is_bot_owner()
    async def admin_promote(self, ctx, member: discord.Member = None, new_role: str = None, *, reason: str = ""):
        """[OWNER] Promouvoir un utilisateur à un rôle supérieur"""
        try:
            if not member or not new_role:
                await ctx.send("❌ Usage: !promote @user <role> [raison]")
                available_roles = ", ".join(ADMIN_CONFIG['promotable_roles'])
                await ctx.send(f"📋 Rôles disponibles: {available_roles}")
                return

            new_role = new_role.lower()
            
            # Vérifier si le rôle est promouvable
            if new_role not in ADMIN_CONFIG['promotable_roles']:
                await ctx.send(f"❌ Rôle '{new_role}' non autorisé pour promotion!")
                available_roles = ", ".join(ADMIN_CONFIG['promotable_roles'])
                await ctx.send(f"📋 Rôles autorisés: {available_roles}")
                return

            # Vérifier le rôle actuel
            current_role = self.points.database.get_user_role(str(member.id))
            hierarchy = ADMIN_CONFIG['user_roles_hierarchy']
            
            current_level = hierarchy.index(current_role) if current_role in hierarchy else 0
            new_level = hierarchy.index(new_role) if new_role in hierarchy else 0
            
            if new_level <= current_level:
                await ctx.send(f"❌ {member.display_name} est déjà '{current_role}' ou supérieur!")
                return

            # Effectuer la promotion
            success = self.points.database.admin_set_user_role(
                str(ctx.author.id), 
                str(member.id), 
                new_role, 
                reason
            )

            if success:
                embed = discord.Embed(
                    title="⬆️ Promotion Effectuée",
                    description=f"**{member.display_name}** a été promu(e)!",
                    color=discord.Color.green()
                )
                embed.add_field(name="👤 Administrateur", value=ctx.author.display_name, inline=True)
                embed.add_field(name="🎯 Utilisateur", value=member.display_name, inline=True)
                embed.add_field(name="📊 Changement", value=f"{current_role} → {new_role}", inline=True)
                
                if reason:
                    embed.add_field(name="📋 Raison", value=reason, inline=False)
                
                await self._safe_send(ctx, embed=embed)
                
                # Notification à l'utilisateur
                try:
                    await member.send(f"🎉 Félicitations! Tu as été promu(e) au rôle **{new_role}** par l'administration!\nRaison: {reason or 'Non spécifiée'}")
                except:
                    pass  # Si les DM sont fermés
            else:
                await ctx.send("❌ Échec de la promotion. Vérifiez les logs.")

        except Exception as e:
            logger.error(f"Error in admin_promote command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    @commands.command(name='demote', aliases=['retrograder', 'downgrade'])
    @is_bot_owner()
    async def admin_demote(self, ctx, member: discord.Member = None, new_role: str = None, *, reason: str = ""):
        """[OWNER] Rétrograder un utilisateur à un rôle inférieur"""
        try:
            if not member or not new_role:
                await ctx.send("❌ Usage: !demote @user <role> [raison]")
                available_roles = ", ".join(ADMIN_CONFIG['demotable_roles'])
                await ctx.send(f"📋 Rôles disponibles: {available_roles}")
                return

            new_role = new_role.lower()
            
            # Vérifier si le rôle est rétrogradable
            if new_role not in ADMIN_CONFIG['demotable_roles'] and new_role != "member":
                await ctx.send(f"❌ Rôle '{new_role}' non autorisé pour rétrogradation!")
                available_roles = ", ".join(ADMIN_CONFIG['demotable_roles'] + ["member"])
                await ctx.send(f"📋 Rôles autorisés: {available_roles}")
                return

            # Vérifier le rôle actuel
            current_role = self.points.database.get_user_role(str(member.id))
            hierarchy = ADMIN_CONFIG['user_roles_hierarchy']
            
            current_level = hierarchy.index(current_role) if current_role in hierarchy else 0
            new_level = hierarchy.index(new_role) if new_role in hierarchy else 0
            
            if new_level >= current_level:
                await ctx.send(f"❌ {member.display_name} est '{current_role}', impossible de rétrograder vers '{new_role}'!")
                return

            # Exiger une raison pour les rétrogradations
            if ADMIN_CONFIG['require_reason'] and not reason:
                await ctx.send("❌ Une raison est obligatoire pour les rétrogradations!")
                return

            # Effectuer la rétrogradation
            success = self.points.database.admin_set_user_role(
                str(ctx.author.id), 
                str(member.id), 
                new_role, 
                reason
            )

            if success:
                embed = discord.Embed(
                    title="⬇️ Rétrogradation Effectuée",
                    description=f"**{member.display_name}** a été rétrogradé(e).",
                    color=discord.Color.red()
                )
                embed.add_field(name="👤 Administrateur", value=ctx.author.display_name, inline=True)
                embed.add_field(name="🎯 Utilisateur", value=member.display_name, inline=True)
                embed.add_field(name="📊 Changement", value=f"{current_role} → {new_role}", inline=True)
                embed.add_field(name="📋 Raison", value=reason, inline=False)
                
                await self._safe_send(ctx, embed=embed)
                
                # Notification à l'utilisateur
                try:
                    await member.send(f"⚠️ Tu as été rétrogradé(e) au rôle **{new_role}** par l'administration.\nRaison: {reason}")
                except:
                    pass  # Si les DM sont fermés
            else:
                await ctx.send("❌ Échec de la rétrogradation. Vérifiez les logs.")

        except Exception as e:
            logger.error(f"Error in admin_demote command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    # === FIN COMMANDES ADMIN AVANCÉES ===

    @commands.command(name='linktwitter', aliases=['liertwitter', 'connecttwitter'])
    @commands.cooldown(1, 900, commands.BucketType.user)  # 1 fois par 15 minutes par utilisateur
    async def link_twitter(self, ctx, username: str):
        """Link a Twitter account (limited to 1 time per 15min) / Lier un compte Twitter"""
        try:
            if not self.twitter_handler.is_available():
                await ctx.send("❌ Service Twitter temporairement indisponible.")
                return
            
            # Vérifier si l'utilisateur a déjà un compte lié
            user_data = self.points.database.get_user_data(str(ctx.author.id))
            if user_data.get('twitter'):
                await ctx.send("❌ Vous avez déjà un compte Twitter lié. Utilisez `!unlinktwitter` d'abord.")
                return
            
            # Nettoyer le nom d'utilisateur
            username = username.replace('@', '').strip()
            
            # Notification que la requête est en queue
            embed = discord.Embed(
                title="🐦 Vérification en cours...",
                description=f"Vérification du compte @{username} en cours.\n"
                           f"Cela peut prendre jusqu'à 15 minutes selon la file d'attente.",
                color=0x1DA1F2
            )
            status_msg = await self._safe_send(ctx, embed=embed)
            
            # Vérifier le compte avec rate limiting
            success, data = await self.twitter_handler.verify_account(username)
            
            if success:
                # Sauvegarder le lien
                user_data['twitter'] = data
                self.points.database.save_data()
                
                # Donner des points bonus pour la liaison
                bonus_points = 500
                self.points.database.add_points(str(ctx.author.id), bonus_points)
                
                embed = discord.Embed(
                    title="✅ Compte Twitter lié",
                    description=f"Votre compte Discord est maintenant lié à [@{data['username']}]",
                    color=0x00FF00
                )
                embed.add_field(name="Nom", value=data['name'], inline=True)
                embed.add_field(name="Followers", value=f"{data['followers_count']:,}", inline=True)
                embed.add_field(name="Bonus", value=f"+{bonus_points} points", inline=True)
                
                await status_msg.edit(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Erreur de vérification",
                    description=str(data),
                    color=0xFF0000
                )
                await status_msg.edit(embed=embed)
                
        except commands.CommandOnCooldown as e:
            remaining_time = int(e.retry_after)
            minutes = remaining_time // 60
            seconds = remaining_time % 60
            await ctx.send(f"❌ Vous devez attendre {minutes}m {seconds}s avant de pouvoir lier un autre compte Twitter.")
        except Exception as e:
            logger.error(f"Error in link_twitter command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite lors de la liaison du compte Twitter.")

    @commands.command(name='twitterstatus', aliases=['statustwitter', 'statut_x'])
    @commands.has_permissions(administrator=True)
    async def twitter_status(self, ctx):
        """Check Twitter service status (Admin only) / Vérifier l'état du service Twitter (Admin seulement)"""
        try:
            # Vérifier la santé
            is_healthy, health_message = await self.twitter_handler.health_check()
            
            # Obtenir le statut du rate limiter
            rate_status = self.twitter_handler.get_rate_limit_status()
            
            embed = discord.Embed(
                title="🐦 État du Service Twitter",
                description=health_message,
                color=0x00FF00 if is_healthy else 0xFF0000
            )
            
            embed.add_field(
                name="Service",
                value="✅ Actif" if self.twitter_handler.is_available() else "❌ Inactif",
                inline=True
            )
            
            embed.add_field(
                name="Requêtes en attente",
                value=rate_status.get('pending_requests', 0),
                inline=True
            )
            
            embed.add_field(
                name="Cache actif",
                value=f"{rate_status.get('cache_entries', 0)} entrées",
                inline=True
            )
            
            # Statut des endpoints
            endpoints_info = ""
            for endpoint, info in rate_status.get('endpoints', {}).items():
                endpoints_info += f"**{endpoint}**: {info['next_available']}\n"
            
            if endpoints_info:
                embed.add_field(
                    name="Prochaines disponibilités",
                    value=endpoints_info,
                    inline=False
                )
            
            await self._safe_send(ctx, embed=embed)
            
        except Exception as e:
            logger.error(f"Error in twitter_status command: {e}", exc_info=True)
            await ctx.send("❌ Erreur lors de la vérification du statut Twitter.")

    @commands.command(name='twitterqueue', aliases=['queuetwitter', 'file_x'])
    @commands.has_permissions(administrator=True)
    async def twitter_queue(self, ctx):
        """View Twitter queue (Admin only) / Voir la file d'attente Twitter (Admin seulement)"""
        try:
            queue_info = await self.twitter_handler.queue_info()
            
            embed = discord.Embed(
                title="📋 File d'attente Twitter",
                color=0x1DA1F2
            )
            
            embed.add_field(
                name="Requêtes en attente",
                value=queue_info.get('pending_requests', 0),
                inline=True
            )
            
            embed.add_field(
                name="Résultats en cache",
                value=queue_info.get('cache_entries', 0),
                inline=True
            )
            
            # Détails des endpoints
            endpoints_status = queue_info.get('endpoints_status', {})
            if endpoints_status:
                status_text = ""
                for endpoint, info in endpoints_status.items():
                    status_text += f"**{endpoint}**:\n"
                    status_text += f"  Utilisé: {info['requests_used']}/{info['requests_limit']}\n"
                    status_text += f"  Prochain: {info['next_available']}\n\n"
                
                embed.add_field(
                    name="État des endpoints",
                    value=status_text or "Aucun endpoint actif",
                    inline=False
                )
            
            await self._safe_send(ctx, embed=embed)
            
        except Exception as e:
            logger.error(f"Error in twitter_queue command: {e}", exc_info=True)
            await ctx.send("❌ Erreur lors de la récupération des informations de queue.")

    @commands.command(name='unlinktwitter', aliases=['deconnectertwitter', 'delier_x'])
    async def unlink_twitter(self, ctx):
        """Unlink Twitter account / Délier le compte Twitter"""
        try:
            user_data = self.points.database.get_user_data(str(ctx.author.id))
            
            if not user_data.get('twitter'):
                await ctx.send("❌ Aucun compte Twitter lié.")
                return
            
            # Supprimer le lien
            del user_data['twitter']
            self.points.database.save_data()
            
            embed = discord.Embed(
                title="✅ Compte Twitter délié",
                description="Votre compte Twitter a été délié avec succès.",
                color=0x00FF00
            )
            await self._safe_send(ctx, embed=embed)
            
        except Exception as e:
            logger.error(f"Error in unlink_twitter command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite lors du délien du compte Twitter.")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle reactions for combat and voting"""
        if user.bot:
            return

        message = reaction.message
        emoji = str(reaction.emoji)

        # Handle tribunal votes
        if message.content.startswith("⚖️"):
            if emoji in ["✅", "❌"]:
                vote = emoji == "✅"
                try:
                    # Extract defendant ID from message content
                    defendant_id = message.content.split('<@')[1].split('>')[0]
                    success, result = await self.points.vote_trial(
                        str(user.id), defendant_id, vote
                    )
                    await message.channel.send(result)
                except Exception as e:
                    logger.error(f"Error processing trial vote: {e}", exc_info=True)
    # === COMMANDE PROFIL ===

    @commands.command(name='profil', aliases=['profile', 'me', 'stats'])
    async def profil_command(self, ctx, member: discord.Member = None):
        """Profil Thugz complet avec historique, stats, taux de criminalité et analyse"""
        try:
            target = member or ctx.author
            user_id = str(target.id)
            data = self.points.get_user_data(user_id)
            points = int(data.get('points', 0))
            db = self.points.db

            # ── Historique depuis point_transactions ──
            stats = await self._get_user_history(user_id)
            total = max(1, stats.get('total_actions', 1))
            crimes = stats.get('crimes', 0)
            work_count = stats.get('work', 0)
            prison_count = stats.get('prison', 0)
            deals = stats.get('deals', 0)
            gambling = stats.get('gambling', 0)
            ken_count = stats.get('ken', 0)
            wesh_count = stats.get('wesh', 0)

            # Taux de criminalité (% d'actions criminelles)
            crime_rate = int((crimes + deals) / total * 100) if total > 0 else 0

            # Gang
            gang_name = "Aucun"
            try:
                gang_id = db.get_user_gang(user_id)
                if gang_id:
                    gang_info = db.get_gang_info(gang_id)
                    if gang_info:
                        gang_name = gang_info.get('name', 'Inconnu')
            except Exception:
                pass

            # Prison
            prison_role = discord.utils.get(ctx.guild.roles, name=PRISON_DISCORD.get("role_name", "🔒 Prisonnier"))
            is_imprisoned = prison_role and prison_role in target.roles

            # Wealth tier
            if points < 0:
                wealth = "💀 Endetté"
            elif points >= 100000:
                wealth = "💎 Milliardaire du Ghetto"
            elif points >= 50000:
                wealth = "🏆 Parrain"
            elif points >= 20000:
                wealth = "💰 Caïd"
            elif points >= 5000:
                wealth = "💵 Dealer confirmé"
            elif points >= 1000:
                wealth = "🪙 Petit voyou"
            else:
                wealth = "🗑️ Clochard du quartier"

            # Nickname
            nickname = self._generate_nickname(points, crimes, prison_count, is_imprisoned)

            # ── Analyse de personnalité ──
            analyses = []
            if crime_rate > 60:
                analyses.append("Un vrai danger public. Les flics ont son poster dans tous les commissariats.")
            elif crime_rate > 30:
                analyses.append("Penche clairement du mauvais côté de la loi.")
            elif crime_rate > 10:
                analyses.append("Fait quelques coups en douce mais reste discret.")
            else:
                analyses.append("Un citoyen presque modèle... presque.")

            if work_count > 10:
                analyses.append("Travailleur acharné malgré les tentations.")
            if prison_count > 3:
                analyses.append("Abonné au service pénitentiaire.")
            if deals > 5:
                analyses.append("Dealer confirmé — son numéro tourne dans tout le quartier.")
            if ken_count > 3:
                analyses.append("Dragueur invétéré. Les gens le fuient au bar.")
            if gambling > 10:
                analyses.append("Accro aux jeux. Les casinos lui envoient des cartes de fidélité.")
            if wesh_count > 5:
                analyses.append("Le destin s'acharne sur lui. Ou c'est lui qui s'acharne sur le destin.")
            if points < 0:
                analyses.append("Endetté jusqu'au cou. Même les huissiers ont pitié.")

            analysis_text = " ".join(analyses[:3]) if analyses else "Pas assez d'historique pour faire une analyse."

            # ── BUILD EMBED ──
            embed = discord.Embed(
                title=f"👤 Profil de {target.display_name}",
                description=f"*\"{nickname}\"*\n\n📝 {analysis_text}",
                color=0xFF0000 if points < 0 else 0xFF4500
            )
            embed.set_thumbnail(url=target.display_avatar.url)

            embed.add_field(name="💰 Richesse", value=f"**{points:,}** 💵\n{wealth}", inline=True)
            embed.add_field(name="🔫 Gang", value=gang_name, inline=True)

            if is_imprisoned:
                release_time = self.points.database.get_prison_time(user_id)
                import time as _time
                remaining = max(0, int(float(release_time or 0) - _time.time())) if release_time else 0
                embed.add_field(name="🏢 Prison", value=f"⛓️ Enfermé ({remaining//60}min)", inline=True)
            else:
                embed.add_field(name="🏢 Prison", value="✅ Libre", inline=True)

            # Stats détaillées
            embed.add_field(name="📊 Statistiques", value=(
                f"🔨 Travaux: **{work_count}**\n"
                f"🦹 Crimes: **{crimes}**\n"
                f"💊 Deals: **{deals}**\n"
                f"🏢 Passages en prison: **{prison_count}**\n"
                f"🎰 Paris: **{gambling}**\n"
                f"🌀 Wesh: **{wesh_count}**\n"
                f"💋 Ken: **{ken_count}**"
            ), inline=False)

            # Taux de criminalité
            crime_bar = "🟥" * (crime_rate // 10) + "⬜" * (10 - crime_rate // 10)
            embed.add_field(name=f"🚨 Criminalité: {crime_rate}%", value=crime_bar, inline=False)

            # Inventaire
            inv = db.get_inventory(user_id)
            inv_text = ", ".join(inv[:5]) if inv else "Vide"
            if len(inv) > 5:
                inv_text += f" (+{len(inv)-5})"
            embed.add_field(name="🎒 Inventaire", value=inv_text, inline=False)

            embed.set_footer(text=f"Total actions: {total} | ID: {user_id}")
            await self._safe_send(ctx, embed=embed)

        except Exception as e:
            logger.error(f"Error in profil command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    def _generate_nickname(self, points, crimes, prisons, is_imprisoned):
        """Generate a gangster nickname based on play style"""
        nicknames_rich = [
            "Le Banquier du Ghetto", "El Chapo des Banlieues", "Le Loup de la Street",
            "Midas du Béton", "Le Parrain des Cités", "Roi du Blanchiment"
        ]
        nicknames_criminal = [
            "L'Ombre des Ruelles", "Le Fantôme du 93", "Braqueur Né",
            "Le Pickpocket Légendaire", "Main de Velours", "L'Homme qui vole des sucettes aux bébés"
        ]
        nicknames_prison = [
            "Vétéran Prisonnier", "L'Éternel Détenu", "Le Roi de la Cour de Promenade",
            "Abonné Fleury-Mérogis", "Le Connaisseur de Cellules"
        ]
        nicknames_broke = [
            "Le SDF du Serveur", "Celui qui fouille les poubelles", "Le Clodo Magnifique",
            "N'a même pas de quoi s'acheter un kebab", "Le mendiant professionnel"
        ]
        nicknames_new = [
            "Le Petit Nouveau", "Fresh Off the Block", "Le Bleu du Quartier",
            "Celui qui comprend pas encore les règles"
        ]

        import random
        if is_imprisoned:
            return random.choice(nicknames_prison)
        elif points >= 50000:
            return random.choice(nicknames_rich)
        elif crimes >= 3:
            return random.choice(nicknames_criminal)
        elif points < 100:
            return random.choice(nicknames_broke)
        else:
            return random.choice(nicknames_new)

    # === COMMANDE KEN ===

    @commands.command(name='ken', aliases=['seduire', 'draguer'])
    async def ken_command(self, ctx, target: discord.Member = None, amount: int = 0):
        """Proposition coquine (PG-13, consentement requis) / Flirty proposal"""
        try:
            if not target:
                await ctx.send("❌ Mentionne quelqu'un! `!ken @user [montant]`")
                return
            if target.id == ctx.author.id:
                await ctx.send("😐 Tu veux te séduire toi-même ? Achète-toi un miroir.")
                return
            if target.bot:
                await ctx.send("🤖 Les bots n'ont pas de sentiments... pour l'instant.")
                return

            # Send consent request with buttons
            embed = discord.Embed(
                title="💋 Proposition Thugz",
                description=(
                    f"**{ctx.author.display_name}** veut tenter sa chance avec **{target.display_name}**"
                    + (f" et mise **{amount}** 💵 !" if amount > 0 else " !")
                    + f"\n\n{target.mention}, tu acceptes ?"
                ),
                color=0xFF69B4
            )

            # Use reactions for consent
            msg = await self._safe_send(ctx, embed=embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

            def check(reaction, user):
                return (
                    user.id == target.id
                    and str(reaction.emoji) in ["✅", "❌"]
                    and reaction.message.id == msg.id
                )

            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=60)
            except asyncio.TimeoutError:
                await ctx.send(f"⏰ {target.display_name} n'a pas répondu... c'est un vent magistral. 💨")
                return

            if str(reaction.emoji) == "❌":
                rejections = [
                    f"💔 {target.display_name} te met un vent cosmique.",
                    f"🚪 {target.display_name} te claque la porte au nez.",
                    f"😂 {target.display_name} éclate de rire et s'en va.",
                    f"👻 {target.display_name} fait semblant de ne pas te connaître.",
                    f"🗑️ {target.display_name} jette ta proposition à la poubelle.",
                ]
                await ctx.send(random.choice(rejections))
                return

            # Accepted! Generate outcome
            outcomes = [
                (f"💕 C'est un match ! {ctx.author.display_name} et {target.display_name} partent ensemble au kebab.", True),
                (f"🌹 {target.display_name} accepte un café... mais {ctx.author.display_name} renverse tout sur la table.", False),
                (f"💃 Soirée dansante ! Mais {ctx.author.display_name} se foule la cheville en essayant le moonwalk.", False),
                (f"🎬 Ciné ensemble ! {ctx.author.display_name} s'endort pendant le film. Romantique.", True),
                (f"🍕 Pizza à deux ! {ctx.author.display_name} mange 3/4 de la pizza. {target.display_name} n'est pas impressionné(e).", False),
                (f"🎵 {ctx.author.display_name} chante une sérénade... les voisins appellent la police.", False),
                (f"✨ Magie ! {ctx.author.display_name} et {target.display_name} deviennent le nouveau couple du serveur !", True),
                (f"🏖️ Balade au parc... un pigeon attaque {ctx.author.display_name}. {target.display_name} filme.", True),
            ]

            outcome_text, success = random.choice(outcomes)

            # Handle money if bet was made
            if amount > 0 and success:
                user_points = self.points.get_user_points(str(ctx.author.id))
                if user_points >= amount:
                    self.points.remove_points(str(ctx.author.id), amount)
                    self.points.add_points(str(target.id), amount, "Ken gift")
                    outcome_text += f"\n💵 {ctx.author.display_name} offre **{amount}** 💵 à {target.display_name} !"

            result_embed = discord.Embed(
                title="💋 Résultat",
                description=outcome_text,
                color=0xFF69B4 if success else 0x808080
            )
            await self._safe_send(ctx, embed=result_embed)

        except Exception as e:
            logger.error(f"Error in ken command: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    # ══════════════════════════════════════════════════════════════
    # ══  NOUVELLES COMMANDES THUGZ LIFE — PHASE 2              ══
    # ══════════════════════════════════════════════════════════════

    # ── !WESH — ÉVÉNEMENTS RANDOM WTF ──

    @commands.command(name='wesh', aliases=['wtf', 'random', 'destin'])
    @check_cooldown_and_limit('wesh')
    async def wesh_command(self, ctx):
        """Tente ta chance avec le destin de la street ! Événement 100% random et WTF."""
        try:
            user_id = str(ctx.author.id)
            user_data = self.points.get_user_data(user_id)
            current_points = int(user_data.get('points', 0))
            name = ctx.author.display_name

            # ── SCÉNARIOS WTF ──
            # Structure: (texte, type, valeur)
            #   type: "lose_pct" (perd % points), "lose_flat" (perd montant fixe),
            #         "gain_flat" (gagne montant), "gain_pct" (gagne % points),
            #         "prison" (envoyé en prison X secondes), "item" (gagne un item),
            #         "combo" (combinaison de plusieurs effets)
            
            SCENARIOS = [
                # ══ CATASTROPHES (pertes) ══
                (
                    f"🐂 **WESH !** Tu marches tranquille dans la rue quand un taureau s'échappe du Buffalo Grill "
                    f"et te fonce dessus à pleine vitesse ! Il te rentre ses cornes dans le... AÏEEE !! 🏥\n\n"
                    f"Tu te retrouves à l'hôpital avec 47 points de suture au fondement. "
                    f"Tu perds **50%** de tes thunes pour l'hospitalisation et t'es dans l'incapacité totale "
                    f"de faire quoi que ce soit pendant un moment.",
                    "combo", {"lose_pct": 50, "prison": 3600, "msg_extra": "💩 Tu ne peux même plus t'asseoir."}
                ),
                (
                    f"🕳️ **WESH !** Tu marches en regardant ton téléphone et tu tombes dans une bouche d'égout "
                    f"ouverte ! Tu atterris dans 2 mètres de merde littérale. 💀\n\n"
                    f"Les pompiers mettent 3h à te sortir. Tu perds ta dignité et **40%** de tes points "
                    f"(nettoyage + antibiotiques).",
                    "combo", {"lose_pct": 40, "prison": 1800, "msg_extra": "🤢 Tu sens la merde pendant 3 jours."}
                ),
                (
                    f"👵 **WESH !** Une mamie te demande de l'aide pour traverser la route. "
                    f"Tu l'aides gentiment... et elle te vole ton portefeuille pendant que tu regardes pas ! "
                    f"Elle sprinte comme Usain Bolt et disparaît dans le métro. 🏃‍♀️💨\n\n"
                    f"Tu perds **30%** de tes thunes. Braqué par mamie Lucette, 83 ans.",
                    "lose_pct", 30
                ),
                (
                    f"🚗 **WESH !** Tu te fais renverser par un Uber Eats en vélo qui grille un feu rouge. "
                    f"Le livreur ramasse ton kebab par terre, le met dans le sac et continue sa livraison. "
                    f"Toi tu restes au sol. 🍗💀\n\n"
                    f"Hospitalisation : **-{min(2000, current_points)}** 💵",
                    "lose_flat", min(2000, current_points)
                ),
                (
                    f"🐦 **WESH !** Un pigeon te chie en plein dans l'œil droit pendant que tu comptais "
                    f"tes billets devant le Franprix. Tu cries, tu fais tomber ton argent, "
                    f"et un gamin de 8 ans ramasse tout et s'enfuit en trottinette. 🛴\n\n"
                    f"Tu perds **25%** de tes points. Le pigeon revient pour le deuxième œil.",
                    "lose_pct", 25
                ),
                (
                    f"💥 **WESH !** Tu pètes un câble dans un McDo parce qu'ils ont oublié ta sauce. "
                    f"Tu fais un scandale, le manager appelle les flics, et tu finis au poste "
                    f"pour \"trouble à l'ordre public\". Pour une sauce barbecue. 🍟🚔",
                    "combo", {"lose_flat": 500, "prison": 2700, "msg_extra": "🍔 T'as même pas eu ta sauce."}
                ),
                (
                    f"🎰 **WESH !** Tu trouves un ticket à gratter par terre. Tu le grattes... "
                    f"c'est marqué \"GAGNANT 50 000€\" ! Tu cours au bureau de tabac... "
                    f"mais le ticket est périmé depuis 2019. Le buraliste se moque de toi "
                    f"et poste la vidéo sur TikTok. 📱😂\n\n"
                    f"Tu perds **500** 💵 de honte (tu payes un Uber pour fuir le quartier).",
                    "lose_flat", 500
                ),
                (
                    f"🦝 **WESH !** Un raton laveur sort de la poubelle et te mord la main ! "
                    f"Tu vas aux urgences, le médecin te dit \"c'est rien\" mais tu dois "
                    f"payer **35%** de tes points en frais d'hôpital. En sortant, le raton laveur "
                    f"t'attend devant la porte. Il a ramené ses potes. 🦝🦝🦝",
                    "lose_pct", 35
                ),
                (
                    f"🧲 **WESH !** T'essayes de voler un truc à Décathlon mais t'as oublié "
                    f"l'antivol magnétique. L'alarme sonne, le vigile te plaque au sol "
                    f"devant 200 personnes. Ta mère était dans le magasin. 😱",
                    "combo", {"lose_flat": 1000, "prison": 3600, "msg_extra": "📞 Ta daronne t'appelle 47 fois."}
                ),
                (
                    f"🌊 **WESH !** Tu fais le malin au bord de la Seine, tu glisses et tu tombes "
                    f"dedans. Un touriste japonais te filme et la vidéo fait 2M de vues. "
                    f"Tu perds **20%** de tes thunes en habits foutus + dignité.",
                    "lose_pct", 20
                ),

                # ══ BONNES FORTUNES (gains) ══
                (
                    f"💰 **WESH !** Tu trouves un sac Chanel par terre dans le métro ! "
                    f"Dedans y'a un portefeuille avec du cash. Tu regardes à gauche, "
                    f"à droite... personne. C'est ton jour de chance, frère ! 🎒✨\n\n"
                    f"Tu gagnes **3000** 💵 !",
                    "gain_flat", 3000
                ),
                (
                    f"🎵 **WESH !** Tu chantes du Jul dans le métro et les gens kiffent ! "
                    f"Ils te filent des sous ! Un producteur dans le wagon te donne sa carte ! "
                    f"(Tu la perdras demain mais aujourd'hui c'est la fête) 🎤\n\n"
                    f"Tu gagnes **1500** 💵 en pourboires !",
                    "gain_flat", 1500
                ),
                (
                    f"🐕 **WESH !** Tu sauves un chien qui allait se faire écraser ! "
                    f"Le proprio c'est un milliardaire ! Il te file un billet de 500€ "
                    f"et te dit \"Merci, t'es un vrai\". Le chien te lèche la face. 🐶💕\n\n"
                    f"Tu gagnes **5000** 💵 ! La bonté ça paye !",
                    "gain_flat", 5000
                ),
                (
                    f"🏆 **WESH !** Tu participes à un concours de bras de fer dans un bar PMU. "
                    f"Tu éclates TOUT LE MONDE. Le patron du bar te donne le jackpot "
                    f"et t'offre un kebab gratuit à vie (enfin, pour la semaine). 💪\n\n"
                    f"Tu gagnes **2500** 💵 !",
                    "gain_flat", 2500
                ),
                (
                    f"🧳 **WESH !** Tu croises un dealer qui se fait courser par les keufs. "
                    f"Il te lance sa sacoche en courant et crie \"GARDE-LA FRÈRE !\". "
                    f"Dedans y'a du cash. Que du cash. 💼💸\n\n"
                    f"Tu gagnes **4000** 💵 ! (Fait pas le malin, planque bien).",
                    "gain_flat", 4000
                ),
                (
                    f"🎰 **WESH !** Le buraliste du coin s'est trompé et t'a donné un ticket "
                    f"à gratter premium au lieu du Millionnaire. Tu grattes... "
                    f"**JACKPOT !!** Bon c'est pas 1 million mais c'est déjà ça ! 🎉\n\n"
                    f"Tu gagnes **50%** de tes points actuels en bonus !",
                    "gain_pct", 50
                ),
                (
                    f"🍀 **WESH !** Tu trouves un trèfle à quatre feuilles devant le Lidl. "
                    f"Juste après, tu trouves 50€ par terre. Puis un billet de concert gratuit. "
                    f"Puis t'apprends que ton PV de stationnement a été annulé. C'est ta journée ! ☘️\n\n"
                    f"Tu gagnes **2000** 💵 !",
                    "gain_flat", 2000
                ),

                # ══ ITEMS GRATUITS ══
                (
                    f"🔪 **WESH !** Un mec louche dans une ruelle te donne un couteau "
                    f"\"cadeau de bienvenue dans le quartier, cousin\". Tu sais pas trop "
                    f"quoi en penser mais bon, c'est gratuit. 🤷\n\n"
                    f"Tu obtiens un **Couteau de Rue** !",
                    "item", "couteau"
                ),
                (
                    f"💊 **WESH !** Tu trouves une boîte de médicaments dans les toilettes "
                    f"du McDo. C'est des potions de guérison... enfin du Doliprane quoi. "
                    f"Mais dans le monde Thugz, ça compte ! 💉\n\n"
                    f"Tu obtiens une **Potion de Guérison** !",
                    "item", "potion_soin"
                ),
                (
                    f"🎭 **WESH !** Un type déguisé en Spider-Man sur les Champs-Élysées "
                    f"te file une cagoule. \"Tiens frère, j'en ai trop.\" "
                    f"Bizarre mais utile pour les braquages. 🕷️\n\n"
                    f"Tu obtiens une **Cagoule de Braqueur** !",
                    "item", "cagoule"
                ),
                (
                    f"🧿 **WESH !** Une voyante au marché aux puces te donne une amulette "
                    f"gratuite. \"Tu en auras besoin, mon fils\", elle dit avec un sourire "
                    f"flippant. Tu la prends quand même. 🔮\n\n"
                    f"Tu obtiens une **Amulette de Chance** !",
                    "item", "amulette"
                ),

                # ══ SITUATIONS MIXTES ══
                (
                    f"🚨 **WESH !** Les flics débarquent dans le bar où tu bois tranquille. "
                    f"Contrôle d'identité. T'as rien fait mais ils trouvent un vieux PV "
                    f"impayé de 2022. Direction le poste. Au moins y'a le wifi. 📶\n\n"
                    f"Tu perds **800** 💵 d'amende et tu fais un tour au poste.",
                    "combo", {"lose_flat": 800, "prison": 1800, "msg_extra": "🚔 Au moins la cellule est propre."}
                ),
                (
                    f"🐈 **WESH !** Un chat noir traverse devant toi. Tu le suis par curiosité. "
                    f"Il te mène à un petit sac de cash abandonné dans un buisson ! "
                    f"MAIS en te relevant tu te prends un poteau en pleine face. 🤕\n\n"
                    f"Tu gagnes **1000** 💵 mais tu perds **300** 💵 en soins (le nez, quoi).",
                    "combo", {"gain_flat": 1000, "lose_flat": 300, "msg_extra": "🐱 Le chat t'a regardé avec mépris."}
                ),
                (
                    f"🎪 **WESH !** Tu te fais recruter comme figurant dans un clip de rap ! "
                    f"Tu danses comme un ouf, le rappeur kiffe, il te file du cash. "
                    f"Par contre ta danse est devenue un meme viral... 📱😬\n\n"
                    f"Tu gagnes **2000** 💵 mais tu perds ta dignité (encore).",
                    "gain_flat", 2000
                ),
                (
                    f"🍕 **WESH !** Tu commandes une pizza. Le livreur se trompe et te "
                    f"livre 15 pizzas à la place d'une seule. Tu les revends au quartier ! "
                    f"Par contre Domino's te facture quand même. 🍕🍕🍕\n\n"
                    f"Tu gagnes **800** 💵 (revente) mais perds **200** 💵 (facture).",
                    "combo", {"gain_flat": 800, "lose_flat": 200, "msg_extra": "🍕 T'en as gardé une pour toi."}
                ),
                (
                    f"🎤 **WESH !** Tu croises Booba dans la rue. Tu lui demandes un selfie. "
                    f"Il te regarde de haut en bas et dit \"T'as une tête de thug, toi\". "
                    f"Il te file un billet et s'en va. Tu planes pendant 3 jours. 🔥\n\n"
                    f"Tu gagnes **3500** 💵 et un souvenir pour la vie !",
                    "gain_flat", 3500
                ),
                (
                    f"🗑️ **WESH !** Tu fais les poubelles derrière le Monoprix (la honte) "
                    f"et tu trouves un iPhone 15 qui marche ! Tu le revends sur Leboncoin "
                    f"en 10 minutes. La street, c'est aussi du recyclage. ♻️\n\n"
                    f"Tu gagnes **4500** 💵 !",
                    "gain_flat", 4500
                ),
                (
                    f"💀 **WESH !** Tu te prends les pieds dans un câble électrique au marché. "
                    f"Tu fais tomber 3 stands de fruits. Les vendeurs te coursent sur 500m. "
                    f"T'es rapide mais pas assez. Tu payes les dégâts. 🍎🍊🍋\n\n"
                    f"Tu perds **1500** 💵 et ta capacité à acheter des fruits ici.",
                    "lose_flat", 1500
                ),
            ]

            # ── Tirer un scénario random ──
            scenario_text, effect_type, effect_value = random.choice(SCENARIOS)

            # ── CHECK POTION DE GUÉRISON ──
            is_negative = effect_type in ("lose_pct", "lose_flat", "prison") or (
                effect_type == "combo" and any(k in effect_value for k in ("lose_pct", "lose_flat", "prison"))
            )
            if is_negative and self._has_item_effect(user_id, "wesh", "heal_wesh"):
                item_name = self._consume_item(user_id, "wesh", "heal_wesh")
                embed_heal = discord.Embed(
                    title="💊 POTION DE GUÉRISON ACTIVÉE !",
                    description=f"{scenario_text}\n\n**MAIS** ta **{item_name}** annule tous les effets negatifs !\nTu t'en sors sans degats. Ouf !\n*({item_name} consommee)*",
                    color=0x00FF00
                )
                await self._safe_send(ctx, embed=embed_heal)
                return

            # ── Appliquer les effets ──
            embed = discord.Embed(
                title="🌀 WESH — Le Destin Frappe !",
                description=scenario_text,
                color=0xFF4500
            )
            embed.set_footer(text=f"Joueur: {name}")

            result_lines = []

            if effect_type == "lose_pct":
                loss = int(current_points * effect_value / 100)
                if loss > 0:
                    self.points.remove_points(user_id, loss)
                    result_lines.append(f"💸 Tu perds **{loss:,}** 💵 ({effect_value}%)")

            elif effect_type == "lose_flat":
                loss = min(int(effect_value), current_points)
                if loss > 0:
                    self.points.remove_points(user_id, loss)
                    result_lines.append(f"💸 Tu perds **{loss:,}** 💵")

            elif effect_type == "gain_flat":
                gain = int(effect_value)
                self.points.add_points(user_id, gain, "Wesh event")
                result_lines.append(f"💰 Tu gagnes **{gain:,}** 💵 !")

            elif effect_type == "gain_pct":
                gain = int(current_points * effect_value / 100)
                if gain > 0:
                    self.points.add_points(user_id, gain, "Wesh event")
                    result_lines.append(f"💰 Tu gagnes **{gain:,}** 💵 ({effect_value}% bonus) !")

            elif effect_type == "prison":
                duration = int(effect_value)
                import time as _time
                self.points.database.set_prison_time(user_id, _time.time() + duration)
                mins = duration // 60
                result_lines.append(f"⛓️ Tu es enfermé pour **{mins} minutes** !")

            elif effect_type == "item":
                item_id = str(effect_value)
                self.points.database.add_item(user_id, item_id)
                from config import SHOP_ITEMS
                item_name = SHOP_ITEMS.get(item_id, {}).get('name', item_id)
                result_lines.append(f"🎁 Tu obtiens : **{item_name}** !")

            elif effect_type == "combo":
                vals = effect_value
                if "lose_pct" in vals:
                    loss = int(current_points * vals["lose_pct"] / 100)
                    if loss > 0:
                        self.points.remove_points(user_id, loss)
                        result_lines.append(f"💸 Perdu **{loss:,}** 💵 ({vals['lose_pct']}%)")
                if "lose_flat" in vals:
                    loss = min(int(vals["lose_flat"]), current_points)
                    if loss > 0:
                        self.points.remove_points(user_id, loss)
                        result_lines.append(f"💸 Perdu **{loss:,}** 💵")
                if "gain_flat" in vals:
                    gain = int(vals["gain_flat"])
                    self.points.add_points(user_id, gain, "Wesh event")
                    result_lines.append(f"💰 Gagné **{gain:,}** 💵")
                if "prison" in vals:
                    duration = int(vals["prison"])
                    import time as _time
                    self.points.database.set_prison_time(user_id, _time.time() + duration)
                    mins = duration // 60
                    result_lines.append(f"⛓️ Enfermé **{mins} min** !")
                if "item" in vals:
                    self.points.database.add_item(user_id, str(vals["item"]))
                    result_lines.append(f"🎁 Item obtenu !")
                if "msg_extra" in vals:
                    result_lines.append(vals["msg_extra"])

            # Ajouter le résumé
            new_points = int(self.points.get_user_data(user_id).get('points', 0))
            result_lines.append(f"\n🏦 Solde actuel: **{new_points:,}** 💵")
            embed.add_field(name="📊 Bilan", value="\n".join(result_lines), inline=False)

            await self._safe_send(ctx, embed=embed)

        except Exception as e:
            logger.error(f"Error in wesh command: {e}", exc_info=True)
            await ctx.send("❌ Wesh, y'a eu un bug.")

    # ── !PICKPOCKET — VOL RAPIDE PETIT GAIN ──

    @commands.command(name='pickpocket', aliases=['pp', 'chourrer', 'piquer'])
    @check_cooldown_and_limit('pickpocket')
    async def pickpocket_command(self, ctx, target: discord.Member = None):
        """Faire les poches de quelqu'un discrètement (petit gain, petit risque)"""
        try:
            if not target:
                await ctx.send("❌ Mentionne ta victime ! `!pickpocket @user`")
                return
            if target.id == ctx.author.id:
                await ctx.send("🤦 Tu fouilles tes propres poches ? Tu trouves un vieux mouchoir.")
                return
            if target.bot:
                await ctx.send("🤖 Les bots n'ont pas de poches.")
                return

            user_id = str(ctx.author.id)
            target_id = str(target.id)
            name = ctx.author.display_name
            target_name = target.display_name

            intros = [
                f"🤏 {name} se glisse discrètement derrière {target_name}...",
                f"👋 {name} fait semblant de serrer la main de {target_name}...",
                f"🚶 {name} bouscule \"accidentellement\" {target_name} dans le métro...",
            ]
            await ctx.send(random.choice(intros))
            await asyncio.sleep(1.5)

            # Item bonus attaquant (lockpick, amulette)
            base_rate = 0.55
            rob_bonus = self._get_item_bonus(user_id, "pickpocket", "rob_bonus")
            luck_bonus = self._get_item_bonus(user_id, "pickpocket", "global_luck")
            success_rate = min(0.90, base_rate + rob_bonus + luck_bonus)
            gain_min, gain_max = 20, 300

            # Check défense victime: spray au poivre
            defense = self._find_defense_item(target_id, "defense_pickpocket")
            if defense and random.random() < defense["cfg"].get("effect", {}).get("counter_pickpocket", 0):
                counter_amt = random.randint(100, 400)
                attacker_pts = int(self.points.get_user_points(user_id))
                counter_amt = min(counter_amt, attacker_pts)
                if counter_amt > 0:
                    self.points.remove_points(user_id, counter_amt)
                    self.points.add_points(target_id, counter_amt, "Counter pickpocket (spray)")
                if defense["cfg"].get("consumable"):
                    self.points.db.remove_item(target_id, defense["item_id"])
                await ctx.send(f"🌶️ **SPRAY AU POIVRE !** {target_name} t'asperge en pleine face ! Le pickpocket echoue et tu perds **{counter_amt}** 💵 ! *(Spray au Poivre consomme)*")
                return

            if random.random() < success_rate:
                amount = random.randint(gain_min, gain_max)
                target_points = self.points.get_user_points(target_id)
                amount = min(amount, target_points)
                if amount <= 0:
                    await ctx.send(f"😅 {target_name} est fauché ! Y'a rien à prendre.")
                    return
                self.points.remove_points(target_id, amount)
                self.points.add_points(user_id, amount, f"Pickpocket {target_name}")
                results = [
                    f"✅ Tes doigts de fée ont chopé **{amount}** 💵 dans la poche de {target_name} !",
                    f"✅ Ni vu ni connu ! **{amount}** 💵 subtilisés à {target_name} !",
                    f"✅ Technique parfaite ! {target_name} n'a rien senti. **{amount}** 💵 pour toi !",
                ]
                await ctx.send(random.choice(results))
            else:
                fails = [
                    f"❌ {target_name} te chope la main dans sa poche ! \"EH OH, TU FAIS QUOI LÀ ?!\"",
                    f"❌ Tu trébuches en essayant et tu tombes sur {target_name}. Très discret.",
                    f"❌ Y'avait un trou dans sa poche. Tu as juste touché sa cuisse. Malaise. 😬",
                    f"❌ {target_name} avait un portefeuille-piège avec un ressort. CLAC ! Tes doigts ! 🤕",
                ]
                # Petite amende si pris
                fine = random.randint(50, 200)
                self.points.remove_points(user_id, min(fine, int(self.points.get_user_points(user_id))))
                await ctx.send(random.choice(fails) + f"\nTu perds **{fine}** 💵 de honte.")

        except Exception as e:
            logger.error(f"Error in pickpocket: {e}", exc_info=True)
            await ctx.send("❌ Une erreur s'est produite.")

    # ── !DEALER — VENTE DE DROGUE ──

    @commands.command(name='dealer', aliases=['deal', 'vendre', 'trafic'])
    @check_cooldown_and_limit('dealer')
    async def dealer_command(self, ctx):
        """Tente un deal de rue. Gros gains possibles mais attention aux flics !"""
        try:
            user_id = str(ctx.author.id)
            name = ctx.author.display_name

            intros = random.choice(COMMAND_NARRATIONS.get('deal', [
                f"🕶️ {name} attend son contact dans une ruelle sombre..."
            ])).format(user=name, target="le client")
            await ctx.send(intros)
            await asyncio.sleep(2)

            # Résultats possibles
            roll = random.random()

            # Item effects: flingue augmente le risque police, cagoule réduit
            police_risk_extra = self._get_item_bonus(user_id, "dealer", "police_risk")
            stealth_bonus = self._get_item_bonus(user_id, "dealer", "stealth_on_fail")
            arrest_threshold = max(0.02, 0.10 + police_risk_extra - stealth_bonus)

            if roll < arrest_threshold:  # ~10% — Arrestation (modifié par items)
                import time as _time
                prison_time = random.randint(1800, 7200)
                self.points.database.set_prison_time(user_id, _time.time() + prison_time)
                fine = random.randint(500, 2000)
                self.points.remove_points(user_id, min(fine, int(self.points.get_user_points(user_id))))
                mins = prison_time // 60
                await ctx.send(
                    f"🚔 **LES STUPS !** Les flics t'ont chopé en flagrant délit !\n"
                    f"💸 Amende de **{fine}** 💵 + ⛓️ **{mins} min** de prison !"
                )
            elif roll < 0.25:  # 15% — Deal foireux
                loss = random.randint(200, 800)
                self.points.remove_points(user_id, min(loss, int(self.points.get_user_points(user_id))))
                fails = [
                    f"❌ Le client t'a filé des faux billets ! Tu perds **{loss}** 💵 !",
                    f"❌ T'as marché sur la marchandise en courant. Perte sèche de **{loss}** 💵.",
                    f"❌ Un autre dealer t'a piqué ton spot ET ton stock. **-{loss}** 💵.",
                ]
                await ctx.send(random.choice(fails))
            elif roll < 0.55:  # 30% — Petit deal
                gain = random.randint(300, 1000)
                self.points.add_points(user_id, gain, "Deal")
                await ctx.send(f"✅ Deal rapide et discret. Tu empoche **{gain}** 💵. Ni vu ni connu. 🤫")
            elif roll < 0.85:  # 30% — Gros deal
                gain = random.randint(1500, 4000)
                self.points.add_points(user_id, gain, "Gros deal")
                await ctx.send(
                    f"💰 **GROS DEAL !** Le client était un vrai, il a tout pris d'un coup !\n"
                    f"Tu empoche **{gain}** 💵 ! Pas mal pour une soirée. 🤑"
                )
            else:  # 15% — JACKPOT
                gain = random.randint(5000, 10000)
                self.points.add_points(user_id, gain, "Deal jackpot")
                await ctx.send(
                    f"🌟 **JACKPOT DEALER !** T'as écoulé tout le stock d'un coup à un riche "
                    f"businessman en Porsche ! Il a même laissé un pourboire !\n"
                    f"Tu gagnes **{gain}** 💵 !! Le game, c'est toi. 🔥"
                )

        except Exception as e:
            logger.error(f"Error in dealer: {e}", exc_info=True)
            await ctx.send("❌ Le deal a foiré techniquement.")

    # ── !GRAFFITI — TAGGER POUR DE LA REP ──

    @commands.command(name='graffiti', aliases=['tag', 'tagger', 'graff'])
    @check_cooldown_and_limit('graffiti')
    async def graffiti_command(self, ctx):
        """Tague un mur du quartier pour gagner du respect et des thunes"""
        try:
            user_id = str(ctx.author.id)
            name = ctx.author.display_name

            await ctx.send(f"🎨 {name} sort ses bombes de peinture et cherche un mur...")
            await asyncio.sleep(1.5)

            roll = random.random()

            if roll < 0.15:  # Pris par les flics
                fine = random.randint(300, 1000)
                self.points.remove_points(user_id, min(fine, int(self.points.get_user_points(user_id))))
                await ctx.send(
                    f"🚔 Les flics t'ont chopé en plein tag ! \"C'est de l'art !\" tu cries "
                    f"pendant qu'ils te mettent les menottes.\n💸 Amende: **{fine}** 💵"
                )
            elif roll < 0.30:  # Tag nul
                await ctx.send(
                    f"😐 T'as dessiné un truc... c'est moche. Les gamins du quartier "
                    f"se moquent de toi. \"C'est censé être quoi ?\" Aucun gain. Aucune dignité."
                )
            elif roll < 0.70:  # Bon tag
                gain = random.randint(200, 800)
                self.points.add_points(user_id, gain, "Graffiti")
                tags = [
                    f"✅ Ton tag \"THUGZ 4 LIFE\" fait sensation ! Les gens prennent des photos. **+{gain}** 💵",
                    f"✅ Fresque magnifique ! Un galeriste passe et te propose un collab. **+{gain}** 💵",
                    f"✅ Tag stylé ! Le quartier te respecte. **+{gain}** 💵 de rep street.",
                ]
                await ctx.send(random.choice(tags))
            else:  # Chef-d'œuvre
                gain = random.randint(1500, 3000)
                self.points.add_points(user_id, gain, "Graffiti masterpiece")
                await ctx.send(
                    f"🌟 **CHEF-D'ŒUVRE !** Ton graff est tellement beau que la mairie "
                    f"décide de le garder ! Un journaliste te contacte. T'es une star locale !\n"
                    f"💰 **+{gain}** 💵 !"
                )

        except Exception as e:
            logger.error(f"Error in graffiti: {e}", exc_info=True)
            await ctx.send("❌ La bombe a explosé (pas la bonne).")

    # ── !MENDIER — MENDICITÉ LOW RISK ──

    @commands.command(name='mendier', aliases=['beg', 'quemander', 'manche'])
    @check_cooldown_and_limit('mendier')
    async def mendier_command(self, ctx):
        """Faire la manche dans le quartier. C'est pas glorieux mais ça nourrit."""
        try:
            user_id = str(ctx.author.id)
            name = ctx.author.display_name

            scenarios = [
                (f"🧎 {name} s'assoit devant le Monoprix avec un carton...\n"
                 f"Un businessman te file **{{gain}}** 💵 sans te regarder.", 50, 300),
                (f"🎸 {name} joue de la guitare (mal) dans le métro...\n"
                 f"Les gens te filent **{{gain}}** 💵 pour que tu t'arrêtes.", 30, 200),
                (f"😢 {name} raconte une histoire triste à un touriste...\n"
                 f"Il te donne **{{gain}}** 💵 et un câlin. Émouvant.", 100, 500),
                (f"🐕 {name} emprunte un chien mignon et fait la manche...\n"
                 f"Le chien est plus populaire que toi. **{{gain}}** 💵 récoltés.", 80, 400),
                (f"🤹 {name} essaie de jongler avec des oranges au feu rouge...\n"
                 f"Un automobiliste mort de rire te lance **{{gain}}** 💵.", 20, 150),
                (f"😐 {name} tend la main... Un gamin lui donne un bonbon.\n"
                 f"C'est tout. Pas d'argent. Juste un bonbon à la fraise.", 0, 0),
                (f"🗣️ {name} fait la manche mais un autre SDF te dit \"C'est MON spot !\"\n"
                 f"Vous vous battez avec des cartons. Tu perds. **0** 💵.", 0, 0),
            ]

            scenario_text, gain_min, gain_max = random.choice(scenarios)
            gain = random.randint(gain_min, gain_max) if gain_max > 0 else 0

            if gain > 0:
                self.points.add_points(user_id, gain, "Mendicité")
            await ctx.send(scenario_text.format(gain=gain))

        except Exception as e:
            logger.error(f"Error in mendier: {e}", exc_info=True)
            await ctx.send("❌ Même la mendicité bug.")

    # ── !FOUILLER — CHERCHER DES TRUCS ──

    @commands.command(name='fouiller', aliases=['search', 'chercher', 'scav'])
    @check_cooldown_and_limit('fouiller')
    async def fouiller_command(self, ctx):
        """Fouiller les alentours pour trouver de l'argent, des items ou des embrouilles"""
        try:
            user_id = str(ctx.author.id)
            name = ctx.author.display_name

            await ctx.send(f"🔍 {name} fouille les alentours...")
            await asyncio.sleep(1.5)

            roll = random.random()

            if roll < 0.10:  # Trouve un item
                items_trouvables = ["couteau", "potion_soin", "bombe_lacrymo", "speed", "pied_de_biche"]
                item_id = random.choice(items_trouvables)
                self.points.database.add_item(user_id, item_id)
                from config import SHOP_ITEMS
                item_name = SHOP_ITEMS.get(item_id, {}).get("name", item_id)
                await ctx.send(f"🎁 Tu trouves un objet dans un buisson : **{item_name}** ! Ajouté à ton inventaire.")

            elif roll < 0.35:  # Trouve du cash
                gain = random.randint(100, 1500)
                self.points.add_points(user_id, gain, "Fouille")
                lieux = ["derrière une poubelle", "sous un banc", "dans une bouche d'aération",
                         "dans un vieux jean abandonné", "sous un plot de chantier"]
                await ctx.send(f"💰 Tu trouves **{gain}** 💵 {random.choice(lieux)} ! Pas mal !")

            elif roll < 0.55:  # Rien du tout
                await ctx.send(random.choice([
                    f"😐 Tu trouves... rien. Juste un vieux préservatif et un ticket de métro périmé.",
                    f"🦗 Tu fouilles pendant 20 min et tu trouves un grillon mort. Bravo.",
                    f"🧻 Tu trouves un rouleau de PQ. C'est toujours utile mais ça rapporte 0 💵.",
                    f"📰 Tu trouves un journal de 2019. L'horoscope disait \"journée favorable\". Menteur.",
                ]))

            elif roll < 0.75:  # Embrouille
                loss = random.randint(100, 500)
                self.points.remove_points(user_id, min(loss, int(self.points.get_user_points(user_id))))
                await ctx.send(random.choice([
                    f"🐀 Tu fouilles dans une poubelle et un RAT te mord ! Hôpital. **-{loss}** 💵.",
                    f"😡 Tu fouilles le sac de quelqu'un... qui était pas abandonné. Son propriétaire "
                    f"t'a mis une droite. **-{loss}** 💵 en soins.",
                    f"🕸️ Tu mets ta main dans un trou et tu te fais piquer par une araignée. "
                    f"**-{loss}** 💵 de pharmacie.",
                ]))
            else:  # Trésor
                gain = random.randint(2000, 5000)
                self.points.add_points(user_id, gain, "Trésor fouille")
                await ctx.send(
                    f"🏆 **TRÉSOR !** Tu trouves une planque oubliée avec du cash dedans !\n"
                    f"Quelqu'un a dû cacher ça y'a longtemps. C'est à toi maintenant !\n"
                    f"💰 **+{gain}** 💵 !!"
                )

        except Exception as e:
            logger.error(f"Error in fouiller: {e}", exc_info=True)
            await ctx.send("❌ Erreur pendant la fouille.")

    # ── !CARJACK — VOL DE VOITURE ──

    @commands.command(name='carjack', aliases=['volvoiture', 'jackcar'])
    @check_cooldown_and_limit('carjack')
    async def carjack_command(self, ctx):
        """Tente de voler une voiture ! Gros risque, gros gain."""
        try:
            user_id = str(ctx.author.id)
            name = ctx.author.display_name

            voitures = [
                ("Twingo cabossée", 200, 500, 0.70),
                ("Clio de location", 500, 1200, 0.55),
                ("BMW Série 3", 1500, 3500, 0.40),
                ("Mercedes AMG", 3000, 7000, 0.30),
                ("Porsche Cayenne", 5000, 12000, 0.20),
                ("Lamborghini du dealer", 10000, 25000, 0.10),
            ]

            voiture_name, gain_min, gain_max, success_rate = random.choice(voitures)
            await ctx.send(f"🚗 {name} repère une **{voiture_name}** garée dans la rue...")
            await asyncio.sleep(2)

            # Item bonus (pied de biche, amulette, cagoule)
            cj_bonus = self._get_item_bonus(user_id, "carjack", "carjack_bonus")
            luck_bonus = self._get_item_bonus(user_id, "carjack", "global_luck")
            success_rate = min(0.90, success_rate + cj_bonus + luck_bonus)

            if random.random() < success_rate:
                gain = random.randint(gain_min, gain_max)
                self.points.add_points(user_id, gain, f"Carjack {voiture_name}")
                await ctx.send(
                    f"✅ **CARJACK RÉUSSI !** Tu démarres la **{voiture_name}** en 10 secondes "
                    f"et tu files ! Revendue au receleur pour **{gain:,}** 💵 ! 🏎️💨"
                )
            else:
                # Échec — prison ou amende
                if random.random() < 0.5:
                    import time as _time
                    prison_time = random.randint(3600, 10800)
                    self.points.database.set_prison_time(user_id, _time.time() + prison_time)
                    mins = prison_time // 60
                    await ctx.send(
                        f"🚔 **GRILLÉ !** L'alarme de la **{voiture_name}** s'est déclenchée ! "
                        f"Les flics t'embarquent direct !\n⛓️ **{mins} min** de prison !"
                    )
                else:
                    fine = random.randint(500, 3000)
                    self.points.remove_points(user_id, min(fine, int(self.points.get_user_points(user_id))))
                    fails = [
                        f"❌ Le proprio de la **{voiture_name}** était dans la voiture. "
                        f"Il t'a défoncé. **-{fine}** 💵 en soins.",
                        f"❌ T'as cassé la vitre mais l'antidémarrage t'a bloqué. "
                        f"Un passant a filmé ta plaque. **-{fine}** 💵 d'amende.",
                        f"❌ T'as réussi à démarrer mais tu t'es pris un poteau 30m plus loin. "
                        f"**-{fine}** 💵.",
                    ]
                    await ctx.send(random.choice(fails))

        except Exception as e:
            logger.error(f"Error in carjack: {e}", exc_info=True)
            await ctx.send("❌ Le moteur a calé (le code aussi).")

    # ── !INSULTER — TRASH TALK POUR DES THUNES ──

    @commands.command(name='insulter', aliases=['clash', 'trashtalk', 'embrouille'])
    @check_cooldown_and_limit('insulter')
    async def insulter_command(self, ctx, target: discord.Member = None):
        """Clash quelqu'un ! Si t'es bon, tu gagnes du respect et des 💵"""
        try:
            if not target:
                await ctx.send("❌ Faut mentionner qui tu veux clasher ! `!insulter @user`")
                return
            if target.id == ctx.author.id:
                await ctx.send("🪞 Tu t'insultes devant le miroir ? C'est triste, frère.")
                return
            if target.bot:
                await ctx.send("🤖 \"01001110 01001111\" — Le bot s'en fout de tes insultes.")
                return

            user_id = str(ctx.author.id)
            name = ctx.author.display_name
            target_name = target.display_name

            # Clashs pré-faits (pas de contenu vraiment méchant, c'est du jeu)
            clashs = [
                (f"🗣️ {name} à {target_name}: \"T'es tellement fauché que quand tu vas au "
                 f"McDo, tu regardes que le menu enfant.\"", True),
                (f"🗣️ {name} à {target_name}: \"T'es tellement lent que quand tu cours, "
                 f"les escargots te doublent.\"", True),
                (f"🗣️ {name} essaie de clasher {target_name}... mais bégaie et dit "
                 f"\"Tu... tu... euh...\" Tout le monde rigole de TOI.", False),
                (f"🗣️ {name} à {target_name}: \"Ton style c'est un mix entre Wish et "
                 f"les vêtements perdus à la piscine.\"", True),
                (f"🗣️ {name} à {target_name}: \"T'es le genre de personne qui met "
                 f"du ketchup sur les pâtes carbo.\"", True),
                (f"🗣️ {name} essaie d'insulter {target_name} mais se mord la langue. "
                 f"Littéralement. Ça fait mal. 🩸", False),
                (f"🗣️ {name} à {target_name}: \"Même Google peut pas trouver "
                 f"quelque chose de bien à dire sur toi.\"", True),
                (f"🗣️ {name} à {target_name}: \"T'as l'air de quelqu'un qui "
                 f"applaudit quand l'avion atterrit.\"", True),
                (f"🗣️ {name} lance un clash mais {target_name} répond encore mieux ! "
                 f"Public: \"OOOOOOH !\" C'est toi qui te fais humilier.", False),
            ]

            clash_text, success = random.choice(clashs)
            await ctx.send(clash_text)

            if success:
                gain = random.randint(100, 500)
                self.points.add_points(user_id, gain, f"Clash {target_name}")
                await ctx.send(f"🏆 Le public est mort de rire ! **+{gain}** 💵 de respect !")
            else:
                loss = random.randint(50, 300)
                self.points.remove_points(user_id, min(loss, int(self.points.get_user_points(user_id))))
                await ctx.send(f"💀 T'as perdu le clash... **-{loss}** 💵 de dignité.")

        except Exception as e:
            logger.error(f"Error in insulter: {e}", exc_info=True)
            await ctx.send("❌ Bug d'embrouille.")

    # ── !CASINO — ROULETTE SIMPLIFIÉE ──

    @commands.command(name='casino', aliases=['roulette_thugz', 'jouer'])
    @check_cooldown_and_limit('casino')
    async def casino_command(self, ctx, mise: int = None):
        """Joue au casino du quartier ! Mise minimum 50 💵"""
        try:
            if not mise or mise < 50:
                await ctx.send("❌ Mise minimum **50** 💵 ! `!casino 200`")
                return
            if mise > 10000:
                await ctx.send("❌ Le casino du quartier accepte max **10 000** 💵 par partie.")
                return

            user_id = str(ctx.author.id)
            current = int(self.points.get_user_points(user_id))
            if current < mise:
                await ctx.send(f"❌ T'as que **{current:,}** 💵, tu peux pas miser {mise:,} !")
                return

            name = ctx.author.display_name
            await ctx.send(f"🎰 {name} entre dans le casino du quartier et mise **{mise:,}** 💵...")
            await asyncio.sleep(2)

            # Item bonus (amulette = luck, porte_bonheur = double gains)
            luck_bonus = self._get_item_bonus(user_id, "casino", "global_luck")
            has_porte_bonheur = self._has_item_effect(user_id, "casino", "double_gambling")
            roll = random.random()
            # Amulette: réduit la zone de perte
            loss_threshold = max(0.15, 0.40 - luck_bonus)

            if roll < loss_threshold:  # ~40% — Perdu (réduit par amulette)
                self.points.remove_points(user_id, mise)
                await ctx.send(f"❌ **Perdu !** La bille tombe sur le mauvais numéro. **-{mise:,}** 💵. Le croupier sourit.")
            elif roll < 0.65:  # 25% — Petite win (x1.5)
                gain = int(mise * 1.5)
                if has_porte_bonheur:
                    gain *= 2
                    self._consume_item(user_id, "casino", "double_gambling")
                profit = gain - mise
                self.points.add_points(user_id, profit, "Casino win")
                pb_msg = " 🍀 *(Trèfle Porte-Bonheur: gains doublés ! Consommé)*" if has_porte_bonheur else ""
                await ctx.send(f"✅ Pas mal ! Tu remporte **{gain:,}** 💵 ! (profit: **+{profit:,}** 💵){pb_msg}")
            elif roll < 0.80:  # 15% — Bonne win (x2)
                gain = mise * 2
                profit = gain - mise
                self.points.add_points(user_id, profit, "Casino big win")
                await ctx.send(f"🎉 **Double mise !** Tu remporte **{gain:,}** 💵 ! (**+{profit:,}** 💵 !)")
            elif roll < 0.92:  # 12% — Grosse win (x3)
                gain = mise * 3
                profit = gain - mise
                self.points.add_points(user_id, profit, "Casino huge win")
                await ctx.send(f"🔥 **TRIPLE !** Le casino pleure ! **{gain:,}** 💵 (**+{profit:,}** 💵) !!")
            else:  # 8% — JACKPOT (x5)
                gain = mise * 5
                profit = gain - mise
                self.points.add_points(user_id, profit, "Casino jackpot")
                await ctx.send(
                    f"🌟💎 **JAAAACKPOT !!!** 🎰🎰🎰\n"
                    f"TOUT LE CASINO APPLAUDIT ! Tu remporte **{gain:,}** 💵 !!\n"
                    f"(**+{profit:,}** 💵 de profit !) Le patron du casino veut te bannir. 😤"
                )

        except Exception as e:
            logger.error(f"Error in casino: {e}", exc_info=True)
            await ctx.send("❌ Le casino a fait disjoncter.")

    # ── !LOTO — TICKET DE LOTERIE ──

    @commands.command(name='loto', aliases=['loterie', 'ticket', 'gratter'])
    @check_cooldown_and_limit('loto')
    async def loto_command(self, ctx):
        """Achète un ticket à gratter pour 100 💵. Jackpot possible !"""
        try:
            user_id = str(ctx.author.id)
            ticket_price = 100
            current = int(self.points.get_user_points(user_id))

            if current < ticket_price:
                await ctx.send(f"❌ Un ticket coûte **{ticket_price}** 💵 et t'as que **{current}** 💵.")
                return

            self.points.remove_points(user_id, ticket_price)
            name = ctx.author.display_name

            await ctx.send(f"🎟️ {name} achète un ticket à gratter et commence à gratter fébrilement...")
            await asyncio.sleep(2)

            # Item bonus (amulette = luck, porte_bonheur = double)
            luck_bonus = self._get_item_bonus(user_id, "loto", "global_luck")
            has_porte_bonheur = self._has_item_effect(user_id, "loto", "double_gambling")
            roll = random.random()
            # Amulette réduit la zone perdante
            lose_threshold = max(0.10, 0.35 - luck_bonus)

            if roll < lose_threshold:  # ~35% — Perdant (réduit par amulette)
                await ctx.send("❌ Rien... pas un seul symbole aligné. **-100** 💵. Le buraliste rigole.")
            elif roll < 0.55:  # 20% — Remboursé
                self.points.add_points(user_id, ticket_price, "Loto remboursement")
                await ctx.send("😐 Tu récupères ta mise. **100** 💵. C'est comme si t'avais rien fait.")
            elif roll < 0.75:  # 20% — Petit gain
                gain = random.randint(200, 500)
                self.points.add_points(user_id, gain, "Loto petit gain")
                await ctx.send(f"✅ Pas mal ! Tu gratte et tu gagnes **{gain}** 💵 ! Profit net : **{gain - ticket_price}** 💵")
            elif roll < 0.90:  # 15% — Bon gain
                gain = random.randint(1000, 3000)
                self.points.add_points(user_id, gain, "Loto bon gain")
                await ctx.send(f"🎉 Beau ticket ! **{gain}** 💵 !! Le buraliste te regarde avec envie.")
            elif roll < 0.97:  # 7% — Gros gain
                gain = random.randint(5000, 15000)
                self.points.add_points(user_id, gain, "Loto gros gain")
                await ctx.send(f"🔥 **GROS GAIN !!** Tu gagnes **{gain:,}** 💵 ! Les gens dans la file font \"ooooh\" !")
            else:  # 3% — MEGA JACKPOT
                gain = random.randint(25000, 50000)
                self.points.add_points(user_id, gain, "Loto JACKPOT")
                await ctx.send(
                    f"💎🎰💎 **JACKPOT LOTO !!!** 🎰💎🎰\n\n"
                    f"TU GAGNES **{gain:,}** 💵 !!!\n"
                    f"Le buraliste pleure. Les clients applaudissent. "
                    f"T'appelles ta daronne pour lui dire que tu l'invites au resto. 🍽️"
                )

        except Exception as e:
            logger.error(f"Error in loto: {e}", exc_info=True)
            await ctx.send("❌ Le ticket était défectueux.")

    # ══════════════════════════════════════════════════════════════
    # ══  COMMANDES DE GALÈRE — QUAND T'ES FAUCHÉ / EN NÉGATIF  ══
    # ══════════════════════════════════════════════════════════════

    # ── !VENDRECUL — Désespoir total ──

    @commands.command(name='vendrecul', aliases=['prostitution', 'trottoir', 'tapin'])
    @check_cooldown_and_limit('vendrecul')
    async def vendrecul_command(self, ctx):
        """Vendre son corps pour survivre... C'est la dèche totale."""
        try:
            user_id = str(ctx.author.id)
            name = ctx.author.display_name

            await ctx.send(f"🚶 {name} arpente les rues sombres du quartier à la recherche de clients...")
            await asyncio.sleep(2)

            scenarios = [
                (f"💋 Un businessman en Audi s'arrête. \"Monte.\" Tu montes. "
                 f"Il te dépose 3 rues plus loin : il voulait juste de la compagnie pour pas se perdre. "
                 f"Il te file **{{gain}}** 💵 pour le GPS humain.", 50, 200),
                (f"👠 Tu fais ton plus beau déhanché au feu rouge. Un bus entier de touristes "
                 f"te prend en photo. Un d'eux te lance **{{gain}}** 💵 par la fenêtre. Humiliant mais rentable.", 100, 400),
                (f"😬 Tu abordes un mec louche. C'était un flic en civil. "
                 f"Il te laisse partir mais te prend **{{loss}}** 💵 d'amende. La honte.", -100, -300),
                (f"🌧️ Il pleut. Personne s'arrête. Tu rentres trempé(e) et bredouille. "
                 f"Par contre tu chopes un rhume. **{{loss}}** 💵 de pharmacie.", -50, -150),
                (f"🚗 Jackpot ! Un client généreux qui a eu pitié de toi te file **{{gain}}** 💵. "
                 f"\"Achète-toi des vêtements, t'as l'air misérable.\" Sympa... je crois.", 200, 600),
                (f"🐕 Un chien errant te suit pendant 2h. Pas de client. "
                 f"Par contre le chien est mignon. Tu gagnes un ami mais **0** 💵.", 0, 0),
                (f"🎭 Tu rencontres un réalisateur qui te propose un rôle dans son film. "
                 f"C'est un film étudiant. Il te paye **{{gain}}** 💵 en tickets restaurant.", 30, 150),
                (f"👵 Une mamie te donne **{{gain}}** 💵 en pensant que t'es SDF. "
                 f"\"Pauvre petit(e)...\" T'es pas SDF mais t'as pris les thunes quand même.", 80, 250),
            ]

            text, val_min, val_max = random.choice(scenarios)
            if val_min < 0:
                amount = random.randint(val_min, val_max)
                self.points.add_points(user_id, amount, "Vente de cul (amende)")
                await ctx.send(text.format(loss=abs(amount)))
            elif val_max > 0:
                amount = random.randint(val_min, val_max)
                self.points.add_points(user_id, amount, "Vente de cul")
                await ctx.send(text.format(gain=amount))
            else:
                await ctx.send(text)

            new_pts = int(self.points.get_user_data(user_id).get('points', 0))
            await ctx.send(f"🏦 Solde : **{new_pts:,}** 💵")

        except Exception as e:
            logger.error(f"Error in vendrecul: {e}", exc_info=True)
            await ctx.send("❌ Même ça, ça bug.")

    # ── !VENDRESLIP — La loose absolue ──

    @commands.command(name='vendreslip', aliases=['slip', 'vendresousvetement', 'calecon'])
    @check_cooldown_and_limit('vendreslip')
    async def vendreslip_command(self, ctx):
        """Vendre ton slip. Oui. T'en es là."""
        try:
            user_id = str(ctx.author.id)
            name = ctx.author.display_name

            scenarios = [
                (f"🩲 {name} retire son slip et le propose à un passant.\n"
                 f"\"Euh... non merci.\" Personne n'en veut. T'as juste perdu un slip.\n"
                 f"Gain: **0** 💵. Dignité restante: 0.", 0),
                (f"🩲 {name} met son slip en vente sur Leboncoin.\n"
                 f"Un fétichiste l'achète pour **{{gain}}** 💵 !\n"
                 f"Tu sais pas si tu dois être content ou dégoûté.", 80),
                (f"🩲 {name} tente de vendre son slip devant le Monoprix.\n"
                 f"Le vigile le jette dehors. Un SDF lui donne **{{gain}}** 💵 par pitié.", 15),
                (f"🩲 {name} essaie de vendre son slip comme \"collector\".\n"
                 f"Un touriste croit que c'est de l'art contemporain et paye **{{gain}}** 💵 !", 200),
                (f"🩲 {name} vend son slip sur eBay comme \"porté par une star\".\n"
                 f"Quelqu'un achète pour **{{gain}}** 💵. L'arnaque du siècle.", 150),
                (f"🩲 {name} vend son slip... mais le vent l'emporte.\n"
                 f"Un gamin le ramasse et s'enfuit en riant. **0** 💵 et plus de slip.", 0),
                (f"🩲 {name} propose son slip dédicacé.\n"
                 f"\"Dédicacé par qui ?\" — \"Bah... par moi.\" — \"...\" \n"
                 f"Le mec finit par payer **{{gain}}** 💵 pour que tu t'en ailles.", 40),
            ]

            text, gain = random.choice(scenarios)
            if gain > 0:
                self.points.add_points(user_id, gain, "Vente de slip")
                await ctx.send(text.format(gain=gain))
            else:
                await ctx.send(text)

            new_pts = int(self.points.get_user_data(user_id).get('points', 0))
            await ctx.send(f"🏦 Solde : **{new_pts:,}** 💵")

        except Exception as e:
            logger.error(f"Error in vendreslip: {e}", exc_info=True)
            await ctx.send("❌ Bug de slip.")

    # ── !VENDREDIGITE — Plus rien à perdre ──

    @commands.command(name='vendredigite', aliases=['dignite', 'fierté', 'honneur'])
    @check_cooldown_and_limit('vendredigite')
    async def vendredigite_command(self, ctx):
        """Vendre ta dignité au plus offrant. T'es vraiment au fond du trou."""
        try:
            user_id = str(ctx.author.id)
            name = ctx.author.display_name

            scenarios = [
                (f"🎪 {name} accepte de se déguiser en poulet géant devant le KFC pour **{{gain}}** 💵.\n"
                 f"Les enfants pleurent. Les parents filment.", True, 100, 300),
                (f"📢 {name} crie \"JE SUIS UN LOSER\" en plein centre-ville pour **{{gain}}** 💵.\n"
                 f"Un mec l'applaudit. Une mamie appelle les pompiers.", True, 150, 400),
                (f"🍕 {name} mange une pizza trouvée dans une poubelle pour un pari.\n"
                 f"Il gagne le pari : **{{gain}}** 💵. Il perd : sa dignité et son estomac.", True, 50, 200),
                (f"🎤 {name} chante du Jul au karaoké pendant 3h d'affilée.\n"
                 f"Le bar le paye **{{gain}}** 💵 pour qu'il ARRÊTE.", True, 200, 500),
                (f"🐔 {name} fait le poulet en pleine rue. Littéralement. Avec les bruits.\n"
                 f"Quelqu'un filme et ça devient viral. Sponsoring de dernière minute : **{{gain}}** 💵 !", True, 300, 800),
                (f"🧎 {name} se met à genoux au McDo et supplie le manager pour un emploi.\n"
                 f"Le manager lui donne **{{gain}}** 💵 et lui dit de ne jamais revenir.", True, 80, 250),
                (f"💇 {name} se rase un sourcil pour un pari.\n"
                 f"Les gens rient. Un streamer le filme. Gain : **{{gain}}** 💵 et un demi-visage.", True, 100, 350),
                (f"🙃 {name} essaie de vendre sa dignité mais personne n'en veut.\n"
                 f"\"Ta dignité vaut rien frère.\" — Un passant philosophe.\n"
                 f"**0** 💵. Même ta dignité est en négatif.", False, 0, 0),
            ]

            text, has_gain, gain_min, gain_max = random.choice(scenarios)
            if has_gain and gain_max > 0:
                gain = random.randint(gain_min, gain_max)
                self.points.add_points(user_id, gain, "Vente de dignité")
                await ctx.send(text.format(gain=gain))
            else:
                await ctx.send(text)

            new_pts = int(self.points.get_user_data(user_id).get('points', 0))
            await ctx.send(f"🏦 Solde : **{new_pts:,}** 💵")

        except Exception as e:
            logger.error(f"Error in vendredigite: {e}", exc_info=True)
            await ctx.send("❌ T'as même pas réussi à vendre ta dignité correctement.")

    # ── !PRET — Demander un prêt à quelqu'un ──

    @commands.command(name='pret', aliases=['emprunt', 'emprunter', 'loan'])
    @check_cooldown_and_limit('pret')
    async def pret_command(self, ctx, target: discord.Member = None, amount: int = None):
        """Demander un prêt à quelqu'un. Attention: il peut te reprendre les thunes à tout moment !"""
        try:
            if not target or not amount or amount <= 0:
                await ctx.send("❌ Usage: `!pret @user <montant>` — Ex: `!pret @Max 1000`")
                return
            if target.id == ctx.author.id:
                await ctx.send("🤦 Tu te prêtes de l'argent à toi-même ? T'es vraiment au bout.")
                return
            if target.bot:
                await ctx.send("🤖 Les bots ne font pas crédit.")
                return

            user_id = str(ctx.author.id)
            target_id = str(target.id)
            name = ctx.author.display_name
            target_name = target.display_name

            # Check que le prêteur a les fonds
            target_points = int(self.points.get_user_data(target_id).get('points', 0))
            if target_points < amount:
                await ctx.send(f"❌ {target_name} n'a que **{target_points:,}** 💵, pas assez pour te prêter {amount:,}.")
                return

            # Demander confirmation au prêteur
            embed = discord.Embed(
                title="💳 Demande de Prêt",
                description=(
                    f"**{name}** demande à emprunter **{amount:,}** 💵 à **{target_name}**.\n\n"
                    f"⚠️ Tu pourras récupérer cet argent à tout moment avec `!rembourser @{name} <montant>`.\n\n"
                    f"{target.mention}, tu acceptes ?"
                ),
                color=0xFFD700
            )
            msg = await self._safe_send(ctx, embed=embed)
            if msg:
                await msg.add_reaction("✅")
                await msg.add_reaction("❌")

            def check(reaction, user):
                return (
                    user.id == target.id
                    and str(reaction.emoji) in ["✅", "❌"]
                    and reaction.message.id == msg.id
                )

            try:
                reaction, _ = await self.bot.wait_for('reaction_add', check=check, timeout=60)
            except asyncio.TimeoutError:
                await ctx.send(f"⏰ {target_name} n'a pas répondu. Prêt refusé.")
                return

            if str(reaction.emoji) == "❌":
                refuses = [
                    f"❌ {target_name} refuse. \"Non frère, j'suis pas la Banque de France.\"",
                    f"❌ {target_name} te regarde et éclate de rire. Prêt refusé.",
                    f"❌ {target_name} : \"Avec ta réputation ? Jamais.\"",
                ]
                await ctx.send(random.choice(refuses))
                return

            # Prêt accepté — transférer l'argent
            self.points.remove_points(target_id, amount)
            self.points.add_points(user_id, amount, f"Prêt de {target_name}")

            # Enregistrer la dette en DB (bot_state)
            try:
                debts = self.points.database.load_bot_state("debts") or {}
                debt_key = f"{user_id}_{target_id}"
                current_debt = debts.get(debt_key, 0)
                debts[debt_key] = current_debt + amount
                self.points.database.save_bot_state("debts", debts)
            except Exception:
                pass  # Si le state fail, le prêt est quand même fait

            await ctx.send(
                f"✅ **PRÊT ACCORDÉ !** {target_name} prête **{amount:,}** 💵 à {name}.\n"
                f"💰 {name} : +{amount:,} 💵\n"
                f"💸 {target_name} : -{amount:,} 💵\n\n"
                f"⚠️ {target_name} peut récupérer cet argent à tout moment avec `!rembourser @{name} <montant>`"
            )

        except Exception as e:
            logger.error(f"Error in pret: {e}", exc_info=True)
            await ctx.send("❌ Erreur lors du prêt.")

    # ── !REMBOURSER — Récupérer un prêt ──

    @commands.command(name='rembourser', aliases=['reprendre', 'collect', 'recup'])
    async def rembourser_command(self, ctx, target: discord.Member = None, amount: int = None):
        """Récupère l'argent que tu as prêté à quelqu'un. Tu peux reprendre ce que tu veux, quand tu veux."""
        try:
            if not target or not amount or amount <= 0:
                await ctx.send("❌ Usage: `!rembourser @user <montant>` — Ex: `!rembourser @Max 500`")
                return

            user_id = str(ctx.author.id)
            target_id = str(target.id)
            name = ctx.author.display_name
            target_name = target.display_name

            # Vérifier la dette
            try:
                debts = self.points.database.load_bot_state("debts") or {}
            except Exception:
                debts = {}

            debt_key = f"{target_id}_{user_id}"  # la dette de target envers user
            current_debt = debts.get(debt_key, 0)

            if current_debt <= 0:
                await ctx.send(f"❌ {target_name} ne te doit rien.")
                return

            # On peut reprendre jusqu'au montant de la dette
            actual_amount = min(amount, current_debt)

            # Reprendre l'argent (même si la cible est en négatif, on s'en fout)
            self.points.remove_points(target_id, actual_amount)
            self.points.add_points(user_id, actual_amount, f"Remboursement de {target_name}")

            # Mettre à jour la dette
            debts[debt_key] = current_debt - actual_amount
            if debts[debt_key] <= 0:
                del debts[debt_key]
            try:
                self.points.database.save_bot_state("debts", debts)
            except Exception:
                pass

            remaining = debts.get(debt_key, 0)
            await ctx.send(
                f"💰 **REMBOURSEMENT !** {name} récupère **{actual_amount:,}** 💵 sur {target_name}.\n"
                f"{'✅ Dette soldée !' if remaining <= 0 else f'📋 {target_name} doit encore **{remaining:,}** 💵.'}"
            )

        except Exception as e:
            logger.error(f"Error in rembourser: {e}", exc_info=True)
            await ctx.send("❌ Erreur lors du remboursement.")

    # ── !DETTE — Voir ses dettes ──

    @commands.command(name='dette', aliases=['dettes', 'debt', 'emprunts'])
    async def dette_command(self, ctx, member: discord.Member = None):
        """Voir tes dettes ou celles de quelqu'un"""
        try:
            target = member or ctx.author
            target_id = str(target.id)
            target_name = target.display_name

            try:
                debts = self.points.database.load_bot_state("debts") or {}
            except Exception:
                debts = {}

            # Dettes que cette personne DOIT (elle a emprunté)
            owes = []
            for key, amount in debts.items():
                parts = key.split("_")
                if len(parts) == 2 and parts[0] == target_id and amount > 0:
                    creditor_id = parts[1]
                    try:
                        creditor = await ctx.guild.fetch_member(int(creditor_id))
                        owes.append(f"💸 Doit **{amount:,}** 💵 à {creditor.display_name}")
                    except Exception:
                        owes.append(f"💸 Doit **{amount:,}** 💵 à Joueur #{creditor_id[-4:]}")

            # Dettes que d'autres lui DOIVENT (elle a prêté)
            owed = []
            for key, amount in debts.items():
                parts = key.split("_")
                if len(parts) == 2 and parts[1] == target_id and amount > 0:
                    debtor_id = parts[0]
                    try:
                        debtor = await ctx.guild.fetch_member(int(debtor_id))
                        owed.append(f"💰 {debtor.display_name} doit **{amount:,}** 💵")
                    except Exception:
                        owed.append(f"💰 Joueur #{debtor_id[-4:]} doit **{amount:,}** 💵")

            embed = discord.Embed(
                title=f"📋 Dettes de {target_name}",
                color=0xFF0000 if owes else 0x00FF00
            )

            if owes:
                embed.add_field(name="🔴 Tu dois", value="\n".join(owes), inline=False)
            if owed:
                embed.add_field(name="🟢 On te doit", value="\n".join(owed), inline=False)
            if not owes and not owed:
                embed.description = "✅ Aucune dette ! T'es clean."

            points = int(self.points.get_user_data(target_id).get('points', 0))
            status = "🔴 EN NÉGATIF !" if points < 0 else "🟢 Positif"
            embed.add_field(name="🏦 Solde actuel", value=f"**{points:,}** 💵 ({status})", inline=False)

            await self._safe_send(ctx, embed=embed)

        except Exception as e:
            logger.error(f"Error in dette: {e}", exc_info=True)
            await ctx.send("❌ Erreur.")

    # ── !FAILLITE — Quand t'es dans le rouge ──

    @commands.command(name='faillite', aliases=['bankrupt', 'ruine', 'fin'])
    async def faillite_command(self, ctx):
        """Déclarer faillite. Remet à 0 mais tu perds TOUT (inventaire + réputation)."""
        try:
            user_id = str(ctx.author.id)
            name = ctx.author.display_name
            points = int(self.points.get_user_data(user_id).get('points', 0))

            if points >= 0:
                await ctx.send(f"❌ T'es pas en négatif ({points:,} 💵). Pas besoin de faillite !")
                return

            await ctx.send(
                f"⚠️ **FAILLITE** — {name}, tu es à **{points:,}** 💵.\n"
                f"Si tu déclares faillite:\n"
                f"• Ton solde revient à **0** 💵\n"
                f"• Tu perds **TOUT** ton inventaire\n"
                f"• Tes dettes sont effacées\n\n"
                f"Réagis avec ✅ pour confirmer ou ❌ pour annuler."
            )

            msg = await ctx.send("Confirmer la faillite ?")
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

            def check(reaction, user):
                return user.id == ctx.author.id and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

            try:
                reaction, _ = await self.bot.wait_for('reaction_add', check=check, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send("⏰ Faillite annulée.")
                return

            if str(reaction.emoji) == "❌":
                await ctx.send("❌ Faillite annulée. Continue à galérer.")
                return

            # Reset complet
            # Remettre à 0
            current = int(self.points.get_user_data(user_id).get('points', 0))
            if current < 0:
                self.points.add_points(user_id, abs(current), "Faillite - reset à 0")

            # Vider l'inventaire
            inv = self.points.db.get_inventory(user_id)
            for item in inv:
                self.points.db.remove_item(user_id, item)

            # Effacer les dettes
            try:
                debts = self.points.database.load_bot_state("debts") or {}
                keys_to_remove = [k for k in debts if k.startswith(f"{user_id}_")]
                for k in keys_to_remove:
                    del debts[k]
                self.points.database.save_bot_state("debts", debts)
            except Exception:
                pass

            await ctx.send(
                f"💀 **FAILLITE DÉCLARÉE** — {name} repart de zéro.\n"
                f"• Solde: **0** 💵\n"
                f"• Inventaire: vidé\n"
                f"• Dettes: effacées\n\n"
                f"Bonne chance pour remonter la pente, frère. 🙏"
            )

        except Exception as e:
            logger.error(f"Error in faillite: {e}", exc_info=True)
            await ctx.send("❌ Erreur.")
