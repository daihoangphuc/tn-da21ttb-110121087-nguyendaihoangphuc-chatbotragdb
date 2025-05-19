"""
Supabase Conversation Manager for handling conversation history with Supabase.
"""

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

    cur_conversation_id = None

    def set_current_conversation_id(self, conversation_id: str) -> None:
        """Đặt conversation_id hiện tại để sử dụng trong các thao tác tiếp theo"""
        self.cur_conversation_id = conversation_id
        print(f"Đã đặt conversation_id hiện tại: {conversation_id}")

    def get_current_conversation_id(self) -> str:
        return self.cur_conversation_id

    def add_user_message(
        self, current_conversation_id: str, message: str, user_id: Optional[str] = None
    ) -> None:
        """
        Thêm tin nhắn người dùng vào bộ nhớ

        Args:
            current_conversation_id: ID của phiên hội thoại
            message: Nội dung tin nhắn
            user_id: ID của người dùng (tùy chọn)
        """
        try:
            # Lấy sequence mới nhất
            sequence = self._get_next_sequence(current_conversation_id)

            # Lưu tin nhắn với role = user
            self.db.save_conversation_message(
                current_conversation_id=current_conversation_id,
                role="user",
                content=message,
                user_id=user_id,
            )
        except Exception as e:
            print(f"Lỗi khi thêm tin nhắn người dùng: {str(e)}")
            raise e

    def add_ai_message(
        self,
        current_conversation_id: str,
        message: str,
        metadata: Optional[Dict] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Thêm tin nhắn AI vào bộ nhớ

        Args:
            current_conversation_id: ID của phiên hội thoại
            message: Nội dung tin nhắn
            metadata: Metadata bổ sung (tùy chọn)
            user_id: ID của người dùng (tùy chọn)
        """
        try:
            # Lấy sequence mới nhất
            sequence = self._get_next_sequence(current_conversation_id)

            # Lưu tin nhắn với role = assistant
            self.db.save_conversation_message(
                current_conversation_id=current_conversation_id,
                role="assistant",
                content=message,
                user_id=user_id,
                metadata=metadata,
            )
        except Exception as e:
            print(f"Lỗi khi thêm tin nhắn AI: {str(e)}")
            raise e

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
            # Lấy tin nhắn từ Supabase
            messages = self.db.get_conversation_history(session_id, limit)
            return messages if messages else []
        except Exception as e:
            print(f"Lỗi khi lấy tin nhắn: {str(e)}")
            return []

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
            return True
        except Exception as e:
            print(f"Lỗi khi xóa bộ nhớ hội thoại: {str(e)}")
            return False

    def format_for_prompt(self, current_conversation_id: str) -> str:
        """
        Định dạng lịch sử hội thoại để sử dụng trong prompt

        Args:
            current_conversation_id: ID phiên hội thoại

        Returns:
            Chuỗi định dạng lịch sử hội thoại
        """
        try:

            # Lấy tin nhắn từ database
            messages = self.get_messages(current_conversation_id)
            if not messages:
                print(f"Không tìm thấy tin nhắn cho session {current_conversation_id}")
                return ""

            # Sắp xếp tin nhắn theo sequence để đảm bảo đúng thứ tự
            messages.sort(key=lambda x: x.get("sequence", 0))
            print(
                f"Đã tìm thấy {len(messages)} tin nhắn cho session {current_conversation_id}"
            )

            formatted_history = []
            for msg in messages:
                role = msg.get("role", "")
                content = msg.get("content", "").strip()

                # Chỉ thêm tin nhắn có nội dung
                if content:
                    if role == "user":
                        formatted_history.append(f"Người dùng: {content}")
                    elif role == "assistant":
                        formatted_history.append(f"Trợ lý: {content}")

            formatted_text = "\n".join(formatted_history)
            print(
                f"Lịch sử hội thoại được định dạng ({len(formatted_history)} tin nhắn):"
            )
            print(
                formatted_text[:200] + "..."
                if len(formatted_text) > 200
                else formatted_text
            )

            return formatted_text
        except Exception as e:
            print(f"Lỗi khi format lịch sử hội thoại: {str(e)}")
            return ""

    def get_conversations(self, user_id: str, delete_empty: bool = True) -> List[Dict]:
        """
        Lấy danh sách các phiên hội thoại của người dùng
        Chỉ trả về những hội thoại có tin nhắn, trừ cuộc hội thoại mới nhất
        Có thể xóa những hội thoại rỗng (không có tin nhắn) nếu delete_empty=True

        Args:
            user_id: ID người dùng
            delete_empty: Nếu True, xóa luôn những cuộc hội thoại không có tin nhắn (trừ cuộc hội thoại mới nhất)

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

            if not hasattr(result, "data") or not result.data:
                return []

            conversations = []
            is_first = True  # Đánh dấu cuộc hội thoại đầu tiên (mới nhất)
            deleted_count = 0  # Đếm số cuộc hội thoại bị xóa

            for conv in result.data:
                conversation_id = conv.get("conversation_id")
                last_updated = conv.get("last_updated")

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

                # Nếu không phải cuộc hội thoại mới nhất và không có tin nhắn, xóa nếu delete_empty=True
                if not is_first and message_count == 0 and delete_empty:
                    try:
                        # Xóa cuộc hội thoại rỗng
                        delete_result = (
                            self.supabase_client.table("conversations")
                            .delete()
                            .eq("conversation_id", conversation_id)
                            .eq("user_id", user_id)
                            .execute()
                        )
                        if hasattr(delete_result, "data") and delete_result.data:
                            deleted_count += 1
                            print(f"Đã xóa cuộc hội thoại rỗng: {conversation_id}")
                        continue  # Bỏ qua, không thêm vào kết quả
                    except Exception as e:
                        print(
                            f"Lỗi khi xóa cuộc hội thoại rỗng {conversation_id}: {str(e)}"
                        )

                # Nếu là cuộc hội thoại mới nhất hoặc có tin nhắn, thì thêm vào danh sách
                if is_first or message_count > 0:
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

                    # Tạo đối tượng hội thoại
                    conversations.append(
                        {
                            "conversation_id": conversation_id,
                            "last_updated": last_updated,
                            "first_message": first_message,
                            "message_count": message_count,
                            "is_newest": is_first,  # Thêm trường để biết đây là cuộc hội thoại mới nhất
                        }
                    )

                # Đánh dấu không còn là cuộc hội thoại đầu tiên nữa
                if is_first:
                    is_first = False

            if delete_empty and deleted_count > 0:
                print(f"Đã xóa {deleted_count} cuộc hội thoại rỗng")

            print(
                f"Đã tìm thấy {len(conversations)} cuộc hội thoại có tin nhắn (hoặc mới nhất)"
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

            if hasattr(delete_result, "data") and delete_result.data:
                print(f"Đã xóa phiên hội thoại {session_id}")
                return True
            else:
                print(f"Lỗi khi xóa phiên hội thoại: {delete_result}")
                return False
        except Exception as e:
            print(f"Lỗi khi xóa phiên hội thoại: {str(e)}")
            return False

    def create_conversation(self, user_id: str) -> str:
        """
        Tạo một phiên hội thoại mới

        Args:
            user_id: ID người dùng sở hữu

        Returns:
            ID phiên hội thoại mới tạo
        """
        try:
            import uuid

            # Tạo ID mới với prefix conv_
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

            # Nếu không có lỗi (status 201), trả về conversation_id
            print(
                f"Đã tạo phiên hội thoại mới {conversation_id} cho người dùng {user_id}"
            )
            self.cur_conversation_id = conversation_id
            return conversation_id

        except Exception as e:
            print(f"Lỗi khi tạo phiên hội thoại: {str(e)}")
            raise e

    def get_latest_conversation_with_messages(
        self, user_id: str, limit: int = 100
    ) -> Dict:
        """
        Lấy đoạn hội thoại gần đây nhất của người dùng có tin nhắn
        - Nếu hội thoại gần nhất có tin nhắn, trả về hội thoại đó
        - Nếu hội thoại gần nhất không có tin nhắn, tìm hội thoại gần thứ hai có tin nhắn

        Args:
            user_id: ID người dùng
            limit: Số lượng tin nhắn tối đa trả về trong mỗi hội thoại

        Returns:
            Dict chứa thông tin hội thoại và danh sách tin nhắn:
            {
                "conversation_info": {
                    "session_id": str,
                    "last_updated": str,
                    "first_message": str,
                    "message_count": int
                },
                "messages": List[Dict]  # Danh sách tin nhắn của hội thoại
            }
            Trả về {} nếu không tìm thấy hội thoại có tin nhắn
        """
        try:
            # Lấy danh sách phiên hội thoại từ Supabase
            result = (
                self.supabase_client.table("conversations")
                .select("conversation_id, last_updated")
                .eq("user_id", user_id)
                .order("last_updated", desc=True)
                .limit(5)  # Giới hạn 5 phiên gần nhất để tìm kiếm
                .execute()
            )

            if not hasattr(result, "data") or not result.data:
                print(f"Không tìm thấy phiên hội thoại nào cho người dùng {user_id}")
                return {}

            for conv in result.data:
                conversation_id = conv.get("conversation_id")
                last_updated = conv.get("last_updated")

                # Lấy tin nhắn của phiên hội thoại
                messages = self.get_messages(conversation_id, limit)

                # Nếu có tin nhắn, trả về thông tin hội thoại và tin nhắn
                if messages and len(messages) > 0:
                    # Lấy tin nhắn đầu tiên để hiển thị làm tiêu đề
                    first_message = ""
                    for msg in messages:
                        if msg.get("role") == "user":
                            first_message = msg.get("content", "")
                            break

                    print(
                        f"Đã tìm thấy hội thoại gần đây có {len(messages)} tin nhắn: {conversation_id}"
                    )

                    return {
                        "conversation_info": {
                            "session_id": conversation_id,
                            "last_updated": last_updated,
                            "first_message": first_message,
                            "message_count": len(messages),
                        },
                        "messages": messages,
                    }

            # Nếu không tìm thấy hội thoại nào có tin nhắn
            print(f"Không tìm thấy hội thoại nào có tin nhắn cho người dùng {user_id}")
            return {}

        except Exception as e:
            print(f"Lỗi khi lấy hội thoại gần đây có tin nhắn: {str(e)}")
            return {}
