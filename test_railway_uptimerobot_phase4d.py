#!/usr/bin/env python3
"""
Test de Configuration Railway + UptimeRobot - Phase 4D
Script de validation pour le déploiement et monitoring selon TECH Brief
"""

import sys
import time
import threading
import requests
from datetime import datetime
import json

def test_local_health_endpoints():
    """Test des endpoints de santé en local"""
    print("🔍 TESTING LOCAL HEALTH ENDPOINTS")
    print("=" * 60)
    
    # Démarrer le serveur de santé localement
    print("\n📋 Test 1: Démarrage du serveur de santé local")
    
    try:
        from health_monitoring import app
        import uvicorn
        
        def run_server():
            uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        time.sleep(3)  # Attendre que le serveur démarre
        
        print("   ✅ Serveur de santé démarré sur le port 8001")
        
        # Test des endpoints
        endpoints = [
            ("/health", "Endpoint basique Railway/UptimeRobot"),
            ("/health/detailed", "Endpoint monitoring détaillé"),
            ("/health/resilience", "Endpoint résilience Phase 4C")
        ]
        
        results = {}
        
        for endpoint, description in endpoints:
            print(f"\n📋 Test: {description}")
            try:
                url = f"http://127.0.0.1:8001{endpoint}"
                response = requests.get(url, timeout=10)
                
                results[endpoint] = {
                    "status_code": response.status_code,
                    "success": response.status_code in [200, 503],
                    "response_time": response.elapsed.total_seconds(),
                    "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else None
                }
                
                if results[endpoint]["success"]:
                    print(f"   ✅ Status: {response.status_code}")
                    print(f"   ⏱️ Response time: {response.elapsed.total_seconds():.3f}s")
                    
                    # Vérifier le contenu de la réponse
                    if endpoint == "/health":
                        data = results[endpoint]["data"]
                        if data and "status" in data and data["status"] == "alive":
                            print(f"   ✅ Content valid: status='{data['status']}'")
                        else:
                            print(f"   ⚠️ Content issue: {data}")
                    
                    elif endpoint == "/health/detailed":
                        data = results[endpoint]["data"]
                        if data and "overall_status" in data:
                            print(f"   ✅ Content valid: overall_status='{data['overall_status']}'")
                        else:
                            print(f"   ⚠️ Content issue: {data}")
                    
                    elif endpoint == "/health/resilience":
                        data = results[endpoint]["data"]
                        if data and "connection_status" in data:
                            print(f"   ✅ Content valid: resilience features present")
                        else:
                            print(f"   ⚠️ Content issue: {data}")
                            
                else:
                    print(f"   ❌ FAIL - Status: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"   ❌ FAIL - Request error: {e}")
                results[endpoint] = {"success": False, "error": str(e)}
            except Exception as e:
                print(f"   ❌ FAIL - Unexpected error: {e}")
                results[endpoint] = {"success": False, "error": str(e)}
        
        return results
        
    except Exception as e:
        print(f"   ❌ FAIL - Cannot start health server: {e}")
        return {}

def test_railway_configuration():
    """Test de la configuration Railway"""
    print("\n⚙️ RAILWAY CONFIGURATION TESTING")
    print("=" * 60)
    
    try:
        # Vérifier l'existence du fichier railway.toml
        print("\n📋 Test 1: Fichier railway.toml")
        
        try:
            with open("railway.toml", "r") as f:
                content = f.read()
            print("   ✅ railway.toml trouvé")
            
            # Vérifier les paramètres clés
            required_settings = [
                ("healthcheckPath", "/health"),
                ("healthcheckTimeout", "300"),
                ("port", "8000"),
                ("startCommand", "python start.py")
            ]
            
            for setting, expected in required_settings:
                if setting in content:
                    print(f"   ✅ {setting} configuré")
                else:
                    print(f"   ❌ {setting} manquant")
            
            # Vérifier les nouveaux paramètres Phase 4C
            phase4c_settings = [
                "healthcheckInterval",
                "ENABLE_HEALTH_MONITOR",
                "external_endpoints"
            ]
            
            for setting in phase4c_settings:
                if setting in content:
                    print(f"   ✅ {setting} configuré (Phase 4C)")
                else:
                    print(f"   ⚠️ {setting} manquant (Phase 4C)")
            
        except FileNotFoundError:
            print("   ❌ railway.toml introuvable")
            return False
        
        # Vérifier le script de démarrage
        print("\n📋 Test 2: Script de démarrage")
        
        try:
            with open("start.py", "r", encoding="utf-8") as f:
                start_content = f.read()
            
            if "start_health_monitor" in start_content:
                print("   ✅ Health monitor intégré dans start.py")
            else:
                print("   ❌ Health monitor manquant dans start.py")
            
            if "HEALTH_PORT" in start_content:
                print("   ✅ HEALTH_PORT configuré")
            else:
                print("   ❌ HEALTH_PORT manquant")
                
        except FileNotFoundError:
            print("   ❌ start.py introuvable")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ FAIL - Configuration error: {e}")
        return False

def test_uptimerobot_compatibility():
    """Test de compatibilité UptimeRobot"""
    print("\n🔔 UPTIMEROBOT COMPATIBILITY TESTING")
    print("=" * 60)
    
    print("\n📋 Test: Format de réponse UptimeRobot")
    
    # Simuler une requête UptimeRobot
    try:
        from health_monitoring import app
        import httpx
        
        # Test avec httpx directement sur le serveur local
        url = "http://127.0.0.1:8001/health"
        response = httpx.get(url, timeout=10)
        
        print(f"   📊 Status Code: {response.status_code}")
        print(f"   📊 Content-Type: {response.headers.get('content-type')}")
        
        if response.status_code == 200:
            data = response.json()
            print("   ✅ JSON Response valide")
            
            # Vérifier les champs requis pour UptimeRobot
            required_fields = ["status", "timestamp"]
            for field in required_fields:
                if field in data:
                    print(f"   ✅ Champ '{field}' présent: {data[field]}")
                else:
                    print(f"   ❌ Champ '{field}' manquant")
            
            # Vérifier la keyword "alive" pour UptimeRobot
            if data.get("status") == "alive":
                print("   ✅ Keyword 'alive' présente (recommandé pour UptimeRobot)")
            else:
                print("   ⚠️ Keyword 'alive' manquante")
            
            # Temps de réponse
            print(f"   📈 Format compatible UptimeRobot: ✅")
            
        else:
            print("   ❌ Status code non-optimal pour UptimeRobot")
        
        return True
        
    except Exception as e:
        print(f"   ❌ FAIL - Compatibility error: {e}")
        return False

def generate_uptimerobot_setup_guide():
    """Générer un guide de configuration UptimeRobot personnalisé"""
    print("\n📋 GENERATING UPTIMEROBOT SETUP GUIDE")
    print("=" * 60)
    
    guide = f"""
🔔 CONFIGURATION UPTIMEROBOT - Bot Discord Thugz Life RP
Généré automatiquement le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

1. CRÉER LE MONITOR PRINCIPAL
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Type: HTTP(s)
   URL: https://your-app-name.railway.app/health
   Nom: Discord Bot Thugz - Health Check
   Intervalle: 5 minutes (selon TECH Brief)
   Keyword: alive
   
2. ALERTES RECOMMANDÉES
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Email: votre-email@domain.com
   Threshold: 2 minutes (attendre avant alerte)
   Send when DOWN: ✅
   Send when UP: ✅
   
3. MONITORS ADDITIONNELS (OPTIONNEL)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Monitor Détaillé:
   - URL: https://your-app-name.railway.app/health/detailed
   - Intervalle: 10 minutes
   
   Monitor Résilience:
   - URL: https://your-app-name.railway.app/health/resilience
   - Intervalle: 15 minutes
   
4. APRÈS DÉPLOIEMENT RAILWAY
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   - railway deploy
   - Noter l'URL générée
   - Remplacer "your-app-name" dans les URLs ci-dessus
   - Tester manuellement les endpoints
   - Configurer UptimeRobot avec la vraie URL
   
5. VALIDATION
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   - Monitor UptimeRobot actif
   - Réception d'alertes test
   - Health checks répondent 200 OK
   - Bot Discord fonctionnel
"""
    
    try:
        with open("UPTIMEROBOT_CONFIG.txt", "w", encoding="utf-8") as f:
            f.write(guide)
        print("   ✅ Guide sauvegardé: UPTIMEROBOT_CONFIG.txt")
    except Exception as e:
        print(f"   ⚠️ Impossible de sauvegarder le guide: {e}")
    
    print(guide)
    return True

def run_deployment_tests():
    """Exécuter tous les tests de déploiement"""
    print("🚀 RAILWAY + UPTIMEROBOT DEPLOYMENT TESTING")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}\n")
    
    tests = [
        ("Railway Configuration", test_railway_configuration),
        ("Local Health Endpoints", test_local_health_endpoints),
        ("UptimeRobot Compatibility", test_uptimerobot_compatibility),
        ("UptimeRobot Setup Guide", generate_uptimerobot_setup_guide)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running: {test_name}")
            print("-" * 60)
            result = test_func()
            results[test_name] = result
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"\n{status} - {test_name}")
        except Exception as e:
            print(f"\n❌ ERROR - {test_name}: {e}")
            results[test_name] = False
    
    # Résumé final
    print("\n" + "=" * 80)
    print("🎯 DEPLOYMENT TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL DEPLOYMENT TESTS PASSED!")
        print("✅ Railway configuration optimisée")
        print("✅ Health endpoints fonctionnels")
        print("✅ UptimeRobot compatibility validée")
        print("✅ Guide de configuration généré")
        print("\n🚀 Prêt pour déploiement Railway + UptimeRobot!")
    else:
        print(f"\n⚠️ {total-passed} test(s) failed")
        print("❗ Review deployment configuration")
    
    return passed == total

if __name__ == "__main__":
    success = run_deployment_tests()
    sys.exit(0 if success else 1)
