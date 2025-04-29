import os
from typing import List, Dict, Any, Optional

# ------------------ Cấu hình collection ------------------ #
COLLECTION_NAME = "rag_collection"
DIMENSION = 1536  # Đối với embeddings mặc định

# ------------------ Cấu hình RAG ------------------ #
RERANKER_ENABLED = True
RERANKER_TOP_K = 5
RETRIEVAL_TOP_K = 20  # Số lượng tài liệu lấy ra từ vector store
QUERY_EXPANSION_ENABLED = True
QUERY_EXPANSION_MODEL = "gemini-pro"
QUERY_EXPANSION_VARIANTS = 3
USE_HYBRID_SEARCH = True  # Tìm kiếm hybrid kết hợp sparse và dense
USE_SELF_QUERY = True  # Sử dụng multi-step reasoning cho truy vấn phức tạp
MULTISTEP_MODEL = "gemini-pro"  # Mô hình cho multi-step reasoning

# ------------------ Cấu hình chunking ------------------ #
# Kích thước cơ bản
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Kích thước cho code (thường nhỏ hơn vì cần chính xác hơn)
CODE_CHUNK_SIZE = 800
CODE_CHUNK_OVERLAP = 150

# Kích thước cho bảng biểu (lớn hơn để bao gồm đủ thông tin)
TABLE_CHUNK_SIZE = 1500
TABLE_CHUNK_OVERLAP = 250

# Kích thước cho PDF (phức tạp hơn vì có thể chứa hình ảnh, bảng)
PDF_CHUNK_SIZE = 1200
PDF_CHUNK_OVERLAP = 200

# Kích thước SQL (nhỏ hơn để bảo toàn tính chính xác)
SQL_CHUNK_SIZE = 1000
SQL_CHUNK_OVERLAP = 200

# ------------------ Cấu hình SQL ------------------ #
SQL_FILE_EXTENSIONS = [".sql", ".ddl"]

# ------------------ Danh sách extension cho các loại tài liệu ------------------ #
CODE_FILE_EXTENSIONS = [
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".cs",
    ".cpp",
    ".c",
    ".h",
    ".rb",
    ".php",
    ".go",
    ".rs",
    ".swift",
]

TABLE_FILE_EXTENSIONS = [".csv", ".xlsx", ".xls", ".json", ".tsv", ".parquet"]

PDF_FILE_EXTENSIONS = [".pdf"]

# ------------------ Cấu hình LLM ------------------ #
LLM_PROVIDER = "gemini"  # Mặc định hoặc openai
LLM_MODEL = "gemini-pro"
TEMPERATURE = 0.2
MAX_OUTPUT_TOKENS = 2048
TOP_P = 0.95
TOP_K = 40

# ------------------ API KEYS ------------------ #
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
