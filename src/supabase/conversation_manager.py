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
    """
    Quản lý hội thoại sử dụng Supabase
    """

    def __init__(self, client=None):
        """Khởi tạo manager với client Supabase"""
        if client:
            self.supabase_client = client
        else:
            supabase = SupabaseClient()
            self.supabase_client = supabase.get_client()

        # Initialize database access
        self.db = SupabaseDatabase(self.supabase_client)

        # Ensure the conversation history table exists
        try:
            print("Bắt đầu tạo/kiểm tra bảng conversations và messages...")
            # Tạo bảng trước khi cố gắng kiểm tra
            self.db.create_conversation_history_table()

            # Thử kiểm tra bảng bằng cách truy vấn đơn giản mà không sử dụng count(*)
            try:
                result = (
                    self.supabase_client.table("conversations")
                    .select("id")
                    .limit(1)
                    .execute()
                )
                if hasattr(result, "data"):
                    record_count = len(result.data)
                    print(
                        f"Bảng conversations đã tồn tại, đã tìm thấy {record_count} bản ghi mẫu"
                    )
                else:
                    print("Bảng conversations đã tạo nhưng chưa có dữ liệu")
            except Exception as e:
                print(f"Lỗi khi kiểm tra dữ liệu trong bảng: {str(e)}")

            print("Đã tạo/kiểm tra bảng conversations và messages thành công")

        except Exception as e:
            print(f"Warning: Could not create conversation tables: {str(e)}")
            import traceback

            print(f"Chi tiết lỗi khi tạo bảng: {traceback.format_exc()}")
            print("Conversation history might not be properly stored in the database.")

    def add_user_message(
        self, session_id: str, message: str, user_id: Optional[str] = None
    ) -> None:
        """
        Thêm tin nhắn người dùng vào hội thoại

        Args:
            session_id: ID của phiên hội thoại
            message: Nội dung tin nhắn
            user_id: ID của người dùng (nếu có)
        """
        try:
            # Sử dụng phương thức save_conversation_message của lớp Database
            self.db.save_conversation_message(
                session_id=session_id, role="user", content=message, user_id=user_id
            )
            print(f"Đã thêm tin nhắn người dùng: {message[:30]}...")
        except Exception as e:
            print(f"Lỗi khi thêm tin nhắn người dùng: {str(e)}")
            self._save_locally(session_id, "user", message, user_id)

    def add_ai_message(
        self,
        session_id: str,
        message: str,
        metadata: Optional[Dict] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Thêm tin nhắn AI vào hội thoại

        Args:
            session_id: ID của phiên hội thoại
            message: Nội dung tin nhắn
            metadata: Metadata kèm theo (ví dụ: sources)
            user_id: ID của người dùng (nếu có)
        """
        try:
            # Sử dụng phương thức save_conversation_message của lớp Database
            self.db.save_conversation_message(
                session_id=session_id,
                role="assistant",
                content=message,
                user_id=user_id,
                metadata=metadata,
            )
            print(f"Đã thêm tin nhắn AI: {message[:30]}...")
        except Exception as e:
            print(f"Lỗi khi thêm tin nhắn AI: {str(e)}")
            self._save_locally(session_id, "assistant", message, user_id, metadata)

    def _ensure_conversation_exists(
        self, session_id: str, user_id: Optional[str] = None
    ) -> str:
        """
        Đảm bảo conversation tồn tại, tạo mới nếu chưa có

        Args:
            session_id: ID phiên hội thoại
            user_id: ID người dùng (nếu có)

        Returns:
            ID của conversation
        """
        try:
            # Kiểm tra conversation đã tồn tại chưa
            result = (
                self.supabase_client.table("conversations")
                .select("id")
                .eq("session_id", session_id)
                .execute()
            )

            if hasattr(result, "data") and result.data:
                return result.data[0]["id"]

            # Tạo mới nếu chưa tồn tại
            conversation_data = {
                "session_id": session_id,
                "last_updated": "NOW()",
            }

            if user_id:
                conversation_data["user_id"] = user_id

            insert_result = (
                self.supabase_client.table("conversations")
                .insert(conversation_data)
                .execute()
            )

            if hasattr(insert_result, "data") and insert_result.data:
                return insert_result.data[0]["id"]

            raise Exception("Không thể tạo conversation")
        except Exception as e:
            print(f"Lỗi khi đảm bảo conversation tồn tại: {str(e)}")
            raise e

    def _update_conversation_timestamp(self, conversation_id: str) -> None:
        """
        Cập nhật timestamp cho conversation

        Args:
            conversation_id: ID của conversation
        """
        try:
            self.supabase_client.table("conversations").update(
                {"last_updated": "NOW()"}
            ).eq("id", conversation_id).execute()
        except Exception as e:
            print(f"Lỗi khi cập nhật timestamp conversation: {str(e)}")

    def get_messages(self, session_id: str, limit: int = 100) -> List[Dict]:
        """
        Lấy tin nhắn từ một phiên hội thoại

        Args:
            session_id: ID của phiên hội thoại
            limit: Số lượng tin nhắn tối đa

        Returns:
            Danh sách tin nhắn theo thứ tự thời gian
        """
        try:
            # Sử dụng phương thức get_conversation_history của lớp Database
            messages = self.db.get_conversation_history(session_id, limit)

            # Nếu không có tin nhắn, thử lấy từ lưu trữ cục bộ
            if not messages:
                return self._get_locally(session_id)

            # Chuyển đổi định dạng để tương thích với hệ thống
            formatted_messages = []
            for msg in messages:
                message = {
                    "role": msg["role"],
                    "content": msg["content"],
                }

                if "metadata" in msg and msg["metadata"]:
                    message["metadata"] = msg["metadata"]

                formatted_messages.append(message)

            return formatted_messages

        except Exception as e:
            print(f"Lỗi khi lấy tin nhắn phiên hội thoại: {str(e)}")
            return self._get_locally(session_id)

    def clear_memory(self, session_id: str) -> bool:
        """
        Xóa tất cả tin nhắn trong một phiên hội thoại

        Args:
            session_id: ID của phiên hội thoại

        Returns:
            True nếu xóa thành công, False nếu thất bại
        """
        try:
            # Sử dụng phương thức clear_conversation_history từ Database
            result = self.db.clear_conversation_history(session_id)

            # Kiểm tra kết quả
            if result and not (isinstance(result, dict) and "error" in result):
                return True

            print(f"Xóa không thành công: {result}")
            return False

        except Exception as e:
            print(f"Lỗi khi xóa tin nhắn phiên hội thoại: {str(e)}")
            return False

    def format_for_prompt(self, session_id: str) -> str:
        """
        Định dạng lịch sử hội thoại để sử dụng trong prompt

        Args:
            session_id: ID của phiên hội thoại

        Returns:
            Chuỗi lịch sử hội thoại định dạng
        """
        messages = self.get_messages(session_id)
        formatted_history = ""

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if role == "user":
                formatted_history += f"Human: {content}\n\n"
            elif role == "assistant":
                formatted_history += f"AI: {content}\n\n"
            # Bỏ qua tin nhắn hệ thống

        return formatted_history.strip()

    def get_conversations(self, user_id: str) -> List[Dict]:
        """
        Lấy danh sách các cuộc hội thoại của người dùng

        Args:
            user_id: ID của người dùng

        Returns:
            Danh sách các cuộc hội thoại
        """
        try:
            # Lấy tất cả conversation của user_id
            conversations_result = (
                self.supabase_client.table("conversations")
                .select("*")
                .eq("user_id", user_id)
                .order("last_updated", desc=True)
                .execute()
            )

            if (
                not hasattr(conversations_result, "data")
                or not conversations_result.data
            ):
                return []

            # Đếm số lượng tin nhắn cho mỗi conversation
            conversations = []

            for conv in conversations_result.data:
                # Lấy tin nhắn đầu tiên của người dùng
                conversation_id = conv["id"]
                messages_result = (
                    self.supabase_client.table("messages")
                    .select("*")
                    .eq("conversation_id", conversation_id)
                    .eq("role", "user")
                    .order("created_at")
                    .limit(1)
                    .execute()
                )

                first_message = ""
                if hasattr(messages_result, "data") and messages_result.data:
                    first_message = messages_result.data[0]["content"]
                    first_message = (
                        first_message[:100] + "..."
                        if len(first_message) > 100
                        else first_message
                    )

                # Đếm tổng số tin nhắn
                count_result = (
                    self.supabase_client.table("messages")
                    .select("id", count="exact")
                    .eq("conversation_id", conversation_id)
                    .execute()
                )

                message_count = (
                    len(count_result.data) if hasattr(count_result, "data") else 0
                )

                conversations.append(
                    {
                        "session_id": conv["session_id"],
                        "message_count": message_count,
                        "last_updated": conv["last_updated"],
                        "first_message": first_message,
                    }
                )

            return conversations

        except Exception as e:
            print(f"Lỗi khi lấy danh sách hội thoại: {str(e)}")
            import traceback

            print(traceback.format_exc())
            return []

    def delete_conversation(self, session_id: str, user_id: str) -> bool:
        """
        Xóa một cuộc hội thoại

        Args:
            session_id: ID của phiên hội thoại
            user_id: ID của người dùng

        Returns:
            True nếu xóa thành công, False nếu thất bại
        """
        try:
            print(f"Bắt đầu xóa hội thoại: session_id={session_id}, user_id={user_id}")

            # Kiểm tra session_id hợp lệ
            if not session_id or session_id == "undefined" or session_id == "null":
                print(f"Lỗi: session_id không hợp lệ: '{session_id}'")
                return False

            # Lấy conversation_id
            conv_result = (
                self.supabase_client.table("conversations")
                .select("id")
                .eq("session_id", session_id)
                .eq("user_id", user_id)
                .execute()
            )

            if not hasattr(conv_result, "data") or not conv_result.data:
                print(
                    f"Không tìm thấy conversation với session_id: {session_id} và user_id: {user_id}"
                )
                return False

            conversation_id = conv_result.data[0]["id"]

            # Xóa conversation (sẽ tự động xóa messages do có ràng buộc CASCADE)
            result = (
                self.supabase_client.table("conversations")
                .delete()
                .eq("id", conversation_id)
                .execute()
            )

            # Kiểm tra kết quả
            if hasattr(result, "data") and result.data:
                print(f"Đã xóa thành công conversation_id: {conversation_id}")
                return True

            print(f"Xóa không thành công, kết quả không có data: {result}")
            return False

        except Exception as e:
            print(f"Lỗi khi xóa hội thoại: {str(e)}")
            import traceback

            print(traceback.format_exc())
            return False

    def create_conversation(self, user_id: str) -> str:
        """
        Tạo một cuộc hội thoại mới

        Args:
            user_id: ID của người dùng

        Returns:
            session_id của cuộc hội thoại mới
        """
        try:
            # Tạo session_id mới
            import uuid

            session_id = str(uuid.uuid4())

            # Tạo conversation mới
            result = (
                self.supabase_client.table("conversations")
                .insert(
                    {
                        "session_id": session_id,
                        "user_id": user_id,
                        "last_updated": "NOW()",
                    }
                )
                .execute()
            )

            if hasattr(result, "data") and result.data:
                conversation_id = result.data[0]["id"]

                # Tạo tin nhắn hệ thống đầu tiên
                self.supabase_client.table("messages").insert(
                    {
                        "conversation_id": conversation_id,
                        "role": "assistant",
                        "content": "Bắt đầu cuộc hội thoại mới",
                    }
                ).execute()

                return session_id

            print("Không thể tạo conversation mới")
            return None

        except Exception as e:
            print(f"Lỗi khi tạo hội thoại mới: {str(e)}")
            return None

    # Các phương thức hỗ trợ lưu trữ cục bộ có thể giữ nguyên
    def _get_local_path(self, session_id: str) -> str:
        import os

        # Xác định thư mục lưu trữ
        history_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "conversation_history",
        )
        if not os.path.exists(history_dir):
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
