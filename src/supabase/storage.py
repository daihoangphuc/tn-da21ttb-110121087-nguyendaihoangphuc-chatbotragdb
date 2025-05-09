"""
Supabase Storage module for file storage management.
"""

import os
from typing import Dict, List, Optional, BinaryIO, Union
from .client import SupabaseClient


class SupabaseStorage:
    """Class for managing file storage with Supabase"""

    def __init__(self, client=None, bucket_name="documents"):
        """Initialize the storage module with a Supabase client"""
        if client:
            self.client = client
        else:
            self.client = SupabaseClient().get_client()

        # Access the storage API
        self.storage = self.client.storage
        self.default_bucket = bucket_name

        # Try to create default bucket if it doesn't exist
        self._ensure_bucket_exists(self.default_bucket)

    def _ensure_bucket_exists(self, bucket_name: str) -> None:
        """Ensure that the bucket exists, create it if it doesn't"""
        try:
            buckets = self.list_buckets()
            if not any(bucket.get("name") == bucket_name for bucket in buckets):
                self.create_bucket(bucket_name)
        except Exception as e:
            # Handle API errors or permissions issues
            print(f"Warning: Could not create or verify bucket {bucket_name}: {str(e)}")

    def create_bucket(self, bucket_name: str, is_public: bool = False) -> Dict:
        """Create a new storage bucket"""
        return self.storage.create_bucket(bucket_name, options={"public": is_public})

    def list_buckets(self) -> List[Dict]:
        """List all available buckets"""
        return self.storage.list_buckets()

    def delete_bucket(self, bucket_name: str) -> Dict:
        """Delete a storage bucket"""
        return self.storage.empty_bucket(bucket_name)
        return self.storage.delete_bucket(bucket_name)

    def upload_file(
        self,
        file_path: str,
        file: Union[str, BinaryIO],
        bucket_name: Optional[str] = None,
        content_type: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict:
        """
        Upload a file to a bucket.

        Args:
            file_path: Path where the file will be stored in the bucket
            file: Either a file object or path to local file
            bucket_name: Bucket name (default: self.default_bucket)
            content_type: MIME type of the file
            user_id: User ID for organization purposes

        Returns:
            Response from Supabase
        """
        bucket = bucket_name or self.default_bucket

        # Determine file options based on content type and user
        file_options = {}
        if content_type:
            file_options["content-type"] = content_type

        # Add user_id as metadata if provided
        if user_id:
            file_options["metadata"] = {"user_id": user_id}

        # Handle file as path or file object
        if isinstance(file, str) and os.path.isfile(file):
            with open(file, "rb") as f:
                return self.storage.from_(bucket).upload(
                    path=file_path, file=f, file_options=file_options
                )
        else:
            return self.storage.from_(bucket).upload(
                path=file_path, file=file, file_options=file_options
            )

    def download_file(self, file_path: str, bucket_name: Optional[str] = None) -> bytes:
        """Download a file from a bucket"""
        bucket = bucket_name or self.default_bucket
        return self.storage.from_(bucket).download(file_path)

    def list_files(
        self, folder_path: str = "", bucket_name: Optional[str] = None
    ) -> List[Dict]:
        """List all files in a folder path"""
        bucket = bucket_name or self.default_bucket
        return self.storage.from_(bucket).list(folder_path)

    def delete_file(
        self, file_paths: Union[str, List[str]], bucket_name: Optional[str] = None
    ) -> Dict:
        """Delete a file or list of files from a bucket"""
        bucket = bucket_name or self.default_bucket

        # Convert single path to list if needed
        paths = file_paths if isinstance(file_paths, list) else [file_paths]
        return self.storage.from_(bucket).remove(paths)

    def move_file(
        self, old_path: str, new_path: str, bucket_name: Optional[str] = None
    ) -> Dict:
        """Move/rename a file within a bucket"""
        bucket = bucket_name or self.default_bucket
        return self.storage.from_(bucket).move(old_path, new_path)

    def copy_file(
        self, source_path: str, destination_path: str, bucket_name: Optional[str] = None
    ) -> Dict:
        """Copy a file within a bucket"""
        bucket = bucket_name or self.default_bucket
        return self.storage.from_(bucket).copy(source_path, destination_path)

    def get_public_url(self, file_path: str, bucket_name: Optional[str] = None) -> str:
        """Get a public URL for a file (only works for public buckets)"""
        bucket = bucket_name or self.default_bucket
        return self.storage.from_(bucket).get_public_url(file_path)

    def create_signed_url(
        self, file_path: str, expires_in: int = 3600, bucket_name: Optional[str] = None
    ) -> Dict:
        """Create a signed URL for temporary access to a file"""
        bucket = bucket_name or self.default_bucket
        return self.storage.from_(bucket).create_signed_url(file_path, expires_in)
