import os
import numpy as np
from typing import List, Tuple, Dict, Any, Optional, Union
from pathlib import Path
from dotenv import load_dotenv

# Load biến môi trường từ .env
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path)

# API Keys và Tokens
HF_TOKEN = os.getenv("HF_TOKEN")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "csdl_docs")

# Cấu hình Model
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")

# Cấu hình Reranker
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
RERANKER_DEVICE = os.getenv("RERANKER_DEVICE", "cpu")
RERANKER_BATCH_SIZE = int(os.getenv("RERANKER_BATCH_SIZE", "16"))
RERANKER_USE_FP16 = os.getenv("RERANKER_USE_FP16", "false").lower() == "true"
RERANKER_ENABLED = os.getenv("RERANKER_ENABLED", "true").lower() == "true"

# Cấu hình Query Expansion
QUERY_EXPANSION_ENABLED = os.getenv("QUERY_EXPANSION_ENABLED", "true").lower() == "true"
QUERY_EXPANSION_NUM_QUERIES = int(os.getenv("QUERY_EXPANSION_NUM_QUERIES", "2"))
USE_SELF_QUERY = os.getenv("USE_SELF_QUERY", "false").lower() == "true"
USE_HYBRID_SEARCH = os.getenv("USE_HYBRID_SEARCH", "false").lower() == "true"

# Cấu hình Tốc độ vs Chất lượng
FAST_MODE = os.getenv("FAST_MODE", "false").lower() == "true"  # Chế độ ưu tiên tốc độ
RERANK_RETRIEVAL_RESULTS = (
    os.getenv("RERANK_RETRIEVAL_RESULTS", "true").lower() == "true"
)  # Có rerank kết quả retrieval không
MAX_FUSION_QUERIES = int(
    os.getenv("MAX_FUSION_QUERIES", "2")
)  # Số lượng queries tối đa cho fusion (bao gồm query gốc)

# Cấu hình Document Loader
DOCUMENT_LOADER_MAX_WORKERS = int(os.getenv("DOCUMENT_LOADER_MAX_WORKERS", "8"))

# Cấu hình Qdrant
QDRANT_BATCH_SIZE = int(os.getenv("QDRANT_BATCH_SIZE", "128"))

# Cấu hình Chunking
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 150
# Cấu hình thêm cho tối ưu code và SQL
CHUNK_SIZE_SPECIALIZED = 2500
CHUNK_OVERLAP_SPECIALIZED = 256
MIN_CHUNK_SIZE = 100
MIN_CHUNK_CHARACTERS = 300

# Kích thước buffer cho khớp với dấu hiệu phân đoạn
CHUNK_BUFFER_SIZE = int(os.getenv("CHUNK_BUFFER_SIZE", "2"))

# Loại ngưỡng phá vỡ chunk - giá trị: "percentile", "absolute"
CHUNK_BREAKPOINT_THRESHOLD_TYPE = os.getenv(
    "CHUNK_BREAKPOINT_THRESHOLD_TYPE", "percentile"
)

# Giá trị ngưỡng (tùy thuộc vào loại, 0.8 cho percentile hoặc giá trị số cho absolute)
CHUNK_BREAKPOINT_THRESHOLD_AMOUNT = float(
    os.getenv("CHUNK_BREAKPOINT_THRESHOLD_AMOUNT", "0.8")
)

# Danh sách dấu hiệu phân đoạn để ưu tiên chia đoạn
CHUNK_SEPARATORS = [
    "\n\n\n",
    "\n\n",
    "\n",
    ". ",
    "! ",
    "? ",
    "；",
    "，",
    "。",
    "、",
]

# Cấu hình SQL Chunking
SQL_FILE_EXTENSIONS = [".sql", ".ddl", ".dml", ".db"]
SQL_CHUNK_SIZE = 2000
SQL_CHUNK_OVERLAP = 200
SQL_QUERY_SAMPLE_LENGTH = 100  # Độ dài mẫu để phát hiện SQL query
SQL_SCHEMA_KEYWORDS = ["CREATE TABLE", "ALTER TABLE", "CREATE INDEX", "PRIMARY KEY"]
SQL_QUERY_KEYWORDS = ["SELECT", "INSERT", "UPDATE", "DELETE", "MERGE", "JOIN", "WHERE"]

# Cấu hình Clustering
CLUSTER_DISTANCE_THRESHOLD = float(os.getenv("CLUSTER_DISTANCE_THRESHOLD", "1.2"))
CLUSTERING_BATCH_SIZE = int(os.getenv("CLUSTERING_BATCH_SIZE", "128"))

# Cấu hình Retrieval
RETRIEVAL_SEARCH_TYPE = os.getenv("RETRIEVAL_SEARCH_TYPE", "similarity")
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "15"))

# Cấu hình Gemini
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.0-flash")
GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.0"))
GEMINI_TOP_P = float(os.getenv("GEMINI_TOP_P", "0.0"))
GEMINI_TOP_K = int(os.getenv("GEMINI_TOP_K", "1"))
