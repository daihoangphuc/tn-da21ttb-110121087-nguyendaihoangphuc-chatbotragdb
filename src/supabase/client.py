"""
Supabase Client module for connecting to Supabase.
"""

import os
import logging
import supabase
from typing import Dict, Optional, Any
import httpx

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
    _service_instance = None
    
    def __new__(cls, use_service_key=False):
        """Singleton pattern to ensure only one client instance"""
        if use_service_key:
            if cls._service_instance is None:
                cls._service_instance = super(SupabaseClient, cls).__new__(cls)
                cls._service_instance.client = None
                cls._service_instance.is_service_client = True
            return cls._service_instance
        else:
            if cls._instance is None:
                cls._instance = super(SupabaseClient, cls).__new__(cls)
                cls._instance.client = None
                cls._instance.is_service_client = False
            return cls._instance
    
    def __init__(self, use_service_key=False):
        """Initialize the Supabase client if not already initialized"""
        self.is_service_client = use_service_key
        
        if self.client is None:
            self.supabase_url = os.getenv("SUPABASE_URL")
            
            # Sử dụng service key nếu yêu cầu, ngược lại sử dụng key thường
            if use_service_key:
                self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
                key_type = "SUPABASE_SERVICE_KEY"
            else:
                self.supabase_key = os.getenv("SUPABASE_KEY")
                key_type = "SUPABASE_KEY"
            
            if not self.supabase_url or not self.supabase_key:
                print(f"Cảnh báo: SUPABASE_URL hoặc {key_type} không được cấu hình trong biến môi trường")
                return
            
            try:
                print(f"Khởi tạo kết nối Supabase với URL: {self.supabase_url} (using {key_type})")
                # Khởi tạo client không sử dụng tham số http_options
                self.client = supabase.create_client(self.supabase_url, self.supabase_key)
                print(f"Kết nối Supabase thành công (using {key_type})")
            except Exception as e:
                print(f"Lỗi khi khởi tạo kết nối Supabase: {str(e)}")
                self.client = None
    
    def get_client(self):
        """Get the Supabase client instance"""
        if self.client is None:
            self.__init__(use_service_key=self.is_service_client)  # Thử khởi tạo lại client nếu chưa được khởi tạo
            
        if self.client is None:
            print("Không thể lấy client Supabase, chưa được khởi tạo thành công")
            
        return self.client
        
    def get_service_client(self):
        """Get the Supabase client instance with service role"""
        # Tạo client với service key để bypass RLS
        service_client = SupabaseClient(use_service_key=True)
        return service_client.get_client()