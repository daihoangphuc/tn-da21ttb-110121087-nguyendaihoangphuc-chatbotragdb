from typing import List, Dict
import logging

# Cấu hình logging
logging.basicConfig(format="[Search] %(message)s", level=logging.INFO)
# Ghi đè hàm print để thêm prefix
original_print = print


def print(*args, **kwargs):
    prefix = "[Search] "
    original_print(prefix + " ".join(map(str, args)), **kwargs)


logger = logging.getLogger(__name__)
from rank_bm25 import BM25Okapi
import re
import numpy as np
from sentence_transformers import CrossEncoder
import os
import pickle
import json
from dotenv import load_dotenv

# Load biến môi trường từ .env
load_dotenv()


class SearchManager:
    """Lớp quản lý các phương pháp tìm kiếm khác nhau"""

    def __init__(self, vector_store, embedding_model):
        """Khởi tạo search manager"""
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.corpus = []
        self.doc_mappings = []
        self.bm25 = None
        self.bm25_initialized = False

        # Đường dẫn lưu BM25 index
        self.data_dir = os.getenv("UPLOAD_DIR", "src/data")
        
        # Lấy user_id từ vector_store
        user_id = self.vector_store.user_id if hasattr(self.vector_store, 'user_id') else None
        
        # if user_id:
        #     # Tạo thư mục bm25_index trong thư mục của người dùng
        #     user_specific_dir = os.path.join(self.data_dir, user_id)
        #     self.bm25_index_dir = os.path.join(user_specific_dir, "bm25_index")
        #     print(f"Sử dụng thư mục BM25 index trong thư mục người dùng: {self.bm25_index_dir}")
        #     os.makedirs(self.bm25_index_dir, exist_ok=True)
        #     self.bm25_index_path = os.path.join(self.bm25_index_dir, "bm25_index.pkl")
        #     self.corpus_path = os.path.join(self.bm25_index_dir, "corpus.pkl")
        #     self.doc_mappings_path = os.path.join(self.bm25_index_dir, "doc_mappings.pkl")
        #     self.metadata_path = os.path.join(self.bm25_index_dir, "bm25_metadata.json")
        #     # Không tải BM25 index ở đây, sẽ được tải/khởi tạo khi set_vector_store_and_reload_bm25 được gọi
        # else:
        #     # Không có user_id khi khởi tạo, các đường dẫn BM25 sẽ là None
        #     # Không tạo thư mục bm25_index mặc định
        #     print("SearchManager khởi tạo không có user_id. BM25 index sẽ được xử lý khi có user context.")
        #     self.bm25_index_dir = None
        #     self.bm25_index_path = None
        #     self.corpus_path = None
        #     self.doc_mappings_path = None
        #     self.metadata_path = None

        # Tải trước model reranking để tránh tải lại mỗi lần cần rerank
        print("Đang tải model reranking...")

        # Sử dụng model tốt hơn cho reranking tài liệu học thuật/kỹ thuật
        # Một số model phù hợp:
        # - "cross-encoder/ms-marco-MiniLM-L-12-v2" (tốt hơn L-6)
        # - "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1" (hỗ trợ đa ngôn ngữ tốt, phù hợp tiếng Việt)
        # - "cross-encoder/stsb-roberta-large" (chất lượng cao cho semantic similarity)
        # - "vblagoje/dres-cross-encoder-roberta-base" (được tinh chỉnh cho tìm kiếm tài liệu)

        # Cho phép cấu hình model thông qua biến môi trường
        default_reranker_model = "ms-marco-MiniLM-L-12-v2"  
        reranker_model = os.getenv("RERANKER_MODEL", default_reranker_model)

        try:
            self.reranker = CrossEncoder(reranker_model)
            print(f"Đã tải xong model reranking: {reranker_model}")
        except Exception as e:
            print(f"Lỗi khi tải model reranking {reranker_model}: {str(e)}")
            print(f"Sử dụng model dự phòng...")
            # Sử dụng model dự phòng nếu có lỗi
            backup_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
            self.reranker = CrossEncoder(backup_model)
            print(f"Đã tải model dự phòng: {backup_model}")

        # Lưu thông tin về model đang sử dụng
        self.reranker_model_name = reranker_model

    # def _preprocess_text(self, text: str) -> str:
    #     """
    #     Tiền xử lý văn bản cho BM25
        
    #     Args:
    #         text: Văn bản cần tiền xử lý
            
    #     Returns:
    #         str: Văn bản đã được tiền xử lý
    #     """
    #     if not text or not isinstance(text, str) or len(text.strip()) == 0:
    #         return ""
            
    #     # Chuyển thành chữ thường
    #     processed_text = text.lower()
        
    #     # Loại bỏ dấu câu thông dụng
    #     processed_text = re.sub(r'[.,;:!?()[\]{}"\'-]', ' ', processed_text)
        
    #     # Loại bỏ nhiều khoảng trắng liên tiếp
    #     processed_text = re.sub(r'\s+', ' ', processed_text)
        
    #     # Loại bỏ khoảng trắng ở đầu và cuối
    #     processed_text = processed_text.strip()
        
    #     return processed_text

    def semantic_search(
        self,
        query: str,
        k: int = 5,
        sources: List[str] = None,
        file_id: List[str] = None,
    ) -> List[Dict]:
        """Tìm kiếm ngữ nghĩa trên vector store"""
        query_vector = self.embedding_model.encode(query).tolist()

        # Sử dụng search_with_filter nếu có danh sách nguồn hoặc file_id
        if sources:
            print(f"Semantic search với sources={sources}")
            results = self.vector_store.search_with_filter(
                query_vector, sources=sources, limit=k
            )
        elif file_id:
            print(f"Semantic search với file_id={file_id}")
            results = self.vector_store.search_with_filter(
                query_vector, file_id=file_id, limit=k
            )
        else:
            print(f"Semantic search trên toàn bộ tài liệu (không có filter)")
            results = self.vector_store.search(query_vector, limit=k)

        # In thông tin để debug
        if results and len(results) > 0:
            first_result = results[0]
            result_file_id = first_result.get("file_id", "unknown")
            print(
                f"Sample result: metadata.source={first_result.get('metadata', {}).get('source')}, "
                f"direct source={first_result.get('source')}, file_id={result_file_id}"
            )

        return results

    def rerank_results(self, query: str, results: List[Dict]) -> List[Dict]:
        """Tái xếp hạng kết quả sử dụng cross-encoder và metadata phong phú"""
        if not results:
            return results

        # Đọc batch_size từ biến môi trường hoặc sử dụng giá trị mặc định cao hơn
        batch_size = int(os.getenv("RERANK_BATCH_SIZE", "32"))
        print(f"Đang rerank với batch_size={batch_size}")

        # Sử dụng model reranker đã được tải trước đó
        pairs = [(query, result["text"]) for result in results]
        scores = self.reranker.predict(pairs, batch_size=batch_size)

        # Nhận dạng loại truy vấn (definition, syntax, example, etc.)
        query_type = self._detect_query_type(query)
        print(f"Loại truy vấn được phát hiện: {query_type}")

        # Cập nhật điểm số và sắp xếp lại
        for idx, result in enumerate(results):
            # Điểm gốc từ reranker
            base_score = float(scores[idx])
            result["rerank_score"] = base_score

            # Tăng điểm dựa trên metadata phong phú nếu phù hợp với loại truy vấn
            metadata = result.get("metadata", {})
            score_boost = 0.0

            # Tăng trọng số cho các chunk phù hợp với loại truy vấn
            if query_type == "definition" and metadata.get("chứa_định_nghĩa", False):
                score_boost += 0.2  # Tăng 20%

            elif query_type == "syntax" and metadata.get("chứa_cú_pháp", False):
                score_boost += 0.25  # Tăng 25%

                # Tăng thêm điểm cho các loại cú pháp SQL cụ thể
                if "SELECT" in query and metadata.get("chứa_cú_pháp_select", False):
                    score_boost += 0.1
                elif "JOIN" in query and metadata.get("chứa_cú_pháp_join", False):
                    score_boost += 0.1
                elif ("CREATE" in query or "ALTER" in query) and metadata.get(
                    "chứa_cú_pháp_ddl", False
                ):
                    score_boost += 0.1
                elif (
                    "INSERT" in query or "UPDATE" in query or "DELETE" in query
                ) and metadata.get("chứa_cú_pháp_dml", False):
                    score_boost += 0.1

            elif query_type == "example" and metadata.get("chứa_mẫu_code", False):
                score_boost += 0.2  # Tăng 20%

            # Tăng điểm cho chunk có bảng nếu truy vấn liên quan đến tổ chức dữ liệu
            if ("bảng" in query.lower() or "table" in query.lower()) and metadata.get(
                "chứa_bảng", False
            ):
                score_boost += 0.15  # Tăng 15%

            # Áp dụng điểm tăng thêm
            if score_boost > 0:
                result["metadata_boost"] = score_boost  # Lưu giá trị tăng để debug
                result["rerank_score"] = base_score * (
                    1 + score_boost
                )  # Tăng theo phần trăm

            # In thông tin boost để debug
            if score_boost > 0:
                print(f"Tăng điểm {score_boost:.2f} cho chunk có metadata phù hợp.")

        return sorted(results, key=lambda x: x["rerank_score"], reverse=True)
        
    def _detect_query_type(self, query: str) -> str:
        """Phát hiện loại truy vấn: định nghĩa, cú pháp, hoặc ví dụ"""
        query_lower = query.lower()

        # Phát hiện truy vấn cú pháp (ưu tiên cao hơn) - liên quan đến SQL và các lệnh
        syntax_patterns = [
            r"\b(cú\s*pháp|syntax|format|khai\s*báo|declaration|statement)\b",
            r"\b(sử\s*dụng|cách\s*sử\s*dụng|usage|how\s*to\s*use)\b",
            r"\b(select|create|alter|insert|update|delete|procedure|function|trigger|view|index)\b",
            r"\b(sql|database|db|query|truy\s*vấn)\b.*\b(viết|tạo|thực\s*hiện)\b",
            r"\b(viết|write|code|lập\s*trình)\b.*\b(câu\s*lệnh|lệnh|command|statement|query)\b",
            r"\b(lệnh|câu\s*lệnh|command)\b.*\b(như\s*thế\s*nào|ra\s*sao|thế\s*nào)\b",
            r"\b(query|truy\s*vấn|câu\s*truy\s*vấn)\b",
        ]

        # Phát hiện truy vấn định nghĩa
        definition_patterns = [
            r"\b(định\s*nghĩa|khái\s*niệm|là\s*gì|what\s*is|define|mean\s*by)\b",
            r"\b(nghĩa\s*của|ý\s*nghĩa|meaning\s*of)\b",
            r"\b(giải\s*thích|explain|mô\s*tả|describe)\b",
        ]

        # Phát hiện truy vấn ví dụ
        example_patterns = [
            r"\b(ví\s*dụ|minh\s*họa|example|demonstrate|sample|mẫu)\b",
            r"\b(cho\s*xem|show\s*me|đưa\s*ra)\b",
            r"\b(demo|demonstration)\b",
        ]

        # Kiểm tra truy vấn cú pháp trước (ưu tiên cao hơn vì cần chính xác)
        for pattern in syntax_patterns:
            if re.search(pattern, query_lower):
                return "syntax"

        # Kiểm tra các từ khóa SQL cụ thể
        sql_keywords = [
            "SELECT", "FROM", "WHERE", "JOIN", "GROUP BY", "HAVING", "ORDER BY",
            "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP",
            "PROCEDURE", "FUNCTION", "TRIGGER", "VIEW", "INDEX", "TABLE"
        ]

        for keyword in sql_keywords:
            if keyword.lower() in query_lower or keyword in query:
                return "syntax"  # Nếu truy vấn chứa từ khóa SQL, coi như truy vấn cú pháp

        # Kiểm tra truy vấn ví dụ
        for pattern in example_patterns:
            if re.search(pattern, query_lower):
                return "example"

        # Kiểm tra truy vấn định nghĩa
        for pattern in definition_patterns:
            if re.search(pattern, query_lower):
                return "definition"

        # Mặc định trả về general nếu không phát hiện loại cụ thể
        return "general"

    # def get_bm25_status(self):
    #     """Trả về thông tin chi tiết về trạng thái của BM25 để debug"""
    #     status = {
    #         "bm25_initialized": self.bm25_initialized,
    #         "bm25_is_none": self.bm25 is None,
    #         "corpus_length": len(self.corpus) if self.corpus else 0,
    #         "doc_mappings_length": len(self.doc_mappings) if self.doc_mappings else 0,
    #         "user_id": self.vector_store.user_id if hasattr(self.vector_store, 'user_id') else None,
    #         "bm25_index_dir": self.bm25_index_dir,
    #         "bm25_index_path": self.bm25_index_path,
    #         "corpus_path": self.corpus_path,
    #         "doc_mappings_path": self.doc_mappings_path,
    #         "metadata_path": self.metadata_path,
    #         "file_exists": {
    #             "bm25_index_path": os.path.exists(self.bm25_index_path),
    #             "corpus_path": os.path.exists(self.corpus_path),
    #             "doc_mappings_path": os.path.exists(self.doc_mappings_path),
    #             "metadata_path": os.path.exists(self.metadata_path),
    #         }
    #     }
        
    #     # Kiểm tra thêm về kích thước file
    #     if os.path.exists(self.bm25_index_path):
    #         status["bm25_index_size"] = os.path.getsize(self.bm25_index_path)
    #     if os.path.exists(self.corpus_path):
    #         status["corpus_size"] = os.path.getsize(self.corpus_path)
    #     if os.path.exists(self.doc_mappings_path):
    #         status["doc_mappings_size"] = os.path.getsize(self.doc_mappings_path)
            
    #     # Thêm thông tin metadata nếu có
    #     if os.path.exists(self.metadata_path):
    #         try:
    #             with open(self.metadata_path, "r") as f:
    #                 metadata = json.load(f)
    #             status["metadata"] = metadata
    #         except Exception as e:
    #             status["metadata_error"] = str(e)
                
    #     # Thêm thông tin về vector_store
    #     try:
    #         collection_info = self.vector_store.get_collection_info()
    #         if collection_info:
    #             status["collection_info"] = {
    #                 "points_count": collection_info.get("points_count", 0),
    #                 "collection_name": collection_info.get("name", "")
    #             }
    #     except Exception as e:
    #         status["collection_info_error"] = str(e)
            
    #     # Log thông tin status
    #     print(f"=== BM25 DEBUG === BM25 Status: {status}")
        
    #     return status
