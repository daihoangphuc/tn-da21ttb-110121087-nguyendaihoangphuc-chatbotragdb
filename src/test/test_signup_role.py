#!/usr/bin/env python3
"""
Script test chức năng đăng ký tài khoản với role mặc định student
"""

import os
import sys
import requests
import uuid
from datetime import datetime

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import để test trực tiếp với database
from src.supabase.client import SupabaseClient

# API Base URL
BASE_URL = "http://localhost:8001/api/v1"

def test_signup_with_role():
    """Test đăng ký tài khoản và kiểm tra role được thêm vào user_roles"""
    print("=" * 60)
    print("TEST SIGNUP WITH ROLE")
    print("=" * 60)
    
    # Tạo email test duy nhất
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_email = f"test_user_{timestamp}@example.com"
    test_password = "TestPassword123!"
    
    print(f"Testing signup with email: {test_email}")
    
    try:
        # 1. Test đăng ký qua API
        print("\n1. Testing signup via API...")
        signup_data = {
            "email": test_email,
            "password": test_password
        }
        
        response = requests.post(f"{BASE_URL}/auth/signup", json=signup_data, timeout=30)
        
        if response.status_code == 200:
            signup_result = response.json()
            user_info = signup_result["user"]
            
            print(f"✅ Signup successful")
            print(f"   User ID: {user_info['id']}")
            print(f"   Email: {user_info['email']}")
            print(f"   Role from API: {user_info['role']}")
            
            user_id = user_info['id']
            
            # 2. Kiểm tra role trong database
            print("\n2. Checking role in database...")
            
            supabase_client = SupabaseClient(use_service_key=True)
            client = supabase_client.get_client()
            
            # Kiểm tra bảng user_roles
            role_data = client.table("user_roles").select("*").eq("user_id", user_id).execute()
            
            if role_data.data and len(role_data.data) > 0:
                db_role = role_data.data[0]
                print(f"✅ Role found in database")
                print(f"   User ID: {db_role['user_id']}")
                print(f"   Role: {db_role['role']}")
                print(f"   Created at: {db_role['created_at']}")
                
                if db_role['role'] == 'student':
                    print("✅ Correct default role 'student' assigned")
                else:
                    print(f"❌ Wrong role assigned: {db_role['role']}")
            else:
                print("❌ No role found in database")
            
            # 3. Test đăng nhập để kiểm tra role
            print("\n3. Testing login to verify role...")
            
            login_data = {
                "email": test_email,
                "password": test_password
            }
            
            login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data, timeout=30)
            
            if login_response.status_code == 200:
                login_result = login_response.json()
                user_info = login_result["user"]
                
                print(f"✅ Login successful")
                print(f"   Role from login API: {user_info['role']}")
                
                if user_info['role'] == 'student':
                    print("✅ Role correctly returned on login")
                else:
                    print(f"❌ Wrong role on login: {user_info['role']}")
            else:
                print(f"❌ Login failed: {login_response.status_code}")
                print(f"   Response: {login_response.text}")
            
            # 4. Cleanup - xóa user test
            print("\n4. Cleaning up test user...")
            try:
                # Xóa từ user_roles
                client.table("user_roles").delete().eq("user_id", user_id).execute()
                print("✅ Deleted from user_roles table")
                
                # Note: Không thể xóa từ auth.users qua API thông thường
                print("ℹ️  User remains in auth.users (manual cleanup required)")
                
            except Exception as e:
                print(f"⚠️ Cleanup error: {str(e)}")
                
        else:
            print(f"❌ Signup failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ Request timeout - make sure API server is running")
        print("   Start server: uvicorn src.api:app --host 0.0.0.0 --port 8001 --reload")
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - make sure API server is running")
        print("   Start server: uvicorn src.api:app --host 0.0.0.0 --port 8001 --reload")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

def test_existing_user_role():
    """Test user hiện tại có role chưa"""
    print("\n" + "=" * 60)
    print("TEST EXISTING USER ROLES")
    print("=" * 60)
    
    try:
        supabase_client = SupabaseClient(use_service_key=True)
        client = supabase_client.get_client()
        
        # Lấy danh sách user từ user_roles
        roles_data = client.table("user_roles").select("*").execute()
        
        if roles_data.data:
            print(f"Found {len(roles_data.data)} users with roles:")
            for role_info in roles_data.data:
                print(f"   User ID: {role_info['user_id']}")
                print(f"   Role: {role_info['role']}")
                print(f"   Created: {role_info['created_at']}")
                print()
        else:
            print("No users found in user_roles table")
            
        # Kiểm tra admin users
        admin_roles = client.table("user_roles").select("*").eq("role", "admin").execute()
        student_roles = client.table("user_roles").select("*").eq("role", "student").execute()
        
        print(f"Summary:")
        print(f"   Admin users: {len(admin_roles.data) if admin_roles.data else 0}")
        print(f"   Student users: {len(student_roles.data) if student_roles.data else 0}")
        
    except Exception as e:
        print(f"❌ Error checking existing users: {str(e)}")

if __name__ == "__main__":
    print("User Signup Role Test Script")
    print("\nThis script will test:")
    print("1. User signup with automatic role assignment")
    print("2. Role storage in user_roles table")
    print("3. Role retrieval on login")
    print("4. Existing user roles")
    
    # Test existing users first
    test_existing_user_role()
    
    # Test new signup
    proceed = input("\nProceed with signup test? (y/N): ")
    if proceed.lower() in ['y', 'yes']:
        test_signup_with_role()
    else:
        print("Signup test cancelled.")
    
    print("\n🎉 Test completed!") 