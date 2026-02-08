# 🔐 IMPLEMENTATION GUIDE - Secure Permissions System

## 📊 Comparaison Avant/Après

### **Avant (VULNERABLE):**
```python
# ❌ N'importe qui avec un rôle "Staff" peut faire:
@commands.command(name='addpoints')
@is_staff()  # ⚠️ Vérification: juste nom de rôle
async def add_points(self, ctx, member, amount):
    self.points.db.add_points(str(member.id), amount)  # ILLIMITÉ!

# Scenario d'exploitation:
# 1. Utilisateur crée un rôle "Staff"
# 2. !addpoints @self 999999999
# ✅ Exécuté! (Faille critique)
```

### **Après (SECURE):**
```python
# ✅ SEULEMENT propriétaire du bot
@commands.command(name='addpoints')
@is_owner_only()  # ✅ ID du propriétaire uniquement
@rate_limit_admin_action(max_per_day=10)  # ✅ Max 10/jour
@validate_amount(max_amount=10000)  # ✅ Max 10k par modification
@require_audit_log("Modified user points", require_amount=True)  # ✅ Audit complet
async def add_points(self, ctx, member, amount):
    # Vérifié: utilisateur = propriétaire du bot
    # Limité: max 10 modifications/jour
    # Limité: max 10k points par modification
    # Audité: toutes les actions loggées
    self.points.db.add_points(str(member.id), amount)

# Scenario de tentative d'exploitation:
# 1. Utilisateur quelconque: !addpoints @self 999999
# ❌ "Permission refusée. Niveau requis: Propriétaire"
# ❌ Tentative loggée dans les audits critiques
```

---

## 🚀 Étapes d'Implémentation

### **Étape 1: Configuration Initiale (15 min)**

#### 1a. Obtenir votre ID Discord:
```
1. Sur Discord, activez le mode développeur (Paramètres > Avancé > Mode développeur)
2. Clic-droit sur votre profil -> Copier l'ID utilisateur
3. Notez cet ID
```

#### 1b. Mettre à jour config.py:
```python
# config.py

# ⭐ À faire IMMÉDIATEMENT:
OWNER_ID = 123456789  # ← Votre ID Discord

# Staff approuvés (les IDs de personnes de confiance SEULEMENT)
APPROVED_STAFF_IDS = [
    123456789,  # Vous-même (optionnel, car automatiquement owner)
    # 987654321,  # Ajouter d'autres modérateurs approuvés
]

# Serveurs de confiance
TRUSTED_GUILD_IDS = [
    # 111111111,  # Votre serveur principal
]
```

---

### **Étape 2: Import du Nouveau Système (5 min)**

#### 2a. Dans commands.py, remplacer les imports:
```python
# ❌ ANCIEN:
# def is_staff():
#     async def predicate(ctx):
#         if ctx.author.guild_permissions.administrator:
#             return True
#         return any(role.name.lower() in ['staff', 'modo', 'admin'] for role in ctx.author.roles)
#     return commands.check(predicate)

# ✅ NOUVEAU:
from permissions import (
    is_owner_only,
    is_staff_or_owner,
    is_admin_or_owner,
    require_permission_level,
    require_audit_log,
    validate_amount,
    rate_limit_admin_action,
    PermissionLevel,
    AuditLogger
)
```

---

### **Étape 3: Mettre à Jour les Commandes Critiques**

#### 3a. Commande `addpoints` (Ligne ~1018):

**Avant:**
```python
@commands.command(name='addpoints', aliases=['ajouterpoints', 'donnerpoints'])
@is_staff()
async def add_points(self, ctx, member: discord.Member = None, amount: int = None):
    """[STAFF] Add points to a member"""
    if not member or amount is None:
        await ctx.send("❌ Usage: !addpoints @user <montant>")
        return
    if amount <= 0:
        await ctx.send("❌ Le montant doit être positif!")
        return
    
    self.points.db.add_points(str(member.id), amount)
    await ctx.send(f"✅ {amount} points ajoutés à {member.name}!")
```

**Après:**
```python
@commands.command(name='addpoints', aliases=['ajouterpoints', 'donnerpoints'])
@is_owner_only()
@rate_limit_admin_action(max_per_day=10)
@require_audit_log("Added points to user", require_amount=True)
async def add_points(self, ctx, member: discord.Member = None, amount: int = None):
    """[OWNER ONLY] Ajouter des points à un membre"""
    if not member or amount is None:
        await ctx.send("❌ Usage: !addpoints @user <montant>")
        return
    
    if amount <= 0:
        await ctx.send("❌ Le montant doit être positif!")
        return
    
    if amount > 10000:  # Nouvelle limite de sécurité
        await ctx.send("❌ Limite maximale: 10000 points par modification!")
        return
    
    self.points.db.add_points(str(member.id), amount)
    await ctx.send(f"✅ {amount} points ajoutés à {member.name}!")
    logger.info(f"Points added: +{amount} to {member.id} by {ctx.author.id}")
```

#### 3b. Commande `removepoints` (Ligne ~1040):

Même pattern que `addpoints`:
```python
@commands.command(name='removepoints', aliases=['retirerpoints', 'enleverpoints'])
@is_owner_only()
@rate_limit_admin_action(max_per_day=10)
@require_audit_log("Removed points from user", require_amount=True)
async def remove_points(self, ctx, member: discord.Member = None, amount: int = None):
    """[OWNER ONLY] Retirer des points à un membre"""
    if not member or amount is None:
        await ctx.send("❌ Usage: !removepoints @user <montant>")
        return
    
    if amount <= 0:
        await ctx.send("❌ Le montant doit être positif!")
        return
    
    if amount > 10000:
        await ctx.send("❌ Limite maximale: 10000 points par suppression!")
        return
    
    current_points = self.points.db.get_user_points(str(member.id))
    if current_points < amount:
        amount = current_points
    
    self.points.db.add_points(str(member.id), -amount)
    await ctx.send(f"✅ {amount} points retirés à {member.name}!")
```

#### 3c. Commande `additem` (Ligne ~1064):

```python
@commands.command(name='additem', aliases=['ajouteritem', 'donneritem'])
@is_owner_only()
@rate_limit_admin_action(max_per_day=20)
@require_audit_log("Added item to user", require_amount=False)
async def add_item(self, ctx, member: discord.Member = None, item_id: int = None, quantity: int = 1):
    """[OWNER ONLY] Ajouter un item à un membre"""
    if not member or item_id is None:
        await ctx.send("❌ Usage: !additem @user <item_id> [quantité]")
        return
    
    if quantity <= 0:
        await ctx.send("❌ La quantité doit être positive!")
        return
    
    if quantity > 100:
        await ctx.send("❌ Limite maximale: 100 items par modification!")
        return
    
    # Ajouter l'item (implémentation dépend de votre système)
    # self.inventory.add_item(str(member.id), item_id, quantity)
    await ctx.send(f"✅ {quantity}x item#{item_id} ajoutés à {member.name}!")
```

---

### **Étape 4: Tester les Changements**

#### 4a. Test unitaire de permissions:

Créer un fichier `test_permissions.py`:
```python
import asyncio
from unittest.mock import MagicMock
from permissions import get_permission_level, PermissionLevel
from config import OWNER_ID, APPROVED_STAFF_IDS

async def test_permissions():
    print("🧪 Testing Permission System...\n")
    
    # Test 1: Owner detection
    print("Test 1: Owner Detection")
    ctx_mock = MagicMock()
    ctx_mock.author.id = OWNER_ID
    ctx_mock.author.guild_permissions.administrator = False
    level = get_permission_level(ctx_mock)
    assert level == PermissionLevel.OWNER, f"Expected OWNER, got {level}"
    print("  ✅ Owner detected correctly\n")
    
    # Test 2: Regular user detection
    print("Test 2: Regular User Detection")
    ctx_mock.author.id = 999999999
    ctx_mock.guild = MagicMock()
    level = get_permission_level(ctx_mock)
    assert level == PermissionLevel.MEMBER, f"Expected MEMBER, got {level}"
    print("  ✅ Regular user detected correctly\n")
    
    # Test 3: Admin detection
    print("Test 3: Admin Detection")
    ctx_mock.author.guild_permissions.administrator = True
    level = get_permission_level(ctx_mock)
    assert level == PermissionLevel.ADMIN, f"Expected ADMIN, got {level}"
    print("  ✅ Admin detected correctly\n")
    
    print("✅ All permission tests passed!")

if __name__ == "__main__":
    asyncio.run(test_permissions())
```

Exécuter:
```bash
python.exe test_permissions.py
```

#### 4b. Test sur serveur de test Discord:

1. Inviter le bot sur un serveur de test
2. Tenter: `!addpoints @user 1000` avec un compte non-owner
3. Vérifier: Message d'erreur "Permission refusée"
4. Tenter avec owner ID
5. Vérifier: Commande exécutée avec log d'audit

---

### **Étape 5: Déploiement Progressif**

#### Phase 1 (Jour 1): Déployer changements sur serveur de test
- Serveurs: Test/Dev uniquement
- Monitoring: Vérifier les logs d'audit
- Rollback: Facile si problème

#### Phase 2 (Jour 2-3): Déployer sur serveurs secondaires
- Serveurs: Non-critiques
- Monitoring: 24h d'observation
- Vérifier: Aucune fausse alerte

#### Phase 3 (Jour 3+): Production
- Serveurs: Tous les serveurs
- Documentation: Communiquer les changements aux staff
- Support: Aide pour les utilisateurs en cas de problème

---

## ✅ Checklist Finale

- [ ] OWNER_ID configuré dans config.py avec votre ID Discord
- [ ] APPROVED_STAFF_IDS rempli avec IDs de confiance (pas de noms de rôles)
- [ ] permissions.py importé dans commands.py
- [ ] `addpoints` changé en `@is_owner_only()`
- [ ] `removepoints` changé en `@is_owner_only()`
- [ ] `additem` changé en `@is_owner_only()`
- [ ] Limites maximales ajoutées (10k points, 100 items max)
- [ ] Rate limiting implémenté
- [ ] Audit logging activé
- [ ] Tests passent sur serveur dev
- [ ] Déployé progressivement
- [ ] Monitored 24h après déploiement
- [ ] Documenté pour mainteneurs futurs

---

## 🔍 Comment Vérifier que Ça Marche

### Vérifier les logs d'audit:
```bash
# Dans les logs du bot, chercher:
[AUDIT_ADMIN] {timestamp, user_id, action, target}
[AUDIT_STAFF] {timestamp, user_id, action}

# Exemple de log positif:
[AUDIT_ADMIN] {'timestamp': '2026-02-08T22:45:00', 'user_id': 123456, 'action': 'Added points', 'target_user': 789012}
```

### Test d'une tentative non-autorisée:
```
Utilisateur: !addpoints @someone 1000
Bot réponse: ❌ Permission refusée. Niveau requis: Propriétaire
Logs: Permission denied for {utilisateur_id} to execute add_points
```

---

## 📞 Support & Questions

Si vous avez des questions:
1. Vérifier les logs d'audit pour les détails
2. Vérifier OWNER_ID dans config.py
3. Vérifier que permissions.py est importé
4. Vérifier les décorateurs sont appliqués

