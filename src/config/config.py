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
