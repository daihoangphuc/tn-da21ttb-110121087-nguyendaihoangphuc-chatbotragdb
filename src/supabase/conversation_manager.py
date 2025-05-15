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

import logging

# Cấu hình logging
logging.basicConfig(format="[Conversation_Manager] %(message)s", level=logging.INFO)
# Ghi đè hàm print để thêm prefix
original_print = print


def print(*args, **kwargs):
    prefix = "[Conversation_Manager] "
    original_print(prefix + " ".join(map(str, args)), **kwargs)

class SupabaseConversationManager:
    """
    Quản lý hội thoại sử dụng Supabase
    """

    def __init__(self, client=None):
        """Khởi tạo manager với client Supabase"""
        from .database import SupabaseDatabase

        try:
            if client:
                self.supabase_client = client
            else:
                from .client import SupabaseClient

                self.supabase_client = SupabaseClient().get_client()

            # Khởi tạo đối tượng Database để sử dụng các phương thức hỗ trợ
            self.db = SupabaseDatabase(self.supabase_client)

            # Tạo bảng sessions và messages nếu chưa tồn tại
            self.db.create_conversation_history_table()

            print(
                "Khởi tạo SupabaseConversationManager thành công để lưu trữ hội thoại qua Supabase"
            )

        except Exception as e:
            import traceback

            print(f"Lỗi khi khởi tạo SupabaseConversationManager: {str(e)}")
            print(traceback.format_exc())
            raise e

    def add_user_message(
        self, session_id: str, message: str, user_id: Optional[str] = None
    ) -> None:
        """
        Thêm tin nhắn người dùng vào bộ nhớ

        Args:
            session_id: ID của phiên hội thoại
            message: Nội dung tin nhắn
            user_id: ID của người dùng (tùy chọn)
        """
        try:
            # Lấy sequence mới nhất
            sequence = self._get_next_sequence(session_id)

            # Lưu tin nhắn với role = user
            self.db.save_conversation_message(
                session_id=session_id,
                role="user",
                content=message,
                user_id=user_id,
            )
        except Exception as e:
            print(f"Lỗi khi thêm tin nhắn người dùng: {str(e)}")
            # Lưu cục bộ nếu lỗi
            self._save_locally(session_id, "user", message, user_id)

    def add_ai_message(
        self,
        session_id: str,
        message: str,
        metadata: Optional[Dict] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Thêm tin nhắn AI vào bộ nhớ

        Args:
            session_id: ID của phiên hội thoại
            message: Nội dung tin nhắn
            metadata: Metadata bổ sung (tùy chọn)
            user_id: ID của người dùng (tùy chọn)
        """
        try:
            # Lấy sequence mới nhất
            sequence = self._get_next_sequence(session_id)

            # Lưu tin nhắn với role = assistant
            self.db.save_conversation_message(
                session_id=session_id,
                role="assistant",
                content=message,
                user_id=user_id,
                metadata=metadata,
            )
        except Exception as e:
            print(f"Lỗi khi thêm tin nhắn AI: {str(e)}")
            # Lưu cục bộ nếu lỗi
            self._save_locally(session_id, "assistant", message, user_id, metadata)

    def _get_next_sequence(self, session_id: str) -> int:
        """Lấy sequence tiếp theo cho tin nhắn mới"""
        try:
            # Tìm sequence lớn nhất
            result = (
                self.supabase_client.table("messages")
                .select("sequence")
                .eq("conversation_id", session_id)
                .order("sequence", desc=True)
                .limit(1)
                .execute()
            )

            if hasattr(result, "data") and result.data:
                return result.data[0]["sequence"] + 1
            return 1
        except Exception as e:
            print(f"Lỗi khi lấy sequence: {str(e)}")
            return 1

    def _ensure_conversation_exists(
        self, session_id: str, user_id: Optional[str] = None
    ) -> str:
        """
        Đảm bảo phiên hội thoại tồn tại, nếu không thì tạo mới

        Args:
            session_id: ID phiên hội thoại
            user_id: ID người dùng (tùy chọn)

        Returns:
            session_id đã tồn tại hoặc mới tạo
        """
        try:
            # Kiểm tra phiên đã tồn tại chưa
            result = (
                self.supabase_client.table("conversations")
                .select("conversation_id")
                .eq("conversation_id", session_id)
                .execute()
            )

            # Nếu chưa tồn tại, tạo mới
            if not hasattr(result, "data") or not result.data:
                import uuid

                create_result = (
                    self.supabase_client.table("conversations")
                    .insert(
                        {
                            "conversation_id": session_id,
                            "user_id": user_id if user_id else uuid.uuid4(),
                            "last_updated": "NOW()",
                        }
                    )
                    .execute()
                )
                if hasattr(create_result, "data") and create_result.data:
                    print(f"Đã tạo phiên hội thoại mới: {session_id}")
                else:
                    print(f"Lỗi khi tạo phiên hội thoại: {create_result}")
            else:
                # Cập nhật last_updated
                self._update_conversation_timestamp(session_id)

            return session_id
        except Exception as e:
            print(f"Lỗi khi đảm bảo phiên hội thoại tồn tại: {str(e)}")
            import traceback

            print(traceback.format_exc())
            return session_id

    def _update_conversation_timestamp(self, session_id: str) -> None:
        """
        Cập nhật thời gian cuối cùng của phiên hội thoại

        Args:
            session_id: ID phiên hội thoại
        """
        try:
            self.supabase_client.table("conversations").update(
                {"last_updated": "NOW()"}
            ).eq("conversation_id", session_id).execute()
        except Exception as e:
            print(f"Lỗi khi cập nhật timestamp: {str(e)}")

    def get_messages(self, session_id: str, limit: int = 100) -> List[Dict]:
        """
        Lấy danh sách tin nhắn của một phiên hội thoại

        Args:
            session_id: ID phiên hội thoại
            limit: Số lượng tin nhắn tối đa trả về

        Returns:
            Danh sách tin nhắn theo thứ tự tăng dần của sequence
        """
        try:
            # Thử lấy từ Supabase trước
            messages = self.db.get_conversation_history(session_id, limit)

            if not messages:
                # Nếu không có kết quả từ Supabase, thử lấy từ local
                local_messages = self._get_locally(session_id)
                if local_messages:
                    print(
                        f"Đã tìm thấy {len(local_messages)} tin nhắn cục bộ cho {session_id}"
                    )
                return local_messages

            return messages
        except Exception as e:
            print(f"Lỗi khi lấy tin nhắn: {str(e)}")
            # Thử lấy từ local nếu lỗi
            return self._get_locally(session_id)

    def clear_memory(self, session_id: str) -> bool:
        """
        Xóa tất cả tin nhắn trong hội thoại

        Args:
            session_id: ID phiên hội thoại cần xóa

        Returns:
            True nếu xóa thành công, False nếu có lỗi
        """
        try:
            # Xóa tin nhắn trên Supabase
            result = self.db.clear_conversation_history(session_id)
            if isinstance(result, dict) and result.get("error"):
                print(f"Lỗi khi xóa tin nhắn từ Supabase: {result.get('error')}")
                return False

            # Xóa tin nhắn cục bộ
            self._clear_local_memory(session_id)

            return True
        except Exception as e:
            print(f"Lỗi khi xóa bộ nhớ hội thoại: {str(e)}")
            return False

    def _clear_local_memory(self, session_id: str) -> None:
        """Xóa bộ nhớ cục bộ cho phiên hội thoại"""
        try:
            local_path = self._get_local_path(session_id)
            if os.path.exists(local_path):
                os.remove(local_path)
                print(f"Đã xóa tệp lưu trữ cục bộ: {local_path}")
        except Exception as e:
            print(f"Lỗi khi xóa bộ nhớ cục bộ: {str(e)}")

    def format_for_prompt(self, session_id: str) -> str:
        """
        Định dạng lịch sử hội thoại để sử dụng trong prompt

        Args:
            session_id: ID phiên hội thoại

        Returns:
            Chuỗi định dạng lịch sử hội thoại
        """
        messages = self.get_messages(session_id)
        if not messages:
            return ""

        formatted_history = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                formatted_history.append(f"Người dùng: {content}")
            elif role == "assistant":
                formatted_history.append(f"Trợ lý: {content}")

        return "\n".join(formatted_history)

    def get_conversations(self, user_id: str) -> List[Dict]:
        """
        Lấy danh sách tất cả các phiên hội thoại của người dùng

        Args:
            user_id: ID người dùng

        Returns:
            Danh sách các phiên hội thoại
        """
        try:
            # Lấy danh sách phiên hội thoại từ Supabase
            result = (
                self.supabase_client.table("conversations")
                .select("conversation_id, last_updated")
                .eq("user_id", user_id)
                .order("last_updated", desc=True)
                .execute()
            )

            if not hasattr(result, "data"):
                return []

            conversations = []
            for conv in result.data:
                conversation_id = conv.get("conversation_id")
                last_updated = conv.get("last_updated")

                # Lấy tin nhắn đầu tiên để hiển thị làm tiêu đề
                first_message = ""
                message_result = (
                    self.supabase_client.table("messages")
                    .select("content")
                    .eq("conversation_id", conversation_id)
                    .eq("role", "user")
                    .order("sequence")
                    .limit(1)
                    .execute()
                )

                if hasattr(message_result, "data") and message_result.data:
                    first_message = message_result.data[0].get("content", "")

                # Đếm số lượng tin nhắn
                count_result = (
                    self.supabase_client.table("messages")
                    .select("count", count="exact")
                    .eq("conversation_id", conversation_id)
                    .execute()
                )

                message_count = 0
                if hasattr(count_result, "count"):
                    message_count = count_result.count

                # Tạo đối tượng hội thoại
                conversations.append(
                    {
                        "session_id": conversation_id,
                        "last_updated": last_updated,
                        "first_message": first_message,
                        "message_count": message_count,
                    }
                )

            return conversations
        except Exception as e:
            print(f"Lỗi khi lấy danh sách hội thoại: {str(e)}")
            return []

    def delete_conversation(self, session_id: str, user_id: str) -> bool:
        """
        Xóa hoàn toàn một phiên hội thoại

        Args:
            session_id: ID phiên hội thoại cần xóa
            user_id: ID người dùng sở hữu

        Returns:
            True nếu xóa thành công, False nếu có lỗi
        """
        try:
            # Kiểm tra phiên tồn tại và thuộc người dùng
            result = (
                self.supabase_client.table("conversations")
                .select("conversation_id")
                .eq("conversation_id", session_id)
                .eq("user_id", user_id)
                .execute()
            )

            if not hasattr(result, "data") or not result.data:
                print(
                    f"Không tìm thấy phiên hội thoại {session_id} của người dùng {user_id}"
                )
                return False

            # Xóa tin nhắn trước (có CASCADE sẽ tự động xóa)
            delete_result = (
                self.supabase_client.table("conversations")
                .delete()
                .eq("conversation_id", session_id)
                .eq("user_id", user_id)
                .execute()
            )

            # Xóa bộ nhớ cục bộ
            self._clear_local_memory(session_id)

            if hasattr(delete_result, "data") and delete_result.data:
                print(f"Đã xóa phiên hội thoại {session_id}")
                return True
            else:
                print(f"Lỗi khi xóa phiên hội thoại: {delete_result}")
                return False
        except Exception as e:
            print(f"Lỗi khi xóa phiên hội thoại: {str(e)}")
            return False

    def create_conversation(
        self, user_id: str, conversation_id: Optional[str] = None
    ) -> str:
        """
        Tạo một phiên hội thoại mới

        Args:
            user_id: ID người dùng sở hữu
            conversation_id: ID phiên hội thoại (tùy chọn, nếu không có sẽ tạo ID mới)

        Returns:
            ID phiên hội thoại mới tạo
        """
        try:
            import uuid

            # Nếu không cung cấp ID, tạo ID mới
            if not conversation_id:
                conversation_id = f"conv_{uuid.uuid4().hex}"

            # Tạo phiên hội thoại mới
            result = (
                self.supabase_client.table("conversations")
                .insert(
                    {
                        "conversation_id": conversation_id,
                        "user_id": user_id,
                        "last_updated": "NOW()",
                    }
                )
                .execute()
            )

            if hasattr(result, "data") and result.data:
                # Tạo tin nhắn chào mừng
                welcome_message = "Chào mừng bạn! Tôi có thể giúp gì cho bạn?"
                self.add_ai_message(
                    session_id=conversation_id, message=welcome_message, user_id=user_id
                )

                print(
                    f"Đã tạo phiên hội thoại mới {conversation_id} cho người dùng {user_id}"
                )
                return conversation_id
            else:
                print(f"Lỗi khi tạo phiên hội thoại: {result}")
                raise Exception("Không thể tạo phiên hội thoại mới")
        except Exception as e:
            print(f"Lỗi khi tạo phiên hội thoại: {str(e)}")
            raise e

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
