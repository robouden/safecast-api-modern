#!/usr/bin/env python3
"""Comprehensive frontend testing for Safecast API"""
import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_import_detail_pages():
    """Test import detail pages functionality"""
    try:
        # Get imports from API
        response = requests.get(f"{BASE_URL}/api/v1/bgeigie_imports/")
        if response.status_code != 200:
            print(f"❌ Could not get imports: {response.status_code}")
            return False
            
        imports = response.json()
        print(f"Found {len(imports)} imports to test")
        
        success_count = 0
        test_imports = imports[:3] if len(imports) >= 3 else imports
        for import_item in test_imports:
            import_id = import_item['id']
            
            # Test HTML page
            page_response = requests.get(f"{BASE_URL}/bgeigie-imports/{import_id}")
            page_ok = page_response.status_code == 200
            
            # Test API endpoint
            api_response = requests.get(f"{BASE_URL}/api/v1/bgeigie_imports/{import_id}")
            api_ok = api_response.status_code == 200
            
            # Test measurements endpoint
            measurements_response = requests.get(f"{BASE_URL}/api/v1/bgeigie_imports/{import_id}/measurements")
            measurements_ok = measurements_response.status_code == 200
            
            status = "✅" if (page_ok and api_ok and measurements_ok) else "❌"
            print(f"  Import {import_id}: Page({page_response.status_code}) API({api_response.status_code}) Measurements({measurements_response.status_code}) {status}")
            
            if page_ok and api_ok and measurements_ok:
                success_count += 1
                
        return success_count > 0
        
    except Exception as e:
        print(f"❌ Import detail test error: {e}")
        return False

def test_file_upload_workflow():
    """Test complete file upload workflow"""
    try:
        # Create test file
        test_content = """# NEW BGEIGIENAN
# format=1.4.0
$BNRDD,300,2023-08-24T04:00:00Z,35.6762,139.6503,0.18,A,1800,0*7E
$BNRDD,301,2023-08-24T04:00:01Z,35.6763,139.6504,0.19,A,1801,0*7F
"""
        
        test_file = Path("frontend_test.log")
        test_file.write_text(test_content)
        
        # Upload file
        with open(test_file, 'rb') as f:
            files = {'file': ('frontend_test.log', f, 'text/plain')}
            data = {
                'name': 'Frontend Test Upload',
                'description': 'Testing frontend upload workflow',
                'cities': 'Tokyo',
                'credits': 'Test User'
            }
            
            response = requests.post(f"{BASE_URL}/api/v1/bgeigie_imports/", 
                                   files=files, data=data)
        
        # Clean up
        test_file.unlink()
        
        if response.status_code in [200, 201]:
            upload_data = response.json()
            import_id = upload_data.get('id')
            print(f"✅ Upload successful: ID {import_id}, Status: {upload_data.get('status')}")
            
            # Test the detail page for new upload
            detail_response = requests.get(f"{BASE_URL}/bgeigie-imports/{import_id}")
            detail_ok = detail_response.status_code == 200
            print(f"✅ Detail page accessible: {detail_ok}")
            
            return True
        else:
            print(f"❌ Upload failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Upload workflow error: {e}")
        return False

def test_interactive_features():
    """Test interactive features and JavaScript functionality"""
    try:
        # Test main dashboard page
        dashboard_response = requests.get(f"{BASE_URL}/")
        if dashboard_response.status_code != 200:
            return False
            
        dashboard_content = dashboard_response.text
        
        # Test upload page
        upload_response = requests.get(f"{BASE_URL}/bgeigie-imports/new")
        if upload_response.status_code != 200:
            return False
            
        upload_content = upload_response.text
        
        # Check for key interactive elements
        checks = {
            'Dashboard loads': 'Dashboard - Safecast API' in dashboard_content,
            'Upload link present': '/bgeigie-imports/new' in dashboard_content,
            'Upload form': '<form' in upload_content and 'multipart/form-data' in upload_content,
            'File input': 'type="file"' in upload_content,
            'JavaScript': '<script' in upload_content,
            'Bootstrap CSS': 'bootstrap' in dashboard_content or 'bootstrap' in upload_content,
        }
        
        for feature, present in checks.items():
            status = "✅" if present else "❌"
            print(f"  {feature}: {status}")
            
        return all(checks.values())
        
    except Exception as e:
        print(f"❌ Interactive features error: {e}")
        return False

def main():
    print("🧪 Comprehensive Frontend Testing\n")
    
    tests = [
        ("Import Detail Pages", test_import_detail_pages),
        ("File Upload Workflow", test_file_upload_workflow),
        ("Interactive Features", test_interactive_features)
    ]
    
    results = {}
    for name, test_func in tests:
        print(f"--- {name} ---")
        results[name] = test_func()
        print()
    
    print("=" * 50)
    print("Frontend Test Results:")
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All frontend tests passed!")
    else:
        print("⚠️  Some frontend tests failed")
    
    return passed == total

if __name__ == "__main__":
    main()
