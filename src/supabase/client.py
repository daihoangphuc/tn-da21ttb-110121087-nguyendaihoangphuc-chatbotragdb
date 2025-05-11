"""
Main Supabase client for RAG system.
"""

import os

# Thay đổi import để tránh xung đột
import supabase as supabase_lib
from supabase.client import Client


class SupabaseClient:
    """Main client class for Supabase integration"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one client instance exists"""
        if cls._instance is None:
            cls._instance = super(SupabaseClient, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self, url=None, key=None):
        """Initialize Supabase client with URL and API key"""
        if self.initialized:
            return

        # Sử dụng thông tin cụ thể nếu không tìm thấy trong biến môi trường
        self.url = (
            url
            or os.getenv("SUPABASE_URL")
            or "https://yhlgzixdgvjllrblsxsr.supabase.co"
        )

        # Ưu tiên sử dụng service_key được cung cấp, nếu không có thì dùng service_key cứng
        self.key = (
            key
            or os.getenv("SUPABASE_SERVICE_KEY")
            or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlobGd6aXhkZ3ZqbGxyYmxzeHNyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0Njc5NjU5MywiZXhwIjoyMDYyMzcyNTkzfQ.Iec0FDbqXp4_RFoLrp6M2rQJNBlr04HyxL8oChpPF04"
        )

        if not self.url or not self.key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_KEY must be provided in .env file or as parameters"
            )

        print(f"Kết nối Supabase URL: {self.url}")
        print(f"Sử dụng service key: {self.key.startswith('eyJ') and 'Có' or 'Không'}")

        # Create Supabase client
        self.client = supabase_lib.create_client(self.url, self.key)
        self.initialized = True

    def get_client(self) -> Client:
        """Get the Supabase client instance"""
        return self.client
