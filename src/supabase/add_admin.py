"""
Script to add admin role to a user
"""

import os
import sys
import uuid
from datetime import datetime
from .client import SupabaseClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def add_admin_user(email):
    """
    Add admin role to a user by email
    
    Args:
        email (str): Email of the user to make admin
    """
    client = SupabaseClient().get_client()
    
    try:
        # Tìm người dùng bằng API admin
        print(f"Tìm người dùng với email: {email}")
        
        # Sử dụng API auth.admin.users thay vì truy vấn trực tiếp vào bảng auth.users
        try:
            # Phương pháp 1: Sử dụng RPC function để tìm user_id từ email
            user_response = client.rpc(
                "get_user_id_by_email",
                {"email_param": email}
            ).execute()
            
            if not user_response.data or len(user_response.data) == 0:
                print(f"Không tìm thấy người dùng với email {email}")
                
                # Thử phương pháp 2: Tạo người dùng mới nếu không tồn tại
                print(f"Bạn cần tạo người dùng trước trong giao diện Supabase Authentication")
                return False
            
            user_id = user_response.data[0]["id"]
            print(f"Tìm thấy người dùng với ID: {user_id}")
            
        except Exception as e:
            print(f"Lỗi khi tìm người dùng bằng RPC: {str(e)}")
            
            # Phương pháp 3: Yêu cầu người dùng nhập user_id trực tiếp
            print("Không thể tìm thấy người dùng từ email.")
            print("Vui lòng cung cấp user_id trực tiếp từ Supabase Authentication dashboard.")
            
            if len(sys.argv) > 2:
                user_id = sys.argv[2]
                print(f"Sử dụng user_id được cung cấp: {user_id}")
            else:
                print("Vui lòng chạy lại lệnh với user_id: python -m src.supabase.add_admin <email> <user_id>")
                return False
        
        # Kiểm tra xem người dùng đã có vai trò chưa
        role_response = client.table("user_roles").select("*").eq("user_id", user_id).execute()
        
        if role_response.data and len(role_response.data) > 0:
            # Cập nhật vai trò hiện có
            role_id = role_response.data[0]["id"]
            client.table("user_roles").update({
                "role": "admin",
                "updated_at": datetime.now().isoformat()
            }).eq("id", role_id).execute()
            print(f"Đã cập nhật người dùng {email} thành vai trò admin")
        else:
            # Thêm vai trò mới
            client.table("user_roles").insert({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "role": "admin",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }).execute()
            print(f"Đã thêm vai trò admin cho người dùng {email}")
        
        return True
    except Exception as e:
        print(f"Lỗi khi thêm vai trò admin: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Cách sử dụng: python -m src.supabase.add_admin <email> [user_id]")
        print("Ví dụ: python -m src.supabase.add_admin admin@example.com")
        print("Hoặc: python -m src.supabase.add_admin admin@example.com 12345-abcde-67890")
        sys.exit(1)
        
    email = sys.argv[1]
    add_admin_user(email) 