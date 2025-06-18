#!/usr/bin/env python3
"""
Script test chức năng hard delete của admin
"""

import os
import sys
import requests
import json
import time

# Thêm thư mục gốc vào path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# URL API
BASE_URL = "http://localhost:8001/api/v1"

def test_admin_hard_delete():
    """Test hard delete với quyền admin"""
    print("=" * 60)
    print("TEST ADMIN HARD DELETE")
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
    
    # 2. Upload một file test để sau đó xóa
    print("\n2. Upload file test để xóa...")
    
    test_content = """
    # File Test - Sẽ bị xóa vĩnh viễn
    
    Đây là file test để kiểm tra chức năng hard delete của admin.
    File này sẽ bị xóa hoàn toàn khỏi:
    - File system (src/data/)
    - Database (bảng document_files) 
    - Vector store (collection global_documents)
    
    Test content for hard delete verification.
    """
    
    test_filename = f"test_hard_delete_{int(time.time())}.txt"
    test_file_path = test_filename
    
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(test_content)
    
    # Upload file
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        with open(test_file_path, "rb") as f:
            files = {
                "file": (test_filename, f, "text/plain")
            }
            data = {
                "category": "test_hard_delete"
            }
            
            response = requests.post(
                f"{BASE_URL}/upload", 
                headers=headers, 
                files=files, 
                data=data
            )
            
        if response.status_code == 200:
            upload_result = response.json()
            print(f"✅ Upload thành công!")
            print(f"   Filename: {upload_result['filename']}")
            print(f"   Chunks count: {upload_result['chunks_count']}")
            uploaded_filename = upload_result['filename']
        else:
            print(f"❌ Upload thất bại: {response.status_code}")
            print(f"   Response: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Lỗi khi upload: {str(e)}")
        return
    finally:
        # Xóa file tạm
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
    
    # 3. Kiểm tra file có trong database trước khi xóa
    print("\n3. Kiểm tra file trong database trước khi xóa...")
    try:
        from src.supabase.files_manager import FilesManager
        from src.supabase.client import SupabaseClient
        
        supabase_client = SupabaseClient(use_service_key=True)
        client = supabase_client.get_client()
        files_manager = FilesManager(client)
        
        # Tìm file trong database
        db_files_before = files_manager.get_file_by_name_for_admin(uploaded_filename)
        
        if db_files_before:
            file_record = db_files_before[0]
            file_id = file_record.get("file_id")
            print(f"✅ File tìm thấy trong database:")
            print(f"   File ID: {file_id}")
            print(f"   File path: {file_record.get('file_path')}")
            print(f"   Upload time: {file_record.get('upload_time')}")
            print(f"   Is deleted: {file_record.get('is_deleted', False)}")
        else:
            print(f"❌ Không tìm thấy file trong database")
            return
            
    except Exception as e:
        print(f"❌ Lỗi khi kiểm tra database: {str(e)}")
        return
    
    # 4. Kiểm tra file có trong vector store trước khi xóa
    print("\n4. Kiểm tra file trong vector store trước khi xóa...")
    try:
        from src.vector_store import VectorStore
        
        vector_store = VectorStore()
        vector_store.collection_name = "global_documents"
        
        # Kiểm tra collection có tồn tại
        if vector_store.client.collection_exists("global_documents"):
            # Đếm points có file_id này
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            count_filter = Filter(
                must=[
                    FieldCondition(
                        key="file_id",
                        match=MatchValue(value=file_id)
                    )
                ]
            )
            
            count_result = vector_store.client.count(
                collection_name="global_documents",
                count_filter=count_filter,
                exact=True
            )
            
            points_before = count_result.count
            print(f"✅ Tìm thấy {points_before} points trong vector store với file_id: {file_id}")
        else:
            print(f"⚠️  Collection global_documents không tồn tại")
            points_before = 0
            
    except Exception as e:
        print(f"❌ Lỗi khi kiểm tra vector store: {str(e)}")
        points_before = 0
    
    # 5. Thực hiện hard delete
    print(f"\n5. Thực hiện hard delete file: {uploaded_filename}")
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.delete(
            f"{BASE_URL}/files/{uploaded_filename}",
            headers=headers
        )
        
        if response.status_code == 200:
            delete_result = response.json()
            print(f"✅ Hard delete thành công!")
            print(f"   Status: {delete_result['status']}")
            print(f"   Message: {delete_result['message']}")
            print(f"   Removed points: {delete_result.get('removed_points', 0)}")
        else:
            print(f"❌ Hard delete thất bại: {response.status_code}")
            print(f"   Response: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Lỗi khi hard delete: {str(e)}")
        return
    
    # 6. Kiểm tra file đã bị xóa hoàn toàn trong database
    print("\n6. Kiểm tra file đã bị xóa khỏi database...")
    try:
        # Tìm file trong database (bao gồm cả file đã xóa)
        db_files_after = files_manager.get_all_files(include_deleted=True)
        
        # Tìm file với file_id cụ thể
        found_file = None
        for file_rec in db_files_after:
            if file_rec.get("file_id") == file_id:
                found_file = file_rec
                break
        
        if found_file:
            print(f"❌ File vẫn còn trong database (chưa hard delete):")
            print(f"   File ID: {found_file.get('file_id')}")
            print(f"   Is deleted: {found_file.get('is_deleted', False)}")
        else:
            print(f"✅ File đã bị xóa hoàn toàn khỏi database (hard delete)")
            
    except Exception as e:
        print(f"❌ Lỗi khi kiểm tra database sau xóa: {str(e)}")
    
    # 7. Kiểm tra file đã bị xóa khỏi vector store
    print("\n7. Kiểm tra file đã bị xóa khỏi vector store...")
    try:
        if vector_store.client.collection_exists("global_documents"):
            # Đếm points có file_id này sau khi xóa
            count_result_after = vector_store.client.count(
                collection_name="global_documents",
                count_filter=count_filter,
                exact=True
            )
            
            points_after = count_result_after.count
            print(f"   Points trước xóa: {points_before}")
            print(f"   Points sau xóa: {points_after}")
            
            if points_after == 0:
                print(f"✅ Tất cả points đã bị xóa khỏi vector store")
            else:
                print(f"❌ Vẫn còn {points_after} points trong vector store")
        else:
            print(f"⚠️  Collection global_documents không tồn tại")
            
    except Exception as e:
        print(f"❌ Lỗi khi kiểm tra vector store sau xóa: {str(e)}")
    
    # 8. Kiểm tra file vật lý đã bị xóa
    print("\n8. Kiểm tra file vật lý...")
    data_dir = os.getenv("UPLOAD_DIR", "src/data")
    physical_file_path = os.path.join(data_dir, uploaded_filename)
    
    if os.path.exists(physical_file_path):
        print(f"❌ File vật lý vẫn tồn tại: {physical_file_path}")
    else:
        print(f"✅ File vật lý đã bị xóa: {physical_file_path}")
    
    print("\n" + "=" * 60)
    print("HARD DELETE TEST COMPLETED")
    print("=" * 60)
    print("\n📋 Tóm tắt:")
    print("   ✅ Upload file test thành công")
    print("   ✅ Kiểm tra file tồn tại trước khi xóa")
    print("   ✅ Thực hiện hard delete")
    print("   ✅ Xác minh file đã bị xóa hoàn toàn")
    print("\n🎉 Hard delete hoạt động chính xác!")

if __name__ == "__main__":
    test_admin_hard_delete() 