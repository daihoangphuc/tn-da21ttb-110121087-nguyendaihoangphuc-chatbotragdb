# Hệ thống RAG cho Cơ sở dữ liệu

Hệ thống RAG (Retrieval-Augmented Generation) tìm kiếm thông tin và trả lời câu hỏi về Cơ sở dữ liệu.

## Cấu trúc thư mục

```
D:/DATN/V4/
├── main.py                  # File chính để chạy ứng dụng
├── requirements.txt         # Danh sách thư viện cần thiết
├── setup.bat                # Script tạo môi trường và cài đặt
├── run.bat                  # Script chạy ứng dụng thông thường
├── run_api.bat              # Script chạy API
├── test_api.py              # Script kiểm tra API
└── src/                     # Thư mục mã nguồn
    ├── __init__.py          # Đánh dấu thư mục là package Python
    ├── embedding.py         # Module quản lý mô hình embedding
    ├── llm.py               # Module quản lý mô hình ngôn ngữ lớn
    ├── vector_store.py      # Module quản lý kho lưu trữ vector
    ├── document_processor.py # Module xử lý tài liệu
    ├── prompt_manager.py    # Module quản lý prompt
    ├── search.py            # Module quản lý tìm kiếm
    ├── rag.py               # Module tổng hợp hệ thống RAG
    ├── api.py               # Module API FastAPI
    └── data/                # Thư mục chứa dữ liệu
```

## Cài đặt và sử dụng

### Phương pháp 1: Sử dụng scripts

1. **Cài đặt và tạo môi trường ảo**:
   - Chạy file `setup.bat` để tạo môi trường ảo và cài đặt các thư viện cần thiết

2. **Chạy ứng dụng thông thường**:
   - Chạy file `run.bat` để kích hoạt môi trường ảo và chạy ứng dụng

3. **Chạy API**:
   - Chạy file `run_api.bat` để kích hoạt môi trường ảo và chạy API

### Phương pháp 2: Thủ công qua Command Prompt

1. **Tạo môi trường ảo Python**:
   ```
   python -m venv venv
   ```

2. **Kích hoạt môi trường ảo**:
   ```
   venv\Scripts\activate
   ```

3. **Cài đặt các thư viện cần thiết**:
   ```
   pip install -r requirements.txt
   ```

4. **Chạy ứng dụng thông thường**:
   ```
   python main.py
   ```

5. **Chạy API**:
   ```
   python -m uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
   ```

## SƠ ĐỒ HOẠT ĐỘNG

```mermaid
graph LR
    A[Frontend] --> B(API (FastAPI))
    B --> C{AdvancedDatabaseRAG}
    B --> D{DocumentProcessor}
    B --> E[Feedback]
    D --> F{Layout Analysis}
    D --> G{Indexing}
    F --> H{Chunking}
    H --> I((Vector Store (Qdrant)))
    C --> I
    I --> J{QueryProcessor (Expansion)}
    J --> K{SearchManager}
    K --> L{PromptManager}
    L --> M{Gemini LLM (Response Generation)}
    M --> N[Final Response with sources]
    B --> O[/api/ask]
    B --> P[/api/upload]
    B --> Q[/api/index]
    B --> R[/api/feedback]
```

## Sử dụng hệ thống

### Ứng dụng thông thường
Khi chạy ứng dụng thông thường, hệ thống sẽ:
1. Tải và xử lý tài liệu từ thư mục `src/data`
2. Chuyển đổi thành vector embedding và lưu trữ trong Qdrant
3. Thực hiện câu hỏi mẫu và hiển thị kết quả
4. Hiển thị thông tin về collection trong Qdrant

### API
Khi chạy API, bạn có thể sử dụng các endpoint sau:
- **API Documentation**: Truy cập http://localhost:8000/docs để xem tài liệu API Swagger
- **Đường dẫn chính**: http://localhost:8000

## Tài liệu chi tiết các API endpoint

### 1. Đặt câu hỏi
**Endpoint**: `POST /api/ask`

**Mô tả**: Đặt câu hỏi và nhận câu trả lời từ hệ thống RAG

**Tham số đầu vào**:
- **Body** (JSON):
  ```json
  {
    "question": "string",
    "search_type": "hybrid" // tùy chọn: "semantic", "keyword", "hybrid"
  }
  ```
- **Query Parameters**:
  - `max_sources`: Số lượng nguồn tham khảo tối đa trả về. Nếu không chỉ định, sẽ trả về tất cả kết quả. (1-50)

**Kết quả trả về**:
```json
{
  "question_id": "string",
  "question": "string",
  "answer": "string",
  "sources": [
    {
      "source": "string",
      "score": 0.95,
      "content_snippet": "string"
    }
  ],
  "search_method": "string",
  "total_reranked": 15
}
```

### 2. Tải lên tài liệu
**Endpoint**: `POST /api/upload`

**Mô tả**: Tải lên một tài liệu để thêm vào hệ thống. Tài liệu sẽ được tự động xử lý và index.

**Tham số đầu vào**:
- **Form Data**:
  - `file`: File tài liệu (PDF, DOCX, TXT, SQL)
  - `category`: Danh mục tài liệu (tùy chọn)

**Kết quả trả về**:
```json
{
  "filename": "string",
  "status": "success",
  "message": "string",
  "chunks_count": 25,
  "category": "string"
}
```

### 3. Index tài liệu
**Endpoint**: `POST /api/index`

**Mô tả**: Bắt đầu quá trình indexing tất cả tài liệu trong thư mục data

**Tham số đầu vào**: Không có

**Kết quả trả về**:
```json
{
  "status": "started",
  "message": "Đã bắt đầu quá trình indexing..."
}
```

### 4. Kiểm tra trạng thái indexing
**Endpoint**: `GET /api/index/status`

**Mô tả**: Kiểm tra trạng thái của quá trình indexing

**Tham số đầu vào**: Không có

**Kết quả trả về**:
```json
{
  "status": "completed",
  "message": "Đã hoàn thành index 120 chunks từ 5 tài liệu",
  "processed_files": 5
}
```

### 5. Thông tin collection
**Endpoint**: `GET /api/collection/info`

**Mô tả**: Lấy thông tin về collection trong vector store

**Tham số đầu vào**: Không có

**Kết quả trả về**:
```json
{
  "name": "csdl_rag_e5_base",
  "points_count": 120,
  "config": {
    "params": {
      "size": 768,
      "distance": "Cosine"
    }
  }
}
```

### 6. Gửi phản hồi
**Endpoint**: `POST /api/feedback`

**Mô tả**: Gửi phản hồi về câu trả lời của hệ thống

**Tham số đầu vào**:
- **Body** (JSON):
  ```json
  {
    "question_id": "string",
    "rating": 5,
    "comment": "string",
    "is_helpful": true,
    "specific_feedback": {
      "accuracy": 5,
      "completeness": 4,
      "clarity": 5
    }
  }
  ```

**Kết quả trả về**:
```json
{
  "status": "success",
  "message": "Đã lưu phản hồi của bạn. Cảm ơn!"
}
```

### 7. Xem thống kê phản hồi
**Endpoint**: `GET /api/feedback/stats`

**Mô tả**: Lấy thống kê về phản hồi người dùng

**Tham số đầu vào**: Không có

**Kết quả trả về**:
```json
{
  "status": "success",
  "message": "Thống kê phản hồi",
  "total_feedback": 25,
  "average_rating": 4.2,
  "helpful_percentage": 85.5,
  "ratings_distribution": {
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 8,
    "5": 11
  }
}
```

### 8. Phân tích SQL
**Endpoint**: `POST /api/analyze/sql`

**Mô tả**: Phân tích và đề xuất cải tiến cho truy vấn SQL

**Tham số đầu vào**:
- **Body** (JSON):
  ```json
  {
    "sql_query": "SELECT * FROM users WHERE id = 1",
    "database_context": "Hệ thống quản lý người dùng với các bảng users, roles, permissions"
  }
  ```

**Kết quả trả về**:
```json
{
  "query": "string",
  "analysis": "string",
  "suggestions": [
    "Thêm index cho cột id",
    "Chỉ chọn các cột cần thiết thay vì SELECT *"
  ],
  "optimized_query": "SELECT username, email FROM users WHERE id = 1"
}
```

### 9. Tìm kiếm ngữ nghĩa
**Endpoint**: `POST /api/search/semantic`

**Mô tả**: Tìm kiếm ngữ nghĩa theo câu truy vấn

**Tham số đầu vào**:
- **Body** (JSON):
  ```json
  {
    "question": "string"
  }
  ```
- **Query Parameters**:
  - `k`: Số lượng kết quả trả về (mặc định: 5)

**Kết quả trả về**:
```json
{
  "query": "string",
  "results": [
    {
      "text": "string",
      "metadata": {},
      "score": 0.95,
      "category": "string"
    }
  ]
}
```

### 10. Tìm kiếm kết hợp (hybrid)
**Endpoint**: `POST /api/search/hybrid`

**Mô tả**: Tìm kiếm kết hợp (hybrid) theo câu truy vấn

**Tham số đầu vào**:
- **Body** (JSON):
  ```json
  {
    "question": "string"
  }
  ```
- **Query Parameters**:
  - `k`: Số lượng kết quả trả về (mặc định: 5)
  - `alpha`: Hệ số kết hợp (0.7 = 70% semantic + 30% keyword) (mặc định: 0.7)

**Kết quả trả về**:
```json
{
  "query": "string",
  "results": [
    {
      "text": "string",
      "metadata": {},
      "score": 0.95,
      "category": "string"
    }
  ]
}
```

### 11. Thống kê danh mục
**Endpoint**: `GET /api/categories`

**Mô tả**: Lấy thống kê về các danh mục tài liệu

**Tham số đầu vào**: Không có

**Kết quả trả về**:
```json
{
  "total_documents": 120,
  "documents_by_category": {
    "sql": 45,
    "database_design": 30,
    "nosql": 25,
    "general": 20
  },
  "categories": ["sql", "database_design", "nosql", "general"]
}
```

### 12. Reset collection
**Endpoint**: `DELETE /api/collection/reset`

**Mô tả**: Xóa toàn bộ dữ liệu đã index trong collection

**Tham số đầu vào**: Không có

**Kết quả trả về**:
```json
{
  "status": "success",
  "message": "Đã xóa và tạo lại collection csdl_rag_e5_base",
  "vector_size": 768
}
```

### 13. Lấy danh sách file
**Endpoint**: `GET /api/files`

**Mô tả**: Lấy danh sách các file đã được upload vào hệ thống

**Tham số đầu vào**: Không có

**Kết quả trả về**:
```json
{
  "total_files": 5,
  "files": [
    {
      "filename": "sql_basics.pdf",
      "path": "D:/DATN/V4/src/data/sql_basics.pdf",
      "size": 2456789,
      "upload_date": "2023-06-15T14:30:25",
      "extension": ".pdf",
      "category": null
    },
    {
      "filename": "database_design.docx",
      "path": "D:/DATN/V4/src/data/database_design.docx",
      "size": 1234567,
      "upload_date": "2023-06-10T09:15:30",
      "extension": ".docx",
      "category": null
    }
  ]
}
```

### 14. Xóa file
**Endpoint**: `DELETE /api/files/{filename}`

**Mô tả**: Xóa file đã upload và các index liên quan trong vector store

**Tham số đầu vào**:
- **Path Parameter**:
  - `filename`: Tên file cần xóa

**Kết quả trả về**:
```json
{
  "filename": "sql_basics.pdf",
  "status": "success",
  "message": "Đã xóa file sql_basics.pdf và 45 index liên quan",
  "removed_points": 45
}
```

## Kiểm tra API
1. Chạy API bằng `run_api.bat`
2. Chạy script kiểm tra: `python test_api.py`

## Tùy chỉnh

- Bạn có thể thêm dữ liệu mới vào thư mục `src/data`
- Các file hỗ trợ: PDF, DOCX, TXT, SQL
- Thay đổi danh sách câu hỏi mẫu trong file `main.py`
- Tùy chỉnh cấu hình API trong file `src/api.py`
