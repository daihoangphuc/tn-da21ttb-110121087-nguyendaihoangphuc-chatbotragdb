import re
from typing import List, Dict, Any, Optional, Pattern
from langchain.schema import Document
from tqdm import tqdm
import sqlparse

from src.config import (
    CHUNK_SIZE_SPECIALIZED,
    CHUNK_OVERLAP_SPECIALIZED,
    MIN_CHUNK_SIZE,
    MIN_CHUNK_CHARACTERS,
)

from src.utils import measure_time, print_document_info


class SQLDocumentProcessor:
    """Lớp xử lý chunking đặc biệt cho tài liệu SQL và schema"""

    def __init__(self, embeddings):
        """Khởi tạo với embedding model đã cho"""
        self.embeddings = embeddings
        # Định nghĩa các regex pattern để nhận diện các phần quan trọng trong SQL
        self._init_patterns()

    def _init_patterns(self):
        """Khởi tạo các regex pattern cho việc xử lý SQL"""
        # Pattern cho câu lệnh CREATE TABLE
        self.create_table_pattern = re.compile(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s(]+)(?:\s|\(|$)",
            re.IGNORECASE,
        )
        # Pattern cho các khối lệnh SQL hoàn chỉnh
        self.statement_patterns = {
            "create_table": re.compile(
                r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[^\s(]+(?:\s|\(|$).+?;",
                re.IGNORECASE | re.DOTALL,
            ),
            "create_index": re.compile(
                r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+.+?;", re.IGNORECASE | re.DOTALL
            ),
            "alter_table": re.compile(
                r"ALTER\s+TABLE\s+.+?;", re.IGNORECASE | re.DOTALL
            ),
            "select_query": re.compile(
                r"SELECT\s+.+?(?:;|$)", re.IGNORECASE | re.DOTALL
            ),
            "insert_query": re.compile(
                r"INSERT\s+INTO\s+.+?(?:;|$)", re.IGNORECASE | re.DOTALL
            ),
            "update_query": re.compile(
                r"UPDATE\s+.+?(?:;|$)", re.IGNORECASE | re.DOTALL
            ),
            "delete_query": re.compile(
                r"DELETE\s+FROM\s+.+?(?:;|$)", re.IGNORECASE | re.DOTALL
            ),
            "procedure": re.compile(
                r"CREATE\s+PROCEDURE\s+.+?END;", re.IGNORECASE | re.DOTALL
            ),
            "function": re.compile(
                r"CREATE\s+FUNCTION\s+.+?END;", re.IGNORECASE | re.DOTALL
            ),
            "trigger": re.compile(
                r"CREATE\s+TRIGGER\s+.+?END;", re.IGNORECASE | re.DOTALL
            ),
            "comment": re.compile(r"/\*.*?\*/", re.DOTALL),
        }

    @measure_time
    def process_sql_documents(self, docs: List[Document]) -> List[Document]:
        """Xử lý tài liệu SQL với phương pháp chunking đặc biệt

        Args:
            docs: Danh sách tài liệu SQL cần xử lý

        Returns:
            Danh sách tài liệu đã được chunk theo cấu trúc SQL
        """
        print("⏳ Đang xử lý tài liệu SQL...")
        sql_chunks = []

        for doc in tqdm(docs, desc="Processing SQL documents", unit="doc"):
            # Phát hiện loại tài liệu SQL (schema, query, mixture)
            document_type = self._detect_document_type(doc.page_content)

            # Thêm loại tài liệu vào metadata
            metadata = {**doc.metadata, "sql_document_type": document_type}

            if document_type == "schema":
                # Xử lý đặc biệt cho schema với CREATE TABLE
                chunks = self._process_schema(doc.page_content, metadata)
            elif document_type == "query":
                # Xử lý các câu query
                chunks = self._process_queries(doc.page_content, metadata)
            else:
                # Xử lý hỗn hợp (có cả schema và query)
                chunks = self._process_mixed_sql(doc.page_content, metadata)

            sql_chunks.extend(chunks)

        # Thêm thông tin về loại chunker đã sử dụng
        for chunk in sql_chunks:
            if "processor" not in chunk.metadata:
                chunk.metadata["processor"] = "sql_processor"

        print(f"✅ Đã xử lý tài liệu SQL: {len(sql_chunks)} chunks")
        print_document_info(sql_chunks, "Kết quả SQL processor")
        return sql_chunks

    def _detect_document_type(self, content: str) -> str:
        """Phát hiện loại tài liệu SQL dựa trên nội dung

        Args:
            content: Nội dung SQL cần phân tích

        Returns:
            Loại tài liệu: "schema", "query", hoặc "mixed"
        """
        # Đếm số lượng CREATE TABLE và SELECT
        create_table_count = len(re.findall(r"CREATE\s+TABLE", content, re.IGNORECASE))
        select_count = len(re.findall(r"SELECT\s+", content, re.IGNORECASE))

        # Nếu chủ yếu là CREATE TABLE, coi là schema
        if create_table_count > 0 and create_table_count > select_count:
            return "schema"
        # Nếu chủ yếu là SELECT, INSERT, UPDATE, DELETE, coi là query
        elif select_count > 0 and select_count >= create_table_count:
            return "query"
        # Nếu có cả hai hoặc không phát hiện được pattern rõ ràng
        else:
            return "mixed"

    def _process_schema(self, content: str, metadata: Dict[str, Any]) -> List[Document]:
        """Xử lý tài liệu schema (CREATE TABLE) với giữ nguyên tính toàn vẹn của mỗi bảng

        Args:
            content: Nội dung schema cần xử lý
            metadata: Metadata của tài liệu gốc

        Returns:
            Danh sách Document đã được chunk theo cấu trúc bảng
        """
        chunks = []

        # Format SQL để dễ đọc và phân tích
        formatted_sql = sqlparse.format(content, reindent=True, keyword_case="upper")

        # Tìm các câu lệnh CREATE TABLE
        create_tables = self.statement_patterns["create_table"].finditer(formatted_sql)

        for match in create_tables:
            # Lấy câu lệnh CREATE TABLE hoàn chỉnh
            table_statement = match.group(0)

            # Trích xuất tên bảng từ câu lệnh
            table_name_match = self.create_table_pattern.search(table_statement)
            table_name = (
                table_name_match.group(1) if table_name_match else "unknown_table"
            )

            # Tạo metadata mới với thông tin bảng
            table_metadata = {
                **metadata,
                "sql_type": "create_table",
                "table_name": table_name,
                "schema_element": True,
            }

            # Tạo document mới cho bảng
            table_doc = Document(
                page_content=table_statement.strip(), metadata=table_metadata
            )
            chunks.append(table_doc)

        # Xử lý các phần không phải CREATE TABLE
        remaining_parts = self._extract_non_create_table_parts(formatted_sql)
        if remaining_parts.strip():
            # Chia các phần còn lại thành chunks nếu cần
            other_chunks = self._chunk_sql_code(
                remaining_parts, {**metadata, "sql_type": "other_schema_elements"}
            )
            chunks.extend(other_chunks)

        return chunks

    def _extract_non_create_table_parts(self, content: str) -> str:
        """Trích xuất các phần không phải CREATE TABLE từ nội dung SQL

        Args:
            content: Nội dung SQL

        Returns:
            Chuỗi chứa các phần không phải CREATE TABLE
        """
        # Thay thế tất cả các câu lệnh CREATE TABLE bằng chuỗi rỗng
        result = self.statement_patterns["create_table"].sub("", content)
        return result

    def _process_queries(
        self, content: str, metadata: Dict[str, Any]
    ) -> List[Document]:
        """Xử lý tài liệu chứa các câu query

        Args:
            content: Nội dung SQL query cần xử lý
            metadata: Metadata của tài liệu gốc

        Returns:
            Danh sách Document đã được chunk theo cấu trúc query
        """
        chunks = []

        # Format SQL để dễ đọc và phân tích
        formatted_sql = sqlparse.format(content, reindent=True, keyword_case="upper")

        # Phân tích các câu lệnh SQL
        statements = sqlparse.split(formatted_sql)

        for statement in statements:
            if not statement.strip():
                continue

            # Phát hiện loại câu lệnh
            stmt_type = self._detect_statement_type(statement)

            # Tạo metadata cho câu lệnh
            stmt_metadata = {
                **metadata,
                "sql_type": stmt_type,
                "query_element": True,
            }

            # Thêm thông tin về bảng liên quan nếu phát hiện được
            tables = self._extract_tables_from_query(statement)
            if tables:
                stmt_metadata["related_tables"] = tables

            # Tạo document mới cho câu lệnh
            stmt_doc = Document(page_content=statement.strip(), metadata=stmt_metadata)
            chunks.append(stmt_doc)

        return chunks

    def _detect_statement_type(self, statement: str) -> str:
        """Phát hiện loại câu lệnh SQL

        Args:
            statement: Câu lệnh SQL cần phân tích

        Returns:
            Loại câu lệnh (select, insert, update, delete, ...)
        """
        statement_lower = statement.lower()

        if re.search(r"^\s*select", statement_lower):
            return "select"
        elif re.search(r"^\s*insert", statement_lower):
            return "insert"
        elif re.search(r"^\s*update", statement_lower):
            return "update"
        elif re.search(r"^\s*delete", statement_lower):
            return "delete"
        elif re.search(r"^\s*create\s+table", statement_lower):
            return "create_table"
        elif re.search(r"^\s*create\s+index", statement_lower):
            return "create_index"
        elif re.search(r"^\s*alter\s+table", statement_lower):
            return "alter_table"
        elif re.search(r"^\s*create\s+procedure", statement_lower):
            return "procedure"
        elif re.search(r"^\s*create\s+function", statement_lower):
            return "function"
        elif re.search(r"^\s*create\s+trigger", statement_lower):
            return "trigger"
        else:
            return "other"

    def _extract_tables_from_query(self, query: str) -> List[str]:
        """Trích xuất tên các bảng từ câu truy vấn

        Args:
            query: Câu truy vấn SQL

        Returns:
            Danh sách tên các bảng được sử dụng trong truy vấn
        """
        # Parse SQL statement
        try:
            parsed = sqlparse.parse(query)
            if not parsed:
                return []

            statement = parsed[0]

            # Tìm các FROM clause và JOIN clause để trích xuất tên bảng
            tables = []

            # Pattern cơ bản để tìm bảng sau FROM và JOIN
            from_pattern = re.compile(r"FROM\s+([a-zA-Z0-9_\.]+)", re.IGNORECASE)
            join_pattern = re.compile(r"JOIN\s+([a-zA-Z0-9_\.]+)", re.IGNORECASE)

            # Tìm bảng sau FROM
            from_matches = from_pattern.findall(query)
            tables.extend(from_matches)

            # Tìm bảng sau JOIN
            join_matches = join_pattern.findall(query)
            tables.extend(join_matches)

            # Loại bỏ trùng lặp và làm sạch tên bảng
            clean_tables = [table.strip() for table in tables]
            return list(set(clean_tables))
        except Exception:
            # Fallback nếu xảy ra lỗi khi parse
            return []

    def _process_mixed_sql(
        self, content: str, metadata: Dict[str, Any]
    ) -> List[Document]:
        """Xử lý tài liệu SQL hỗn hợp (có cả schema và query)

        Args:
            content: Nội dung SQL cần xử lý
            metadata: Metadata của tài liệu gốc

        Returns:
            Danh sách Document đã được chunk
        """
        # Kết hợp phương pháp xử lý schema và query
        schema_chunks = self._process_schema(content, metadata)
        query_chunks = self._process_queries(content, metadata)

        # Loại bỏ các chunk trùng lặp
        unique_chunks = self._remove_duplicate_chunks(schema_chunks + query_chunks)

        # Nếu số lượng chunk quá ít, thử áp dụng phương pháp chunking thông thường
        if len(unique_chunks) < 2:
            return self._chunk_sql_code(content, metadata)

        return unique_chunks

    def _remove_duplicate_chunks(self, chunks: List[Document]) -> List[Document]:
        """Loại bỏ các chunk có nội dung trùng lặp

        Args:
            chunks: Danh sách các chunk cần kiểm tra

        Returns:
            Danh sách các chunk sau khi loại bỏ trùng lặp
        """
        seen_contents = set()
        unique_chunks = []

        for chunk in chunks:
            content = chunk.page_content.strip()
            if content and content not in seen_contents:
                seen_contents.add(content)
                unique_chunks.append(chunk)

        return unique_chunks

    def _chunk_sql_code(self, content: str, metadata: Dict[str, Any]) -> List[Document]:
        """Chia nhỏ đoạn code SQL theo kích thước cố định

        Args:
            content: Đoạn code SQL cần chia
            metadata: Metadata của tài liệu gốc

        Returns:
            Danh sách các chunk
        """
        # Sử dụng kích thước chunk và overlap đặc biệt cho SQL
        chunk_size = CHUNK_SIZE_SPECIALIZED
        chunk_overlap = CHUNK_OVERLAP_SPECIALIZED

        # Nếu nội dung quá ngắn, trả về nguyên
        if len(content) <= chunk_size:
            return [Document(page_content=content, metadata=metadata)]

        chunks = []
        # Chia theo các dấu phân cách logic của SQL
        separators = [";", "\nGO\n", "\ngo\n", "\n\n"]

        # Chia dựa trên các dấu phân cách
        current_chunk = ""
        lines = content.split("\n")

        for line in lines:
            # Thêm dòng hiện tại vào chunk
            temp_chunk = current_chunk + "\n" + line if current_chunk else line

            # Kiểm tra nếu có dấu phân cách hoặc chunk đủ lớn
            has_separator = any(sep in line for sep in [";", "GO", "go"])

            if has_separator or len(temp_chunk) >= chunk_size:
                # Nếu chunk đủ lớn, thêm vào danh sách
                if (
                    len(temp_chunk.split()) >= MIN_CHUNK_SIZE
                    and len(temp_chunk) >= MIN_CHUNK_CHARACTERS
                ):
                    chunks.append(Document(page_content=temp_chunk, metadata=metadata))

                # Bắt đầu chunk mới, giữ lại phần overlap
                if has_separator and chunk_overlap > 0:
                    # Giữ lại các dòng cuối cùng cho overlap
                    lines_for_overlap = temp_chunk.split("\n")[-3:]  # Lấy 3 dòng cuối
                    current_chunk = "\n".join(lines_for_overlap)
                else:
                    current_chunk = ""
            else:
                current_chunk = temp_chunk

        # Xử lý phần còn lại nếu có
        if (
            current_chunk
            and len(current_chunk.split()) >= MIN_CHUNK_SIZE
            and len(current_chunk) >= MIN_CHUNK_CHARACTERS
        ):
            chunks.append(Document(page_content=current_chunk, metadata=metadata))

        return chunks
