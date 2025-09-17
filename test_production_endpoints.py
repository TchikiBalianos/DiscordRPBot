#!/usr/bin/env python3
"""
Test Production Endpoints - Phase 4D
Teste les endpoints après déploiement Railway
"""

import sys
import requests
import time
from datetime import datetime

def test_production_endpoints(base_url):
    """Test endpoints en production"""
    print(f"TESTING PRODUCTION DEPLOYMENT: {base_url}")
    print("=" * 70)
    
    endpoints = [
        ("/health", "UptimeRobot Health Check"),
        ("/health/detailed", "Detailed Health Status"),
        ("/health/resilience", "Connection Resilience"),
        ("/metrics", "Performance Metrics"),
        ("/status", "System Status")
    ]
    
    results = {}
    
    for endpoint, description in endpoints:
        print(f"\nTesting: {description}")
        print(f"URL: {base_url}{endpoint}")
        
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=30)
            
            results[endpoint] = {
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "success": response.status_code in [200, 503]
            }
            
            print(f"Status: {response.status_code}")
            print(f"Response time: {response.elapsed.total_seconds():.3f}s")
            
            if response.status_code == 200:
                print("✅ SUCCESS")
                
                # Validation spécifique pour /health
                if endpoint == "/health":
                    try:
                        data = response.json()
                        if data.get("status") == "alive":
                            print("✅ UptimeRobot keyword 'alive' found")
                        else:
                            print("⚠️ Missing 'alive' keyword for UptimeRobot")
                    except:
                        print("⚠️ Invalid JSON response")
                        
            elif response.status_code == 503:
                print("⚠️ SERVICE DEGRADED (acceptable for detailed health)")
            else:
                print("❌ FAILED")
                
        except requests.exceptions.Timeout:
            print("❌ TIMEOUT (>30s)")
            results[endpoint] = {"success": False, "error": "timeout"}
        except requests.exceptions.ConnectionError:
            print("❌ CONNECTION ERROR")
            results[endpoint] = {"success": False, "error": "connection"}
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results[endpoint] = {"success": False, "error": str(e)}
    
    return results

def test_uptimerobot_simulation(base_url):
    """Simule le comportement d'UptimeRobot"""
    print("\nUPTIMEROBOT SIMULATION")
    print("=" * 50)
    
    # Test 5 requêtes comme UptimeRobot
    print("Simulating UptimeRobot checks (5 requests over 25 seconds)...")
    
    success_count = 0
    response_times = []
    
    for i in range(5):
        try:
            start_time = time.time()
            response = requests.get(f"{base_url}/health", timeout=30)
            end_time = time.time()
            
            response_time = end_time - start_time
            response_times.append(response_time)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "alive":
                    success_count += 1
                    print(f"Check {i+1}/5: ✅ UP ({response_time:.3f}s)")
                else:
                    print(f"Check {i+1}/5: ❌ Wrong keyword")
            else:
                print(f"Check {i+1}/5: ❌ Status {response.status_code}")
            
            if i < 4:  # Pause sauf dernier
                time.sleep(5)
                
        except Exception as e:
            print(f"Check {i+1}/5: ❌ Error: {e}")
    
    # Résultats
    uptime_percentage = (success_count / 5) * 100
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    print(f"\nUptimeRobot Simulation Results:")
    print(f"Uptime: {uptime_percentage:.1f}% ({success_count}/5)")
    print(f"Avg Response Time: {avg_response_time:.3f}s")
    
    if uptime_percentage >= 80:
        print("✅ UptimeRobot would show GREEN status")
    else:
        print("❌ UptimeRobot would show RED status")
    
    return uptime_percentage >= 80

def generate_production_report(base_url, test_results, uptimerobot_ok):
    """Génère rapport de test production"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    report = f"""
PRODUCTION DEPLOYMENT TEST REPORT
Generated: {timestamp}
Target URL: {base_url}

ENDPOINT TESTS:
"""
    
    for endpoint, result in test_results.items():
        status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
        response_time = result.get("response_time", 0)
        report += f"  {endpoint}: {status} ({response_time:.3f}s)\n"
    
    passed = sum(1 for r in test_results.values() if r.get("success", False))
    total = len(test_results)
    
    report += f"""
SUMMARY:
  Endpoints: {passed}/{total} successful
  UptimeRobot simulation: {'✅ PASS' if uptimerobot_ok else '❌ FAIL'}
  
DEPLOYMENT STATUS: {'✅ PRODUCTION READY' if passed >= 3 and uptimerobot_ok else '❌ NEEDS ATTENTION'}

NEXT STEPS:
  1. Configure UptimeRobot monitor with URL: {base_url}/health
  2. Set keyword monitoring: 'alive'
  3. Configure email alerts
  4. Monitor for 24h to ensure stability
"""
    
    try:
        with open("production_test_report.txt", "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n📋 Report saved to: production_test_report.txt")
    except Exception as e:
        print(f"⚠️ Could not save report: {e}")
    
    print(report)
    return passed >= 3 and uptimerobot_ok

def main():
    """Test déploiement production"""
    if len(sys.argv) != 2:
        print("Usage: python test_production_endpoints.py <base_url>")
        print("Example: python test_production_endpoints.py https://your-app.railway.app")
        return False
    
    base_url = sys.argv[1].rstrip('/')
    
    print("🚀 PRODUCTION DEPLOYMENT TESTING")
    print("=" * 70)
    print(f"Testing deployment at: {base_url}")
    print(f"Started: {datetime.now().isoformat()}\n")
    
    try:
        # Test endpoints
        test_results = test_production_endpoints(base_url)
        
        # Test UptimeRobot simulation
        uptimerobot_ok = test_uptimerobot_simulation(base_url)
        
        # Générer rapport
        success = generate_production_report(base_url, test_results, uptimerobot_ok)
        
        return success
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
