#!/usr/bin/env python3
"""
Script để cập nhật RLS policies cho admin có thể quản lý tất cả file
"""

import os
import sys
from supabase import create_client, Client

def update_admin_policies():
    """Cập nhật policies cho admin"""
    
    # Lấy thông tin kết nối Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_service_key:
        print("❌ Thiếu SUPABASE_URL hoặc SUPABASE_SERVICE_KEY trong environment variables")
        return False
    
    try:
        # Tạo client với service key để có quyền admin
        supabase: Client = create_client(supabase_url, supabase_service_key)
        
        print("🔄 Đang cập nhật RLS policies cho admin...")
        
        # Đọc và thực thi script SQL
        sql_script = """
        -- Xóa policy cũ nếu tồn tại
        DROP POLICY IF EXISTS "Admin can delete all files" ON document_files;
        DROP POLICY IF EXISTS "Admin can update all files" ON document_files;
        DROP POLICY IF EXISTS "Admin can view all files" ON document_files;

        -- Tạo policy mới cho phép admin xóa tất cả file
        CREATE POLICY "Admin can delete all files" ON document_files
        FOR DELETE
        USING (
            EXISTS (
                SELECT 1 FROM user_roles
                WHERE user_id = auth.uid() AND role = 'admin'
            )
        );

        -- Tạo policy mới cho phép admin cập nhật tất cả file
        CREATE POLICY "Admin can update all files" ON document_files
        FOR UPDATE
        USING (
            EXISTS (
                SELECT 1 FROM user_roles
                WHERE user_id = auth.uid() AND role = 'admin'
            )
        );

        -- Tạo policy mới cho phép admin xem tất cả file
        CREATE POLICY "Admin can view all files" ON document_files
        FOR SELECT
        USING (
            EXISTS (
                SELECT 1 FROM user_roles
                WHERE user_id = auth.uid() AND role = 'admin'
            )
        );
        """
        
        # Thực thi script SQL
        result = supabase.rpc('run_sql', {'query': sql_script}).execute()
        
        print("✅ Đã cập nhật thành công RLS policies cho admin")
        
        # Kiểm tra các policy đã được tạo
        check_sql = """
        SELECT schemaname, tablename, policyname, cmd, qual 
        FROM pg_policies 
        WHERE tablename = 'document_files' 
        ORDER BY policyname;
        """
        
        policies_result = supabase.rpc('run_sql', {'query': check_sql}).execute()
        print("📋 Danh sách policies hiện tại:")
        print(policies_result.data)
        
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi cập nhật policies: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Bắt đầu cập nhật RLS policies...")
    
    success = update_admin_policies()
    
    if success:
        print("🎉 Hoàn thành cập nhật policies!")
        sys.exit(0)
    else:
        print("💥 Cập nhật policies thất bại!")
        sys.exit(1) 