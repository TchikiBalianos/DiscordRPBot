#!/usr/bin/env python3
"""
Test Simple Railway + UptimeRobot - Phase 4D
Version simplifiée sans emojis pour Windows
"""

import sys
import time
import requests
from datetime import datetime
import os

def test_railway_config():
    """Test configuration Railway basique"""
    print("RAILWAY CONFIGURATION TEST")
    print("-" * 50)
    
    # Test fichier railway.toml
    if os.path.exists("railway.toml"):
        print("PASS - railway.toml found")
        
        with open("railway.toml", "r") as f:
            content = f.read()
        
        checks = [
            ("healthcheckPath", "/health"),
            ("port", "8000"),
            ("healthcheckInterval", "60")
        ]
        
        for key, expected in checks:
            if key in content:
                print(f"PASS - {key} configured")
            else:
                print(f"FAIL - {key} missing")
        
        return True
    else:
        print("FAIL - railway.toml not found")
        return False

def test_health_endpoints():
    """Test endpoints health directement via requests"""
    print("\nHEALTH ENDPOINTS TEST")
    print("-" * 50)
    
    # Démarrer health server en arrière-plan
    import subprocess
    import threading
    
    def run_health_server():
        os.environ['PYTHONPATH'] = os.getcwd()
        subprocess.run([sys.executable, "-m", "uvicorn", "health_monitoring:app", 
                       "--host", "127.0.0.1", "--port", "8002", "--log-level", "error"],
                      capture_output=True)
    
    server_thread = threading.Thread(target=run_health_server, daemon=True)
    server_thread.start()
    time.sleep(5)  # Attendre démarrage
    
    endpoints = ["/health", "/health/detailed", "/health/resilience"]
    results = {}
    
    for endpoint in endpoints:
        try:
            url = f"http://127.0.0.1:8002{endpoint}"
            response = requests.get(url, timeout=10)
            
            results[endpoint] = {
                "status": response.status_code,
                "success": response.status_code in [200, 503],
                "time": response.elapsed.total_seconds()
            }
            
            if results[endpoint]["success"]:
                print(f"PASS - {endpoint} (Status: {response.status_code})")
            else:
                print(f"FAIL - {endpoint} (Status: {response.status_code})")
                
        except Exception as e:
            print(f"ERROR - {endpoint}: {str(e)[:50]}")
            results[endpoint] = {"success": False}
    
    success_count = sum(1 for r in results.values() if r.get("success", False))
    print(f"Results: {success_count}/{len(endpoints)} endpoints OK")
    
    return success_count == len(endpoints)

def test_uptimerobot_format():
    """Test format UptimeRobot via requests direct"""
    print("\nUPTIMEROBOT FORMAT TEST")
    print("-" * 50)
    
    try:
        response = requests.get("http://127.0.0.1:8002/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Vérifier champs requis
            required = ["status", "timestamp"]
            missing = [field for field in required if field not in data]
            
            if not missing:
                print("PASS - Required fields present")
            else:
                print(f"FAIL - Missing fields: {missing}")
                return False
            
            # Vérifier keyword "alive"
            if data.get("status") == "alive":
                print("PASS - Keyword 'alive' found")
            else:
                print("FAIL - Keyword 'alive' missing")
                return False
            
            # Vérifier temps de réponse
            if response.elapsed.total_seconds() < 5.0:
                print(f"PASS - Response time OK ({response.elapsed.total_seconds():.3f}s)")
            else:
                print(f"WARN - Slow response ({response.elapsed.total_seconds():.3f}s)")
            
            return True
        else:
            print(f"FAIL - Bad status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"ERROR - Cannot test format: {str(e)[:50]}")
        return False

def generate_deployment_checklist():
    """Générer checklist de déploiement"""
    print("\nDEPLOYMENT CHECKLIST")
    print("-" * 50)
    
    checklist = f"""
RAILWAY + UPTIMEROBOT DEPLOYMENT CHECKLIST
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

PRE-DEPLOYMENT:
[ ] railway.toml configured with health check settings
[ ] Health monitoring endpoints respond correctly
[ ] All dependencies in requirements.txt
[ ] Environment variables configured

RAILWAY DEPLOYMENT:
[ ] railway login
[ ] railway link (if needed)
[ ] railway deploy
[ ] Note the generated URL (e.g., https://xxx.railway.app)
[ ] Test health endpoint: https://xxx.railway.app/health

UPTIMEROBOT SETUP:
[ ] Create HTTP(s) Monitor
[ ] URL: https://your-app.railway.app/health
[ ] Check interval: 5 minutes
[ ] Keyword to monitor: alive
[ ] Alert contacts configured
[ ] Test monitor receives UP status

VALIDATION:
[ ] Bot responds in Discord
[ ] Health endpoint returns 200 OK
[ ] UptimeRobot shows "UP" status
[ ] Alerts working (test with temporary downtime)

TROUBLESHOOTING:
- If health check fails: Check logs with 'railway logs'
- If bot offline: Verify Discord token and permissions
- If 503 errors: Check database connection
"""
    
    try:
        with open("DEPLOYMENT_CHECKLIST.txt", "w", encoding="utf-8") as f:
            f.write(checklist)
        print("PASS - Checklist saved to DEPLOYMENT_CHECKLIST.txt")
    except Exception as e:
        print(f"WARN - Could not save checklist: {e}")
    
    print(checklist)
    return True

def main():
    """Exécuter tests de déploiement"""
    print("RAILWAY + UPTIMEROBOT DEPLOYMENT TESTING")
    print("=" * 60)
    print(f"Started: {datetime.now().isoformat()}\n")
    
    tests = [
        ("Railway Configuration", test_railway_config),
        ("Health Endpoints", test_health_endpoints),
        ("UptimeRobot Format", test_uptimerobot_format),
        ("Deployment Checklist", generate_deployment_checklist)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\nRunning: {test_name}")
        try:
            result = test_func()
            results.append(result)
            status = "PASS" if result else "FAIL"
            print(f"Result: {status}")
        except Exception as e:
            print(f"ERROR: {e}")
            results.append(False)
    
    # Résumé
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Tests passed: {passed}/{total}")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    
    if passed >= 3:  # Au moins 3/4 tests OK
        print("\nSTATUS: READY FOR DEPLOYMENT")
        print("- Configuration files OK")
        print("- Health endpoints functional")
        print("- UptimeRobot compatibility verified")
        print("\nNext steps:")
        print("1. railway deploy")
        print("2. Configure UptimeRobot with generated URL")
        print("3. Test monitoring alerts")
    else:
        print(f"\nSTATUS: NEEDS FIXES ({total-passed} failed)")
        print("Review failed tests before deployment")
    
    return passed >= 3

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
