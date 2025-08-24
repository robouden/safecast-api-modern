#!/usr/bin/env python3
"""
Test the approval/rejection system for bGeigie imports
"""
import asyncio
import requests
import time
from pathlib import Path

# Sample bGeigie log content for testing
SAMPLE_LOG_CONTENT = """# NEW LOG
# format=1.2.0
$BNRDD,300,2011-01-15T00:00:01Z,0,0,0,A,2200,V*35
$BNRDD,301,2011-01-15T00:00:02Z,35.6894,139.6917,32,A,2300,A*6E
$BNRDD,302,2011-01-15T00:00:03Z,35.6895,139.6918,33,A,2400,A*6F
$BNRDD,303,2011-01-15T00:00:04Z,35.6896,139.6919,34,A,2500,A*70
$BNRDD,304,2011-01-15T00:00:05Z,35.6897,139.6920,35,A,2600,A*71
"""

def test_approval_workflow():
    """Test the complete approval workflow"""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Approval System Workflow")
    print("=" * 50)
    
    # Step 1: Check if server is running
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code != 200:
            print("❌ Server not running. Please start the server first.")
            return
        print("✅ Server is running")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Please start the server first.")
        return
    
    # Step 2: Upload a test file
    print("\n📤 Uploading test bGeigie file...")
    
    files = {
        'file': ('test_bgeigie.log', SAMPLE_LOG_CONTENT, 'text/plain')
    }
    data = {
        'name': 'Test Import for Approval',
        'description': 'Testing the approval workflow',
        'cities': 'Tokyo',
        'credits': 'Test User'
    }
    
    try:
        response = requests.post(f"{base_url}/api/v1/bgeigie_imports/", files=files, data=data)
        if response.status_code != 200:
            print(f"❌ Upload failed: {response.status_code} - {response.text}")
            return
        
        import_data = response.json()
        import_id = import_data['id']
        print(f"✅ Upload successful! Import ID: {import_id}")
        print(f"   Status: {import_data.get('status', 'unknown')}")
        print(f"   Approved: {import_data.get('approved', False)}")
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return
    
    # Step 3: Wait a moment for processing
    print("\n⏳ Waiting for processing...")
    time.sleep(2)
    
    # Step 4: Check import status
    try:
        response = requests.get(f"{base_url}/api/v1/bgeigie_imports/{import_id}")
        if response.status_code == 200:
            import_data = response.json()
            print(f"📊 Import Status: {import_data.get('status', 'unknown')}")
            print(f"   Measurements: {import_data.get('measurements_count', 0)}")
            print(f"   Approved: {import_data.get('approved', False)}")
            print(f"   Rejected: {import_data.get('rejected', False)}")
        else:
            print(f"❌ Failed to get import status: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Status check error: {e}")
        return
    
    # Step 5: Test approval
    print(f"\n✅ Testing approval for import {import_id}...")
    try:
        response = requests.patch(f"{base_url}/api/v1/bgeigie_imports/{import_id}/approve")
        if response.status_code == 200:
            import_data = response.json()
            print("🎉 Approval successful!")
            print(f"   Approved: {import_data.get('approved', False)}")
            print(f"   Rejected: {import_data.get('rejected', False)}")
        else:
            print(f"❌ Approval failed: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"❌ Approval error: {e}")
        return
    
    # Step 6: Test rejection (create another import first)
    print(f"\n📤 Creating second import for rejection test...")
    files = {
        'file': ('test_bgeigie2.log', SAMPLE_LOG_CONTENT, 'text/plain')
    }
    data = {
        'name': 'Test Import for Rejection',
        'description': 'Testing the rejection workflow',
        'cities': 'Osaka',
        'credits': 'Test User 2'
    }
    
    try:
        response = requests.post(f"{base_url}/api/v1/bgeigie_imports/", files=files, data=data)
        if response.status_code == 200:
            import_data2 = response.json()
            import_id2 = import_data2['id']
            print(f"✅ Second upload successful! Import ID: {import_id2}")
            
            # Wait for processing
            time.sleep(2)
            
            # Test rejection
            print(f"\n❌ Testing rejection for import {import_id2}...")
            response = requests.patch(f"{base_url}/api/v1/bgeigie_imports/{import_id2}/reject")
            if response.status_code == 200:
                import_data2 = response.json()
                print("🚫 Rejection successful!")
                print(f"   Approved: {import_data2.get('approved', False)}")
                print(f"   Rejected: {import_data2.get('rejected', False)}")
                print(f"   Rejected by: {import_data2.get('rejected_by', 'N/A')}")
            else:
                print(f"❌ Rejection failed: {response.status_code} - {response.text}")
        
    except Exception as e:
        print(f"❌ Second upload error: {e}")
    
    print(f"\n🎯 Test Summary:")
    print(f"   - Created import {import_id} and approved it")
    print(f"   - Created import {import_id2} and rejected it")
    print(f"   - Both imports should now show different approval states")
    print(f"\n🌐 Visit the web interface:")
    print(f"   - Main page: {base_url}/")
    print(f"   - Import {import_id}: {base_url}/bgeigie_imports/{import_id}")
    print(f"   - Import {import_id2}: {base_url}/bgeigie_imports/{import_id2}")

if __name__ == "__main__":
    test_approval_workflow()
