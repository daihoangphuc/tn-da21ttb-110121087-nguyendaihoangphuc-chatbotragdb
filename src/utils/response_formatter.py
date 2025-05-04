import re
from typing import Dict, Any, Optional, List
from src.utils.markdown_formatter import format_markdown, analyze_markdown_structure


class ResponseFormatter:
    """Lớp xử lý và định dạng phản hồi từ LLM theo chuẩn Markdown"""

    @staticmethod
    def format_response(
        response_text: str, query_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Định dạng phản hồi từ LLM và trả về kèm metadata

        Args:
            response_text: Phản hồi gốc từ LLM
            query_type: Loại truy vấn (sql, schema, entity, performance, general)

        Returns:
            Dict chứa phản hồi đã định dạng và metadata
        """
        # Định dạng phản hồi sử dụng markdown_formatter
        formatted_text = format_markdown(response_text)

        # Phân tích cấu trúc markdown để cung cấp metadata
        structure = analyze_markdown_structure(formatted_text)

        # Xác định loại truy vấn nếu không được chỉ định
        if not query_type:
            query_type = ResponseFormatter._detect_query_type(formatted_text)

        # Bổ sung định dạng đặc biệt cho từng loại truy vấn
        formatted_text = ResponseFormatter._apply_specific_formatting(
            formatted_text, query_type
        )

        # Tạo metadata dựa trên cấu trúc phản hồi
        format_metadata = {
            "format": "markdown",
            "has_code_blocks": len(structure.get("code_blocks", [])) > 0,
            "has_tables": len(structure.get("tables", [])) > 0,
            "has_images": len(structure.get("images", [])) > 0,
            "has_math": "$$" in formatted_text or "\\(" in formatted_text,
            "has_headings": len(structure.get("headings", [])) > 0,
        }

        # Thêm các metadata cụ thể theo loại query
        if query_type:
            format_metadata["query_type"] = query_type

        # Kiểm tra các loại code block cụ thể
        if structure.get("code_blocks"):
            languages = [
                block.get("language", "").lower()
                for block in structure.get("code_blocks", [])
            ]
            format_metadata["has_sql"] = "sql" in languages
            format_metadata["has_python"] = "python" in languages
            format_metadata["has_diagram"] = any(
                lang in languages for lang in ["mermaid", "plantuml", "dot"]
            )

        return {"response": formatted_text, "format_metadata": format_metadata}

    @staticmethod
    def _detect_query_type(text: str) -> str:
        """Phát hiện loại truy vấn dựa trên nội dung phản hồi

        Args:
            text: Phản hồi được định dạng

        Returns:
            Loại truy vấn: sql, schema, entity, performance, general
        """
        # SQL generation
        if re.search(
            r"(##\s+Câu\s+(?:truy\s+vấn|lệnh)\s+SQL|```sql)", text, re.IGNORECASE
        ):
            return "sql"

        # Schema analysis
        if re.search(
            r"(#\s+Phân\s+tích\s+Schema|##\s+(?:Tổng\s+quan\s+về|Phân\s+tích)\s+schema)",
            text,
            re.IGNORECASE,
        ):
            return "schema"

        # Entity relationship
        if re.search(
            r"(#\s+Phân\s+tích\s+ERD|##\s+(?:Các\s+thực\s+thể|Mối\s+quan\s+hệ))",
            text,
            re.IGNORECASE,
        ):
            return "entity"

        # Performance analysis
        if re.search(
            r"(#\s+Phân\s+tích\s+hiệu\s+suất|##\s+(?:Điểm\s+nghẽn|Tối\s+ưu\s+truy\s+vấn))",
            text,
            re.IGNORECASE,
        ):
            return "performance"

        # Default to general
        return "general"

    @staticmethod
    def _apply_specific_formatting(text: str, query_type: str) -> str:
        """Áp dụng định dạng đặc biệt cho từng loại truy vấn

        Args:
            text: Phản hồi được định dạng
            query_type: Loại truy vấn

        Returns:
            Phản hồi đã được định dạng tùy chỉnh
        """
        if query_type == "sql":
            # Đảm bảo code SQL được định dạng chuẩn
            text = ResponseFormatter._format_sql_response(text)
        elif query_type == "schema":
            # Định dạng đặc biệt cho phân tích schema
            text = ResponseFormatter._format_schema_response(text)
        elif query_type == "entity":
            # Định dạng đặc biệt cho ERD
            text = ResponseFormatter._format_erd_response(text)
        elif query_type == "performance":
            # Định dạng đặc biệt cho phân tích hiệu suất
            text = ResponseFormatter._format_performance_response(text)

        return text

    @staticmethod
    def _format_sql_response(text: str) -> str:
        """Định dạng phản hồi liên quan đến sinh mã SQL

        Args:
            text: Phản hồi gốc

        Returns:
            Phản hồi đã định dạng chuẩn cho SQL
        """
        # Đảm bảo có các tiêu đề cần thiết
        headers = ["Cách tiếp cận", "Câu truy vấn SQL", "Giải thích", "Kết quả dự kiến"]

        for header in headers:
            if not re.search(rf"##\s+{header}", text, re.IGNORECASE):
                # Tìm vị trí thích hợp để thêm tiêu đề này
                if header == "Cách tiếp cận" and not re.search(r"##\s+.+", text):
                    # Nếu không có tiêu đề nào, thêm tiêu đề đầu tiên
                    text = f"## Cách tiếp cận\n\n{text}"
                elif (
                    header == "Câu truy vấn SQL"
                    and "```sql" in text
                    and not re.search(
                        r"##\s+Câu\s+truy\s+vấn\s+SQL", text, re.IGNORECASE
                    )
                ):
                    # Tìm vị trí của code block SQL đầu tiên
                    sql_pos = text.find("```sql")
                    if sql_pos > 0:
                        # Tìm vị trí của dòng mới trước khối SQL
                        newline_pos = text.rfind("\n\n", 0, sql_pos)
                        if newline_pos > 0:
                            text = (
                                text[:newline_pos]
                                + "\n\n## Câu truy vấn SQL\n"
                                + text[newline_pos + 2 :]
                            )

        # Đảm bảo SQL keywords được viết hoa trong code blocks
        sql_blocks = re.finditer(r"```sql\s*([\s\S]*?)```", text)
        for match in sql_blocks:
            sql_code = match.group(1)
            formatted_sql = ResponseFormatter._format_sql_keywords(sql_code)
            text = text.replace(match.group(0), f"```sql\n{formatted_sql}\n```")

        return text

    @staticmethod
    def _format_schema_response(text: str) -> str:
        """Định dạng phản hồi liên quan đến phân tích schema

        Args:
            text: Phản hồi gốc

        Returns:
            Phản hồi đã định dạng chuẩn cho phân tích schema
        """
        # Đảm bảo có tiêu đề chính
        if not re.search(r"#\s+Phân\s+tích\s+Schema", text, re.IGNORECASE):
            text = "# Phân tích Schema\n\n" + text

        # Đảm bảo có các tiêu đề cần thiết
        headers = [
            "Tổng quan về schema",
            "Phân tích chi tiết từng bảng",
            "Mối quan hệ và ràng buộc",
            "Đánh giá thiết kế",
            "Đề xuất cải tiến",
        ]

        # Đảm bảo SQL trong code blocks được định dạng chuẩn
        sql_blocks = re.finditer(r"```sql\s*([\s\S]*?)```", text)
        for match in sql_blocks:
            sql_code = match.group(1)
            formatted_sql = ResponseFormatter._format_sql_keywords(sql_code)
            text = text.replace(match.group(0), f"```sql\n{formatted_sql}\n```")

        # Đảm bảo bảng có định dạng đúng
        tables = re.finditer(r"\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|", text)
        for match in tables:
            # Kiểm tra nếu có cột khóa và có các từ "PK", "FK"
            if ("Khóa" in match.group(0) or "khóa" in match.group(0)) and not (
                "**" in match.group(0) or "*" in match.group(0)
            ):
                # Định dạng lại bảng với khóa chính đậm, khóa ngoại nghiêng
                table_lines = []
                in_table = False
                for line in text.split("\n"):
                    if "|" in line:
                        if not in_table:
                            in_table = True
                            table_lines.append(line)
                        else:
                            # Tìm cột khóa
                            cols = line.split("|")
                            if len(cols) >= 4:  # Đảm bảo có đủ cột
                                key_col_idx = -1
                                for i, col in enumerate(cols):
                                    if (
                                        "PK" in col
                                        or "FK" in col
                                        or "khóa" in col.lower()
                                    ):
                                        key_col_idx = i
                                        break

                                if key_col_idx > 0:
                                    # Định dạng tên khóa
                                    name_col = cols[1].strip()
                                    if "PK" in cols[key_col_idx]:
                                        cols[1] = f" **{name_col}** "
                                    elif "FK" in cols[key_col_idx]:
                                        cols[1] = f" *{name_col}* "

                                    line = "|".join(cols)

                            table_lines.append(line)
                    else:
                        if in_table:
                            in_table = False
                            # Gộp bảng đã định dạng lại vào text
                            formatted_table = "\n".join(table_lines)
                            text = text.replace("\n".join(table_lines), formatted_table)
                            table_lines = []

        return text

    @staticmethod
    def _format_erd_response(text: str) -> str:
        """Định dạng phản hồi liên quan đến ERD

        Args:
            text: Phản hồi gốc

        Returns:
            Phản hồi đã định dạng chuẩn cho ERD
        """
        # Tương tự như các hàm định dạng khác
        return text

    @staticmethod
    def _format_performance_response(text: str) -> str:
        """Định dạng phản hồi liên quan đến phân tích hiệu suất

        Args:
            text: Phản hồi gốc

        Returns:
            Phản hồi đã định dạng chuẩn cho phân tích hiệu suất
        """
        # Tương tự như các hàm định dạng khác
        return text

    @staticmethod
    def _format_sql_keywords(sql_code: str) -> str:
        """Định dạng các từ khóa SQL thành chữ hoa

        Args:
            sql_code: Mã SQL cần định dạng

        Returns:
            Mã SQL đã định dạng
        """
        keywords = [
            "SELECT",
            "FROM",
            "WHERE",
            "JOIN",
            "LEFT",
            "RIGHT",
            "INNER",
            "OUTER",
            "GROUP BY",
            "ORDER BY",
            "HAVING",
            "LIMIT",
            "OFFSET",
            "INSERT INTO",
            "VALUES",
            "UPDATE",
            "SET",
            "DELETE",
            "CREATE",
            "ALTER",
            "DROP",
            "TABLE",
            "INDEX",
            "VIEW",
            "PROCEDURE",
            "FUNCTION",
            "TRIGGER",
            "CONSTRAINT",
            "PRIMARY KEY",
            "FOREIGN KEY",
            "REFERENCES",
            "CASCADE",
            "UNION",
            "INTERSECT",
            "EXCEPT",
            "WITH",
            "AS",
            "ON",
            "AND",
            "OR",
            "NOT",
            "NULL",
            "IS",
            "IN",
            "BETWEEN",
            "EXISTS",
            "CASE",
            "WHEN",
            "THEN",
            "ELSE",
            "END",
        ]

        # Thay thế từng từ khóa, đảm bảo chỉ thay thế từ khóa hoàn chỉnh
        formatted_code = sql_code
        for keyword in keywords:
            pattern = re.compile(r"\b" + re.escape(keyword) + r"\b", re.IGNORECASE)
            formatted_code = pattern.sub(keyword, formatted_code)

        return formatted_code
