#!/usr/bin/env python3
"""
Simple API testing script for Safecast API endpoints
"""
import requests
import json
import sys
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test basic health check endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✓ Health check: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_docs_endpoint():
    """Test API documentation endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/docs")
        print(f"✓ Docs endpoint: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Docs endpoint failed: {e}")
        return False

def test_bgeigie_imports_list():
    """Test bGeigie imports list endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/bgeigie_imports/")
        print(f"✓ bGeigie imports list: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Found {len(data)} imports")
            return True
        return False
    except Exception as e:
        print(f"✗ bGeigie imports list failed: {e}")
        return False

def test_measurements_endpoint():
    """Test measurements endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/measurements/")
        print(f"✓ Measurements endpoint: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Found {len(data)} measurements")
            return True
        return False
    except Exception as e:
        print(f"✗ Measurements endpoint failed: {e}")
        return False

def create_sample_log_file():
    """Create a sample bGeigie log file for testing"""
    sample_content = """# NEW BGEIGIENAN
# format=1.4.0
$BNRDD,300,2023-08-24T02:00:00Z,35.6762,139.6503,0.12,A,1800,0*7E
$BNRDD,301,2023-08-24T02:00:01Z,35.6763,139.6504,0.13,A,1801,0*7F
$BNRDD,302,2023-08-24T02:00:02Z,35.6764,139.6505,0.11,A,1802,0*7D
"""
    
    test_file = Path("test_bgeigie.log")
    test_file.write_text(sample_content)
    return test_file

def test_file_upload():
    """Test file upload functionality"""
    try:
        # Create sample file
        test_file = create_sample_log_file()
        
        with open(test_file, 'rb') as f:
            files = {'file': ('test_bgeigie.log', f, 'text/plain')}
            data = {
                'name': 'Test Upload',
                'description': 'API test upload',
                'cities': 'Tokyo',
                'credits': 'Test User'
            }
            
            response = requests.post(f"{BASE_URL}/api/v1/bgeigie_imports/", 
                                   files=files, data=data)
            
            print(f"✓ File upload: {response.status_code}")
            if response.status_code in [200, 201]:
                result = response.json()
                print(f"  Upload ID: {result.get('id')}")
                print(f"  Status: {result.get('status')}")
                return result.get('id')
            else:
                print(f"  Error: {response.text}")
                return None
                
    except Exception as e:
        print(f"✗ File upload failed: {e}")
        return None
    finally:
        # Clean up test file
        if test_file.exists():
            test_file.unlink()

def test_import_detail(import_id):
    """Test import detail endpoint"""
    if not import_id:
        return False
        
    try:
        response = requests.get(f"{BASE_URL}/api/v1/bgeigie_imports/{import_id}")
        print(f"✓ Import detail: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Import name: {data.get('name')}")
            print(f"  Status: {data.get('status')}")
            print(f"  Measurements: {data.get('measurements_count', 0)}")
            return True
        return False
    except Exception as e:
        print(f"✗ Import detail failed: {e}")
        return False

def main():
    """Run all API tests"""
    print("🧪 Testing Safecast API endpoints...\n")
    
    tests = [
        ("Health Check", test_health_check),
        ("Docs Endpoint", test_docs_endpoint),
        ("bGeigie Imports List", test_bgeigie_imports_list),
        ("Measurements Endpoint", test_measurements_endpoint),
    ]
    
    results = {}
    for name, test_func in tests:
        print(f"\n--- {name} ---")
        results[name] = test_func()
    
    # Test file upload
    print(f"\n--- File Upload ---")
    import_id = test_file_upload()
    results["File Upload"] = import_id is not None
    
    # Test import detail if upload succeeded
    if import_id:
        print(f"\n--- Import Detail ---")
        results["Import Detail"] = test_import_detail(import_id)
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 Test Results Summary:")
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
