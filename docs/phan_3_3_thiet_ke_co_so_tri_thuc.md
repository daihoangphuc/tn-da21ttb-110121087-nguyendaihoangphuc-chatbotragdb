# 3.3. Thiết kế cơ sở tri thức (Knowledge Base)

## 3.3.1. Tổng quan thiết kế cơ sở tri thức

Cơ sở tri thức (Knowledge Base) là thành phần trung tâm của hệ thống RAG, có nhiệm vụ lưu trữ, tổ chức và quản lý toàn bộ thông tin liên quan đến môn Cơ sở dữ liệu. Thiết kế cơ sở tri thức của hệ thống được xây dựng theo kiến trúc đa tầng, đảm bảo khả năng mở rộng, hiệu quả truy xuất và tính bảo mật dữ liệu người dùng.

### Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE BASE                            │
├─────────────────────────────────────────────────────────────┤
│  Tầng Xử lý Tài liệu (Document Processing Layer)            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │  File Converter │  │  Text Extractor │  │ Categorizer │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Tầng Phân đoạn (Chunking Layer)                            │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  Structure-aware│  │ Metadata        │                  │
│  │  Chunking       │  │ Enhancement     │                  │
│  └─────────────────┘  └─────────────────┘                  │
├─────────────────────────────────────────────────────────────┤
│  Tầng Vector Store (Vector Storage Layer)                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │  Qdrant Vector │  │  Collection     │  │ Search &    │  │
│  │  Database       │  │  Management     │  │ Filtering   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Tầng Metadata (Metadata Storage Layer)                     │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  Supabase       │  │  File           │                  │
│  │  Database       │  │  Management     │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

## 3.3.2. Chiến lược xử lý và phân đoạn tài liệu

### 3.3.2.1. Hỗ trợ đa định dạng tài liệu

Hệ thống được thiết kế để hỗ trợ nhiều định dạng tài liệu phổ biến trong giáo dục và nghiên cứu:

**Định dạng được hỗ trợ:**
- **PDF** (.pdf): Sử dụng PyPDFLoader
- **Microsoft Word** (.docx): Sử dụng Docx2txtLoader  
- **Text files** (.txt): Sử dụng TextLoader
- **SQL scripts** (.sql): Sử dụng TextLoader với xử lý đặc biệt
- **Markdown** (.md): Sử dụng TextLoader

**Chuyển đổi tự động:**
```python
def convert_to_pdf(self, input_path: str, *, remove_original: bool = True) -> str:
    """Chuyển đổi tài liệu sang PDF bằng LibreOffice"""
    convertible_formats = [
        ".sql", ".doc", ".docx", ".ppt", ".pptx", 
        ".xls", ".xlsx", ".odt", ".ods", ".odp"
    ]
```

Hệ thống tự động chuyển đổi các định dạng Office và OpenDocument sang PDF để đảm bảo tính nhất quán trong xử lý.

### 3.3.2.2. Chiến lược phân đoạn thông minh

#### A. Phân đoạn theo cấu trúc (Structure-aware Chunking)

Hệ thống ưu tiên sử dụng phương pháp phân đoạn theo cấu trúc để bảo toàn ngữ cảnh:

```python
def _chunk_by_structure(self, text: str, metadata: Dict) -> List[Dict]:
    """Phân đoạn dựa trên cấu trúc tài liệu"""
    # Phát hiện tiêu đề bằng regex pattern
    heading_pattern = r"(?:^|\n)([A-Za-z0-9\u00C0-\u1EF9][^\n.!?]{5,99})\n\s*\n"
    
    # Xây dựng vị trí các phần trong tài liệu
    positions = []
    for heading in headings:
        positions.append((start_idx, end_idx, heading_text))
```

**Ưu điểm của phương pháp này:**
- Giữ nguyên mối quan hệ giữa tiêu đề và nội dung
- Phát hiện và bảo toàn cấu trúc bảng, danh sách, code blocks
- Tự động nhận diện loại nội dung (heading, table, code, text)

#### B. Phân đoạn theo kích thước (Size-based Chunking)

Khi không phát hiện được cấu trúc rõ ràng, hệ thống sử dụng phương pháp dự phòng:

```python
self.text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,          # Kích thước chunk tối ưu
    chunk_overlap=150,       # Độ chồng lấp để bảo toàn ngữ cảnh
    length_function=len,
    separators=["\n\n", "\n", ".", " ", ""]
)
```

**Cấu hình tối ưu:**
- **Chunk size**: 800 ký tự (cân bằng giữa ngữ cảnh và độ chính xác)
- **Overlap**: 150 ký tự (đảm bảo không mất thông tin quan trọng)
- **Separators**: Ưu tiên ngắt tại các ranh giới tự nhiên

### 3.3.2.3. Phân loại và làm giàu metadata

#### A. Hệ thống phân loại tự động

Hệ thống sử dụng từ khóa để tự động phân loại nội dung:

```python
category_keywords = {
    "sql": [
        "sql", "select", "insert", "update", "delete", "join", 
        "where", "group by", "order by", "index", "primary key",
        "foreign key", "constraint", "view", "stored procedure"
    ],
    "nosql": [
        "nosql", "mongodb", "redis", "cassandra", "neo4j",
        "dynamodb", "document store", "key-value", "graph database"
    ],
    "database_design": [
        "schema", "normalization", "entity relationship", "er diagram",
        "data modeling", "logical design", "physical design"
    ],
    "database_administration": [
        "backup", "restore", "replication", "high availability",
        "performance tuning", "user management", "security"
    ]
}
```

#### B. Làm giàu metadata cho chunk

Mỗi chunk được bổ sung thông tin metadata chi tiết:

```python
def _enhance_chunk_metadata(self, text: str, metadata: Dict) -> Dict:
    enhanced = dict(metadata)
    
    # Phát hiện nội dung định nghĩa
    if contains_definition_patterns(text):
        enhanced["chứa_định_nghĩa"] = True
    
    # Phát hiện cú pháp SQL
    if "SELECT" in text and "FROM" in text:
        enhanced["chứa_cú_pháp_select"] = True
    
    # Phát hiện bảng và hình ảnh
    if detect_table_structure(text):
        enhanced["chứa_bảng"] = True
        
    return enhanced
```

**Các loại metadata được bổ sung:**
- Loại nội dung (definition, syntax, code, table)
- Cú pháp SQL cụ thể (SELECT, JOIN, DDL, DML)
- Thông tin cấu trúc (heading, table, list)
- Thời gian index và nguồn tài liệu

## 3.3.3. Thiết kế Vector Store với Qdrant

### 3.3.3.1. Kiến trúc lưu trữ vector

Hệ thống sử dụng Qdrant làm vector database với thiết kế collection riêng biệt cho từng người dùng:

```python
def get_collection_name_for_user(self, user_id):
    """Tạo collection riêng cho mỗi user"""
    return f"user_{user_id}"

def ensure_collection_exists(self, vector_size, user_id=None):
    """Đảm bảo collection tồn tại với cấu hình tối ưu"""
    self.client.create_collection(
        collection_name=self.collection_name,
        vectors_config=VectorParams(
            size=vector_size,      # 768 cho sentence-transformers
            distance=Distance.COSINE  # Khoảng cách cosine
        )
    )
```

### 3.3.3.2. Schema lưu trữ và metadata

Mỗi vector point trong Qdrant chứa thông tin đầy đủ:

```python
payload = {
    "text": chunk["text"],                    # Nội dung chunk
    "metadata": chunk["metadata"],           # Metadata gốc
    "source": source,                        # Tên file nguồn
    "file_id": file_id,                     # UUID của file
    "file_path": chunk.get("file_path"),    # Đường dẫn file
    "indexed_at": int(time.time())          # Timestamp index
}
```

**Cấu trúc metadata chi tiết:**
- **text**: Nội dung văn bản của chunk
- **metadata**: Dict chứa thông tin phân loại, loại nội dung, vị trí
- **source**: Tên file gốc để truy vết nguồn gốc
- **file_id**: UUID duy nhất cho việc quản lý và xóa
- **file_path**: Đường dẫn đầy đủ trên hệ thống
- **indexed_at**: Timestamp để theo dõi thời gian cập nhật

### 3.3.3.3. Cơ chế tìm kiếm và lọc

#### A. Tìm kiếm vector với bộ lọc

```python
def search_with_filter(self, query_vector, sources=None, file_id=None, limit=5):
    """Tìm kiếm với khả năng lọc theo nguồn và file"""
    
    # Tạo filter conditions
    should_conditions = []
    
    if sources:
        for source in sources:
            should_conditions.append({"key": "source", "match": {"value": source}})
            should_conditions.append({"key": "file_path", "match": {"value": source}})
    
    if file_id:
        should_conditions.append({"key": "file_id", "match": {"value": file_id}})
    
    search_filter = {"should": should_conditions}
    
    return self.client.search(
        collection_name=self.collection_name,
        query_vector=query_vector,
        limit=limit,
        query_filter=models.Filter(**search_filter)
    )
```

#### B. Tìm kiếm theo danh mục

```python
def get_document_by_category(self, category, limit=100):
    """Lấy tài liệu theo danh mục cụ thể"""
    category_filter = Filter(
        must=[{"key": "metadata.category", "match": {"value": category}}]
    )
    
    results = self.client.scroll(
        collection_name=self.collection_name,
        filter=category_filter,
        limit=limit
    )
```

### 3.3.3.4. Quản lý và cập nhật dữ liệu

#### A. Indexing với batch processing

```python
def index_documents(self, chunks, embeddings, user_id, file_id):
    """Index dữ liệu với xử lý batch để tối ưu hiệu suất"""
    
    batch_size = 100
    points = []
    
    for idx, chunk in enumerate(chunks):
        point_id = str(uuid.uuid4())
        payload = self.create_payload(chunk, file_id)
        
        points.append(PointStruct(
            id=point_id,
            vector=embeddings[idx].tolist(),
            payload=payload
        ))
    
    # Upload theo batch
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        self.client.upsert(collection_name=self.collection_name, points=batch)
```

#### B. Xóa dữ liệu theo file

```python
def delete_by_file_id(self, file_id):
    """Xóa tất cả chunk thuộc một file cụ thể"""
    filter_condition = {
        "filter": {"must": [{"key": "file_id", "match": {"value": file_id}}]}
    }
    
    self.client.delete(
        collection_name=self.collection_name,
        points_selector=models.FilterSelector(filter=filter_condition["filter"])
    )
```

## 3.3.4. Quản lý metadata với Supabase

### 3.3.4.1. Schema cơ sở dữ liệu metadata

Hệ thống sử dụng Supabase để lưu trữ metadata về files và users:

```sql
-- Bảng document_files
CREATE TABLE document_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id VARCHAR(255) UNIQUE NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    file_type VARCHAR(50),
    metadata JSONB,
    upload_time TIMESTAMP DEFAULT NOW()
);

-- Index để tối ưu truy vấn
CREATE INDEX idx_document_files_user_id ON document_files(user_id);
CREATE INDEX idx_document_files_file_id ON document_files(file_id);
```

### 3.3.4.2. Lưu trữ thông tin file

```python
def save_file_metadata(self, file_id, filename, file_path, user_id, 
                      file_type=None, metadata=None):
    """Lưu metadata file vào Supabase"""
    data = {
        "file_id": file_id,
        "filename": filename,
        "file_path": file_path,
        "user_id": user_id,
        "upload_time": datetime.now().isoformat(),
    }
    
    if metadata:
        data["metadata"] = {
            "category": metadata.get("category"),
            "file_size": metadata.get("file_size"),
            "chunks_count": metadata.get("chunks_count"),
            "is_indexed": True,
            "original_extension": metadata.get("original_extension"),
            "converted_to_pdf": metadata.get("converted_to_pdf", False)
        }
    
    return self.client.table("document_files").insert(data).execute()
```

## 3.3.5. Cơ chế cập nhật và đồng bộ tri thức

### 3.3.5.1. Quy trình upload và xử lý

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Upload    │ -> │  Document   │ -> │  Chunking   │
│   File      │    │ Processing  │    │ & Metadata  │
└─────────────┘    └─────────────┘    └─────────────┘
        │                   │                   │
        v                   v                   v
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  File       │ -> │ Embedding   │ -> │ Vector      │
│ Conversion  │    │ Generation  │    │ Indexing    │
└─────────────┘    └─────────────┘    └─────────────┘
        │                   │                   │
        v                   v                   v
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Metadata    │    │ Qdrant      │    │ Supabase    │
│ Extraction  │    │ Storage     │    │ Metadata    │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 3.3.5.2. Theo dõi tiến trình xử lý

Hệ thống cung cấp API theo dõi tiến trình xử lý chi tiết:

```python
indexing_status = {
    "status": "processing",
    "progress": 0,
    "stage": "loading",      # loading -> chunking -> vectorizing -> completed
    "message": "Đang tải tài liệu...",
    "processed_files": 0,
    "total_files": 0,
    "chunks_processed": 0
}
```

**4 giai đoạn xử lý:**
1. **Loading** (0-25%): Tải và chuyển đổi tài liệu
2. **Chunking** (25-50%): Phân đoạn và phân loại
3. **Clustering** (50-75%): Nhóm các chunk liên quan (nếu có)
4. **Vectorizing** (75-100%): Tạo embedding và lưu vào vector store

### 3.3.5.3. Cơ chế xóa và cập nhật

#### A. Xóa theo file

```python
def delete_file_from_knowledge_base(self, file_id, user_id):
    """Xóa file khỏi cơ sở tri thức"""
    
    # 1. Xóa từ vector store
    self.vector_store.delete_by_file_id(file_id, user_id)
    
    # 2. Xóa metadata từ Supabase
    self.files_manager.delete_file_metadata(file_id)
    
    # 3. Xóa file vật lý (nếu cần)
    if os.path.exists(file_path):
        os.remove(file_path)
```

#### B. Cập nhật nội dung

Khi cập nhật tài liệu, hệ thống thực hiện:
1. Xóa các chunk cũ của file
2. Xử lý lại toàn bộ tài liệu
3. Tạo embedding mới
4. Cập nhật metadata

## 3.3.6. Tối ưu hóa hiệu suất

### 3.3.6.1. Batch processing

- **Embedding generation**: Xử lý theo batch 32 samples
- **Vector indexing**: Upload theo batch 100 points
- **File processing**: Xử lý song song cho nhiều file

### 3.3.6.2. Caching và tối ưu truy vấn

```python
# Index tối ưu cho Supabase
CREATE INDEX idx_document_files_user_id ON document_files(user_id);
CREATE INDEX idx_document_files_category ON document_files USING GIN ((metadata->>'category'));

# Tối ưu Qdrant search
- Sử dụng collection riêng biệt cho từng user
- Filter hiệu quả với indexed payload fields
- Limit kết quả trả về hợp lý (5-10)
```

### 3.3.6.3. Monitoring và logging

```python
# Theo dõi performance
@measure_time
def index_documents(self, chunks, embeddings, user_id, file_id):
    start_time = time.time()
    # ... xử lý ...
    duration = time.time() - start_time
    print(f"Index completed in {duration:.2f} seconds")
```

## 3.3.7. Bảo mật và phân quyền

### 3.3.7.1. Isolation theo user

- Mỗi user có collection riêng trong Qdrant: `user_{user_id}`
- Metadata trong Supabase được filter theo `user_id`
- File upload được lưu trong thư mục riêng: `uploads/{user_id}/`

### 3.3.7.2. Xác thực và phân quyền

```python
@app.post("/upload")
async def upload_document(current_user=Depends(get_current_user)):
    user_id = current_user.id
    
    # Đảm bảo chỉ truy cập data của user hiện tại
    rag_system.vector_store.user_id = user_id
    rag_system.vector_store.collection_name = f"user_{user_id}"
```

## 3.3.8. Khả năng mở rộng

### 3.3.8.1. Horizontal scaling

- **Qdrant**: Hỗ trợ clustering và sharding
- **Supabase**: Auto-scaling database
- **API**: Stateless design cho load balancing

### 3.3.8.2. Tính mở rộng về định dạng

Hệ thống được thiết kế để dễ dàng thêm loader mới:

```python
# Thêm loader cho định dạng mới
self.loaders[".pptx"] = PowerPointLoader
self.loaders[".xlsx"] = ExcelLoader

# Cập nhật convertible formats
self.convertible_formats.extend([".pptx", ".xlsx"])
```

## 3.3.9. Kết luận

Thiết kế cơ sở tri thức của hệ thống chatbot RAG đảm bảo:

1. **Tính nhất quán**: Quy trình xử lý chuẩn hóa cho mọi loại tài liệu
2. **Hiệu quả truy xuất**: Vector search với metadata filtering
3. **Khả năng mở rộng**: Kiến trúc modular và stateless
4. **Bảo mật**: Phân tách dữ liệu theo user
5. **Tính linh hoạt**: Hỗ trợ nhiều định dạng và phương pháp chunking

Cơ sở tri thức được thiết kế để phục vụ hiệu quả cho việc học tập và tra cứu thông tin về Cơ sở dữ liệu, với khả năng cập nhật và mở rộng linh hoạt theo nhu cầu sử dụng thực tế.
