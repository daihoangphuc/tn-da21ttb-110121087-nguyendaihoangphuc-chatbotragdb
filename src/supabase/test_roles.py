"""
Script để kiểm tra hệ thống phân quyền
"""

import os
import sys
import json
from dotenv import load_dotenv
from .client import SupabaseClient

# Load environment variables
load_dotenv()

def run_tests():
    """Chạy các bài kiểm tra hệ thống phân quyền"""
    client = SupabaseClient().get_client()
    
    print("=== Kiểm tra hệ thống phân quyền ===")
    
    # 1. Kiểm tra bảng user_roles đã tồn tại chưa
    try:
        response = client.table("user_roles").select("*").limit(1).execute()
        print("✅ Bảng user_roles đã tồn tại")
    except Exception as e:
        print(f"❌ Bảng user_roles chưa tồn tại: {str(e)}")
        print("Vui lòng chạy script src.supabase.init_db để tạo bảng user_roles")
        return
    
    # 2. Kiểm tra RLS policies cho bảng document_files - kiểm tra gián tiếp
    print("\n=== Kiểm tra RLS policies ===")
    print("Không thể kiểm tra trực tiếp RLS policies qua API.")
    print("Các policies sau đây nên được thiết lập cho bảng document_files:")
    print("1. 'Users can view all files' - Cho phép tất cả người dùng xem tài liệu")
    print("2. 'Only admin can insert files' - Chỉ admin mới có thể thêm tài liệu")
    print("3. 'Only admin can update their files' - Chỉ admin mới có thể cập nhật tài liệu của họ")
    print("4. 'Only admin can delete their files' - Chỉ admin mới có thể xóa tài liệu của họ")
    
    # 3. Liệt kê các admin hiện tại
    try:
        admins = client.table("user_roles").select("*").eq("role", "admin").execute()
        print(f"\n=== Danh sách admin hiện tại ===")
        if not admins.data or len(admins.data) == 0:
            print("Chưa có admin nào được cấu hình")
        else:
            for admin in admins.data:
                # Lấy thông tin email của admin
                user_id = admin["user_id"]
                try:
                    user_info = client.rpc("get_user_by_id", {"user_id_param": user_id}).execute()
                    email = user_info.data[0]["email"] if user_info.data and len(user_info.data) > 0 else "Unknown"
                    print(f"- {email} (ID: {user_id})")
                except Exception as e:
                    print(f"- User ID: {user_id} (Không thể lấy email: {str(e)})")
    except Exception as e:
        print(f"❌ Lỗi khi liệt kê admin: {str(e)}")
    
    print("\n=== Hướng dẫn thêm admin ===")
    print("Để thêm admin, chạy lệnh: python -m src.supabase.add_admin <email> [user_id]")
    print("Ví dụ: python -m src.supabase.add_admin admin@example.com")
    print("Hoặc: python -m src.supabase.add_admin admin@example.com 12345-abcde-67890")

if __name__ == "__main__":
    run_tests() 