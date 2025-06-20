#!/usr/bin/env python3
"""
Script để cấp quyền admin cho người dùng trong hệ thống
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.supabase.client import SupabaseClient

def grant_admin_role(email: str):
    """
    Cấp quyền admin cho người dùng theo email
    """
    try:
        # Khởi tạo Supabase client với service key
        client = SupabaseClient(use_service_key=True)
        supabase_client = client.get_client()
        
        # Tìm người dùng theo email
        print(f"🔍 Tìm người dùng với email: {email}")
        
        # Lấy thông tin người dùng từ Supabase Auth
        auth_users = supabase_client.auth.admin.list_users()
        user = None
        
        for auth_user in auth_users.users:
            if auth_user.email == email:
                user = auth_user
                break
        
        if not user:
            print(f"❌ Không tìm thấy người dùng với email: {email}")
            return False
        
        user_id = user.id
        print(f"✅ Tìm thấy người dùng: {user.email} (ID: {user_id})")
        
        # Kiểm tra xem bảng user_roles có tồn tại không
        try:
            existing_role = supabase_client.table("user_roles").select("*").eq("user_id", user_id).execute()
            
            if existing_role.data:
                # Cập nhật role hiện tại
                print(f"📝 Cập nhật role hiện tại thành 'admin'")
                result = supabase_client.table("user_roles").update({
                    "role": "admin"
                }).eq("user_id", user_id).execute()
                
                if result.data:
                    print(f"✅ Đã cập nhật role thành công cho {email}")
                    return True
                else:
                    print(f"❌ Lỗi khi cập nhật role: {result}")
                    return False
            else:
                # Thêm role mới
                print(f"➕ Thêm role 'admin' mới")
                result = supabase_client.table("user_roles").insert({
                    "user_id": user_id,
                    "role": "admin"
                }).execute()
                
                if result.data:
                    print(f"✅ Đã thêm role admin thành công cho {email}")
                    return True
                else:
                    print(f"❌ Lỗi khi thêm role: {result}")
                    return False
                    
        except Exception as table_error:
            print(f"⚠️ Lỗi khi truy cập bảng user_roles: {str(table_error)}")
            print("💡 Bảng user_roles có thể chưa tồn tại. Đang tạo bảng...")
            
            # Tạo bảng user_roles nếu chưa tồn tại
            try:
                # Thử tạo bảng (có thể cần thực hiện thủ công qua Supabase Dashboard)
                result = supabase_client.table("user_roles").insert({
                    "user_id": user_id,
                    "role": "admin"
                }).execute()
                
                if result.data:
                    print(f"✅ Đã tạo bảng và thêm role admin thành công cho {email}")
                    return True
                else:
                    print(f"❌ Lỗi khi tạo role: {result}")
                    return False
            except Exception as create_error:
                print(f"❌ Không thể tạo bảng user_roles: {str(create_error)}")
                print("\n📋 Bạn cần tạo bảng user_roles thủ công trong Supabase Dashboard:")
                print("   1. Mở Supabase Dashboard")
                print("   2. Vào Table Editor")
                print("   3. Tạo bảng mới với tên 'user_roles'")
                print("   4. Thêm các cột:")
                print("      - id: int8 (Primary Key, Identity)")
                print("      - user_id: uuid (Foreign Key to auth.users)")
                print("      - role: text (Default: 'student')")
                print("      - created_at: timestamptz (Default: now())")
                print("   5. Chạy lại script này")
                return False
                
    except Exception as e:
        print(f"❌ Lỗi: {str(e)}")
        return False

def list_admin_users():
    """
    Liệt kê tất cả người dùng có quyền admin
    """
    try:
        client = SupabaseClient(use_service_key=True)
        supabase_client = client.get_client()
        
        print("📋 Danh sách người dùng có quyền admin:")
        
        # Lấy danh sách user có role admin
        admin_roles = supabase_client.table("user_roles").select("*").eq("role", "admin").execute()
        
        if not admin_roles.data:
            print("   Không có người dùng nào có quyền admin")
            return
        
        # Lấy thông tin chi tiết của các admin users
        auth_users = supabase_client.auth.admin.list_users()
        
        for role_data in admin_roles.data:
            user_id = role_data["user_id"]
            
            # Tìm thông tin user trong auth
            user_info = None
            for auth_user in auth_users.users:
                if auth_user.id == user_id:
                    user_info = auth_user
                    break
            
            if user_info:
                print(f"   ✅ {user_info.email} (ID: {user_id})")
            else:
                print(f"   ⚠️ User ID: {user_id} (email không tìm thấy)")
                
    except Exception as e:
        print(f"❌ Lỗi khi liệt kê admin users: {str(e)}")

def main():
    if len(sys.argv) < 2:
        print("🚀 Script cấp quyền admin")
        print("\nCách sử dụng:")
        print("  python scripts/grant_admin_role.py <email>")
        print("  python scripts/grant_admin_role.py --list")
        print("\nVí dụ:")
        print("  python scripts/grant_admin_role.py admin@example.com")
        print("  python scripts/grant_admin_role.py --list")
        return
    
    if sys.argv[1] == "--list":
        list_admin_users()
        return
    
    email = sys.argv[1]
    success = grant_admin_role(email)
    
    if success:
        print(f"\n🎉 Thành công! {email} đã được cấp quyền admin.")
        print("💡 Người dùng có thể cần đăng xuất và đăng nhập lại để role mới có hiệu lực.")
    else:
        print(f"\n❌ Không thể cấp quyền admin cho {email}")

if __name__ == "__main__":
    main() 