#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Bitcoin Passphrase Cracking Bot
Tests all API endpoints, database operations, and edge cases
"""

import requests
import json
import time
import sys
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://67759e13-7d38-4161-a006-b1c1a9442f40.preview.emergentagent.com/api"

class BackendTester:
    def __init__(self):
        self.test_results = []
        self.failed_tests = []
        
    def log_test(self, test_name, success, message="", details=None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"   {message}")
        if not success:
            self.failed_tests.append(test_name)
        print()
    
    def test_api_connectivity(self):
        """Test basic API connectivity"""
        try:
            response = requests.get(f"{BACKEND_URL}/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "Bitcoin Passphrase Cracking Bot" in data.get("message", ""):
                    self.log_test("API Connectivity", True, "Backend is accessible and responding")
                    return True
                else:
                    self.log_test("API Connectivity", False, f"Unexpected response: {data}")
                    return False
            else:
                self.log_test("API Connectivity", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("API Connectivity", False, f"Connection failed: {str(e)}")
            return False
    
    def test_status_endpoint(self):
        """Test /api/status endpoint"""
        try:
            response = requests.get(f"{BACKEND_URL}/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                required_fields = ["is_running", "current_passphrase", "total_attempts", "found_keys", "progress"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    self.log_test("Status Endpoint", True, f"Status: {data}")
                    return data
                else:
                    self.log_test("Status Endpoint", False, f"Missing fields: {missing_fields}")
                    return None
            else:
                self.log_test("Status Endpoint", False, f"HTTP {response.status_code}: {response.text}")
                return None
        except Exception as e:
            self.log_test("Status Endpoint", False, f"Request failed: {str(e)}")
            return None
    
    def test_clear_data_endpoint(self):
        """Test /api/clear-data endpoint"""
        try:
            response = requests.delete(f"{BACKEND_URL}/clear-data", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "cleared" in data.get("message", "").lower():
                    self.log_test("Clear Data Endpoint", True, "Data cleared successfully")
                    return True
                else:
                    self.log_test("Clear Data Endpoint", False, f"Unexpected response: {data}")
                    return False
            else:
                self.log_test("Clear Data Endpoint", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Clear Data Endpoint", False, f"Request failed: {str(e)}")
            return False
    
    def test_crypto_functions(self):
        """Test /api/test-crypto endpoint with various passphrases"""
        test_passphrases = ["password", "123456", "test", "bitcoin"]
        
        for passphrase in test_passphrases:
            try:
                response = requests.post(f"{BACKEND_URL}/test-crypto", 
                                       params={"passphrase": passphrase}, 
                                       timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    required_fields = ["passphrase", "private_key", "bitcoin_address", "balance"]
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if not missing_fields:
                        # Validate data format
                        if (len(data["private_key"]) == 64 and  # 32 bytes in hex
                            data["bitcoin_address"].startswith("1") and  # Bitcoin mainnet address
                            isinstance(data["balance"], (int, float))):
                            self.log_test(f"Crypto Functions - {passphrase}", True, 
                                        f"Address: {data['bitcoin_address']}, Balance: {data['balance']} BTC")
                        else:
                            self.log_test(f"Crypto Functions - {passphrase}", False, 
                                        f"Invalid data format: {data}")
                    else:
                        self.log_test(f"Crypto Functions - {passphrase}", False, 
                                    f"Missing fields: {missing_fields}")
                else:
                    self.log_test(f"Crypto Functions - {passphrase}", False, 
                                f"HTTP {response.status_code}: {response.text}")
            except Exception as e:
                self.log_test(f"Crypto Functions - {passphrase}", False, f"Request failed: {str(e)}")
    
    def test_start_cracking_when_stopped(self):
        """Test starting cracking when not running"""
        try:
            response = requests.post(f"{BACKEND_URL}/start-cracking", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "started" in data.get("message", "").lower():
                    self.log_test("Start Cracking (When Stopped)", True, "Cracking started successfully")
                    return True
                else:
                    self.log_test("Start Cracking (When Stopped)", False, f"Unexpected response: {data}")
                    return False
            else:
                self.log_test("Start Cracking (When Stopped)", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Start Cracking (When Stopped)", False, f"Request failed: {str(e)}")
            return False
    
    def test_start_cracking_when_running(self):
        """Test starting cracking when already running (should fail)"""
        try:
            response = requests.post(f"{BACKEND_URL}/start-cracking", timeout=10)
            if response.status_code == 400:
                data = response.json()
                if "already running" in data.get("detail", "").lower():
                    self.log_test("Start Cracking (When Running)", True, "Correctly rejected duplicate start")
                    return True
                else:
                    self.log_test("Start Cracking (When Running)", False, f"Wrong error message: {data}")
                    return False
            else:
                self.log_test("Start Cracking (When Running)", False, 
                            f"Expected HTTP 400, got {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Start Cracking (When Running)", False, f"Request failed: {str(e)}")
            return False
    
    def test_stop_cracking(self):
        """Test stopping cracking"""
        try:
            response = requests.post(f"{BACKEND_URL}/stop-cracking", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "stopped" in data.get("message", "").lower():
                    self.log_test("Stop Cracking", True, "Cracking stopped successfully")
                    return True
                else:
                    self.log_test("Stop Cracking", False, f"Unexpected response: {data}")
                    return False
            else:
                self.log_test("Stop Cracking", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Stop Cracking", False, f"Request failed: {str(e)}")
            return False
    
    def test_status_during_cracking(self):
        """Test status updates during cracking process"""
        # Start cracking
        start_response = requests.post(f"{BACKEND_URL}/start-cracking", timeout=10)
        if start_response.status_code != 200:
            self.log_test("Status During Cracking", False, "Could not start cracking for test")
            return False
        
        # Wait a bit and check status
        time.sleep(3)
        
        try:
            response = requests.get(f"{BACKEND_URL}/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("is_running") and data.get("total_attempts", 0) > 0:
                    self.log_test("Status During Cracking", True, 
                                f"Status updating correctly: {data['total_attempts']} attempts, {data['progress']:.1f}% progress")
                    
                    # Stop cracking for cleanup
                    requests.post(f"{BACKEND_URL}/stop-cracking", timeout=10)
                    return True
                else:
                    self.log_test("Status During Cracking", False, f"Status not updating: {data}")
                    requests.post(f"{BACKEND_URL}/stop-cracking", timeout=10)
                    return False
            else:
                self.log_test("Status During Cracking", False, f"HTTP {response.status_code}: {response.text}")
                requests.post(f"{BACKEND_URL}/stop-cracking", timeout=10)
                return False
        except Exception as e:
            self.log_test("Status During Cracking", False, f"Request failed: {str(e)}")
            requests.post(f"{BACKEND_URL}/stop-cracking", timeout=10)
            return False
    
    def test_attempts_endpoint(self):
        """Test /api/attempts endpoint"""
        try:
            # Test with default limit
            response = requests.get(f"{BACKEND_URL}/attempts", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Attempts Endpoint (Default)", True, f"Retrieved {len(data)} attempts")
                    
                    # Test with custom limit
                    response2 = requests.get(f"{BACKEND_URL}/attempts?limit=5", timeout=10)
                    if response2.status_code == 200:
                        data2 = response2.json()
                        if isinstance(data2, list) and len(data2) <= 5:
                            self.log_test("Attempts Endpoint (Limited)", True, f"Retrieved {len(data2)} attempts with limit=5")
                            return True
                        else:
                            self.log_test("Attempts Endpoint (Limited)", False, f"Limit not working: got {len(data2)} items")
                            return False
                    else:
                        self.log_test("Attempts Endpoint (Limited)", False, f"HTTP {response2.status_code}: {response2.text}")
                        return False
                else:
                    self.log_test("Attempts Endpoint (Default)", False, f"Expected list, got: {type(data)}")
                    return False
            else:
                self.log_test("Attempts Endpoint (Default)", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Attempts Endpoint", False, f"Request failed: {str(e)}")
            return False
    
    def test_results_endpoint(self):
        """Test /api/results endpoint"""
        try:
            response = requests.get(f"{BACKEND_URL}/results", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Results Endpoint", True, f"Retrieved {len(data)} results")
                    return True
                else:
                    self.log_test("Results Endpoint", False, f"Expected list, got: {type(data)}")
                    return False
            else:
                self.log_test("Results Endpoint", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Results Endpoint", False, f"Request failed: {str(e)}")
            return False
    
    def test_database_persistence(self):
        """Test that data persists in database"""
        # Clear data first
        self.test_clear_data_endpoint()
        
        # Generate some test data by running crypto test
        requests.post(f"{BACKEND_URL}/test-crypto", params={"passphrase": "testdata"}, timeout=15)
        
        # Start and quickly stop cracking to generate attempts
        requests.post(f"{BACKEND_URL}/start-cracking", timeout=10)
        time.sleep(2)  # Let it run briefly
        requests.post(f"{BACKEND_URL}/stop-cracking", timeout=10)
        
        # Check if attempts were stored
        try:
            response = requests.get(f"{BACKEND_URL}/attempts?limit=10", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if len(data) > 0:
                    # Verify data structure
                    attempt = data[0]
                    required_fields = ["passphrase", "private_key", "bitcoin_address", "balance", "attempted_at"]
                    missing_fields = [field for field in required_fields if field not in attempt]
                    
                    if not missing_fields:
                        self.log_test("Database Persistence", True, 
                                    f"Data persisted correctly: {len(data)} attempts stored")
                        return True
                    else:
                        self.log_test("Database Persistence", False, 
                                    f"Stored data missing fields: {missing_fields}")
                        return False
                else:
                    self.log_test("Database Persistence", False, "No attempts were stored in database")
                    return False
            else:
                self.log_test("Database Persistence", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Database Persistence", False, f"Request failed: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Comprehensive Backend Testing for Bitcoin Passphrase Cracking Bot")
        print("=" * 80)
        
        # Test basic connectivity first
        if not self.test_api_connectivity():
            print("❌ Backend is not accessible. Stopping tests.")
            return False
        
        # Test all endpoints and functionality
        print("\n📡 Testing API Endpoints...")
        self.test_status_endpoint()
        self.test_clear_data_endpoint()
        
        print("\n🔐 Testing Crypto Functions...")
        self.test_crypto_functions()
        
        print("\n⚙️ Testing Cracking Control...")
        # Ensure we start from stopped state
        requests.post(f"{BACKEND_URL}/stop-cracking", timeout=10)
        
        self.test_start_cracking_when_stopped()
        self.test_start_cracking_when_running()
        self.test_status_during_cracking()
        self.test_stop_cracking()
        
        print("\n💾 Testing Data Endpoints...")
        self.test_attempts_endpoint()
        self.test_results_endpoint()
        self.test_database_persistence()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t["success"]])
        failed_tests = len(self.failed_tests)
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if self.failed_tests:
            print(f"\n❌ Failed Tests:")
            for test in self.failed_tests:
                print(f"   - {test}")
        
        return failed_tests == 0

if __name__ == "__main__":
    tester = BackendTester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open("/app/backend_test_results.json", "w") as f:
        json.dump(tester.test_results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: /app/backend_test_results.json")
    
    sys.exit(0 if success else 1)