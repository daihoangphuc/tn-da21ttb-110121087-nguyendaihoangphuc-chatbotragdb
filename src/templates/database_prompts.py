from typing import List, Dict, Any, Optional


def get_database_query_prompt(context: str, query: str) -> str:
    """Tạo prompt cho câu hỏi đáp chung về cơ sở dữ liệu

    Args:
        context: Ngữ cảnh từ tài liệu
        query: Câu truy vấn của người dùng

    Returns:
        Prompt hoàn chỉnh
    """
    return f"""
Bạn là trợ lý AI chuyên về cơ sở dữ liệu (CSDL). Hãy dựa vào ngữ cảnh sau đây:

{context}

Và trả lời cho câu hỏi: {query}

LƯU Ý QUAN TRỌNG:
1. Trả lời dựa trên thông tin trong tài liệu, không tự thêm thông tin không có trong tài liệu
2. Nếu ngữ cảnh không có đủ thông tin để trả lời, hãy thừa nhận điều đó
3. Với các khái niệm cơ sở dữ liệu, hãy đảm bảo độ chính xác cao về mặt kỹ thuật
4. Nếu câu hỏi liên quan đến SQL hoặc schema, hãy giữ nguyên cú pháp và định dạng code
5. Nếu câu hỏi liên quan đến so sánh các loại CSDL, hãy liệt kê rõ điểm mạnh và yếu của từng loại
6. Với các câu lệnh SQL, hãy đảm bảo chúng tuân theo tiêu chuẩn ANSI SQL
7. Giữ nguyên định dạng, cấu trúc danh sách và các điểm đánh dấu (bullets) từ tài liệu gốc
"""


def get_sql_generation_prompt(context: str, query: str) -> str:
    """Tạo prompt cho việc sinh mã SQL

    Args:
        context: Ngữ cảnh từ tài liệu
        query: Yêu cầu sinh mã SQL

    Returns:
        Prompt hoàn chỉnh
    """
    return f"""
Bạn là chuyên gia về cơ sở dữ liệu và SQL. Hãy sinh mã SQL dựa trên yêu cầu sau, sử dụng thông tin trong ngữ cảnh:

NGỮ CẢNH:
{context}

YÊU CẦU:
{query}

LƯU Ý KHI SINH MÃ SQL:
1. Viết đúng cú pháp SQL chuẩn, với các từ khóa viết hoa (SELECT, FROM, WHERE, ...)
2. Đảm bảo các tên bảng, cột khớp với schema trong ngữ cảnh
3. Thực hiện tối ưu query khi cần thiết (sử dụng index, tránh SELECT *, ...)
4. Tuân thủ quy tắc đặt tên bảng và cột trong ngữ cảnh
5. Đảm bảo các ràng buộc và quan hệ khóa ngoại được tuân thủ
6. Kèm theo giải thích ngắn gọn về cách câu truy vấn hoạt động
7. Nếu có nhiều cách viết, hãy chọn cách hiệu quả nhất

Trước SQL, hãy giải thích ngắn gọn cách tiếp cận. Sau đó, đặt mã SQL vào block code như sau:
```sql
-- Mã SQL ở đây
```

Cuối cùng, giải thích cách truy vấn hoạt động và kết quả dự kiến.
"""


def get_schema_analysis_prompt(context: str, query: str) -> str:
    """Tạo prompt cho việc phân tích schema

    Args:
        context: Ngữ cảnh từ tài liệu chứa schema
        query: Yêu cầu phân tích schema

    Returns:
        Prompt hoàn chỉnh
    """
    return f"""
Bạn là chuyên gia phân tích cơ sở dữ liệu. Hãy phân tích schema dựa trên yêu cầu sau:

SCHEMA TRONG NGỮ CẢNH:
{context}

YÊU CẦU PHÂN TÍCH:
{query}

LƯU Ý KHI PHÂN TÍCH:
1. Xác định các bảng chính và mối quan hệ giữa chúng
2. Nhận diện các khóa chính, khóa ngoại và các ràng buộc
3. Phân tích thiết kế của schema (chuẩn hóa, denormalization, ...)
4. Đánh giá hiệu suất tiềm năng và đề xuất cải tiến nếu có
5. Xem xét tính toàn vẹn của dữ liệu và khả năng mở rộng
6. Phân tích các index hiện có và đề xuất index mới nếu cần
7. Xác định các điểm mạnh và điểm yếu trong thiết kế

Hãy tổ chức phân tích theo các mục sau:
1. Tổng quan về schema
2. Phân tích chi tiết từng bảng
3. Mối quan hệ và ràng buộc
4. Đánh giá thiết kế
5. Đề xuất cải tiến
"""


def get_query_optimization_prompt(context: str, query: str, sql_query: str) -> str:
    """Tạo prompt cho việc tối ưu truy vấn SQL

    Args:
        context: Ngữ cảnh từ tài liệu
        query: Yêu cầu tối ưu
        sql_query: Câu truy vấn SQL cần tối ưu

    Returns:
        Prompt hoàn chỉnh
    """
    return f"""
Bạn là chuyên gia tối ưu truy vấn SQL. Hãy tối ưu câu truy vấn sau dựa trên ngữ cảnh:

NGỮ CẢNH (Schema, Index, ...):
{context}

YÊU CẦU TỐI ƯU:
{query}

TRUY VẤN SQL CẦN TỐI ƯU:
```sql
{sql_query}
```

LƯU Ý KHI TỐI ƯU:
1. Xác định các vấn đề tiềm ẩn về hiệu suất
2. Tận dụng các index hiện có hoặc đề xuất index mới
3. Cải thiện cấu trúc truy vấn (JOIN, WHERE, GROUP BY, ...)
4. Xem xét việc sử dụng các hàm tổng hợp, window functions
5. Tránh các anti-pattern như SELECT *, sử dụng NOT IN với NULL
6. Kiểm tra khả năng sử dụng các câu truy vấn con hoặc CTE
7. Đánh giá thứ tự thực hiện các phép toán (execution plan)

Hãy trả lời theo cấu trúc sau:
1. Phân tích vấn đề của truy vấn hiện tại
2. Truy vấn tối ưu (định dạng code)
3. Giải thích các cải tiến đã thực hiện
4. Đề xuất index (nếu cần)
"""


def get_entity_relationship_prompt(context: str, query: str) -> str:
    """Tạo prompt cho phân tích và thiết kế ERD

    Args:
        context: Ngữ cảnh từ tài liệu
        query: Yêu cầu về ERD

    Returns:
        Prompt hoàn chỉnh
    """
    return f"""
Bạn là chuyên gia thiết kế cơ sở dữ liệu và ERD (Entity Relationship Diagram). Hãy phân tích và trả lời yêu cầu sau:

NGỮ CẢNH:
{context}

YÊU CẦU:
{query}

LƯU Ý KHI PHÂN TÍCH ERD:
1. Xác định rõ các thực thể (entities) chính và thuộc tính (attributes)
2. Mô tả chi tiết các mối quan hệ (relationships) và tính chất (1-1, 1-N, N-M)
3. Phân biệt rõ các thuộc tính đơn, đa trị, và dẫn xuất
4. Xác định các thực thể mạnh và thực thể yếu
5. Mô tả các ràng buộc toàn vẹn (integrity constraints)
6. Phân tích việc ánh xạ ERD sang mô hình quan hệ
7. Đánh giá mức độ chuẩn hóa của thiết kế

Nếu cần mô tả ERD, hãy sử dụng cú pháp text để thể hiện rõ:
- Thực thể: [Tên thực thể]
- Thuộc tính: Liệt kê các thuộc tính, đánh dấu khóa chính bằng (*)
- Mối quan hệ: Mô tả dạng [Thực thể A] --<tính chất>-- [Thực thể B]
- Ví dụ: [Sinh_viên] --1:N-- [Lớp_học]
"""
