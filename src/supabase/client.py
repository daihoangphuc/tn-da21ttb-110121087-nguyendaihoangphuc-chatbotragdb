"""
Supabase Client module for connecting to Supabase.
"""

import os
import logging
import supabase
from typing import Dict, Optional, Any

# Cấu hình logging
logging.basicConfig(format="[SupabaseClient] %(message)s", level=logging.INFO)
# Ghi đè hàm print để thêm prefix
original_print = print


def print(*args, **kwargs):
    prefix = "[SupabaseClient] "
    original_print(prefix + " ".join(map(str, args)), **kwargs)

class SupabaseClient:
    """Class for managing Supabase connection"""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one client instance"""
        if cls._instance is None:
            cls._instance = super(SupabaseClient, cls).__new__(cls)
            cls._instance.client = None
        return cls._instance
    
    def __init__(self):
        """Initialize the Supabase client if not already initialized"""
        if self.client is None:
            self.supabase_url = os.getenv("SUPABASE_URL")
            self.supabase_key = os.getenv("SUPABASE_KEY")
            
            if not self.supabase_url or not self.supabase_key:
                print("Cảnh báo: SUPABASE_URL hoặc SUPABASE_KEY không được cấu hình trong biến môi trường")
                return
            
            try:
                print(f"Khởi tạo kết nối Supabase với URL: {self.supabase_url}")
                self.client = supabase.create_client(self.supabase_url, self.supabase_key)
                print("Kết nối Supabase thành công")
            except Exception as e:
                print(f"Lỗi khi khởi tạo kết nối Supabase: {str(e)}")
                self.client = None
    
    def get_client(self):
        """Get the Supabase client instance"""
        if self.client is None:
            self.__init__()  # Thử khởi tạo lại client nếu chưa được khởi tạo
            
        if self.client is None:
            print("Không thể lấy client Supabase, chưa được khởi tạo thành công")
            
        return self.client