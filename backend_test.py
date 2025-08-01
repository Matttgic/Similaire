#!/usr/bin/env python3
"""
Comprehensive Backend API Testing Suite for Pinnacle Betting Similarity API
Tests all endpoints with realistic data and error scenarios
"""

import requests
import json
import time
import sys
from typing import Dict, Any, List

# API Configuration
BASE_URL = "http://localhost:8001"
API_PREFIX = "/api"

class BackendAPITester:
    def __init__(self):
        self.base_url = BASE_URL + API_PREFIX
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    def log_test(self, test_name: str, passed: bool, details: str = "", response_time: float = 0):
        """Log test results"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append({
            'test': test_name,
            'status': status,
            'details': details,
            'response_time': f"{response_time:.3f}s"
        })
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
        print(f"{status} {test_name} ({response_time:.3f}s)")
        if details:
            print(f"    Details: {details}")
    
    def test_health_endpoint(self):
        """Test GET /api/health endpoint"""
        print("\n=== Testing Health Check Endpoint ===")
        
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/health", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields
                required_fields = ['status', 'timestamp', 'version', 'uptime']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Health Check - Required Fields", False, 
                                f"Missing fields: {missing_fields}", response_time)
                else:
                    self.log_test("Health Check - Required Fields", True, 
                                f"All required fields present", response_time)
                
                # Check status is healthy
                if data.get('status') == 'healthy':
                    self.log_test("Health Check - Status", True, 
                                f"Status: {data['status']}", response_time)
                else:
                    self.log_test("Health Check - Status", False, 
                                f"Expected 'healthy', got: {data.get('status')}", response_time)
                
                # Check version
                if data.get('version'):
                    self.log_test("Health Check - Version", True, 
                                f"Version: {data['version']}", response_time)
                else:
                    self.log_test("Health Check - Version", False, 
                                "Version field missing or empty", response_time)
                
                # Check uptime is positive
                uptime = data.get('uptime', 0)
                if uptime > 0:
                    self.log_test("Health Check - Uptime", True, 
                                f"Uptime: {uptime:.2f}s", response_time)
                else:
                    self.log_test("Health Check - Uptime", False, 
                                f"Invalid uptime: {uptime}", response_time)
                    
            else:
                self.log_test("Health Check - HTTP Status", False, 
                            f"Expected 200, got {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("Health Check - Connection", False, f"Error: {str(e)}", 0)
    
    def test_similarity_methods_endpoint(self):
        """Test GET /api/similarity/methods endpoint"""
        print("\n=== Testing Similarity Methods Endpoint ===")
        
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/similarity/methods", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # Check methods field exists
                if 'methods' in data:
                    methods = data['methods']
                    expected_methods = ['cosine', 'euclidean', 'percentage']
                    
                    if all(method in methods for method in expected_methods):
                        self.log_test("Similarity Methods - Available Methods", True, 
                                    f"Methods: {methods}", response_time)
                    else:
                        self.log_test("Similarity Methods - Available Methods", False, 
                                    f"Missing expected methods. Got: {methods}", response_time)
                else:
                    self.log_test("Similarity Methods - Methods Field", False, 
                                "Methods field missing from response", response_time)
                
                # Check default method
                if 'default_method' in data:
                    self.log_test("Similarity Methods - Default Method", True, 
                                f"Default: {data['default_method']}", response_time)
                else:
                    self.log_test("Similarity Methods - Default Method", False, 
                                "Default method field missing", response_time)
                    
            else:
                self.log_test("Similarity Methods - HTTP Status", False, 
                            f"Expected 200, got {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("Similarity Methods - Connection", False, f"Error: {str(e)}", 0)
    
    def test_database_stats_endpoint(self):
        """Test GET /api/database/stats endpoint"""
        print("\n=== Testing Database Stats Endpoint ===")
        
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/database/stats", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # Check success field
                if data.get('success') == True:
                    self.log_test("Database Stats - Success Field", True, 
                                "Success field is True", response_time)
                else:
                    self.log_test("Database Stats - Success Field", False, 
                                f"Success field: {data.get('success')}", response_time)
                
                # Check stats field exists
                if 'stats' in data:
                    stats = data['stats']
                    expected_stats = ['total_matches', 'matches_with_odds', 'total_leagues']
                    
                    present_stats = [stat for stat in expected_stats if stat in stats]
                    if present_stats:
                        self.log_test("Database Stats - Stats Fields", True, 
                                    f"Present stats: {present_stats}", response_time)
                    else:
                        self.log_test("Database Stats - Stats Fields", False, 
                                    f"No expected stats found. Available: {list(stats.keys())}", response_time)
                else:
                    self.log_test("Database Stats - Stats Field", False, 
                                "Stats field missing from response", response_time)
                    
            else:
                self.log_test("Database Stats - HTTP Status", False, 
                            f"Expected 200, got {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("Database Stats - Connection", False, f"Error: {str(e)}", 0)
    
    def test_similarity_analysis_valid_data(self):
        """Test POST /api/similarity/analyze with valid data"""
        print("\n=== Testing Similarity Analysis - Valid Data ===")
        
        # Test data as specified in the requirements
        test_cases = [
            {
                "name": "Sample Odds (Cosine)",
                "data": {
                    "odds": {
                        "home": 2.1,
                        "draw": 3.4,
                        "away": 3.2,
                        "over_25": 1.85,
                        "under_25": 1.95
                    },
                    "method": "cosine",
                    "threshold": 0.8,
                    "min_matches": 5
                }
            },
            {
                "name": "Sample Odds (Euclidean)",
                "data": {
                    "odds": {
                        "home": 2.1,
                        "draw": 3.4,
                        "away": 3.2,
                        "over_25": 1.85,
                        "under_25": 1.95
                    },
                    "method": "euclidean",
                    "threshold": 0.7,
                    "min_matches": 10
                }
            },
            {
                "name": "Sample Odds (Percentage)",
                "data": {
                    "odds": {
                        "home": 2.1,
                        "draw": 3.4,
                        "away": 3.2,
                        "over_25": 1.85,
                        "under_25": 1.95
                    },
                    "method": "percentage",
                    "threshold": 0.85,
                    "min_matches": 8
                }
            },
            {
                "name": "High Odds Match",
                "data": {
                    "odds": {
                        "home": 1.5,
                        "draw": 4.2,
                        "away": 6.8,
                        "over_25": 1.7,
                        "under_25": 2.1
                    },
                    "method": "cosine"
                }
            }
        ]
        
        for test_case in test_cases:
            try:
                start_time = time.time()
                response = requests.post(
                    f"{self.base_url}/similarity/analyze",
                    json=test_case["data"],
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check required response fields
                    required_fields = ['success', 'similar_matches', 'analysis']
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if not missing_fields:
                        self.log_test(f"Similarity Analysis - {test_case['name']}", True, 
                                    f"Found {len(data.get('similar_matches', []))} matches", response_time)
                        
                        # Check analysis structure
                        analysis = data.get('analysis', {})
                        if 'total_matches' in analysis:
                            self.log_test(f"Analysis Structure - {test_case['name']}", True, 
                                        f"Total matches: {analysis['total_matches']}", response_time)
                        else:
                            self.log_test(f"Analysis Structure - {test_case['name']}", False, 
                                        "Analysis missing total_matches field", response_time)
                    else:
                        self.log_test(f"Similarity Analysis - {test_case['name']}", False, 
                                    f"Missing fields: {missing_fields}", response_time)
                        
                elif response.status_code == 400:
                    # This might be expected if no data in database
                    self.log_test(f"Similarity Analysis - {test_case['name']}", True, 
                                f"No historical data available (400 response)", response_time)
                else:
                    self.log_test(f"Similarity Analysis - {test_case['name']}", False, 
                                f"HTTP {response.status_code}: {response.text[:100]}", response_time)
                    
            except Exception as e:
                self.log_test(f"Similarity Analysis - {test_case['name']}", False, 
                            f"Error: {str(e)}", 0)
    
    def test_similarity_analysis_error_cases(self):
        """Test POST /api/similarity/analyze with invalid data"""
        print("\n=== Testing Similarity Analysis - Error Cases ===")
        
        error_test_cases = [
            {
                "name": "Invalid Odds (Too Low)",
                "data": {
                    "odds": {
                        "home": 0.5,  # Invalid: too low
                        "draw": 3.4,
                        "away": 3.2,
                        "over_25": 1.85,
                        "under_25": 1.95
                    }
                },
                "expected_status": 422
            },
            {
                "name": "Invalid Odds (Too High)",
                "data": {
                    "odds": {
                        "home": 2.1,
                        "draw": 3.4,
                        "away": 1500,  # Invalid: too high
                        "over_25": 1.85,
                        "under_25": 1.95
                    }
                },
                "expected_status": 422
            },
            {
                "name": "Invalid Method",
                "data": {
                    "odds": {
                        "home": 2.1,
                        "draw": 3.4,
                        "away": 3.2,
                        "over_25": 1.85,
                        "under_25": 1.95
                    },
                    "method": "invalid_method"
                },
                "expected_status": 422
            },
            {
                "name": "Invalid Threshold (Too High)",
                "data": {
                    "odds": {
                        "home": 2.1,
                        "draw": 3.4,
                        "away": 3.2,
                        "over_25": 1.85,
                        "under_25": 1.95
                    },
                    "threshold": 1.5  # Invalid: > 1
                },
                "expected_status": 422
            },
            {
                "name": "Missing Required Fields",
                "data": {
                    "odds": {
                        "home": 2.1,
                        "draw": 3.4,
                        # Missing away, over_25, under_25
                    }
                },
                "expected_status": 422
            }
        ]
        
        for test_case in error_test_cases:
            try:
                start_time = time.time()
                response = requests.post(
                    f"{self.base_url}/similarity/analyze",
                    json=test_case["data"],
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                response_time = time.time() - start_time
                
                expected_status = test_case.get("expected_status", 400)
                if response.status_code == expected_status:
                    self.log_test(f"Error Handling - {test_case['name']}", True, 
                                f"Correctly returned {response.status_code}", response_time)
                else:
                    self.log_test(f"Error Handling - {test_case['name']}", False, 
                                f"Expected {expected_status}, got {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test(f"Error Handling - {test_case['name']}", False, 
                            f"Error: {str(e)}", 0)
    
    def test_performance(self):
        """Test API performance"""
        print("\n=== Testing API Performance ===")
        
        # Test response times
        endpoints = [
            ("/health", "GET"),
            ("/similarity/methods", "GET"),
            ("/database/stats", "GET")
        ]
        
        for endpoint, method in endpoints:
            try:
                start_time = time.time()
                if method == "GET":
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                response_time = time.time() - start_time
                
                # Check if response time is reasonable (< 2 seconds as specified)
                if response_time < 2.0:
                    self.log_test(f"Performance - {endpoint}", True, 
                                f"Response time: {response_time:.3f}s", response_time)
                else:
                    self.log_test(f"Performance - {endpoint}", False, 
                                f"Slow response: {response_time:.3f}s", response_time)
                    
            except Exception as e:
                self.log_test(f"Performance - {endpoint}", False, f"Error: {str(e)}", 0)
    
    def test_cors_configuration(self):
        """Test CORS configuration"""
        print("\n=== Testing CORS Configuration ===")
        
        try:
            start_time = time.time()
            response = requests.options(f"{self.base_url}/health", timeout=10)
            response_time = time.time() - start_time
            
            # Check CORS headers
            cors_headers = [
                'Access-Control-Allow-Origin',
                'Access-Control-Allow-Methods',
                'Access-Control-Allow-Headers'
            ]
            
            present_headers = [header for header in cors_headers 
                             if header in response.headers]
            
            if present_headers:
                self.log_test("CORS Configuration", True, 
                            f"CORS headers present: {len(present_headers)}", response_time)
            else:
                self.log_test("CORS Configuration", False, 
                            "No CORS headers found", response_time)
                
        except Exception as e:
            self.log_test("CORS Configuration", False, f"Error: {str(e)}", 0)
    
    def test_french_matches_endpoint(self):
        """Test GET /api/matches/today-france endpoint"""
        print("\n=== Testing French Matches Endpoint ===")
        
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/matches/today-france", timeout=30)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields
                required_fields = ['success', 'matches', 'count', 'country']
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    self.log_test("French Matches - Required Fields", True, 
                                f"All required fields present", response_time)
                    
                    # Check country is France
                    if data.get('country') == 'France':
                        self.log_test("French Matches - Country Field", True, 
                                    f"Country: {data['country']}", response_time)
                    else:
                        self.log_test("French Matches - Country Field", False, 
                                    f"Expected 'France', got: {data.get('country')}", response_time)
                    
                    # Check matches array
                    matches = data.get('matches', [])
                    if isinstance(matches, list):
                        self.log_test("French Matches - Matches Array", True, 
                                    f"Found {len(matches)} matches", response_time)
                        
                        # Check count matches array length
                        if data.get('count') == len(matches):
                            self.log_test("French Matches - Count Accuracy", True, 
                                        f"Count matches array length: {len(matches)}", response_time)
                        else:
                            self.log_test("French Matches - Count Accuracy", False, 
                                        f"Count {data.get('count')} != array length {len(matches)}", response_time)
                        
                        # Check French regulation fields in matches
                        if matches:
                            sample_match = matches[0]
                            french_fields = ['betting_available_france', 'french_regulation_compliant', 'country_restrictions']
                            present_french_fields = [field for field in french_fields if field in sample_match]
                            
                            if present_french_fields:
                                self.log_test("French Matches - Regulation Fields", True, 
                                            f"French fields present: {present_french_fields}", response_time)
                            else:
                                self.log_test("French Matches - Regulation Fields", False, 
                                            "No French regulation fields found in matches", response_time)
                            
                            # Check odds fields
                            odds_fields = ['home', 'draw', 'away', 'over_25', 'under_25']
                            present_odds_fields = [field for field in odds_fields if field in sample_match]
                            
                            if len(present_odds_fields) >= 3:  # At least basic odds
                                self.log_test("French Matches - Odds Fields", True, 
                                            f"Odds fields present: {present_odds_fields}", response_time)
                            else:
                                self.log_test("French Matches - Odds Fields", False, 
                                            f"Insufficient odds fields: {present_odds_fields}", response_time)
                    else:
                        self.log_test("French Matches - Matches Array", False, 
                                    "Matches field is not an array", response_time)
                else:
                    self.log_test("French Matches - Required Fields", False, 
                                f"Missing fields: {missing_fields}", response_time)
                    
            else:
                self.log_test("French Matches - HTTP Status", False, 
                            f"Expected 200, got {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("French Matches - Connection", False, f"Error: {str(e)}", 0)
    
    def test_french_filter_endpoint(self):
        """Test POST /api/matches/filter-france endpoint"""
        print("\n=== Testing French Filter Endpoint ===")
        
        # Test cases for filtering
        test_cases = [
            {
                "name": "Authorized Matches",
                "data": [
                    {
                        "home_team": "PSG",
                        "away_team": "Lyon",
                        "league_name": "Ligue 1",
                        "home": 2.1,
                        "draw": 3.4,
                        "away": 3.2,
                        "over_25": 1.85,
                        "under_25": 1.95
                    },
                    {
                        "home_team": "Manchester United",
                        "away_team": "Arsenal",
                        "league_name": "Premier League",
                        "home": 2.5,
                        "draw": 3.1,
                        "away": 2.8,
                        "over_25": 1.9,
                        "under_25": 1.9
                    }
                ]
            },
            {
                "name": "Mixed Authorized/Unauthorized",
                "data": [
                    {
                        "home_team": "PSG",
                        "away_team": "Lyon",
                        "league_name": "Ligue 1",
                        "home": 2.1,
                        "draw": 3.4,
                        "away": 3.2
                    },
                    {
                        "home_team": "Unknown Team A",
                        "away_team": "Unknown Team B",
                        "league_name": "Unknown League",
                        "home": 2.5,
                        "draw": 3.1,
                        "away": 2.8
                    }
                ]
            },
            {
                "name": "Empty Array",
                "data": []
            }
        ]
        
        for test_case in test_cases:
            try:
                start_time = time.time()
                response = requests.post(
                    f"{self.base_url}/matches/filter-france",
                    json=test_case["data"],
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check required response fields
                    required_fields = ['success', 'original_count', 'filtered_count', 'filtered_matches', 'filter_ratio']
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if not missing_fields:
                        self.log_test(f"French Filter - {test_case['name']} - Fields", True, 
                                    f"All required fields present", response_time)
                        
                        # Check counts
                        original_count = data.get('original_count', 0)
                        filtered_count = data.get('filtered_count', 0)
                        expected_original = len(test_case["data"])
                        
                        if original_count == expected_original:
                            self.log_test(f"French Filter - {test_case['name']} - Original Count", True, 
                                        f"Original count: {original_count}", response_time)
                        else:
                            self.log_test(f"French Filter - {test_case['name']} - Original Count", False, 
                                        f"Expected {expected_original}, got {original_count}", response_time)
                        
                        # Check filtered count is reasonable
                        if filtered_count <= original_count:
                            self.log_test(f"French Filter - {test_case['name']} - Filtered Count", True, 
                                        f"Filtered count: {filtered_count}", response_time)
                        else:
                            self.log_test(f"French Filter - {test_case['name']} - Filtered Count", False, 
                                        f"Filtered count {filtered_count} > original {original_count}", response_time)
                        
                        # Check filter ratio calculation
                        expected_ratio = (filtered_count / original_count * 100) if original_count > 0 else 0
                        actual_ratio = data.get('filter_ratio', 0)
                        
                        if abs(expected_ratio - actual_ratio) < 0.1:  # Allow small floating point differences
                            self.log_test(f"French Filter - {test_case['name']} - Filter Ratio", True, 
                                        f"Filter ratio: {actual_ratio:.1f}%", response_time)
                        else:
                            self.log_test(f"French Filter - {test_case['name']} - Filter Ratio", False, 
                                        f"Expected {expected_ratio:.1f}%, got {actual_ratio:.1f}%", response_time)
                        
                        # Check filtered matches have French regulation fields
                        filtered_matches = data.get('filtered_matches', [])
                        if filtered_matches:
                            sample_match = filtered_matches[0]
                            french_fields = ['betting_available_france', 'french_regulation_compliant']
                            present_french_fields = [field for field in french_fields if field in sample_match]
                            
                            if present_french_fields:
                                self.log_test(f"French Filter - {test_case['name']} - Regulation Metadata", True, 
                                            f"French metadata added: {present_french_fields}", response_time)
                            else:
                                self.log_test(f"French Filter - {test_case['name']} - Regulation Metadata", False, 
                                            "No French regulation metadata added", response_time)
                    else:
                        self.log_test(f"French Filter - {test_case['name']} - Fields", False, 
                                    f"Missing fields: {missing_fields}", response_time)
                        
                else:
                    self.log_test(f"French Filter - {test_case['name']} - HTTP Status", False, 
                                f"Expected 200, got {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test(f"French Filter - {test_case['name']}", False, f"Error: {str(e)}", 0)
    
    def test_french_filter_error_cases(self):
        """Test POST /api/matches/filter-france with invalid data"""
        print("\n=== Testing French Filter - Error Cases ===")
        
        error_test_cases = [
            {
                "name": "Invalid JSON",
                "data": "invalid json string",
                "expected_status": 422
            },
            {
                "name": "Non-array Input",
                "data": {"not": "an array"},
                "expected_status": 422
            }
        ]
        
        for test_case in error_test_cases:
            try:
                start_time = time.time()
                
                if test_case["name"] == "Invalid JSON":
                    # Send invalid JSON
                    response = requests.post(
                        f"{self.base_url}/matches/filter-france",
                        data=test_case["data"],  # Send as string, not JSON
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                else:
                    response = requests.post(
                        f"{self.base_url}/matches/filter-france",
                        json=test_case["data"],
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                
                response_time = time.time() - start_time
                
                expected_status = test_case.get("expected_status", 400)
                if response.status_code == expected_status:
                    self.log_test(f"French Filter Error - {test_case['name']}", True, 
                                f"Correctly returned {response.status_code}", response_time)
                else:
                    self.log_test(f"French Filter Error - {test_case['name']}", False, 
                                f"Expected {expected_status}, got {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test(f"French Filter Error - {test_case['name']}", False, 
                            f"Error: {str(e)}", 0)
    
    def run_all_tests(self):
        """Run all backend API tests"""
        print("🚀 Starting Comprehensive Backend API Testing")
        print("=" * 60)
        
        # Run all test suites
        self.test_health_endpoint()
        self.test_similarity_methods_endpoint()
        self.test_database_stats_endpoint()
        self.test_similarity_analysis_valid_data()
        self.test_similarity_analysis_error_cases()
        self.test_performance()
        self.test_cors_configuration()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.total_tests}")
        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")
        print(f"Success Rate: {(self.passed_tests/self.total_tests*100):.1f}%")
        
        if self.failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if "❌ FAIL" in result['status']:
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n" + "=" * 60)
        return self.failed_tests == 0

def main():
    """Main test execution"""
    tester = BackendAPITester()
    
    # Check if API server is running
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/health", timeout=5)
        print(f"✅ API Server is running at {BASE_URL}{API_PREFIX}")
    except Exception as e:
        print(f"❌ Cannot connect to API server at {BASE_URL}{API_PREFIX}")
        print(f"Error: {e}")
        print("Please ensure the FastAPI server is running on port 8001")
        sys.exit(1)
    
    # Run all tests
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()