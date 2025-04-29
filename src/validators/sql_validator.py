import re
import sqlparse
from typing import Dict, List, Tuple, Any, Optional, Union


class SQLValidator:
    """Lớp kiểm tra tính đúng đắn của các câu lệnh SQL"""

    @staticmethod
    def validate(sql_query: str) -> Tuple[bool, List[str]]:
        """Kiểm tra tính đúng đắn của câu lệnh SQL

        Args:
            sql_query: Câu lệnh SQL cần kiểm tra

        Returns:
            Tuple gồm (is_valid, errors)
            - is_valid: True nếu SQL hợp lệ, False nếu không
            - errors: Danh sách các lỗi phát hiện được
        """
        # Danh sách lưu các lỗi
        errors = []

        # Kiểm tra cơ bản
        if not sql_query or not sql_query.strip():
            errors.append("SQL trống")
            return False, errors

        # Phân tích và format SQL
        try:
            formatted_sql = sqlparse.format(
                sql_query, reindent=True, keyword_case="upper"
            )
            statements = sqlparse.parse(formatted_sql)

            if not statements:
                errors.append("Không thể phân tích cú pháp SQL")
                return False, errors

        except Exception as e:
            errors.append(f"Lỗi khi phân tích cú pháp SQL: {str(e)}")
            return False, errors

        # Đối với mỗi câu lệnh, kiểm tra các lỗi cơ bản
        for stmt in statements:
            # Kiểm tra câu lệnh trống
            if not str(stmt).strip():
                continue

            # Kiểm tra dấu chấm phẩy cuối câu
            if not str(stmt).strip().endswith(";"):
                errors.append(f"Câu lệnh thiếu dấu chấm phẩy kết thúc: {str(stmt)}")

            # Kiểm tra lỗi cú pháp cơ bản theo loại câu lệnh
            errors.extend(SQLValidator._validate_statement_by_type(stmt))

        # Nếu không có lỗi nào, SQL hợp lệ
        is_valid = len(errors) == 0
        return is_valid, errors

    @staticmethod
    def _validate_statement_by_type(stmt) -> List[str]:
        """Kiểm tra lỗi cú pháp dựa trên loại câu lệnh

        Args:
            stmt: Câu lệnh SQL đã qua phân tích

        Returns:
            Danh sách các lỗi phát hiện được
        """
        errors = []
        stmt_type = stmt.get_type()
        stmt_text = str(stmt)

        if stmt_type == "SELECT":
            errors.extend(SQLValidator._validate_select(stmt_text))
        elif stmt_type == "INSERT":
            errors.extend(SQLValidator._validate_insert(stmt_text))
        elif stmt_type == "UPDATE":
            errors.extend(SQLValidator._validate_update(stmt_text))
        elif stmt_type == "DELETE":
            errors.extend(SQLValidator._validate_delete(stmt_text))
        elif stmt_type == "CREATE":
            if "TABLE" in stmt_text.upper():
                errors.extend(SQLValidator._validate_create_table(stmt_text))

        return errors

    @staticmethod
    def _validate_select(query: str) -> List[str]:
        """Kiểm tra câu lệnh SELECT

        Args:
            query: Câu lệnh SELECT cần kiểm tra

        Returns:
            Danh sách các lỗi phát hiện được
        """
        errors = []

        # Kiểm tra FROM thiếu
        if "SELECT" in query.upper() and "FROM" not in query.upper():
            errors.append("Câu lệnh SELECT thiếu mệnh đề FROM")

        # Kiểm tra lỗi JOIN không có điều kiện
        join_pattern = re.compile(r"JOIN\s+(\w+)(?:\s+AS\s+\w+)?\s+ON", re.IGNORECASE)
        if "JOIN" in query.upper() and not join_pattern.search(query):
            errors.append("JOIN thiếu điều kiện ON")

        # Kiểm tra GROUP BY không đúng với các cột aggregate
        if "GROUP BY" in query.upper():
            if (
                "COUNT(" in query.upper()
                or "SUM(" in query.upper()
                or "AVG(" in query.upper()
            ):
                # Kiểm tra cơ bản - cần phân tích sâu hơn trong triển khai thực tế
                pass

        return errors

    @staticmethod
    def _validate_insert(query: str) -> List[str]:
        """Kiểm tra câu lệnh INSERT

        Args:
            query: Câu lệnh INSERT cần kiểm tra

        Returns:
            Danh sách các lỗi phát hiện được
        """
        errors = []

        # Kiểm tra thiếu INTO
        if "INSERT" in query.upper() and "INTO" not in query.upper():
            errors.append("Câu lệnh INSERT thiếu từ khóa INTO")

        # Kiểm tra VALUES hoặc SELECT
        if "VALUES" not in query.upper() and "SELECT" not in query.upper():
            errors.append("INSERT thiếu mệnh đề VALUES hoặc SELECT")

        return errors

    @staticmethod
    def _validate_update(query: str) -> List[str]:
        """Kiểm tra câu lệnh UPDATE

        Args:
            query: Câu lệnh UPDATE cần kiểm tra

        Returns:
            Danh sách các lỗi phát hiện được
        """
        errors = []

        # Kiểm tra thiếu SET
        if "UPDATE" in query.upper() and "SET" not in query.upper():
            errors.append("Câu lệnh UPDATE thiếu từ khóa SET")

        # Cảnh báo UPDATE không có WHERE (có thể nguy hiểm)
        if "UPDATE" in query.upper() and "WHERE" not in query.upper():
            errors.append(
                "Cảnh báo: UPDATE không có điều kiện WHERE - sẽ cập nhật tất cả các hàng"
            )

        return errors

    @staticmethod
    def _validate_delete(query: str) -> List[str]:
        """Kiểm tra câu lệnh DELETE

        Args:
            query: Câu lệnh DELETE cần kiểm tra

        Returns:
            Danh sách các lỗi phát hiện được
        """
        errors = []

        # Kiểm tra thiếu FROM
        if "DELETE" in query.upper() and "FROM" not in query.upper():
            errors.append("Câu lệnh DELETE thiếu từ khóa FROM")

        # Cảnh báo DELETE không có WHERE (nguy hiểm)
        if "DELETE" in query.upper() and "WHERE" not in query.upper():
            errors.append(
                "Cảnh báo: DELETE không có điều kiện WHERE - sẽ xóa tất cả các hàng"
            )

        return errors

    @staticmethod
    def _validate_create_table(query: str) -> List[str]:
        """Kiểm tra câu lệnh CREATE TABLE

        Args:
            query: Câu lệnh CREATE TABLE cần kiểm tra

        Returns:
            Danh sách các lỗi phát hiện được
        """
        errors = []

        # Kiểm tra thiếu tên bảng
        table_pattern = re.compile(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", re.IGNORECASE
        )
        if not table_pattern.search(query):
            errors.append("CREATE TABLE không có tên bảng hợp lệ")

        # Kiểm tra thiếu dấu ngoặc đơn
        if "(" not in query or ")" not in query:
            errors.append("CREATE TABLE thiếu dấu ngoặc đơn để định nghĩa cột")

        # Kiểm tra khóa chính
        if "PRIMARY KEY" not in query.upper() and "CONSTRAINT" not in query.upper():
            errors.append("Cảnh báo: CREATE TABLE không có khóa chính")

        return errors


def validate_sql(sql_query: str) -> Dict[str, Any]:
    """Wrapper function để kiểm tra tính đúng đắn của SQL

    Args:
        sql_query: Câu lệnh SQL cần kiểm tra

    Returns:
        Dict chứa kết quả kiểm tra
    """
    is_valid, errors = SQLValidator.validate(sql_query)

    # Format SQL nếu hợp lệ
    formatted_sql = None
    if is_valid:
        try:
            formatted_sql = sqlparse.format(
                sql_query, reindent=True, keyword_case="upper"
            )
        except:
            # Nếu không thể format, trả về nguyên bản
            formatted_sql = sql_query

    return {
        "is_valid": is_valid,
        "errors": errors,
        "formatted_sql": formatted_sql if is_valid else None,
    }
 