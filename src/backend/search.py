from typing import List, Dict
import logging
import asyncio

# Cấu hình logging
logging.basicConfig(format="[Search] %(message)s", level=logging.INFO)
# Ghi đè hàm print để thêm prefix
original_print = print


def print(*args, **kwargs):
    prefix = "[Search] "
    original_print(prefix + " ".join(map(str, args)), **kwargs)


logger = logging.getLogger(__name__)
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
    """Lớp quản lý các phương pháp tìm kiếm khác nhau với hỗ trợ async"""

    def __init__(self, vector_store, embedding_model):
        """Khởi tạo search manager"""
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.corpus = []
        self.doc_mappings = []
        self.bm25 = None
        self.bm25_initialized = False

        # Đường dẫn lưu BM25 index
        self.data_dir = os.getenv("UPLOAD_DIR", "backend/data")
        
        # Lấy user_id từ vector_store
        user_id = self.vector_store.user_id if hasattr(self.vector_store, 'user_id') else None
        
        # Tải trước model reranking để tránh tải lại mỗi lần cần rerank
        print("Đang tải model reranking...")

        # Sử dụng model tốt hơn cho reranking tài liệu học thuật/kỹ thuật
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
            try:
                self.reranker = CrossEncoder(backup_model)
                print(f"Đã tải model dự phòng: {backup_model}")
                reranker_model = backup_model  # Update model name for later reference
            except Exception as backup_error:
                print(f"Lỗi nghiêm trọng: Không thể tải model dự phòng {backup_model}: {str(backup_error)}")
                raise RuntimeError(f"Không thể khởi tạo model reranking. Lỗi gốc: {str(e)}, Lỗi dự phòng: {str(backup_error)}")

        # Lưu thông tin về model đang sử dụng
        self.reranker_model_name = reranker_model

    async def semantic_search(
        self,
        query: str,
        k: int = 5,
        sources: List[str] = None,
        file_id: List[str] = None,
    ) -> List[Dict]:
        """Tìm kiếm ngữ nghĩa trên vector store (bất đồng bộ)"""
        # Tạo query vector bất đồng bộ
        query_vector_array = await self.embedding_model.encode(query)
        query_vector = query_vector_array.tolist()

        # Sử dụng search_with_filter nếu có danh sách nguồn hoặc file_id
        if sources:
            print(f"Semantic search với sources={sources}")
            results = await self.vector_store.search_with_filter(
                query_vector, sources=sources, limit=k
            )
        elif file_id:
            print(f"Semantic search với file_id={file_id}")
            results = await self.vector_store.search_with_filter(
                query_vector, file_id=file_id, limit=k
            )
        else:
            print(f"Semantic search trên toàn bộ tài liệu (không có filter)")
            results = await self.vector_store.search(query_vector, limit=k)

        # In thông tin để debug
        if results and len(results) > 0:
            first_result = results[0]
            result_file_id = first_result.get("file_id", "unknown")
            print(
                f"Sample result: metadata.source={first_result.get('metadata', {}).get('source')}, "
                f"direct source={first_result.get('source')}, file_id={result_file_id}"
            )

        return results

    def semantic_search_sync(
        self,
        query: str,
        k: int = 5,
        sources: List[str] = None,
        file_id: List[str] = None,
    ) -> List[Dict]:
        """Tìm kiếm ngữ nghĩa trên vector store (đồng bộ - để tương thích ngược)"""
        query_vector = self.embedding_model.encode_sync(query).tolist()

        # Sử dụng search_with_filter nếu có danh sách nguồn hoặc file_id
        if sources:
            print(f"Semantic search với sources={sources}")
            results = self.vector_store.search_with_filter_sync(
                query_vector, sources=sources, limit=k
            )
        elif file_id:
            print(f"Semantic search với file_id={file_id}")
            results = self.vector_store.search_with_filter_sync(
                query_vector, file_id=file_id, limit=k
            )
        else:
            print(f"Semantic search trên toàn bộ tài liệu (không có filter)")
            results = self.vector_store.search_sync(query_vector, limit=k)

        # In thông tin để debug
        if results and len(results) > 0:
            first_result = results[0]
            result_file_id = first_result.get("file_id", "unknown")
            print(
                f"Sample result: metadata.source={first_result.get('metadata', {}).get('source')}, "
                f"direct source={first_result.get('source')}, file_id={result_file_id}"
            )

        return results

    async def rerank_results(self, query: str, results: List[Dict]) -> List[Dict]:
        """Tái xếp hạng kết quả sử dụng cross-encoder và metadata phong phú (bất đồng bộ)"""
        if not results:
            return results

        # Đọc batch_size từ biến môi trường hoặc sử dụng giá trị mặc định cao hơn
        batch_size = int(os.getenv("RERANK_BATCH_SIZE", "32"))
        print(f"Đang rerank với batch_size={batch_size}")

        # Sử dụng model reranker đã được tải trước đó
        pairs = [(query, result["text"]) for result in results]
        
        # Chạy reranker trong thread pool để không block
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(
            None,
            lambda: self.reranker.predict(pairs, batch_size=batch_size)
        )

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

            elif query_type == "example" and metadata.get("chứa_ví_dụ", False):
                score_boost += 0.15  # Tăng 15%

            elif query_type == "comparison" and metadata.get("chứa_so_sánh", False):
                score_boost += 0.15  # Tăng 15%

            elif query_type == "troubleshooting" and metadata.get("chứa_lỗi", False):
                score_boost += 0.2  # Tăng 20%

            # Áp dụng điểm cộng thêm
            result["final_score"] = base_score + score_boost

        # Sắp xếp theo điểm cuối cùng
        results.sort(key=lambda x: x.get("final_score", 0), reverse=True)

        # Log kết quả reranking
        print(f"Đã rerank {len(results)} kết quả theo query_type='{query_type}'")
        if results:
            top_score = results[0].get("final_score", 0)
            print(f"Điểm cao nhất sau reranking: {top_score:.4f}")

        return results

    def rerank_results_sync(self, query: str, results: List[Dict]) -> List[Dict]:
        """Tái xếp hạng kết quả sử dụng cross-encoder và metadata phong phú (đồng bộ)"""
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

            elif query_type == "example" and metadata.get("chứa_ví_dụ", False):
                score_boost += 0.15  # Tăng 15%

            elif query_type == "comparison" and metadata.get("chứa_so_sánh", False):
                score_boost += 0.15  # Tăng 15%

            elif query_type == "troubleshooting" and metadata.get("chứa_lỗi", False):
                score_boost += 0.2  # Tăng 20%

            # Áp dụng điểm cộng thêm
            result["final_score"] = base_score + score_boost

        # Sắp xếp theo điểm cuối cùng
        results.sort(key=lambda x: x.get("final_score", 0), reverse=True)

        # Log kết quả reranking
        print(f"Đã rerank {len(results)} kết quả theo query_type='{query_type}'")
        if results:
            top_score = results[0].get("final_score", 0)
            print(f"Điểm cao nhất sau reranking: {top_score:.4f}")

        return results

    def _detect_query_type(self, query: str) -> str:
        """
        Phát hiện loại truy vấn dựa trên từ khóa và cấu trúc câu
        
        Args:
            query: Câu truy vấn cần phân loại
            
        Returns:
            Loại truy vấn: definition, syntax, example, comparison, troubleshooting, general
        """
        query_lower = query.lower()
        
        # Pattern cho các loại truy vấn khác nhau
        definition_patterns = [
            r'\b(là gì|định nghĩa|khái niệm|what is|define|meaning)\b',
            r'\b(giải thích|explain|nghĩa là)\b'
        ]
        
        syntax_patterns = [
            r'\b(cú pháp|syntax|viết|write|tạo|create|câu lệnh|command|lệnh)\b',
            r'\b(select|insert|update|delete|join|where|group by|order by)\b',
            r'\b(sql|query|truy vấn)\b.*\b(như thế nào|how to|cách)\b'
        ]
        
        example_patterns = [
            r'\b(ví dụ|example|minh họa|demo|thực hành|practice)\b',
            r'\b(cho tôi|give me|show me|hiển thị)\b.*\b(ví dụ|example)\b'
        ]
        
        comparison_patterns = [
            r'\b(khác nhau|khác biệt|so sánh|compare|difference|vs|versus)\b',
            r'\b(tốt hơn|better|nên chọn|should choose)\b'
        ]
        
        troubleshooting_patterns = [
            r'\b(lỗi|error|sửa|fix|debug|không hoạt động|not working|issue|problem)\b',
            r'\b(tại sao|why|làm sao|how come)\b.*\b(không|not|lỗi|error)\b'
        ]
        
        # Kiểm tra từng loại pattern
        for pattern in definition_patterns:
            if re.search(pattern, query_lower):
                return "definition"
                
        for pattern in syntax_patterns:
            if re.search(pattern, query_lower):
                return "syntax"
                
        for pattern in example_patterns:
            if re.search(pattern, query_lower):
                return "example"
                
        for pattern in comparison_patterns:
            if re.search(pattern, query_lower):
                return "comparison"
                
        for pattern in troubleshooting_patterns:
            if re.search(pattern, query_lower):
                return "troubleshooting"
        
        return "general"
