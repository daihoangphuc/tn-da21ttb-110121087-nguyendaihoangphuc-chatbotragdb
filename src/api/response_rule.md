# Quy tắc phản hồi API

Tài liệu này định nghĩa các quy tắc và cấu trúc chuẩn cho phản hồi từ API của hệ thống RAG để đảm bảo frontend có thể xử lý và hiển thị dữ liệu một cách nhất quán.

## Cấu trúc phản hồi chung

Phản hồi từ API `/query` sẽ có cấu trúc chung sau:

```json
{
  "response": "Nội dung phản hồi (định dạng Markdown)",
  "sources": [
    {
      "index": 0,
      "source": "tên_file.pdf",
      "source_path": "đường_dẫn/đến/tên_file.pdf",
      "file_type": "pdf",
      "chunk_length": 1024,
      "chunk_word_count": 150,
      "start_index": 0,
      "chunk_count": 1,
      "has_list_content": false,
      "content_preview": "Đoạn trích từ tài liệu...",
      "page_number": 42,
      "image_paths": ["đường_dẫn/ảnh1.png", "đường_dẫn/ảnh2.png"]
    }
  ],
  "prompt": "Nội dung prompt dùng để tạo phản hồi",
  "model": "gemini-pro",
  "query": "Câu truy vấn gốc của người dùng",
  "temperature": 0.7,
  "total_sources": 5,
  "retrieval_time_ms": 254,
  "llm_time_ms": 1021,
  "total_tokens": 2048,
  "related_images": ["/images/upload_20231225_123456/image1.png"],
  "format_metadata": {
    "format": "markdown",
    "has_code_blocks": true,
    "has_tables": true,
    "has_images": true,
    "has_math": false,
    "has_headings": true
  }
}
```

## Quy tắc định dạng nội dung phản hồi (Markdown)

Nội dung phản hồi (`response`) được định dạng theo chuẩn Markdown, đảm bảo các quy tắc sau:

### 1. Tiêu đề và phân cấp

- Sử dụng `#`, `##`, `###` cho các cấp tiêu đề khác nhau
- Luôn có khoảng trắng sau dấu `#`
- Mỗi tiêu đề được phân cách với nội dung trước đó bằng một dòng trống

```markdown
# Tiêu đề chính

Nội dung đoạn văn...

## Tiêu đề phụ
```

### 2. Khối mã (Code blocks)

- Mã SQL luôn được đặt trong khối mã với chỉ định ngôn ngữ `sql`
- Mã nguồn của các ngôn ngữ khác được đặt trong khối mã với chỉ định ngôn ngữ tương ứng
- Luôn thêm khoảng trống trước và sau khối mã

```markdown
Đây là truy vấn SQL:

```sql
SELECT * FROM users WHERE age > 18;
```

Mã Python:

```python
def hello_world():
    print("Hello, world!")
```
```

### 3. Bảng dữ liệu

- Bảng được định dạng theo chuẩn Markdown với dấu `|` và dòng phân cách
- Dòng phân cách có độ dài phù hợp với số cột
- Mỗi ô trong bảng có căn chỉnh phù hợp (trái, phải, giữa)

```markdown
| Tên cột 1 | Tên cột 2 | Tên cột 3 |
|-----------|----------:|:---------:|
| Trái      | Phải      | Giữa      |
| Dữ liệu   | 123       | Giá trị   |
```

### 4. Danh sách

- Danh sách có thứ tự sử dụng `1.`, `2.`, `3.`, ...
- Danh sách không thứ tự sử dụng `-` hoặc `*`
- Danh sách lồng nhau được thể hiện bằng thụt đầu dòng

```markdown
1. Mục thứ nhất
2. Mục thứ hai
   - Mục con không thứ tự
   - Mục con khác
3. Mục thứ ba
```

### 5. Đoạn trích dẫn

- Sử dụng dấu `>` cho đoạn trích dẫn
- Có thể lồng nhiều cấp trích dẫn với `>>`, `>>>`, ...

```markdown
> Đây là đoạn trích dẫn.
> Nó có thể kéo dài nhiều dòng.
>
> > Đây là trích dẫn lồng nhau.
```

### 6. Định dạng chữ

- **In đậm** được thể hiện bằng `**in đậm**`
- *In nghiêng* được thể hiện bằng `*in nghiêng*`
- `Code inline` được thể hiện bằng dấu backtick (`` `code inline` ``)

### 7. Liên kết và hình ảnh

- Liên kết: `[Tên hiển thị](URL)`
- Hình ảnh: `![Văn bản thay thế](URL)`

## Cách hiển thị trên Frontend

### 1. Hiển thị mã nguồn

- Sử dụng thư viện highlight.js hoặc Prism.js để syntax highlighting
- Thêm nút Copy cho code blocks
- Đảm bảo định dạng đúng với ngôn ngữ được chỉ định

### 2. Hiển thị bảng

- Sử dụng CSS để định dạng bảng đẹp và dễ đọc
- Hỗ trợ responsive cho bảng trên thiết bị di động
- Cân nhắc tính năng sắp xếp và lọc cho bảng lớn

### 3. Hiển thị hình ảnh

- Hiển thị hình ảnh từ mảng `related_images`
- Hỗ trợ xem hình ảnh lớn (lightbox) khi click
- Tối ưu kích thước hiển thị phù hợp với nội dung

### 4. Xử lý các nguồn tham khảo

- Hiển thị nguồn tham khảo dưới dạng danh sách có thể mở rộng/thu gọn
- Thêm liên kết đến nguồn gốc nếu có
- Hiển thị số trang và trích đoạn ngắn

## Mẫu phản hồi theo loại truy vấn

### Phản hồi SQL

```json
{
  "response": "## Cách tiếp cận\n\nTruy vấn này cần lấy danh sách nhân viên và thông tin phòng ban của họ.\n\n## Câu truy vấn SQL\n\n```sql\nSELECT\n    employees.name,\n    employees.position,\n    departments.name as department\nFROM\n    employees\nJOIN\n    departments ON employees.department_id = departments.id\nWHERE\n    employees.status = 'active'\nORDER BY\n    departments.name, employees.name;\n```\n\n## Giải thích\n\n1. Chọn các cột `name` và `position` từ bảng `employees`\n2. Chọn cột `name` từ bảng `departments` và đổi tên thành `department`\n3. Kết hợp hai bảng bằng điều kiện `employees.department_id = departments.id`\n4. Chỉ lấy nhân viên có trạng thái 'active'\n5. Sắp xếp kết quả theo tên phòng ban và tên nhân viên\n\n## Kết quả dự kiến\n\nKết quả sẽ là danh sách nhân viên với thông tin họ tên, chức vụ và phòng ban, được sắp xếp theo tên phòng ban và tên nhân viên.",
  "format_metadata": {
    "format": "markdown",
    "has_code_blocks": true,
    "has_tables": false,
    "has_images": false,
    "has_math": false,
    "has_headings": true
  }
}
```

### Phản hồi phân tích Schema

```json
{
  "response": "# Phân tích Schema\n\n## Tổng quan về schema\n\nSchema này mô tả hệ thống quản lý học viên của một trường đại học, bao gồm các bảng chính như `Students`, `Courses`, `Enrollments` và `Departments`.\n\n## Phân tích chi tiết từng bảng\n\n### Bảng Students\n\n| Tên cột | Kiểu dữ liệu | Mô tả | Khóa |\n|---------|--------------|-------|------|\n| **student_id** | INT | ID học viên | PK |\n| first_name | VARCHAR(50) | Tên | |\n| last_name | VARCHAR(50) | Họ | |\n| email | VARCHAR(100) | Email | Unique |\n| *department_id* | INT | Khoa/ngành | FK |\n\n```sql\nCREATE TABLE Students (\n  student_id INT PRIMARY KEY,\n  first_name VARCHAR(50) NOT NULL,\n  last_name VARCHAR(50) NOT NULL,\n  email VARCHAR(100) UNIQUE,\n  department_id INT,\n  FOREIGN KEY (department_id) REFERENCES Departments(department_id)\n);\n```\n\n> Bảng Students lưu trữ thông tin cơ bản về học viên, với khóa ngoại liên kết đến khoa/ngành.\n\n## Mối quan hệ và ràng buộc\n\n- `Students` (N) - (1) `Departments`: Một học viên thuộc về một khoa/ngành\n- `Students` (1) - (N) `Enrollments`: Một học viên có thể đăng ký nhiều khóa học\n- `Courses` (1) - (N) `Enrollments`: Một khóa học có thể có nhiều học viên đăng ký\n- `Departments` (1) - (N) `Courses`: Một khoa/ngành có thể quản lý nhiều khóa học\n\n## Đánh giá thiết kế\n\nSchema được thiết kế khá tốt, ở dạng chuẩn 3NF, tránh được dư thừa dữ liệu. Tuy nhiên, có một số điểm có thể cải thiện:\n\n1. Thiếu bảng quản lý giảng viên\n2. Chưa có thông tin về học kỳ, năm học\n3. Chưa có cơ chế lưu trữ lịch sử học tập\n\n## Đề xuất cải tiến\n\n1. Thêm bảng `Professors` và mối quan hệ với `Courses`\n2. Bổ sung bảng `Semesters` để quản lý học kỳ\n3. Thêm bảng `Grades` để lưu điểm số của học viên",
  "format_metadata": {
    "format": "markdown",
    "has_code_blocks": true,
    "has_tables": true,
    "has_images": false,
    "has_math": false,
    "has_headings": true
  }
}
```

## Xử lý lỗi

Khi có lỗi xảy ra, API sẽ trả về định dạng lỗi chuẩn:

```json
{
  "detail": "Mô tả chi tiết về lỗi xảy ra"
}
```

Các mã lỗi HTTP phổ biến:

- 400: Bad Request - Yêu cầu không hợp lệ
- 404: Not Found - Không tìm thấy tài nguyên
- 500: Internal Server Error - Lỗi máy chủ nội bộ

## Lưu ý quan trọng

1. **Độ dài phản hồi**: Không giới hạn cứng về độ dài, nhưng nên giữ ngắn gọn và tập trung vào thông tin cần thiết
2. **Xử lý Markdown**: Frontend nên sử dụng thư viện hiển thị Markdown như marked.js, markdown-it
3. **Cấu hình CORS**: API đã được cấu hình để cho phép truy cập từ các nguồn khác nhau
4. **Hiển thị nguồn**: Hiển thị nguồn tham khảo để người dùng có thể kiểm chứng thông tin
5. **Hiệu suất**: Metadata về thời gian truy vấn nên được hiển thị để người dùng biết thời gian xử lý
6. **Tương tác**: Frontend nên cho phép người dùng tương tác với phần phản hồi (copy, chia sẻ, đánh dấu)
