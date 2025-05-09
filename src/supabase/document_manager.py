"""
Supabase Document Manager for handling document storage and metadata.
Utilizes Supabase Storage and Database for document management.
"""

import os
import time
import mimetypes
from typing import Dict, List, Optional, BinaryIO, Union, Tuple, Any
from pathlib import Path
from .client import SupabaseClient
from .storage import SupabaseStorage
from .database import SupabaseDatabase


class SupabaseDocumentManager:
    """Manager for document storage and metadata using Supabase"""

    def __init__(self, client=None, bucket_name="documents"):
        """Initialize the document manager with Supabase client"""
        if client:
            self.supabase_client = client
        else:
            self.supabase_client = SupabaseClient().get_client()

        # Initialize storage and database modules
        self.storage = SupabaseStorage(self.supabase_client, bucket_name)
        self.db = SupabaseDatabase(self.supabase_client)

        # Ensure document metadata table exists
        try:
            self.db.create_document_metadata_table()
        except Exception as e:
            print(f"Warning: Could not create document metadata table: {str(e)}")
            print("Document metadata might not be properly stored in the database.")

        # Local fallback directory
        self.local_dir = os.getenv("UPLOAD_DIR", "src/data")
        os.makedirs(self.local_dir, exist_ok=True)

    def upload_document(
        self,
        file_path: str,
        file: Union[str, BinaryIO],
        category: Optional[str] = None,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        additional_metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Upload a document to Supabase Storage and save its metadata

        Args:
            file_path: Path where the file will be stored in Supabase
            file: File object or path to local file
            category: Optional category for the document
            user_id: Optional ID of the user uploading the document
            title: Optional title for the document
            description: Optional description for the document
            additional_metadata: Optional additional metadata

        Returns:
            Dictionary with upload results and metadata
        """
        # Get filename from path
        filename = os.path.basename(file_path)

        # Determine file type and size
        file_type = self._get_file_type(filename)
        file_size = self._get_file_size(file)

        try:
            # Determine content type based on file extension
            content_type = mimetypes.guess_type(filename)[0]

            # Upload to Supabase Storage
            upload_result = self.storage.upload_file(
                file_path=file_path,
                file=file,
                content_type=content_type,
                user_id=user_id,
            )

            # Save metadata to database
            metadata_result = self.db.save_document_metadata(
                filename=filename,
                file_path=file_path,
                file_type=file_type,
                file_size=file_size,
                user_id=user_id,
                category=category,
                title=title or filename,
                description=description,
                metadata=additional_metadata,
            )

            return {
                "success": True,
                "storage_result": upload_result,
                "metadata_result": metadata_result,
                "filename": filename,
                "file_path": file_path,
            }
        except Exception as e:
            print(f"Warning: Failed to upload document to Supabase: {str(e)}")
            # Fall back to local storage
            local_result = self._save_locally(file, file_path, user_id, category)
            return {
                "success": local_result["success"],
                "message": f"Stored locally due to Supabase error: {str(e)}",
                "local_path": local_result.get("local_path"),
            }

    def download_document(self, file_path: str) -> Tuple[bytes, Dict]:
        """
        Download a document from Supabase Storage

        Args:
            file_path: Path to the file in storage

        Returns:
            Tuple containing (file_bytes, metadata)
        """
        try:
            # Get file content from Supabase Storage
            file_bytes = self.storage.download_file(file_path)

            # Get metadata from database
            filename = os.path.basename(file_path)
            metadata_list = self.db.get_document_metadata(filename=filename)
            metadata = metadata_list[0] if metadata_list else {}

            return file_bytes, metadata
        except Exception as e:
            print(f"Warning: Failed to download document from Supabase: {str(e)}")
            # Fall back to local storage
            return self._load_locally(file_path)

    def list_documents(
        self, user_id: Optional[str] = None, category: Optional[str] = None
    ) -> List[Dict]:
        """
        List all documents with optional filtering

        Args:
            user_id: Optional filter by user ID
            category: Optional filter by category

        Returns:
            List of document metadata
        """
        try:
            # Query database for document metadata
            table = self.db.from_table("document_metadata")
            query = table.select("*")

            # Apply filters if provided
            if user_id:
                query = query.eq("user_id", user_id)

            if category:
                query = query.eq("category", category)

            # Order by upload date (newest first)
            query = query.order("upload_date", ascending=False)

            # Execute query
            response = query.execute()
            documents = response.data

            # Add URLs and additional information
            for doc in documents:
                file_path = doc.get("file_path")
                if file_path:
                    # Try to get a public URL if available
                    try:
                        doc["url"] = self.storage.get_public_url(file_path)
                    except:
                        # If bucket is not public, generate a signed URL
                        signed_url = self.storage.create_signed_url(file_path, 3600)
                        doc["url"] = signed_url.get("signedURL")

            return documents
        except Exception as e:
            print(f"Warning: Failed to list documents from Supabase: {str(e)}")
            # Fall back to local listing
            return self._list_locally(user_id, category)

    def delete_document(self, filename: str) -> Dict:
        """
        Delete a document from storage and its metadata

        Args:
            filename: Name of the file to delete

        Returns:
            Result of the operation
        """
        try:
            # Get metadata to find the file path
            metadata_list = self.db.get_document_metadata(filename=filename)

            if not metadata_list:
                return {"success": False, "message": f"Document '{filename}' not found"}

            metadata = metadata_list[0]
            file_path = metadata.get("file_path")

            # Delete from storage if we have the path
            if file_path:
                try:
                    self.storage.delete_file(file_path)
                except Exception as e:
                    print(f"Warning: Failed to delete document from storage: {str(e)}")

            # Delete metadata from database
            self.db.delete_document_metadata(filename)

            # Also delete locally if it exists
            local_path = os.path.join(self.local_dir, filename)
            if os.path.exists(local_path):
                os.remove(local_path)

            return {
                "success": True,
                "message": f"Document '{filename}' deleted successfully",
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to delete document: {str(e)}"}

    def update_document_metadata(
        self,
        filename: str,
        is_indexed: Optional[bool] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Update document metadata

        Args:
            filename: Name of the file
            is_indexed: Whether the document has been indexed
            title: New title
            description: New description
            category: New category
            metadata: New additional metadata

        Returns:
            Result of the operation
        """
        try:
            # Build update data
            table = self.db.from_table("document_metadata")
            data = {}

            if is_indexed is not None:
                data["is_indexed"] = is_indexed
                data["last_indexed"] = "NOW()"

            if title:
                data["title"] = title

            if description:
                data["description"] = description

            if category:
                data["category"] = category

            if metadata:
                data["metadata"] = metadata

            # Only update if we have changes
            if data:
                response = table.update(data).eq("filename", filename).execute()
                return {"success": True, "data": response.data}
            else:
                return {"success": True, "message": "No changes to update"}
        except Exception as e:
            return {"success": False, "message": f"Failed to update metadata: {str(e)}"}

    # Helper methods

    def _get_file_type(self, filename: str) -> str:
        """Get file type from filename"""
        _, ext = os.path.splitext(filename)
        return ext.lstrip(".").lower() if ext else ""

    def _get_file_size(self, file: Union[str, BinaryIO]) -> Optional[int]:
        """Get file size in bytes"""
        try:
            if isinstance(file, str):
                # It's a file path
                return os.path.getsize(file)
            else:
                # It's a file-like object
                if hasattr(file, "seek") and hasattr(file, "tell"):
                    # Save current position
                    current_pos = file.tell()
                    # Seek to end to get size
                    file.seek(0, os.SEEK_END)
                    size = file.tell()
                    # Restore position
                    file.seek(current_pos)
                    return size
        except Exception:
            return None

    # Local storage fallback methods

    def _save_locally(
        self,
        file: Union[str, BinaryIO],
        file_path: str,
        user_id: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict:
        """Save file locally as fallback"""
        try:
            # Get filename from path
            filename = os.path.basename(file_path)
            local_path = os.path.join(self.local_dir, filename)

            # Save file content
            if isinstance(file, str):
                # It's a file path, just copy
                with open(file, "rb") as src, open(local_path, "wb") as dst:
                    dst.write(src.read())
            else:
                # It's a file-like object
                # Save current position
                current_pos = file.tell()
                # Seek to start
                file.seek(0)
                # Write content
                with open(local_path, "wb") as dst:
                    dst.write(file.read())
                # Restore position
                file.seek(current_pos)

            # Save metadata in a sidecar file
            metadata_path = local_path + ".metadata.json"
            metadata = {
                "filename": filename,
                "file_path": file_path,
                "file_type": self._get_file_type(filename),
                "file_size": os.path.getsize(local_path),
                "upload_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "user_id": user_id,
                "category": category,
                "is_indexed": False,
            }

            with open(metadata_path, "w", encoding="utf-8") as f:
                import json

                json.dump(metadata, f, ensure_ascii=False, indent=2)

            return {"success": True, "local_path": local_path, "metadata": metadata}
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to save file locally: {str(e)}",
            }

    def _load_locally(self, file_path: str) -> Tuple[bytes, Dict]:
        """Load file locally as fallback"""
        # Get filename from path
        filename = os.path.basename(file_path)
        local_path = os.path.join(self.local_dir, filename)

        # Load file content
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"File not found: {local_path}")

        with open(local_path, "rb") as f:
            file_bytes = f.read()

        # Load metadata if available
        metadata_path = local_path + ".metadata.json"
        metadata = {}

        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    import json

                    metadata = json.load(f)
            except Exception:
                # Continue with empty metadata
                pass

        return file_bytes, metadata

    def _list_locally(
        self, user_id: Optional[str] = None, category: Optional[str] = None
    ) -> List[Dict]:
        """List documents locally as fallback"""
        try:
            results = []

            # Iterate through all files in the local directory
            for filename in os.listdir(self.local_dir):
                # Skip metadata files
                if filename.endswith(".metadata.json"):
                    continue

                # Skip non-file items
                local_path = os.path.join(self.local_dir, filename)
                if not os.path.isfile(local_path):
                    continue

                # Load metadata if available
                metadata_path = local_path + ".metadata.json"
                metadata = {
                    "filename": filename,
                    "file_path": filename,
                    "file_type": self._get_file_type(filename),
                    "file_size": os.path.getsize(local_path),
                    "upload_date": time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime(os.path.getmtime(local_path))
                    ),
                    "is_indexed": False,
                }

                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, "r", encoding="utf-8") as f:
                            import json

                            loaded_metadata = json.load(f)
                            metadata.update(loaded_metadata)
                    except Exception:
                        # Continue with basic metadata
                        pass

                # Apply filters if specified
                if user_id and metadata.get("user_id") != user_id:
                    continue

                if category and metadata.get("category") != category:
                    continue

                # Add local URL
                metadata["url"] = f"file://{local_path}"

                results.append(metadata)

            # Sort by upload date (newest first)
            results.sort(key=lambda x: x.get("upload_date", ""), reverse=True)

            return results
        except Exception as e:
            print(f"Error listing documents locally: {str(e)}")
            return []
