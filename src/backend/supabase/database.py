"""
Supabase Database module for database operations.
"""

from typing import Dict, List, Optional, Any, Union
from .client import SupabaseClient
import json
import pytz
from datetime import datetime

import logging

# Cấu hình logging
logging.basicConfig(format="[Database_InitInit] %(message)s", level=logging.INFO)
# Ghi đè hàm print để thêm prefix
original_print = print


def print(*args, **kwargs):
    prefix = "[Database_Init] "
    original_print(prefix + " ".join(map(str, args)), **kwargs)

# Hàm utility để lấy thời gian Việt Nam
def get_vietnam_time():
    """Lấy thời gian hiện tại theo múi giờ Việt Nam"""
    vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    return datetime.now(vietnam_tz)

def format_vietnam_time_for_db():
    """Format thời gian Việt Nam cho database"""
    vietnam_time = get_vietnam_time()
    return vietnam_time.isoformat()


class SupabaseDatabase:
    """Class for managing database operations with Supabase"""

    def __init__(self, client=None):
        """Initialize the database module with a Supabase client"""
        if client:
            self.client = client
        else:
            self.client = SupabaseClient().get_client()

    def from_table(self, table_name: str):
        """Get a query builder for a specific table"""
        return self.client.table(table_name)

    def query(self, sql_query: str, params: Optional[Dict] = None):
        """Execute a raw SQL query"""
        return self.client.rpc("run_sql", {"sql": sql_query})

    # Conversation History Management

    # def create_conversation_history_table(self):
    #     """Create the conversations and messages tables if they don't exist"""
    #     print("Đang cố gắng tạo bảng conversations và messages...")
    #     try:
    #         # Phương pháp 1: Sử dụng SQL trực tiếp qua REST API
    #         direct_sql = """
    #         -- Bảng lưu phiên làm việc chính
    #         CREATE TABLE IF NOT EXISTS public.conversations (
    #           conversation_id    TEXT        PRIMARY KEY,                  -- Khóa chính duy nhất cho mỗi session
    #           user_id       UUID        NOT NULL,                     -- ID người dùng (IdentityUser.Id)
    #           last_updated  TIMESTAMP   NOT NULL DEFAULT now()        -- Thời gian cập nhật cuối cùng
    #         );

    #         -- Bảng lưu chi tiết các tin nhắn cho mỗi phiên
    #         CREATE TABLE IF NOT EXISTS public.messages (
    #           message_id    BIGSERIAL   PRIMARY KEY,                  -- Khóa tự tăng
    #           conversation_id    TEXT        NOT NULL,                     -- Khóa ngoại liên kết về conversations.conversation_id
    #           sequence      INT         NOT NULL,                     -- Thứ tự tin nhắn trong phiên
    #           role          TEXT        NOT NULL CHECK (role IN ('user','assistant')), 
    #                                                         -- Vai trò: user hoặc assistant
    #           content       TEXT        NOT NULL,                     -- Nội dung tin nhắn
    #           metadata      JSONB,                                    -- Metadata bổ sung
    #           created_at    TIMESTAMP   NOT NULL DEFAULT now(),       -- Thời gian tạo
    #           CONSTRAINT fk_messages_conversations
    #             FOREIGN KEY (conversation_id)
    #             REFERENCES public.conversations(conversation_id)
    #             ON DELETE CASCADE
    #         );

    #         -- Tạo index để truy vấn nhanh các tin nhắn theo session và thứ tự
    #         CREATE INDEX IF NOT EXISTS idx_messages_conversation_seq
    #           ON public.messages(conversation_id, sequence);
    #         """

    #         print("Thực thi SQL trực tiếp để tạo bảng...")
    #         # Phương pháp 1: Dùng SQL trực tiếp với run_sql thay vì exec_sql
    #         result = self.client.postgrest.rpc(
    #             "run_sql", {"sql": direct_sql}
    #         ).execute()
    #         # print(f"Kết quả tạo bảng: {result}")
    #         return result

    #     except Exception as e:
    #         print(f"Lỗi khi tạo bảng qua SQL trực tiếp: {str(e)}")
    #         import traceback

    #         print(f"Chi tiết: {traceback.format_exc()}")

    #         # Phương pháp 2: Thử tạo từng bảng riêng biệt
    #         try:
    #             print("Thử phương pháp tạo từng bảng riêng biệt...")
                
    #             # Tạo bảng conversations
    #             conversations_sql = """
    #             CREATE TABLE IF NOT EXISTS public.conversations (
    #               conversation_id    TEXT        PRIMARY KEY,
    #               user_id       UUID        NOT NULL,
    #               last_updated  TIMESTAMP   NOT NULL DEFAULT now()
    #             );
    #             """
    #             self.client.postgrest.rpc("run_sql", {"sql": conversations_sql}).execute()
    #             print("Đã tạo bảng conversations")
                
    #             # Tạo bảng messages
    #             messages_sql = """
    #             CREATE TABLE IF NOT EXISTS public.messages (
    #               message_id    BIGSERIAL   PRIMARY KEY,
    #               conversation_id    TEXT        NOT NULL,
    #               sequence      INT         NOT NULL,
    #               role          TEXT        NOT NULL CHECK (role IN ('user','assistant')),
    #               content       TEXT        NOT NULL,
    #               metadata      JSONB,
    #               created_at    TIMESTAMP   NOT NULL DEFAULT now(),
    #               CONSTRAINT fk_messages_conversations
    #                 FOREIGN KEY (conversation_id)
    #                 REFERENCES public.conversations(conversation_id)
    #                 ON DELETE CASCADE
    #             );
    #             """
    #             self.client.postgrest.rpc("run_sql", {"sql": messages_sql}).execute()
    #             print("Đã tạo bảng messages")
                
    #             # Tạo index
    #             index_sql = """
    #             CREATE INDEX IF NOT EXISTS idx_messages_conversation_seq
    #               ON public.messages(conversation_id, sequence);
    #             """
    #             self.client.postgrest.rpc("run_sql", {"sql": index_sql}).execute()
    #             print("Đã tạo index cho bảng messages")
                
    #             return {"success": True, "message": "Đã tạo bảng conversations và messages"}
                
    #         except Exception as e2:
    #             print(f"Lỗi khi tạo từng bảng riêng biệt: {str(e2)}")

    #             # Phương pháp 3: Thử insert để xem bảng đã tồn tại chưa
    #             try:
    #                 print("Thử phương pháp insert để tạo bảng...")
    #                 # Tạo một session trước
    #                 import uuid

    #                 conversation_id = f"test_session_init_{uuid.uuid4().hex[:8]}"
    #                 session_data = {
    #                     "conversation_id": conversation_id,
    #                     "user_id": uuid.uuid4(),
    #                     "last_updated": format_vietnam_time_for_db(),
    #                 }
    #                 session_result = (
    #                     self.client.table("conversations").insert(session_data).execute()
    #                 )

    #                 # Sau đó tạo một message
    #                 if hasattr(session_result, "data") and session_result.data:
    #                     message_data = {
    #                         "conversation_id": conversation_id,
    #                         "sequence": 1,
    #                         "role": "assistant",
    #                         "content": "Khởi tạo bảng dữ liệu",
    #                     }
    #                     message_result = (
    #                         self.client.table("messages").insert(message_data).execute()
    #                     )
    #                     print(
    #                         f"Đã tạo bản ghi test thành công: {message_result.data if hasattr(message_result, 'data') else 'No data'}"
    #                     )

    #                 return session_result
    #             except Exception as e3:
    #                 print(f"Tất cả các phương pháp tạo bảng thất bại: {str(e3)}")
    #                 raise Exception(
    #                     "Không thể tạo bảng conversations và messages bằng bất kỳ phương pháp nào"
    #                 )

    def save_conversation_message(
        self,
        current_conversation_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Lưu tin nhắn vào cơ sở dữ liệu với cấu trúc bảng mới

        Args:
            current_conversation_id: ID phiên hội thoại
            role: Vai trò ('user' hoặc 'assistant')
            content: Nội dung tin nhắn
            user_id: ID người dùng (nếu có)
            metadata: Metadata bổ sung (nếu có)

        Returns:
            Bản ghi đã tạo
        """
        print(
            f"Lưu tin nhắn: current_conversation_id={current_conversation_id}, role={role}, content={content[:30]}..."
        )

        # Đảm bảo dữ liệu đúng định dạng
        if role not in ["user", "assistant", "system"]:
            print(f"Warning: Role '{role}' không hợp lệ, đang sử dụng 'user' thay thế")
            role = "user"

        # Kiểm tra conversation_id không được để trống
        if not current_conversation_id:
            print("Warning: current_conversation_id rỗng, đang tạo ID ngẫu nhiên")
            import uuid

            current_conversation_id = f"conv_{uuid.uuid4().hex}"

        # Kiểm tra content không được để trống
        if not content:
            content = "<empty message>"

        try:
            # Bước 1: Kiểm tra và tạo session nếu chưa tồn tại
            conv_table = self.from_table("conversations")
            conv_result = (
                conv_table.select("conversation_id")
                .eq("conversation_id", current_conversation_id)
                .execute()
            )

            if hasattr(conv_result, "data") and len(conv_result.data) > 0:
                # Session đã tồn tại
                conversation_id = conv_result.data[0]["conversation_id"]
                print(f"Conversation đã tồn tại với id: {conversation_id}")

                # Cập nhật last_updated
                conv_table.update({"last_updated": format_vietnam_time_for_db()}).eq(
                    "conversation_id", current_conversation_id
                ).execute()
            else:
                # Tạo session mới
                print(
                    f"Conversation không tồn tại, tạo mới với id: {current_conversation_id}"
                )
                import uuid

                # Nếu không có user_id, tạo một UUID mới
                if not user_id:
                    user_id = str(uuid.uuid4())

                session_data = {
                    "conversation_id": current_conversation_id,
                    "user_id": user_id,
                    "last_updated": format_vietnam_time_for_db(),
                }
                conv_result = conv_table.insert(session_data).execute()

                if hasattr(conv_result, "data") and len(conv_result.data) > 0:
                    conversation_id = conv_result.data[0]["conversation_id"]
                else:
                    conversation_id = current_conversation_id

            # Bước 2: Xác định sequence cho tin nhắn mới
            sequence_result = (
                self.client.table("messages")
                .select("sequence")
                .eq("conversation_id", current_conversation_id)
                .order("sequence", desc=True)
                .limit(1)
                .execute()
            )

            sequence = 1  # Mặc định cho tin nhắn đầu tiên
            if hasattr(sequence_result, "data") and len(sequence_result.data) > 0:
                sequence = sequence_result.data[0]["sequence"] + 1

            # Bước 3: Tạo metadata object nếu cần
            metadata_obj = metadata or {}

            # Bước 4: Lưu tin nhắn
            message_data = {
                "conversation_id": current_conversation_id,
                "sequence": sequence,
                "role": role,
                "content": content,
            }

            # Thêm metadata nếu có
            if metadata_obj:
                print(f"Thêm metadata: {metadata_obj}")
                message_data["metadata"] = json.dumps(metadata_obj)

            message_result = (
                self.client.table("messages").insert(message_data).execute()
            )

            if hasattr(message_result, "data") and len(message_result.data) > 0:
                return message_result.data[0]
            else:
                print(f"Lỗi khi lưu tin nhắn: {message_result}")
                return {"error": "Không thể lưu tin nhắn"}

        except Exception as e:
            print(f"Lỗi khi lưu tin nhắn: {str(e)}")
            import traceback

            print(f"Chi tiết: {traceback.format_exc()}")
            return {"error": str(e)}

    def get_conversation_history(
        self, current_conversation_id: str, limit: int = 100
    ) -> List[Dict]:
        """
        Lấy lịch sử hội thoại cho một phiên cụ thể với cấu trúc bảng mới

        Args:
            current_conversation_id: ID phiên hội thoại
            limit: Số lượng tin nhắn tối đa cần lấy

        Returns:
            Danh sách tin nhắn của cuộc hội thoại, sắp xếp theo thời gian
        """
        try:
            # Bước 1: Lấy conversation_id từ conversation_id
            conv_result = (
                self.from_table("conversations")
                .select("conversation_id")
                .eq("conversation_id", current_conversation_id)
                .execute()
            )

            if not hasattr(conv_result, "data") or not conv_result.data:
                print(
                    f"Không tìm thấy conversation với conversation_id: {current_conversation_id}"
                )
                return []

            conversation_id = conv_result.data[0]["conversation_id"]

            # Bước 2: Lấy tin nhắn từ bảng messages
            msg_result = (
                self.from_table("messages")
                .select("*")
                .eq("conversation_id", current_conversation_id)
                .order("sequence")
                .limit(limit)
                .execute()
            )

            if not hasattr(msg_result, "data"):
                return []

            # Chuyển đổi định dạng để tương thích với code cũ
            messages = []
            for msg in msg_result.data:
                message = {
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg.get(
                        "created_at", msg.get("timestamp", datetime.now().isoformat())
                    ),  # Đảm bảo có trường timestamp, sử dụng created_at hoặc timestamp nếu có
                }

                if "metadata" in msg and msg["metadata"]:
                    message["metadata"] = msg["metadata"]

                messages.append(message)

            return messages

        except Exception as e:
            print(f"Lỗi khi lấy lịch sử hội thoại: {str(e)}")
            import traceback

            print(f"Chi tiết lỗi: {traceback.format_exc()}")
            return []

    def clear_conversation_history(
        self, current_conversation_id: str, user_id: str = None
    ) -> Dict:
        """
        Xóa tất cả tin nhắn trong một phiên hội thoại nhưng giữ lại phiên

        Args:
            current_conversation_id: ID phiên hội thoại
            user_id: ID người dùng sở hữu (tùy chọn)

        Returns:
            Kết quả của thao tác
        """
        try:
            # Bước 1: Lấy conversation_id từ conversation_id, kiểm tra cả user_id nếu có
            query = (
                self.from_table("conversations")
                .select("conversation_id")
                .eq("conversation_id", current_conversation_id)
            )

            # Thêm điều kiện user_id nếu được cung cấp
            if user_id:
                query = query.eq("user_id", user_id)

            conv_result = query.execute()

            if not hasattr(conv_result, "data") or not conv_result.data:
                print(
                    f"Không tìm thấy conversation với conversation_id: {current_conversation_id}"
                    + (f" và user_id: {user_id}" if user_id else "")
                )
                return {"error": "Không tìm thấy phiên hội thoại"}

            conversation_id = conv_result.data[0]["conversation_id"]

            # Bước 2: Xóa tất cả tin nhắn của session này
            # (giữ lại session để có thể thêm tin nhắn mới)
            result = (
                self.from_table("messages")
                .delete()
                .eq("conversation_id", current_conversation_id)
                .execute()
            )

            # Bước 3: Cập nhật last_updated cho session
            self.from_table("conversations").update({"last_updated": format_vietnam_time_for_db()}).eq(
                "conversation_id", current_conversation_id
            ).execute()

            return result

        except Exception as e:
            print(f"Lỗi khi xóa lịch sử hội thoại: {str(e)}")
            import traceback

            print(f"Chi tiết lỗi: {traceback.format_exc()}")
            return {"error": str(e)}

    # Document Files Management
    def create_document_files_table(self):
        """Create the document files table if it doesn't exist"""
        sql = """
        -- Tạo bảng document_files để lưu trữ thông tin file
        CREATE TABLE IF NOT EXISTS public.document_files (
          file_id UUID PRIMARY KEY,
          filename TEXT NOT NULL,
          file_path TEXT NOT NULL,
          user_id UUID NOT NULL REFERENCES auth.users(id),
          upload_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          file_type TEXT,
          is_deleted BOOLEAN DEFAULT FALSE,
          deleted_at TIMESTAMPTZ,
          metadata JSONB
        );
        
        -- Tạo index để tìm kiếm nhanh
        CREATE INDEX IF NOT EXISTS idx_document_files_user_id ON public.document_files(user_id);
        CREATE INDEX IF NOT EXISTS idx_document_files_filename ON public.document_files(filename);
        CREATE INDEX IF NOT EXISTS idx_document_files_upload_time ON public.document_files(upload_time);

        -- Policy để mỗi người dùng chỉ thấy file của mình
        CREATE POLICY IF NOT EXISTS "Người dùng chỉ thấy file của mình" 
        ON public.document_files FOR SELECT 
        USING (auth.uid() = user_id);

        -- Policy cho phép người dùng tạo file của mình
        CREATE POLICY IF NOT EXISTS "Người dùng có thể tạo file" 
        ON public.document_files FOR INSERT 
        WITH CHECK (auth.uid() = user_id);

        -- Policy cho phép người dùng cập nhật file của mình
        CREATE POLICY IF NOT EXISTS "Người dùng có thể cập nhật file của mình" 
        ON public.document_files FOR UPDATE 
        USING (auth.uid() = user_id);

        -- Policy cho phép người dùng xóa file của mình
        CREATE POLICY IF NOT EXISTS "Người dùng có thể xóa file của mình" 
        ON public.document_files FOR DELETE 
        USING (auth.uid() = user_id);
        """
        return self.query(sql)

    def save_document_file(
        self,
        filename: str,
        file_path: str,
        file_type: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Save document file information to the database

        Args:
            filename: Name of the file
            file_path: Path to the file (in storage)
            file_type: Type of the file (extension)
            user_id: ID of the user who uploaded the file
            metadata: Additional metadata

        Returns:
            The created record
        """
        import uuid
        table = self.from_table("document_files")

        data = {
            "file_id": str(uuid.uuid4()),
            "filename": filename,
            "file_path": file_path,
            "user_id": user_id,
            "upload_time": "NOW()"
        }

        if file_type:
            data["file_type"] = file_type

        if metadata:
            data["metadata"] = metadata

        return table.insert(data).execute()

    def get_document_files(
        self, filename: str = None, user_id: str = None
    ) -> List[Dict]:
        """
        Get document file information from the database

        Args:
            filename: Optional filename to filter by
            user_id: Optional user ID to filter by

        Returns:
            List of document file records
        """
        table = self.from_table("document_files")
        query = table.select("*").eq("is_deleted", False)  # Only return non-deleted files

        if filename:
            query = query.eq("filename", filename)

        if user_id:
            query = query.eq("user_id", user_id)

        response = query.execute()
        return response.data

    def update_document_file_metadata(
        self, filename: str, is_indexed: bool = True
    ) -> Dict:
        """
        Update metadata of a document file

        Args:
            filename: Name of the file
            is_indexed: Whether the document has been indexed

        Returns:
            The updated record
        """
        table = self.from_table("document_files")
        # Store indexing information in the metadata field
        data = {
            "metadata": {
                "is_indexed": is_indexed,
                "last_indexed": "NOW()"
            }
        }

        return table.update(data).eq("filename", filename).execute()

    def delete_document_file(self, filename: str) -> Dict:
        """
        Mark a document file as deleted (soft delete)

        Args:
            filename: Name of the file

        Returns:
            Result of the operation
        """
        table = self.from_table("document_files")
        data = {
            "is_deleted": True,
            "deleted_at": "NOW()"
        }
        return table.update(data).eq("filename", filename).execute()

    def delete_conversation(self, conversation_id: str, user_id: str = None) -> Dict:
        """
        Xóa hoàn toàn một phiên hội thoại bao gồm tất cả tin nhắn của nó

        Args:
            conversation_id: ID phiên hội thoại cần xóa
            user_id: ID người dùng sở hữu (tùy chọn)

        Returns:
            Kết quả của thao tác xóa
        """
        try:
            # Chuẩn bị truy vấn
            query = self.from_table("conversations").delete()

            # Lọc theo conversation_id
            query = query.eq("conversation_id", conversation_id)

            # Thêm điều kiện user_id nếu được cung cấp
            if user_id:
                query = query.eq("user_id", user_id)
                print(f"Đang xóa hội thoại {conversation_id} của người dùng {user_id}")
            else:
                print(f"Đang xóa hội thoại {conversation_id} (không kiểm tra user_id)")

            # Thực thi truy vấn
            result = query.execute()

            # Kiểm tra kết quả
            if hasattr(result, "data") and len(result.data) > 0:
                print(f"Đã xóa hội thoại {conversation_id} thành công")
                return {
                    "success": True,
                    "message": f"Đã xóa hội thoại {conversation_id}",
                }
            else:
                print(
                    f"Không tìm thấy hội thoại {conversation_id}"
                    + (f" thuộc người dùng {user_id}" if user_id else "")
                )
                return {"success": False, "message": "Không tìm thấy hội thoại để xóa"}

        except Exception as e:
            print(f"Lỗi khi xóa hội thoại: {str(e)}")
            import traceback

            print(f"Chi tiết lỗi: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}
