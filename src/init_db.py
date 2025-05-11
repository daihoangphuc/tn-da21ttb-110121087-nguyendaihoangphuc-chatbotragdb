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
    from src.supabase.database import SupabaseDatabase
    from src.supabase.client import SupabaseClient

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
        print("\n[1/3] Tạo bảng conversations và messages...")
        convo_result = db.create_conversation_history_table()
        print(f"Kết quả: {convo_result}")

        # Tạo bảng user_feedback
        print("\n[2/3] Tạo bảng user_feedback...")
        feedback_result = db.create_feedback_table()
        print(f"Kết quả: {feedback_result}")

        # Tạo bảng document_metadata
        print("\n[3/3] Tạo bảng document_metadata...")
        doc_result = db.create_document_metadata_table()
        print(f"Kết quả: {doc_result}")

        print("\n=== HOÀN THÀNH KHỞI TẠO CƠ SỞ DỮ LIỆU ===")
    except Exception as e:
        print(f"\n!!! LỖI KHI KHỞI TẠO CƠ SỞ DỮ LIỆU: {str(e)}")
        print("\nChi tiết lỗi:")
        traceback.print_exc()
        print("\nHãy kiểm tra lại kết nối và quyền truy cập Supabase.")


if __name__ == "__main__":
    init_database()
