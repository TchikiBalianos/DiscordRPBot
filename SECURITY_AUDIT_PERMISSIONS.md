# 🔐 Audit de Sécurité - Système de Permissions

## 🚨 Failles Identifiées

### **Faille #1: Vérification de Rôle Insuffisante (CRITIQUE)**

**Commande affectée:** `!addpoints`, `!removepoints`

**Code actuel:**
```python
def is_staff():
    """Check if the user has staff role or is an administrator"""
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        return any(role.name.lower() in ['staff', 'modo', 'admin'] for role in ctx.author.roles)
    return commands.check(predicate)
```

**Problème:** 
- ✅ Vérifie si l'utilisateur a le rôle Discord "staff"/"modo"/"admin"
- ❌ **N'importe quel administrateur serveur peut créer un rôle nommé "staff"**
- ❌ Aucune vérification de niveau d'ID ou de propriété du bot
- ❌ Les noms de rôles sont case-insensitive, facile à contourner

**Scénario d'exploitation:**
```
1. Utilisateur crée un serveur Discord
2. Le rôle par défaut @everyone a des "Administrator" permissions
3. Utilisateur crée un rôle "Staff" ou crée son propre rôle "Admin"
4. Utilisateur s'attribue ce rôle
5. Utilisateur exécute: !addpoints @self 999999
6. ✅ Commande exécutée car il passe la vérification is_staff()
```

---

### **Faille #2: Pas de Limite Maximale sur `addpoints` (CRITIQUE)**

**Commande affectée:** `!addpoints`

**Code actuel:**
```python
@commands.command(name='addpoints', aliases=['ajouterpoints', 'donnerpoints'])
@is_staff()
async def add_points(self, ctx, member: discord.Member = None, amount: int = None):
    """[STAFF] Add points to a member"""
    # ... validation ...
    self.points.db.add_points(str(member.id), amount)  # ⚠️ AUCUNE LIMITE!
```

**Problème:**
- ❌ Un utilisateur "staff" peut donner **ILLIMITÉ** de points d'un coup
- ❌ Contrairement à `gift` qui a une limite de 1000
- ❌ Aucun log d'audit pour les modifications massives

---

### **Faille #3: Permissions Discord Insuffisantes (MAJEURE)**

**Système actuel:**
- Vérifie juste `ctx.author.guild_permissions.administrator`
- Utilise des noms de rôles arbitraires ("staff", "admin", "modo")

**Problème:**
- ❌ Un serveur créé hier avec 1 utilisateur peut être "admin"
- ❌ Aucune vérification d'identité du propriétaire du bot
- ❌ Aucune chaîne de trust

---

### **Faille #4: Pas de Rate Limiting sur Commandes Critiques (MAJEURE)**

**Commandes critiques sans limite:**
- `!addpoints` → Pas de cooldown
- `!removepoints` → Pas de cooldown
- `!additem` → Pas de cooldown

**Résultat:** Un utilisateur peut faire 1000 `!addpoints` en 1 seconde

---

## 📊 Commandes et leurs Protections Actuelles

| Commande | Effet | Protection | Risque |
|----------|--------|-----------|--------|
| `!gift` | Transfert max 1000pts | ✅ Check cooldown + limit auto-check | Bas |
| `!addpoints` | Ajout ILLIMITÉ | ❌ Juste `is_staff()` | **CRITIQUE** |
| `!removepoints` | Retrait ILLIMITÉ | ❌ Juste `is_staff()` | **CRITIQUE** |
| `!work` | +100-300pts | ✅ Cooldown + daily limit | Bas |
| `!steal` | Vol aléatoire | ✅ Cooldown + daily limit | Moyen |

---

## 🛡️ Système de Permissions Proposé

### **Architecture à 3 Niveaux:**

```python
# Niveau 1: OWNER (Propriétaire du bot)
def is_owner():
    """Seul l'ID du propriétaire"""
    return ctx.author.id == OWNER_ID

# Niveau 2: SERVER_ADMIN (Admin du serveur)
def is_server_admin():
    """Administrateur Discord du serveur où la commande est exécutée"""
    return ctx.author.guild_permissions.administrator

# Niveau 3: ELEVATED_STAFF (Staff approuvé)
def is_elevated_staff():
    """Staff list in config (whitelist d'IDs, pas de noms de rôles)"""
    return ctx.author.id in APPROVED_STAFF_IDS

# Niveau 4: TRUSTED_GUILD (Serveur approuvé)
def is_trusted_guild():
    """Vérifier si le serveur est dans la whitelist approuvée"""
    return ctx.guild.id in TRUSTED_GUILD_IDS
```

### **Règles pour Commandes Critiques:**

| Commande | Niveau requis | Limite | Cooldown | Audit |
|----------|---------------|--------|----------|-------|
| `!addpoints` | OWNER only | 10k max par jour | 5s | ✅ Requise |
| `!removepoints` | OWNER only | Illimité | 5s | ✅ Requise |
| `!additem` | OWNER only | N/A | 5s | ✅ Requise |
| Modifier gang | SERVER_ADMIN | N/A | 1s | ✅ Requise |

---

## 📝 Configuration Sécurisée Proposée

```python
# config.py - Ajouter:

# Propriétaire du bot (ID Discord)
OWNER_ID = 123456789  # ⚠️ À configurer avec votre ID

# Staff approuvés (whitelist d'IDs, pas de rôles)
APPROVED_STAFF_IDS = [
    123456789,  # Toi
    987654321,  # Un modérateur approuvé
]

# Serveurs de confiance pour commandes sensibles
TRUSTED_GUILD_IDS = [
    111111111,  # Ton serveur principal
    222222222,  # Serveur de test
]

# Limites pour commandes de modification de points
STAFF_EDITPOINTS_DAILY_LIMIT = 10  # Max 10 modifications/jour
STAFF_EDITPOINTS_MAX_PER_CHANGE = 10000  # Max 10k par modification
```

---

## 🔧 Implémentation Recommandée

### **1. Nouveau Décorateur Sécurisé:**

```python
def is_owner_only():
    """Strict: Owner du bot uniquement"""
    async def predicate(ctx):
        if ctx.author.id != OWNER_ID:
            await ctx.send("❌ Cette commande est réservée au propriétaire du bot.")
            return False
        return True
    return commands.check(predicate)

def is_admin_with_audit():
    """Admin serveur avec log d'audit"""
    async def predicate(ctx):
        if not ctx.author.guild_permissions.administrator:
            return False
        # Log l'exécution pour audit
        logger.warning(f"ADMIN_ACTION: {ctx.author} executed {ctx.command} on server {ctx.guild}")
        return True
    return commands.check(predicate)

def is_elevated_staff():
    """Staff approuvé avec whitelist d'IDs"""
    async def predicate(ctx):
        if ctx.author.id not in APPROVED_STAFF_IDS:
            return False
        logger.info(f"STAFF_ACTION: {ctx.author} executed {ctx.command}")
        return True
    return commands.check(predicate)
```

### **2. Commandes Sécurisées:**

```python
@commands.command(name='addpoints')
@is_owner_only()  # ✅ Strict: propriétaire uniquement
async def add_points(self, ctx, member: discord.Member = None, amount: int = None):
    """[OWNER ONLY] Ajouter des points"""
    if amount > 10000:  # ✅ Limite maximale
        await ctx.send("❌ Max 10k points à la fois!")
        return
    
    # ✅ Log d'audit complet
    logger.warning(f"AUDIT: {ctx.author} added {amount} points to {member}")
    self.points.db.add_points(str(member.id), amount)
    await ctx.send(f"✅ {amount} points added")
```

### **3. Système d'Audit:**

```python
# Ajouter à advanced_logging.py
class AuditLog:
    def log_sensitive_action(self, user_id, action, details):
        """Log les actions sensibles"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "action": action,
            "details": details,
        }
        # Sauvegarder dans base de données ou fichier sécurisé
        logger.warning(f"AUDIT_LOG: {entry}")
```

---

## ✅ Checklist de Sécurité

- [ ] Remplacer tous `is_staff()` par `is_owner_only()` pour commandes critiques
- [ ] Ajouter whitelist d'IDs pour staff (pas de noms de rôles)
- [ ] Implémenter limites maximales sur `!addpoints` et `!removepoints`
- [ ] Ajouter système d'audit complet (AuditLog)
- [ ] Ajouter rate limiting sur commandes sensibles
- [ ] Tester les permissions sur serveur de test
- [ ] Documenter le système de permissions pour futurs mainteneurs
- [ ] Configurer OWNER_ID et APPROVED_STAFF_IDS dans config.py

---

## 🎯 Priorités d'Implémentation

1. **🔴 CRITIQUE** - Changer `addpoints`/`removepoints` → `is_owner_only()`
2. **🟠 MAJEURE** - Implémenter whitelist d'IDs pour staff
3. **🟡 IMPORTANTE** - Ajouter limites maximales sur modifications points
4. **🟢 NORMAL** - Système d'audit complet

