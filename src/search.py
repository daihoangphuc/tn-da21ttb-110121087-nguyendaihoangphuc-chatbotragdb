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
        data_dir = os.getenv("UPLOAD_DIR", "src/data")
        self.bm25_index_dir = os.path.join(data_dir, "bm25_index")
        os.makedirs(self.bm25_index_dir, exist_ok=True)
        self.bm25_index_path = os.path.join(self.bm25_index_dir, "bm25_index.pkl")
        self.corpus_path = os.path.join(self.bm25_index_dir, "corpus.pkl")
        self.doc_mappings_path = os.path.join(self.bm25_index_dir, "doc_mappings.pkl")

        # Nếu có index BM25 đã lưu, tải lên khi khởi tạo
        self._try_load_bm25_index()

        # Tải trước model reranking để tránh tải lại mỗi lần cần rerank
        print("Đang tải model reranking...")

        # Sử dụng model tốt hơn cho reranking tài liệu học thuật/kỹ thuật
        # Một số model phù hợp:
        # - "cross-encoder/ms-marco-MiniLM-L-12-v2" (tốt hơn L-6)
        # - "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1" (hỗ trợ đa ngôn ngữ tốt, phù hợp tiếng Việt)
        # - "cross-encoder/stsb-roberta-large" (chất lượng cao cho semantic similarity)
        # - "vblagoje/dres-cross-encoder-roberta-base" (được tinh chỉnh cho tìm kiếm tài liệu)

        # Cho phép cấu hình model thông qua biến môi trường
        default_reranker_model = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"  # Mặc định là model đa ngôn ngữ tốt
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

    def _try_load_bm25_index(self):
        """Thử tải BM25 index từ file nếu tồn tại"""
        try:
            if (
                os.path.exists(self.bm25_index_path)
                and os.path.exists(self.corpus_path)
                and os.path.exists(self.doc_mappings_path)
            ):

                print("Đang tải BM25 index từ file...")

                with open(self.bm25_index_path, "rb") as f:
                    self.bm25 = pickle.load(f)

                with open(self.corpus_path, "rb") as f:
                    self.corpus = pickle.load(f)

                with open(self.doc_mappings_path, "rb") as f:
                    self.doc_mappings = pickle.load(f)

                self.bm25_initialized = True
                print("Đã tải xong BM25 index từ file")
                return True
        except Exception as e:
            print(f"Lỗi khi tải BM25 index: {str(e)}")
            # Nếu lỗi, reset các biến và tiếp tục như trước
            self.bm25 = None
            self.corpus = []
            self.doc_mappings = []
            self.bm25_initialized = False

        return False

    def _save_bm25_index(self):
        """Lưu BM25 index, corpus và doc_mappings vào file"""
        try:
            if self.bm25_initialized and self.bm25 is not None:
                print("Đang lưu BM25 index...")

                with open(self.bm25_index_path, "wb") as f:
                    pickle.dump(self.bm25, f)

                with open(self.corpus_path, "wb") as f:
                    pickle.dump(self.corpus, f)

                with open(self.doc_mappings_path, "wb") as f:
                    pickle.dump(self.doc_mappings, f)

                print("Đã lưu xong BM25 index")
                return True
        except Exception as e:
            print(f"Lỗi khi lưu BM25 index: {str(e)}")

        return False

    def _initialize_bm25(self):
        """Khởi tạo BM25 từ các tài liệu trong vector store và lưu vào file"""
        # Lấy tất cả dữ liệu từ vector store
        try:
            # Kiểm tra xem collection có thay đổi không dựa trên số lượng points
            collection_info = self.vector_store.get_collection_info()
            current_points_count = collection_info.get("points_count", 0)

            # Kiểm tra xem đã có file bm25_metadata.json chứa thông tin về số lượng points đã indexing trước đó
            metadata_path = os.path.join(self.bm25_index_dir, "bm25_metadata.json")
            previous_points_count = 0

            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                        previous_points_count = metadata.get("points_count", 0)
                except:
                    previous_points_count = 0

            # Nếu số lượng points không thay đổi và đã có index, không cần tạo lại
            if (
                current_points_count == previous_points_count
                and current_points_count > 0
                and self.bm25_initialized
            ):
                print(
                    f"Số lượng points không thay đổi ({current_points_count}), sử dụng BM25 index đã có"
                )
                return True

            # Nếu không có points, không thể tạo index
            if current_points_count == 0:
                print("Không tìm thấy dữ liệu để khởi tạo BM25")
                return False

            all_docs = self.vector_store.get_all_documents()

            if not all_docs:
                print("Không tìm thấy tài liệu để khởi tạo BM25")
                return False

            # Tiền xử lý văn bản để chuẩn bị cho BM25
            corpus = []
            doc_mappings = []

            for doc in all_docs:
                # Tiền xử lý văn bản
                text = doc["text"]
                # Chuyển thành chữ thường
                text = text.lower()
                # Loại bỏ các ký tự đặc biệt
                text = re.sub(r"[^\w\s]", " ", text)
                # Tokenize đơn giản bằng khoảng trắng
                tokens = text.split()

                # Lưu tokens và mapping đến tài liệu gốc
                corpus.append(tokens)
                doc_mappings.append(doc)

            # Khởi tạo BM25
            self.bm25 = BM25Okapi(corpus)
            self.corpus = corpus
            self.doc_mappings = doc_mappings
            self.bm25_initialized = True

            # Lưu BM25 index vào file
            self._save_bm25_index()

            # Lưu metadata
            try:
                with open(metadata_path, "w") as f:
                    json.dump({"points_count": current_points_count}, f)
            except Exception as e:
                print(f"Lỗi khi lưu metadata: {str(e)}")

            return True
        except Exception as e:
            print(f"Lỗi khi khởi tạo BM25: {str(e)}")
            return False

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

    def keyword_search(
        self,
        query: str,
        k: int = 5,
        sources: List[str] = None,
        file_id: List[str] = None,
    ) -> List[Dict]:
        """Tìm kiếm từ khóa sử dụng BM25"""
        # Khởi tạo BM25 nếu chưa được khởi tạo
        if not self.bm25_initialized:
            initialized = self._initialize_bm25()
            if not initialized:
                # Fallback to semantic search if BM25 initialization fails
                print("Không thể khởi tạo BM25, quay lại tìm kiếm ngữ nghĩa")
                return self.semantic_search(
                    query, k=k, sources=sources, file_id=file_id
                )

        # Tiền xử lý query tương tự như corpus
        query = query.lower()
        query = re.sub(r"[^\w\s]", " ", query)
        query_tokens = query.split()

        # Lấy điểm BM25 cho mỗi tài liệu
        bm25_scores = self.bm25.get_scores(query_tokens)

        # Lấy top-k kết quả
        top_k_indices = np.argsort(bm25_scores)[::-1][: k * 2]  # Lấy nhiều hơn để lọc

        # Xử lý danh sách nguồn để hỗ trợ so sánh với cả tên file đơn thuần và đường dẫn
        normalized_sources = []
        if sources:
            for source in sources:
                normalized_sources.append(source)  # Giữ nguyên source gốc
                # Thêm tên file đơn thuần (nếu source chứa đường dẫn)
                if os.path.sep in source:
                    filename = os.path.basename(source)
                    if filename and filename not in normalized_sources:
                        normalized_sources.append(filename)
            print(
                f"Keyword search với sources={sources}, normalized_sources={normalized_sources}"
            )

        results = []
        for idx in top_k_indices:
            if bm25_scores[idx] > 0:  # Chỉ lấy kết quả có điểm số dương
                doc = self.doc_mappings[idx]

                # Nếu có danh sách file_id, chỉ lấy tài liệu từ các file_id được chỉ định
                if file_id:
                    doc_file_id = doc.get("file_id", "unknown")
                    if doc_file_id not in file_id:
                        continue

                # Nếu có danh sách nguồn, chỉ lấy tài liệu từ các nguồn được chỉ định
                elif sources:
                    doc_source = doc.get(
                        "source", doc["metadata"].get("source", "unknown")
                    )
                    doc_filename = (
                        os.path.basename(doc_source)
                        if os.path.sep in doc_source
                        else doc_source
                    )

                    if (
                        doc_source not in normalized_sources
                        and doc_filename not in normalized_sources
                    ):
                        continue

                results.append(
                    {
                        "text": doc["text"],
                        "metadata": doc["metadata"],
                        "score": float(
                            bm25_scores[idx]
                        ),  # Chuyển numpy float sang Python float
                        "file_id": doc.get("file_id", "unknown"),  # Thêm file_id
                    }
                )

                # Nếu đủ k kết quả thì dừng
                if len(results) >= k:
                    break

        # Nếu không tìm thấy kết quả nào, fallback sang semantic search
        if not results:
            print("Không tìm thấy kết quả với BM25, quay lại tìm kiếm ngữ nghĩa")
            return self.semantic_search(query, k=k, sources=sources, file_id=file_id)

        return results

    # Phương thức được gọi sau khi indexing tài liệu mới để cập nhật BM25
    def update_bm25_index(self):
        """Cập nhật lại BM25 index sau khi có thay đổi trong vector store"""
        print("Đang cập nhật BM25 index...")
        # Reset lại trạng thái để buộc tạo lại index
        self.bm25_initialized = False
        self.bm25 = None
        self.corpus = []
        self.doc_mappings = []

        # Xóa các file index cũ nếu có
        if os.path.exists(self.bm25_index_path):
            os.remove(self.bm25_index_path)
        if os.path.exists(self.corpus_path):
            os.remove(self.corpus_path)
        if os.path.exists(self.doc_mappings_path):
            os.remove(self.doc_mappings_path)

        # Khởi tạo lại BM25
        return self._initialize_bm25()

    # def hybrid_search(
    #     self,
    #     query: str,
    #     k: int = 5,
    #     alpha: float = 0.7,
    #     sources: List[str] = None,
    #     file_id: List[str] = None,
    #     ) -> List[Dict]:
    #     """Kết hợp tìm kiếm ngữ nghĩa và keyword"""
    #     print(f"=== Bắt đầu hybrid search với alpha={alpha} ===")

    #     semantic = self.semantic_search(query, k=k, sources=sources, file_id=file_id)
    #     print(f"Đã tìm được {len(semantic)} kết quả từ semantic search")

    #     keyword = self.keyword_search(query, k=k, sources=sources, file_id=file_id)
    #     print(f"Đã tìm được {len(keyword)} kết quả từ keyword search")

    #     combined = {}
    #     for res in semantic:
    #         combined[res["text"]] = {**res, "score": alpha * res["score"]}

    #     for res in keyword:
    #         if res["text"] in combined:
    #             combined[res["text"]]["score"] += (1 - alpha) * res["score"]
    #             print(f"Đã kết hợp kết quả trùng lặp: {res['text'][:50]}...")
    #         else:
    #             combined[res["text"]] = {**res, "score": (1 - alpha) * res["score"]}

    #     sorted_results = sorted(
    #         combined.values(), key=lambda x: x["score"], reverse=True
    #     )

    #     print(
    #         f"=== Kết thúc hybrid search: {len(sorted_results[:k])}/{len(combined)} kết quả ==="
    #     )

    #     return sorted_results[:k]

    def rerank_results(self, query: str, results: List[Dict]) -> List[Dict]:
        """Tái xếp hạng kết quả sử dụng cross-encoder và metadata phong phú"""
        if not results:
            return results

        # Sử dụng model reranker đã được tải trước đó
        pairs = [(query, result["text"]) for result in results]
        scores = self.reranker.predict(pairs, batch_size=8)

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

        # Phát hiện truy vấn định nghĩa
        definition_patterns = [
            r"\b(định nghĩa|khái niệm|là gì|what is|define|mean by)\b",
            r"\b(nghĩa của|ý nghĩa|meaning of)\b",
        ]

        # Phát hiện truy vấn cú pháp
        syntax_patterns = [
            r"\b(cú pháp|syntax|format|khai báo|declaration|statement)\b",
            r"\b(sử dụng|cách sử dụng|usage|how to use)\b",
            r"\b(SELECT|CREATE|ALTER|INSERT|UPDATE|DELETE)\b.*\b(như thế nào|ra sao|thế nào)\b",
            r"\b(viết|write)\b.*\b(câu lệnh|lệnh|command|statement)\b",
        ]

        # Phát hiện truy vấn ví dụ
        example_patterns = [
            r"\b(ví dụ|minh họa|example|demonstrate|sample|mẫu)\b",
            r"\b(show me|cho xem)\b",
        ]

        # Kiểm tra theo từng loại pattern
        for pattern in definition_patterns:
            if re.search(pattern, query_lower):
                return "definition"

        for pattern in syntax_patterns:
            if re.search(pattern, query_lower):
                return "syntax"

        for pattern in example_patterns:
            if re.search(pattern, query_lower):
                return "example"

        # Kiểm tra các từ khóa SQL cụ thể
        sql_keywords = [
            "SELECT",
            "FROM",
            "WHERE",
            "JOIN",
            "GROUP BY",
            "HAVING",
            "ORDER BY",
            "INSERT",
            "UPDATE",
            "DELETE",
            "CREATE",
            "ALTER",
            "DROP",
        ]

        for keyword in sql_keywords:
            if keyword in query.upper():
                return (
                    "syntax"  # Nếu truy vấn chứa từ khóa SQL, coi như truy vấn cú pháp
                )

        # Mặc định trả về general nếu không phát hiện loại cụ thể
        return "general"
