import re
import sqlparse
from typing import List, Dict, Any
from langchain.schema import Document
from tqdm import tqdm

from src.utils import measure_time, print_document_info
from src.config import (
    SQL_CHUNK_SIZE,
    SQL_CHUNK_OVERLAP,
    SQL_SCHEMA_KEYWORDS,
    SQL_QUERY_KEYWORDS,
    SQL_FILE_EXTENSIONS,
)


class SQLDocumentProcessor:
    """Lớp xử lý chunking đặc biệt cho cơ sở dữ liệu SQL"""

    def __init__(self, embeddings):
        """Khởi tạo với embedding model đã cho"""
        self.embeddings = embeddings

    @measure_time
    def process_sql_documents(self, docs: List[Document]) -> List[Document]:
        """Xử lý tài liệu SQL với chunking đặc biệt

        Args:
            docs: Danh sách tài liệu SQL cần xử lý

        Returns:
            Danh sách tài liệu đã được chunk
        """
        print("⏳ Đang xử lý tài liệu SQL...")
        sql_chunks = []

        for doc in tqdm(docs, desc="Processing SQL documents", unit="doc"):
            # Đọc nội dung SQL
            sql_content = doc.page_content
            # Phân loại loại nội dung SQL
            sql_type = self._classify_sql_content(sql_content)

            # Metadata cơ bản
            metadata = {
                **doc.metadata,
                "sql_document_type": sql_type,
                "processor": "sql_processor",
            }

            # Xử lý SQL tùy thuộc vào loại
            if sql_type == "schema":
                chunks = self._process_schema(sql_content, metadata)
            elif sql_type == "query":
                chunks = self._process_query(sql_content, metadata)
            else:
                # Xử lý SQL tổng quát nếu không phân loại được
                chunks = self._process_general_sql(sql_content, metadata)

            # Thêm các chunk vào kết quả
            sql_chunks.extend(chunks)

        print(f"✅ Đã xử lý tài liệu SQL: {len(sql_chunks)} chunks")
        print_document_info(sql_chunks, "Kết quả SQL processor")
        return sql_chunks

    def _classify_sql_content(self, content: str) -> str:
        """Phân loại nội dung SQL thành schema, query hoặc mixed

        Args:
            content: Nội dung SQL cần phân loại

        Returns:
            Loại SQL: "schema", "query", hoặc "mixed"
        """
        # Chuẩn hóa nội dung để so sánh
        content_upper = content.upper()

        # Đếm từ khóa schema và query
        schema_count = sum(
            1 for kw in SQL_SCHEMA_KEYWORDS if kw.upper() in content_upper
        )
        query_count = sum(1 for kw in SQL_QUERY_KEYWORDS if kw.upper() in content_upper)

        if schema_count > 0 and query_count == 0:
            return "schema"
        elif query_count > 0 and schema_count == 0:
            return "query"
        else:
            return "mixed"

    def _process_schema(self, content: str, metadata: Dict[str, Any]) -> List[Document]:
        """Xử lý SQL định nghĩa schema/DDL

        Args:
            content: Nội dung SQL
            metadata: Metadata cơ bản

        Returns:
            Danh sách các Document đã được chunk
        """
        # Sử dụng sqlparse để phân tích cú pháp SQL
        statements = sqlparse.parse(content)
        chunks = []

        # Xử lý từng statement riêng biệt
        current_chunk = ""
        current_length = 0

        for statement in statements:
            stmt_str = str(statement)
            stmt_length = len(stmt_str)

            # Nếu statement quá dài, cắt nó riêng biệt
            if stmt_length > SQL_CHUNK_SIZE:
                # Thêm chunk hiện tại nếu có
                if current_chunk:
                    chunks.append(
                        Document(
                            page_content=current_chunk,
                            metadata={**metadata, "sql_type": "schema"},
                        )
                    )
                    current_chunk = ""
                    current_length = 0

                # Tạo chunk riêng cho statement lớn
                chunks.append(
                    Document(
                        page_content=stmt_str,
                        metadata={**metadata, "sql_type": "schema"},
                    )
                )
            # Hoặc thêm vào chunk hiện tại nếu còn đủ chỗ
            elif current_length + stmt_length <= SQL_CHUNK_SIZE:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += stmt_str
                current_length += stmt_length
            # Nếu không đủ chỗ, bắt đầu chunk mới
            else:
                chunks.append(
                    Document(
                        page_content=current_chunk,
                        metadata={**metadata, "sql_type": "schema"},
                    )
                )
                current_chunk = stmt_str
                current_length = stmt_length

        # Thêm chunk cuối cùng nếu có
        if current_chunk:
            chunks.append(
                Document(
                    page_content=current_chunk,
                    metadata={**metadata, "sql_type": "schema"},
                )
            )

        return chunks

    def _process_query(self, content: str, metadata: Dict[str, Any]) -> List[Document]:
        """Xử lý SQL queries

        Args:
            content: Nội dung SQL
            metadata: Metadata cơ bản

        Returns:
            Danh sách các Document đã được chunk
        """
        # Phân tích cú pháp query
        statements = sqlparse.parse(content)
        chunks = []

        # Xử lý từng query riêng biệt
        for statement in statements:
            stmt_str = str(statement)
            # Bỏ qua statements rỗng
            if not stmt_str.strip():
                continue

            # Thêm thông tin loại query vào metadata
            query_metadata = {**metadata, "sql_type": "query"}

            # Xác định loại query (SELECT, INSERT, UPDATE, v.v.)
            query_type = statement.get_type()
            if query_type:
                query_metadata["query_type"] = query_type

            chunks.append(
                Document(
                    page_content=stmt_str,
                    metadata=query_metadata,
                )
            )

        return chunks

    def _process_general_sql(
        self, content: str, metadata: Dict[str, Any]
    ) -> List[Document]:
        """Xử lý SQL tổng quát

        Args:
            content: Nội dung SQL
            metadata: Metadata cơ bản

        Returns:
            Danh sách các Document đã được chunk
        """
        # Xử lý tương tự như schema nhưng với SQL mixed
        statements = sqlparse.parse(content)
        chunks = []

        current_chunk = ""
        current_length = 0

        for statement in statements:
            stmt_str = str(statement)
            if not stmt_str.strip():
                continue

            stmt_length = len(stmt_str)

            # Nếu statement quá dài, cắt nó riêng biệt
            if stmt_length > SQL_CHUNK_SIZE:
                # Thêm chunk hiện tại nếu có
                if current_chunk:
                    chunks.append(
                        Document(
                            page_content=current_chunk,
                            metadata={**metadata, "sql_type": "mixed"},
                        )
                    )
                    current_chunk = ""
                    current_length = 0

                # Tạo chunk riêng cho statement lớn
                chunks.append(
                    Document(
                        page_content=stmt_str,
                        metadata={**metadata, "sql_type": "mixed"},
                    )
                )
            # Hoặc thêm vào chunk hiện tại nếu còn đủ chỗ
            elif current_length + stmt_length <= SQL_CHUNK_SIZE:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += stmt_str
                current_length += stmt_length
            # Nếu không đủ chỗ, bắt đầu chunk mới
            else:
                chunks.append(
                    Document(
                        page_content=current_chunk,
                        metadata={**metadata, "sql_type": "mixed"},
                    )
                )
                current_chunk = stmt_str
                current_length = stmt_length

        # Thêm chunk cuối cùng nếu có
        if current_chunk:
            chunks.append(
                Document(
                    page_content=current_chunk,
                    metadata={**metadata, "sql_type": "mixed"},
                )
            )

        return chunks
