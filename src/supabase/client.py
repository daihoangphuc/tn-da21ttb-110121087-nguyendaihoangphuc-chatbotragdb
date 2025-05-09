"""
Main Supabase client for RAG system.
"""

import os

# Thay đổi import để tránh xung đột
import supabase as supabase_lib
from supabase.lib import Client


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
        self.key = key or os.getenv("SUPABASE_KEY")

        if not self.url or not self.key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be provided in .env file or as parameters"
            )

        # Create Supabase client
        self.client = supabase_lib.create_client(self.url, self.key)
        self.initialized = True

    def get_client(self) -> Client:
        """Get the Supabase client instance"""
        return self.client
