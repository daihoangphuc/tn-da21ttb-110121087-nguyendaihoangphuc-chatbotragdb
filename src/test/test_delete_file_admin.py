#!/usr/bin/env python3
"""
Test script để kiểm tra việc xóa file với quyền admin
"""

import os
import sys
import requests
import json

# Thêm src vào path để có thể import
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def test_admin_delete_file():
    """Test xóa file với quyền admin"""
    
    # Cấu hình
    API_BASE = "http://localhost:8000/api"
    
    # Thông tin admin
    admin_email = "phucadmin@gmail.com"
    admin_password = "123456"
    
    print("🔐 Đang đăng nhập với tài khoản admin...")
    
    # Đăng nhập admin
    login_response = requests.post(f"{API_BASE}/auth/login", json={
        "email": admin_email,
        "password": admin_password
    })
    
    if login_response.status_code != 200:
        print(f"❌ Đăng nhập thất bại: {login_response.text}")
        return False
    
    login_data = login_response.json()
    access_token = login_data["access_token"]
    user_info = login_data["user"]
    
    print(f"✅ Đăng nhập thành công với role: {user_info['role']}")
    
    # Headers cho các request tiếp theo
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Lấy danh sách file
    print("📋 Lấy danh sách file hiện có...")
    files_response = requests.get(f"{API_BASE}/files", headers=headers)
    
    if files_response.status_code != 200:
        print(f"❌ Lỗi khi lấy danh sách file: {files_response.text}")
        return False
    
    files_data = files_response.json()
    files = files_data.get("files", [])
    
    print(f"📁 Tìm thấy {len(files)} file:")
    for file_info in files:
        print(f"  - {file_info['filename']} (ID: {file_info.get('id', 'N/A')})")
    
    if not files:
        print("⚠️ Không có file nào để test xóa")
        return True
    
    # Chọn file đầu tiên để test xóa
    test_file = files[0]
    filename_to_delete = test_file["filename"]
    
    print(f"🗑️ Thử xóa file: {filename_to_delete}")
    
    # Thực hiện xóa file
    delete_response = requests.delete(f"{API_BASE}/files/{filename_to_delete}", headers=headers)
    
    print(f"📤 Response status: {delete_response.status_code}")
    print(f"📤 Response body: {delete_response.text}")
    
    if delete_response.status_code == 200:
        delete_data = delete_response.json()
        print(f"✅ Xóa file thành công!")
        print(f"   - File: {delete_data.get('filename')}")
        print(f"   - Status: {delete_data.get('status')}")
        print(f"   - Message: {delete_data.get('message')}")
        print(f"   - Removed points: {delete_data.get('removed_points', 0)}")
        
        # Kiểm tra lại danh sách file
        print("🔍 Kiểm tra lại danh sách file sau khi xóa...")
        files_response_after = requests.get(f"{API_BASE}/files", headers=headers)
        
        if files_response_after.status_code == 200:
            files_data_after = files_response_after.json()
            files_after = files_data_after.get("files", [])
            print(f"📁 Còn lại {len(files_after)} file")
            
            # Kiểm tra file đã bị xóa chưa
            remaining_filenames = [f["filename"] for f in files_after]
            if filename_to_delete not in remaining_filenames:
                print(f"✅ File {filename_to_delete} đã được xóa khỏi danh sách")
            else:
                print(f"⚠️ File {filename_to_delete} vẫn còn trong danh sách")
        
        return True
    else:
        print(f"❌ Xóa file thất bại: {delete_response.text}")
        return False

def test_vector_store_connection():
    """Test kết nối tới vector store"""
    print("🔍 Kiểm tra kết nối vector store...")
    
    try:
        from src.vector_store import VectorStore
        
        # Khởi tạo vector store
        vector_store = VectorStore()
        vector_store.collection_name = "global_documents"
        
        # Kiểm tra collection có tồn tại không
        if vector_store.client.collection_exists("global_documents"):
            print("✅ Collection global_documents tồn tại")
            
            # Lấy thông tin collection
            collection_info = vector_store.get_collection_info()
            if collection_info:
                points_count = collection_info.get("points_count", 0)
                print(f"📊 Collection có {points_count} points")
            else:
                print("⚠️ Không thể lấy thông tin collection")
        else:
            print("❌ Collection global_documents không tồn tại")
            
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi kiểm tra vector store: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Bắt đầu test xóa file với quyền admin...")
    
    # Test kết nối vector store
    vector_success = test_vector_store_connection()
    
    # Test xóa file
    delete_success = test_admin_delete_file()
    
    if vector_success and delete_success:
        print("🎉 Tất cả test đã pass!")
        sys.exit(0)
    else:
        print("💥 Một số test đã fail!")
        sys.exit(1) 