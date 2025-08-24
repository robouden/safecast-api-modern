#!/usr/bin/env python3
"""Simple frontend test for Safecast API"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_main_page():
    """Test main page accessibility"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"Main page: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Main page error: {e}")
        return False

def test_import_detail_pages():
    """Test import detail pages for existing imports"""
    try:
        # Get list of imports first
        imports_response = requests.get(f"{BASE_URL}/api/v1/bgeigie_imports/")
        if imports_response.status_code != 200:
            print("Could not get imports list")
            return False
            
        imports_data = imports_response.json()
        print(f"Found {len(imports_data)} imports")
        
        # Test detail pages for first few imports
        test_imports = imports_data[:3] if len(imports_data) >= 3 else imports_data
        for import_item in test_imports:
            import_id = import_item['id']
            detail_response = requests.get(f"{BASE_URL}/bgeigie-imports/{import_id}")
            status = "✅" if detail_response.status_code == 200 else "❌"
            print(f"  Import {import_id} detail page: {detail_response.status_code} {status}")
            
        return True
    except Exception as e:
        print(f"Import detail pages error: {e}")
        return False

def test_api_endpoints():
    """Test key API endpoints"""
    endpoints = [
        "/api/v1/bgeigie_imports/",
        "/api/v1/measurements/",
        "/docs"
    ]
    
    results = {}
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            status = "✅" if response.status_code == 200 else "❌"
            results[endpoint] = response.status_code == 200
            print(f"  {endpoint}: {response.status_code} {status}")
        except Exception as e:
            results[endpoint] = False
            print(f"  {endpoint}: Error - {e}")
    
    return all(results.values())

def main():
    print("🧪 Frontend Testing...")
    
    tests = [
        ("Main Page", test_main_page),
        ("Import Detail Pages", test_import_detail_pages),
        ("API Endpoints", test_api_endpoints)
    ]
    
    results = {}
    for name, test_func in tests:
        print(f"\n--- {name} ---")
        results[name] = test_func()
    
    print(f"\n{'='*40}")
    print("Frontend Test Summary:")
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    return passed == total

if __name__ == "__main__":
    main()
