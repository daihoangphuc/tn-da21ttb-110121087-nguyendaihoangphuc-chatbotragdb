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

        self.url = url or os.getenv("SUPABASE_URL")
        # Ưu tiên sử dụng service_key nếu có, còn không thì sử dụng key thông thường
        self.key = key or os.getenv("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_KEY"))

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
