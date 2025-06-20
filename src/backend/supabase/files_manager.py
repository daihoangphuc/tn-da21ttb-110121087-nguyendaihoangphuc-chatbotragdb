"""
Module quản lý tệp tin trong Supabase cho hệ thống RAG
"""

import os
import uuid
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from .client import SupabaseClient


class FilesManager:
    """Quản lý thông tin tệp tin trong Supabase"""

    def __init__(self, client=None):
        """Khởi tạo với Supabase client"""
        if client:
            self.client = client
        else:
            self.client = SupabaseClient().get_client()

    def create_document_files_table(self):
        """Tạo bảng document_files nếu chưa tồn tại"""
        sql = """
        CREATE TABLE IF NOT EXISTS document_files (
          file_id UUID PRIMARY KEY,
          filename TEXT NOT NULL,
          file_path TEXT NOT NULL,
          user_id UUID NOT NULL REFERENCES auth.users(id),
          upload_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          file_type TEXT,
          file_size BIGINT,
          is_deleted BOOLEAN DEFAULT FALSE,
          deleted_at TIMESTAMPTZ,
          metadata JSONB
        );

        -- Tạo index để tìm kiếm nhanh
        CREATE INDEX IF NOT EXISTS idx_document_files_user_id ON document_files(user_id);
        CREATE INDEX IF NOT EXISTS idx_document_files_filename ON document_files(filename);
        CREATE INDEX IF NOT EXISTS idx_document_files_upload_time ON document_files(upload_time);
        """
        return self.client.rpc("exec_sql", {"query": sql, "params": {}})

    def save_file_metadata(
        self,
        file_id: str,
        filename: str,
        file_path: str,
        user_id: str,
        file_type: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Lưu thông tin file vào bảng document_files

        Args:
            file_id: ID duy nhất của file (UUID)
            filename: Tên file
            file_path: Đường dẫn đến file
            user_id: ID của người dùng tải lên
            file_type: Loại file (extension)
            metadata: Thông tin metadata bổ sung (JSON)

        Returns:
            Kết quả thao tác insert
        """
        data = {
            "file_id": file_id,
            "filename": filename,
            "file_path": file_path,
            "user_id": user_id,
            "upload_time": datetime.now().isoformat(),
        }

        if file_type:
            data["file_type"] = file_type

        if metadata:
            data["metadata"] = metadata

        # Thực hiện insert vào bảng document_files
        result = self.client.table("document_files").insert(data).execute()
        return result

    def get_files_by_user(
        self, user_id: str, include_deleted: bool = False
    ) -> List[Dict]:
        """
        Lấy danh sách file của một người dùng

        Args:
            user_id: ID của người dùng
            include_deleted: Có bao gồm file đã bị xóa hay không

        Returns:
            Danh sách thông tin file
        """
        query = self.client.table("document_files").select("*").eq("user_id", user_id)
        
        if not include_deleted:
            query = query.eq("is_deleted", False)
            
        query = query.order("upload_time", desc=True)
        
        result = query.execute()
        
        return result.data if hasattr(result, "data") else []

    def get_file_by_id(self, file_id: str) -> Optional[Dict]:
        """
        Lấy thông tin file theo ID

        Args:
            file_id: ID của file

        Returns:
            Thông tin file hoặc None nếu không tìm thấy
        """
        result = (
            self.client.table("document_files")
            .select("*")
            .eq("file_id", file_id)
            .execute()
        )
        if hasattr(result, "data") and len(result.data) > 0:
            return result.data[0]
        return None

    def get_file_by_name_and_user(self, filename: str, user_id: str) -> List[Dict]:
        """
        Lấy thông tin file theo tên và user_id

        Args:
            filename: Tên file
            user_id: ID người dùng

        Returns:
            Danh sách thông tin file (có thể có nhiều file cùng tên)
        """
        result = (
            self.client.table("document_files")
            .select("*")
            .eq("filename", filename)
            .eq("user_id", user_id)
            .eq("is_deleted", False)
            .execute()
        )

        return result.data if hasattr(result, "data") else []

    def get_file_by_name_for_admin(self, filename: str) -> List[Dict]:
        """
        Lấy thông tin file theo tên cho admin (không phân biệt user_id)

        Args:
            filename: Tên file

        Returns:
            Danh sách thông tin file (có thể có nhiều file cùng tên từ các user khác nhau)
        """
        result = (
            self.client.table("document_files")
            .select("*")
            .eq("filename", filename)
            .eq("is_deleted", False)
            .execute()
        )

        return result.data if hasattr(result, "data") else []

    def mark_file_as_deleted(self, file_id: str) -> Dict:
        """
        Đánh dấu file đã bị xóa (soft delete)

        Args:
            file_id: ID của file

        Returns:
            Kết quả thao tác update
        """
        data = {"is_deleted": True, "deleted_at": datetime.now().isoformat()}

        result = (
            self.client.table("document_files")
            .update(data)
            .eq("file_id", file_id)
            .execute()
        )
        return result

    def delete_file_permanently(self, file_id: str) -> Dict:
        """
        Xóa vĩnh viễn thông tin file từ database (hard delete)

        Args:
            file_id: ID của file

        Returns:
            Kết quả thao tác delete
        """
        result = (
            self.client.table("document_files")
            .delete()
            .eq("file_id", file_id)
            .execute()
        )
        return result

    def get_all_files(self, include_deleted: bool = False) -> List[Dict]:
        """
        Lấy danh sách tất cả file trong hệ thống

        Args:
            include_deleted: Có bao gồm file đã bị xóa hay không

        Returns:
            Danh sách thông tin file
        """
        query = self.client.table("document_files").select("*")
        
        if not include_deleted:
            query = query.eq("is_deleted", False)
            
        query = query.order("upload_time", desc=True)
        
        result = query.execute()
        
        return result.data if hasattr(result, "data") else []
