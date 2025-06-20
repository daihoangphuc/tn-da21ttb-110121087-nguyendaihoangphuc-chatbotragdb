#!/usr/bin/env python
"""
Script để khởi tạo cấu trúc cơ sở dữ liệu trong Supabase
"""

import os
import sys
import traceback
from dotenv import load_dotenv

# Thêm thư mục gốc vào PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load biến môi trường
print("Đang tải biến môi trường từ .env...")
load_dotenv(verbose=True)

try:
    from backend.supabase.database import SupabaseDatabase
    from backend.supabase.client import SupabaseClient
    from backend.supabase.files_manager import FilesManager

    print("Đã import các module thành công")
except Exception as e:
    print(f"Lỗi khi import module: {str(e)}")
    sys.exit(1)


def init_database():
    print("=== BẮT ĐẦU KHỞI TẠO CƠ SỞ DỮ LIỆU ===")

    try:
        # Khởi tạo client và database
        print("Đang kết nối đến Supabase...")
        print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL')}")
        print(
            f"SUPABASE_SERVICE_KEY: {'Có' if os.getenv('SUPABASE_SERVICE_KEY') else 'Không'}"
        )

        client = SupabaseClient().get_client()
        print("Kết nối thành công!")

        db = SupabaseDatabase(client)
        print("Đã khởi tạo database")

        # Tạo bảng conversations và messages
        print("\nTạo bảng conversations và messages...")
        convo_result = db.create_conversation_history_table()
        print(f"Kết quả: {convo_result}")

        # Tạo bảng document_files
        print("\nTạo bảng document_files...")
        files_manager = FilesManager(client)
        files_result = files_manager.create_document_files_table()
        print(f"Kết quả: {files_result}")

        print("\n=== HOÀN THÀNH KHỞI TẠO CƠ SỞ DỮ LIỆU ===")
    except Exception as e:
        print("Lỗi khi khởi tạo cơ sở dữ liệu:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    init_database()
