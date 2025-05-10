"""
Supabase Conversation Manager for handling conversation history with Supabase.
Replaces the traditional conversation_memory.py functionality.
"""

import os
import json
import datetime
from typing import Dict, List, Optional, Any
from .client import SupabaseClient
from .database import SupabaseDatabase


class SupabaseConversationManager:
    """Manager for conversation history using Supabase database"""

    def __init__(self, client=None):
        """Initialize the conversation manager with Supabase client"""
        if client:
            self.supabase_client = client
        else:
            self.supabase_client = SupabaseClient().get_client()

        # Initialize database access
        self.db = SupabaseDatabase(self.supabase_client)

        # Ensure the conversation history table exists
        try:
            print("Bắt đầu tạo/kiểm tra bảng conversation_history...")
            # Tạo bảng trước khi cố gắng kiểm tra
            self.db.create_conversation_history_table()

            # Thử kiểm tra bảng bằng cách truy vấn đơn giản mà không sử dụng count(*)
            try:
                result = (
                    self.supabase_client.table("conversation_history")
                    .select("id")
                    .limit(1)
                    .execute()
                )
                if hasattr(result, "data"):
                    record_count = len(result.data)
                    print(
                        f"Bảng conversation_history đã tồn tại, đã tìm thấy {record_count} bản ghi mẫu"
                    )
                else:
                    print("Bảng conversation_history đã tạo nhưng chưa có dữ liệu")
            except Exception as e:
                print(f"Lỗi khi kiểm tra dữ liệu trong bảng: {str(e)}")

            print("Đã tạo/kiểm tra bảng conversation_history thành công")

        except Exception as e:
            print(f"Warning: Could not create conversation history table: {str(e)}")
            import traceback

            print(f"Chi tiết lỗi khi tạo bảng: {traceback.format_exc()}")
            print("Conversation history might not be properly stored in the database.")

    def add_user_message(
        self, session_id: str, message: str, user_id: Optional[str] = None
    ) -> None:
        """
        Add a user message to the conversation history

        Args:
            session_id: Unique identifier for the conversation
            message: Content of the user's message
            user_id: Optional user identifier for authenticated users
        """
        try:
            # Phương pháp 1: Sử dụng SupabaseDatabase
            result = self.db.save_conversation_message(
                session_id=session_id, role="user", content=message, user_id=user_id
            )
            # In ra kết quả thành công để debug
            print(
                f"Đã lưu tin nhắn người dùng thành công, ID: {result.data[0].get('id') if hasattr(result, 'data') and result.data else 'không có ID'}"
            )
        except Exception as e:
            print(
                f"Warning: Failed to save user message to database using SupabaseDatabase: {str(e)}"
            )
            import traceback

            print(f"Chi tiết lỗi: {traceback.format_exc()}")

            # Phương pháp 2: Thử trực tiếp với supabase_client
            try:
                print("Thử lưu tin nhắn người dùng trực tiếp với supabase_client")
                result = (
                    self.supabase_client.table("conversation_history")
                    .insert(
                        {
                            "session_id": session_id,
                            "role": "user",
                            "content": message,
                            "user_id": user_id if user_id else None,
                        }
                    )
                    .execute()
                )
                print(
                    f"Đã lưu tin nhắn người dùng thành công với phương pháp trực tiếp: {result.data[0].get('id') if hasattr(result, 'data') and result.data else 'không có ID'}"
                )
            except Exception as e2:
                print(
                    f"Warning: Failed to save user message to database directly: {str(e2)}"
                )
                # Fallback to local file storage
                self._save_locally(session_id, "user", message, user_id)

    def add_ai_message(
        self,
        session_id: str,
        message: str,
        metadata: Optional[Dict] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Add an AI message to the conversation history

        Args:
            session_id: Unique identifier for the conversation
            message: Content of the AI's message
            metadata: Optional metadata about the message (sources, etc.)
            user_id: Optional user identifier for authenticated users
        """
        try:
            # Phương pháp 1: Sử dụng SupabaseDatabase
            result = self.db.save_conversation_message(
                session_id=session_id,
                role="assistant",
                content=message,
                user_id=user_id,
                metadata=metadata,
            )
            # In ra kết quả thành công để debug
            print(
                f"Đã lưu tin nhắn AI thành công, ID: {result.data[0].get('id') if hasattr(result, 'data') and result.data else 'không có ID'}"
            )
        except Exception as e:
            print(
                f"Warning: Failed to save AI message to database using SupabaseDatabase: {str(e)}"
            )
            import traceback

            print(f"Chi tiết lỗi: {traceback.format_exc()}")

            # Phương pháp 2: Thử trực tiếp với supabase_client
            try:
                print("Thử lưu tin nhắn AI trực tiếp với supabase_client")
                data = {
                    "session_id": session_id,
                    "role": "assistant",
                    "content": message,
                }
                if user_id:
                    data["user_id"] = user_id
                if metadata:
                    data["metadata"] = metadata

                result = (
                    self.supabase_client.table("conversation_history")
                    .insert(data)
                    .execute()
                )
                print(
                    f"Đã lưu tin nhắn AI thành công với phương pháp trực tiếp: {result.data[0].get('id') if hasattr(result, 'data') and result.data else 'không có ID'}"
                )
            except Exception as e2:
                print(
                    f"Warning: Failed to save AI message to database directly: {str(e2)}"
                )
                # Fallback to local file storage
                self._save_locally(session_id, "assistant", message, user_id, metadata)

    def get_messages(self, session_id: str, limit: int = 100) -> List[Dict]:
        """
        Lấy danh sách tin nhắn từ cơ sở dữ liệu

        Args:
            session_id: ID phiên hội thoại
            limit: Số lượng tin nhắn tối đa cần lấy

        Returns:
            Danh sách các tin nhắn
        """
        try:
            # Lấy tin nhắn từ Supabase
            result = (
                self.supabase_client.table("conversation_history")
                .select("*")
                .eq("session_id", session_id)
                .order("timestamp")  # Sắp xếp theo thời gian
                .limit(limit)
                .execute()
            )

            if not hasattr(result, "data"):
                return []

            # Chuyển đổi kết quả thành định dạng chuẩn
            messages = []
            for msg in result.data:
                message = {
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                    "timestamp": msg.get("timestamp"),
                }
                # Thêm metadata nếu có
                if msg.get("metadata"):
                    message["metadata"] = msg.get("metadata")
                messages.append(message)

            return messages

        except Exception as e:
            print(f"Lỗi khi lấy tin nhắn từ cơ sở dữ liệu: {str(e)}")
            # Fallback to local storage if database fails
            return self._get_locally(session_id)

    def clear_memory(self, session_id: str) -> bool:
        """
        Clear conversation history for a specific session

        Args:
            session_id: Unique identifier for the conversation

        Returns:
            Success status
        """
        try:
            self.db.clear_conversation_history(session_id)
            # Also clear local backup if it exists
            local_path = self._get_local_path(session_id)
            if os.path.exists(local_path):
                os.remove(local_path)
            return True
        except Exception as e:
            print(f"Warning: Failed to clear conversation history: {str(e)}")
            return False

    def format_for_prompt(self, session_id: str) -> str:
        """
        Định dạng lịch sử hội thoại để sử dụng trong prompt

        Args:
            session_id: ID phiên hội thoại

        Returns:
            Chuỗi lịch sử hội thoại đã định dạng
        """
        try:
            # Lấy tin nhắn từ cơ sở dữ liệu
            result = (
                self.supabase_client.table("conversation_history")
                .select("*")
                .eq("session_id", session_id)
                .order("timestamp")  # Sắp xếp theo thời gian
                .execute()
            )

            if not hasattr(result, "data") or not result.data:
                return ""

            formatted_history = "LỊCH SỬ CUỘC HỘI THOẠI:\n"
            for message in result.data:
                role = message.get("role", "unknown")
                content = message.get("content", "")

                if role == "user":
                    formatted_history += f"Người dùng: {content}\n"
                elif role == "assistant":
                    formatted_history += f"Trợ lý: {content}\n"
                elif role == "system":
                    formatted_history += f"Hệ thống: {content}\n"

            return formatted_history

        except Exception as e:
            print(f"Lỗi khi định dạng lịch sử hội thoại: {str(e)}")
            return ""

    # Fallback local methods for offline or error situations

    def _get_local_path(self, session_id: str) -> str:
        """Generate local file path for conversation session"""
        import os

        # Kiểm tra xem có lưu cục bộ hay không
        use_local_storage = os.getenv("USE_LOCAL_STORAGE", "False").lower() in [
            "true",
            "1",
            "yes",
        ]

        history_dir = os.path.join("src", "conversation_history")
        if use_local_storage:
            os.makedirs(history_dir, exist_ok=True)

        return os.path.join(history_dir, f"{session_id}.json")

    def _save_locally(
        self,
        session_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Save message to local file as fallback"""
        # Kiểm tra xem có cần lưu cục bộ hay không
        import os

        use_local_storage = os.getenv("USE_LOCAL_STORAGE", "False").lower() in [
            "true",
            "1",
            "yes",
        ]

        if not use_local_storage:
            print("Bỏ qua lưu cục bộ vì USE_LOCAL_STORAGE không bật")
            return

        file_path = self._get_local_path(session_id)

        # Read existing history if it exists
        history_data = {
            "session_id": session_id,
            "last_updated": datetime.datetime.now().isoformat(),
            "messages": [],
        }

        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
            except Exception:
                # If file is corrupted, start with a fresh history
                pass

        # Add new message
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now().isoformat(),
        }

        # Add optional fields if provided
        if user_id:
            message["user_id"] = user_id

        if metadata:
            message["metadata"] = metadata

        history_data["messages"].append(message)
        history_data["last_updated"] = datetime.datetime.now().isoformat()

        # Save updated history
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)

    def _get_locally(self, session_id: str) -> List[Dict]:
        """Get messages from local file as fallback"""
        file_path = self._get_local_path(session_id)

        if not os.path.exists(file_path):
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                history_data = json.load(f)

            # Extract and format messages
            messages = []
            for msg in history_data.get("messages", []):
                formatted_message = {
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                }

                # Add metadata if available
                if "metadata" in msg:
                    formatted_message["metadata"] = msg.get("metadata")

                messages.append(formatted_message)

            return messages
        except Exception as e:
            print(f"Warning: Failed to read local conversation history: {str(e)}")
            return []
