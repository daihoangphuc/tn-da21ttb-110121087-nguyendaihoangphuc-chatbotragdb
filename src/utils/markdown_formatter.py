import re
from typing import Dict, Any, List, Optional


def format_sql_code(sql_text: str) -> str:
    """Chuẩn hóa mã SQL để định dạng tốt hơn

    Args:
        sql_text: Đoạn mã SQL cần định dạng

    Returns:
        Đoạn mã SQL đã được định dạng
    """
    # Viết hoa các từ khóa SQL
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

    # Thay thế các từ khóa SQL không phân biệt chữ hoa thường
    formatted_text = sql_text
    for keyword in keywords:
        pattern = re.compile(r"\b" + keyword + r"\b", re.IGNORECASE)
        formatted_text = pattern.sub(keyword, formatted_text)

    # Đảm bảo mỗi mệnh đề chính được bắt đầu ở một dòng mới
    for keyword in ["SELECT", "FROM", "WHERE", "GROUP BY", "ORDER BY", "HAVING"]:
        formatted_text = re.sub(
            r"(\s)" + keyword + r"\b",
            r"\n" + keyword,
            formatted_text,
            flags=re.IGNORECASE,
        )

    # Thêm khoảng trắng sau dấu phẩy nếu chưa có
    formatted_text = re.sub(r",(\S)", r", \1", formatted_text)

    return formatted_text


def detect_sql_blocks(text: str) -> str:
    """Phát hiện và định dạng các khối mã SQL không được đánh dấu là sql

    Args:
        text: Văn bản đầu vào

    Returns:
        Văn bản với các khối SQL đã được định dạng
    """
    # Tìm các khối code chưa có chỉ định ngôn ngữ
    unlabeled_code_blocks = re.findall(r"```(?!\w+)([\s\S]*?)```", text)

    # Kiểm tra xem khối code có phải là SQL không
    for block in unlabeled_code_blocks:
        if re.search(
            r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE)\b",
            block,
            re.IGNORECASE,
        ):
            # Định dạng SQL
            formatted_sql = format_sql_code(block)
            # Thay thế khối code
            text = text.replace(f"```{block}```", f"```sql\n{formatted_sql}\n```", 1)

    # Phát hiện các đoạn SQL không nằm trong code blocks
    sql_pattern = r"(?i)(?<!\`\`\`sql\s)(?<!\`\`\`\s)(\b(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE)[\s\S]+?;)(?!\s*\`\`\`)"
    sql_matches = re.finditer(sql_pattern, text)

    # Xử lý từng phần trùng khớp
    for match in reversed(
        list(sql_matches)
    ):  # Đảo ngược để không bị ảnh hưởng bởi sự thay đổi vị trí
        sql = match.group(1)
        # Chỉ chuyển đổi nếu không nằm trong code block
        if not is_in_code_block(text, match.start()):
            formatted_sql = format_sql_code(sql)
            text = (
                text[: match.start()]
                + f"\n```sql\n{formatted_sql}\n```\n"
                + text[match.end() :]
            )

    return text


def is_in_code_block(text: str, position: int) -> bool:
    """Kiểm tra xem vị trí có nằm trong code block không

    Args:
        text: Văn bản đầu vào
        position: Vị trí cần kiểm tra

    Returns:
        True nếu vị trí nằm trong code block, ngược lại False
    """
    # Tìm tất cả các code block
    code_blocks = []
    for match in re.finditer(r"```[\s\S]*?```", text):
        code_blocks.append((match.start(), match.end()))

    # Kiểm tra xem vị trí có nằm trong bất kỳ khối nào không
    for start, end in code_blocks:
        if start <= position <= end:
            return True

    return False


def format_tables(text: str) -> str:
    """Định dạng các bảng Markdown để đảm bảo cấu trúc chuẩn

    Args:
        text: Văn bản đầu vào

    Returns:
        Văn bản với các bảng đã được định dạng
    """
    # Tìm các tiềm năng bảng không có định dạng đúng
    # Mẫu: Các dòng có nhiều khoảng trắng hoặc tabs phân cách

    # 1. Tìm các dòng có khoảng trắng hoặc tab phân tách 3 cột trở lên
    potential_tables = re.findall(
        r"(?:^|\n)((?:[^\n]+(?:\s{2,}|\t)[^\n]+(?:\s{2,}|\t)[^\n]+.+\n){2,})", text
    )

    for potential_table in potential_tables:
        # Kiểm tra xem có phải là cấu trúc bảng hay không
        lines = potential_table.strip().split("\n")

        # Nếu có ít nhất 2 dòng và không phải là bảng Markdown hiện có
        if len(lines) >= 2 and "|" not in lines[0]:
            # Phân tích các cột
            columns = []
            for i, line in enumerate(lines):
                # Tách cột bằng khoảng trắng hoặc tab
                cols = re.split(r"\s{2,}|\t", line)
                columns.append(cols)

            # Xác định số cột tối đa
            max_cols = max(len(cols) for cols in columns)

            # Tạo bảng mới với định dạng Markdown
            markdown_table = []

            # Dòng đầu tiên (tiêu đề)
            header = (
                "| "
                + " | ".join(columns[0] + [""] * (max_cols - len(columns[0])))
                + " |"
            )
            markdown_table.append(header)

            # Dòng phân cách
            separator = "|" + "|".join(["---"] * max_cols) + "|"
            markdown_table.append(separator)

            # Dòng dữ liệu
            for cols in columns[1:]:
                row = "| " + " | ".join(cols + [""] * (max_cols - len(cols))) + " |"
                markdown_table.append(row)

            # Thay thế bảng tiềm năng bằng bảng Markdown
            markdown_table_str = "\n".join(markdown_table)
            text = text.replace(potential_table, markdown_table_str)

    return text


def ensure_correct_headings(text: str) -> str:
    """Đảm bảo các tiêu đề Markdown được định dạng đúng

    Args:
        text: Văn bản đầu vào

    Returns:
        Văn bản với các tiêu đề đã được định dạng đúng
    """
    # Đảm bảo có khoảng trắng sau dấu #
    text = re.sub(r"(^|\n)#([^#\s])", r"\1# \2", text)
    text = re.sub(r"(^|\n)##([^#\s])", r"\1## \2", text)
    text = re.sub(r"(^|\n)###([^#\s])", r"\1### \2", text)
    text = re.sub(r"(^|\n)####([^#\s])", r"\1#### \2", text)
    text = re.sub(r"(^|\n)#####([^#\s])", r"\1##### \2", text)

    # Đảm bảo tiêu đề có dòng trống phía trên (trừ khi là dòng đầu tiên)
    text = re.sub(r"(?<!^)(?<=\n)(?<!\n\n)(#+ )", r"\n\1", text)

    return text


def format_markdown(text: str) -> str:
    """Định dạng văn bản thành Markdown chuẩn

    Args:
        text: Văn bản đầu vào cần định dạng

    Returns:
        Văn bản đã được định dạng theo chuẩn Markdown
    """
    # Định dạng code blocks SQL
    text = detect_sql_blocks(text)

    # Đảm bảo code blocks có ngôn ngữ được chỉ định
    text = re.sub(r"```(?!\w+)([\s\S]*?)```", r"```text\n\1\n```", text)

    # Định dạng các bảng
    text = format_tables(text)

    # Đảm bảo tiêu đề đúng định dạng
    text = ensure_correct_headings(text)

    # Định dạng đường dẫn URL
    url_pattern = r"(?<!\[)(?<![\(\[])(https?://\S+)(?![\)\]])"
    text = re.sub(url_pattern, r"[\1](\1)", text)

    # Xóa khoảng trắng dư thừa giữa các đoạn
    text = re.sub(r"\n{3,}", r"\n\n", text)

    return text


def extract_code_blocks(text: str) -> List[Dict[str, Any]]:
    """Trích xuất các khối code từ văn bản Markdown

    Args:
        text: Văn bản Markdown đầu vào

    Returns:
        Danh sách các khối code với thông tin về loại ngôn ngữ và nội dung
    """
    code_blocks = []

    # Tìm tất cả các code block
    pattern = r"```(\w+)?\s*([\s\S]*?)```"
    matches = re.finditer(pattern, text)

    for match in matches:
        language = match.group(1) or "text"
        content = match.group(2).strip()
        position = match.start()

        code_blocks.append(
            {"language": language, "content": content, "position": position}
        )

    return code_blocks


def extract_tables(text: str) -> List[Dict[str, Any]]:
    """Trích xuất các bảng từ văn bản Markdown

    Args:
        text: Văn bản Markdown đầu vào

    Returns:
        Danh sách các bảng với thông tin về cấu trúc và nội dung
    """
    tables = []

    # Tìm tất cả các bảng
    # Mẫu: dòng bắt đầu với | và có ít nhất một | khác
    table_pattern = (
        r"(?:(?:^|\n)\|[^|\n]+\|[^|\n]+.*(?:\n\|[\s-:]*\|[\s-:]*.*)?(?:\n\|.*)*)"
    )
    matches = re.finditer(table_pattern, text)

    for match in matches:
        table_text = match.group(0).strip()
        position = match.start()

        # Tách các dòng của bảng
        lines = table_text.split("\n")

        # Kiểm tra xem có phải là bảng Markdown hợp lệ không
        if len(lines) >= 2:
            # Phân tích cấu trúc bảng
            rows = []
            headers = []

            # Xử lý header (dòng đầu tiên)
            header_cells = [cell.strip() for cell in lines[0].split("|")[1:-1]]
            headers = header_cells

            # Bỏ qua dòng phân cách (dòng thứ hai)

            # Xử lý các dòng dữ liệu
            for line in lines[2:] if len(lines) > 2 else []:
                cells = [cell.strip() for cell in line.split("|")[1:-1]]
                rows.append(cells)

            tables.append(
                {
                    "headers": headers,
                    "rows": rows,
                    "text": table_text,
                    "position": position,
                }
            )

    return tables


def analyze_markdown_structure(text: str) -> Dict[str, Any]:
    """Phân tích cấu trúc của văn bản Markdown

    Args:
        text: Văn bản Markdown đầu vào

    Returns:
        Thông tin chi tiết về cấu trúc văn bản
    """
    # Trích xuất các thành phần
    code_blocks = extract_code_blocks(text)
    tables = extract_tables(text)

    # Phát hiện các tiêu đề
    headings = []
    for match in re.finditer(r"^(#{1,6})\s+(.+?)(?:\s+#{1,6})?$", text, re.MULTILINE):
        level = len(match.group(1))
        content = match.group(2).strip()
        position = match.start()

        headings.append({"level": level, "content": content, "position": position})

    # Phát hiện các liên kết
    links = []
    for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", text):
        link_text = match.group(1)
        url = match.group(2)
        position = match.start()

        links.append({"text": link_text, "url": url, "position": position})

    # Phát hiện các hình ảnh
    images = []
    for match in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", text):
        alt_text = match.group(1)
        url = match.group(2)
        position = match.start()

        images.append({"alt": alt_text, "url": url, "position": position})

    # Phát hiện các danh sách
    lists = []
    list_pattern = (
        r"(?:(?:^|\n)(?:[-*+]|\d+\.)\s+.+(?:\n(?:(?:[-*+]|\d+\.)\s+.+|\s+.+))*)"
    )
    for match in re.finditer(list_pattern, text):
        list_text = match.group(0)
        position = match.start()

        is_ordered = bool(re.search(r"^\d+\.", list_text.strip()))

        lists.append(
            {
                "type": "ordered" if is_ordered else "unordered",
                "text": list_text,
                "position": position,
            }
        )

    # Phát hiện các trích dẫn
    quotes = []
    quote_pattern = r"(?:^|\n)>\s+.+(?:\n>\s+.+)*"
    for match in re.finditer(quote_pattern, text):
        quote_text = match.group(0)
        position = match.start()

        quotes.append({"text": quote_text, "position": position})

    # Kết quả phân tích
    return {
        "code_blocks": code_blocks,
        "tables": tables,
        "headings": headings,
        "links": links,
        "images": images,
        "lists": lists,
        "quotes": quotes,
        "has_math": bool(re.search(r"(\$\$[\s\S]*?\$\$|\\\([\s\S]*?\\\))", text)),
        "statistics": {
            "code_block_count": len(code_blocks),
            "table_count": len(tables),
            "heading_count": len(headings),
            "link_count": len(links),
            "image_count": len(images),
            "list_count": len(lists),
            "quote_count": len(quotes),
        },
    }
