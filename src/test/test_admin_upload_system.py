#!/usr/bin/env python3
"""
Script test hệ thống upload mới - chỉ admin được upload file vào hệ thống chung
"""

import os
import sys
import requests
import json

# Thêm thư mục gốc vào path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# URL API
BASE_URL = "http://localhost:8001/api/v1"

def test_admin_upload():
    """Test upload file với quyền admin"""
    print("=" * 60)
    print("TEST ADMIN UPLOAD SYSTEM")
    print("=" * 60)
    
    # 1. Đăng nhập với tài khoản admin
    print("\n1. Đăng nhập với tài khoản admin...")
    login_data = {
        "email": "admin@datn.com",  # Thay bằng email admin thực tế
        "password": "123456"  # Thay bằng password admin thực tế
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            login_result = response.json()
            admin_token = login_result["access_token"]
            admin_user = login_result["user"]
            print(f"✅ Đăng nhập admin thành công")
            print(f"   Email: {admin_user['email']}")
            print(f"   Role: {admin_user['role']}")
            
            if admin_user['role'] != 'admin':
                print("❌ Tài khoản này không phải admin!")
                return
                
        else:
            print(f"❌ Đăng nhập admin thất bại: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"❌ Lỗi khi đăng nhập admin: {str(e)}")
        return
    
    # 2. Test upload file với admin
    print("\n2. Test upload file với quyền admin...")
    
    # Tạo file test
    test_content = """
    # Tài liệu Test - Admin Upload
    
    Đây là tài liệu test được upload bởi admin vào hệ thống chung.
    
    ## Thông tin
    - File được lưu trong thư mục data chung
    - Index vào collection global_documents 
    - Không phân chia theo user_id
    - Tất cả user có thể truy cập
    
    ## Nội dung
    Đây là nội dung tài liệu để test việc tìm kiếm và truy vấn.
    Hệ thống RAG sẽ sử dụng nội dung này để trả lời câu hỏi của người dùng.
    """
    
    test_file_path = "test_admin_upload.txt"
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(test_content)
    
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        with open(test_file_path, "rb") as f:
            files = {
                "file": ("test_admin_upload.txt", f, "text/plain")
            }
            data = {
                "category": "test_documents"
            }
            
            response = requests.post(
                f"{BASE_URL}/upload", 
                headers=headers, 
                files=files, 
                data=data
            )
            
        if response.status_code == 200:
            upload_result = response.json()
            print(f"✅ Admin upload thành công!")
            print(f"   Filename: {upload_result['filename']}")
            print(f"   Status: {upload_result['status']}")
            print(f"   Message: {upload_result['message']}")
            print(f"   Chunks count: {upload_result['chunks_count']}")
            print(f"   Shared resource: {upload_result.get('shared_resource', False)}")
            
        else:
            print(f"❌ Admin upload thất bại: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Lỗi khi upload với admin: {str(e)}")
    finally:
        # Xóa file test
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
    
    # 3. Đăng nhập với tài khoản user thường
    print("\n3. Đăng nhập với tài khoản user thường...")
    user_login_data = {
        "email": "user@test.com",  # Thay bằng email user thực tế
        "password": "123456"  # Thay bằng password user thực tế
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=user_login_data)
        if response.status_code == 200:
            login_result = response.json()
            user_token = login_result["access_token"]
            user_info = login_result["user"]
            print(f"✅ Đăng nhập user thành công")
            print(f"   Email: {user_info['email']}")
            print(f"   Role: {user_info['role']}")
            
        else:
            print(f"❌ Đăng nhập user thất bại: {response.status_code}")
            print(f"   Tạo tài khoản user test...")
            # Tạo tài khoản user test
            signup_data = {
                "email": "user@test.com",
                "password": "123456"
            }
            signup_response = requests.post(f"{BASE_URL}/auth/signup", json=signup_data)
            if signup_response.status_code == 200:
                signup_result = signup_response.json()
                user_token = signup_result["access_token"]
                user_info = signup_result["user"]
                print(f"✅ Tạo và đăng nhập user mới thành công")
                print(f"   Email: {user_info['email']}")
                print(f"   Role: {user_info['role']}")
            else:
                print(f"❌ Tạo user thất bại: {signup_response.status_code}")
                return
                
    except Exception as e:
        print(f"❌ Lỗi khi đăng nhập user: {str(e)}")
        return
    
    # 4. Test upload file với user thường (phải thất bại)
    print("\n4. Test upload file với user thường (phải thất bại)...")
    
    test_file_path = "test_user_upload.txt"
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("Test content from regular user")
    
    try:
        headers = {"Authorization": f"Bearer {user_token}"}
        
        with open(test_file_path, "rb") as f:
            files = {
                "file": ("test_user_upload.txt", f, "text/plain")
            }
            data = {
                "category": "test_documents"
            }
            
            response = requests.post(
                f"{BASE_URL}/upload", 
                headers=headers, 
                files=files, 
                data=data
            )
            
        if response.status_code == 403:
            error_result = response.json()
            print(f"✅ User upload bị từ chối đúng như mong đợi!")
            print(f"   Status code: {response.status_code}")
            print(f"   Error: {error_result['detail']}")
            
        else:
            print(f"❌ User upload không bị từ chối như mong đợi!")
            print(f"   Status code: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Lỗi khi test upload với user: {str(e)}")
    finally:
        # Xóa file test
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
    
    # 5. Test lấy danh sách file (cả admin và user đều thấy file chung)
    print("\n5. Test lấy danh sách file...")
    
    # Test với admin
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/files", headers=headers)
        
        if response.status_code == 200:
            files_result = response.json()
            print(f"✅ Admin lấy danh sách file thành công")
            print(f"   Total files: {files_result['total_files']}")
            
            if files_result['files']:
                print("   Files:")
                for file_info in files_result['files'][:3]:  # Hiển thị 3 file đầu
                    print(f"     - {file_info['filename']} ({file_info['size']} bytes)")
        else:
            print(f"❌ Admin lấy danh sách file thất bại: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Lỗi khi admin lấy danh sách file: {str(e)}")
    
    # Test với user
    try:
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get(f"{BASE_URL}/files", headers=headers)
        
        if response.status_code == 200:
            files_result = response.json()
            print(f"✅ User lấy danh sách file thành công")
            print(f"   Total files: {files_result['total_files']}")
            print("   👍 User có thể xem file do admin upload (tài nguyên chung)")
        else:
            print(f"❌ User lấy danh sách file thất bại: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Lỗi khi user lấy danh sách file: {str(e)}")
    
    # 6. Test tìm kiếm với user (sử dụng tài nguyên chung)
    print("\n6. Test tìm kiếm với user (sử dụng tài nguyên chung)...")
    
    try:
        headers = {"Authorization": f"Bearer {user_token}"}
        search_data = {
            "question": "Tài liệu test là gì?"
        }
        
        response = requests.post(f"{BASE_URL}/ask/stream", headers=headers, json=search_data)
        
        if response.status_code == 200:
            print(f"✅ User tìm kiếm thành công")
            print(f"   👍 User có thể tìm kiếm trên tài nguyên chung do admin upload")
        else:
            print(f"❌ User tìm kiếm thất bại: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Lỗi khi user tìm kiếm: {str(e)}")
    
    print("\n" + "=" * 60)
    print("TEST HOÀN THÀNH")
    print("=" * 60)

if __name__ == "__main__":
    test_admin_upload() 