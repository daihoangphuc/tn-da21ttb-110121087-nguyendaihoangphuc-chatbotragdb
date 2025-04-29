from typing import List, Dict, Any, Optional, Union, Tuple
import numpy as np
from langchain.schema import Document
from langchain.vectorstores import VectorStore

from src.retrieval.retriever import Retriever
from src.utils import measure_time, print_document_info
from src.reranking import RerankerFactory
from src.config import RETRIEVAL_TOP_K, RERANKER_ENABLED

# Thử nhập các gói cần thiết cho sparse retrieval
try:
    from rank_bm25 import BM25Okapi

    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    print("⚠️ rank_bm25 không được cài đặt. Sparse retrieval sẽ bị giới hạn.")

try:
    import spacy

    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    print(
        "⚠️ spacy không được cài đặt. Tokenization cho sparse retrieval sẽ sử dụng phương pháp đơn giản."
    )


class HybridRetriever(Retriever):
    """Lớp triển khai hybrid retrieval kết hợp dense và sparse retrieval"""

    def __init__(
        self,
        vectorstore: VectorStore,
        use_reranker: bool = RERANKER_ENABLED,
        alpha: float = 0.5,
        enable_sparse: bool = True,
    ):
        """Khởi tạo HybridRetriever

        Args:
            vectorstore: Vector store cho dense retrieval
            use_reranker: Có sử dụng reranker hay không
            alpha: Trọng số pha trộn giữa dense và sparse (0: chỉ sparse, 1: chỉ dense)
            enable_sparse: Bật/tắt sparse retrieval
        """
        super().__init__(vectorstore, use_reranker)
        self.alpha = alpha
        self.enable_sparse = enable_sparse and BM25_AVAILABLE
        self.sparse_index = None
        self.sparse_documents = []
        self.tokenizer = None
        self._initialize_tokenizer()

    def _initialize_tokenizer(self):
        """Khởi tạo tokenizer"""
        # Bỏ qua việc khởi tạo spaCy để tránh lỗi
        self.tokenizer = None
        print("ℹ️ Sử dụng tokenizer đơn giản cho sparse retrieval")

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize văn bản thành các từ

        Args:
            text: Văn bản cần tokenize

        Returns:
            Danh sách các token
        """
        # Sử dụng tokenize đơn giản cho mọi trường hợp
        # Loại bỏ các ký tự đặc biệt và dấu câu cơ bản
        import re

        # Chuyển văn bản về chữ thường
        text = text.lower()
        # Loại bỏ các ký tự đặc biệt, giữ lại chữ và số
        text = re.sub(r"[^\w\s]", " ", text)
        # Chia thành các từ và loại bỏ khoảng trắng thừa
        tokens = [token.strip() for token in text.split() if token.strip()]
        return tokens

    def build_sparse_index(self, documents: List[Document]):
        """Xây dựng sparse index (BM25) cho tập tài liệu

        Args:
            documents: Danh sách tài liệu
        """
        if not self.enable_sparse:
            print(
                "⚠️ Sparse retrieval đã bị vô hiệu hóa hoặc gói rank_bm25 không được cài đặt"
            )
            return

        print("⏳ Đang xây dựng sparse index (BM25)...")
        # Lưu trữ documents để có thể truy xuất sau
        self.sparse_documents = documents

        # Tokenize văn bản và xây dựng corpus
        corpus = []
        for doc in documents:
            tokens = self._tokenize(doc.page_content)
            corpus.append(tokens)

        # Xây dựng BM25 index
        if corpus:
            self.sparse_index = BM25Okapi(corpus)
            print(f"✅ Đã xây dựng sparse index cho {len(corpus)} tài liệu")
        else:
            print("⚠️ Không có tài liệu nào để xây dựng sparse index")

    def update_sparse_index(self, documents: List[Document]):
        """Cập nhật sparse index với tài liệu mới

        Args:
            documents: Danh sách tài liệu mới
        """
        # Đơn giản là xây dựng lại index với danh sách tài liệu cũ + mới
        all_documents = self.sparse_documents + documents
        self.build_sparse_index(all_documents)

    def _sparse_search(
        self, query: str, k: int = RETRIEVAL_TOP_K
    ) -> List[Tuple[Document, float]]:
        """Thực hiện sparse search (BM25)

        Args:
            query: Câu truy vấn
            k: Số lượng kết quả trả về

        Returns:
            Danh sách cặp (document, score)
        """
        if not self.enable_sparse or not self.sparse_index:
            return []

        # Tokenize truy vấn
        query_tokens = self._tokenize(query)

        # Lấy điểm BM25 cho các tài liệu
        scores = self.sparse_index.get_scores(query_tokens)

        # Sắp xếp theo điểm số và lấy top k
        top_indices = np.argsort(scores)[::-1][:k]

        # Tạo kết quả
        results = [
            (self.sparse_documents[idx], scores[idx])
            for idx in top_indices
            if scores[idx] > 0
        ]

        return results

    @measure_time
    def hybrid_retrieve(
        self, query: str, alpha: Optional[float] = None, k: int = RETRIEVAL_TOP_K
    ) -> List[Document]:
        """Thực hiện hybrid retrieval kết hợp cả dense và sparse

        Args:
            query: Câu truy vấn
            alpha: Trọng số kết hợp (0: chỉ sparse, 1: chỉ dense)
            k: Số lượng kết quả trả về

        Returns:
            Danh sách tài liệu liên quan
        """
        # Sử dụng alpha được cung cấp hoặc giá trị mặc định
        alpha = alpha if alpha is not None else self.alpha
        print(f"⏳ Đang thực hiện hybrid retrieval với alpha={alpha}")

        # 1. Dense retrieval (vector search)
        dense_k = min(
            k * 3, 100
        )  # Lấy nhiều hơn để đảm bảo có đủ tài liệu sau khi kết hợp
        try:
            # Tìm kiếm similarity với kích thước lớn hơn
            dense_docs = self.vectorstore.similarity_search_with_score(query, k=dense_k)

            # Chuẩn hóa điểm số dense (điểm similarity cao hơn = tốt hơn)
            if dense_docs:
                # Chuyển đổi dạng dữ liệu
                dense_results = [(doc, score) for doc, score in dense_docs]
                # Chuẩn hóa điểm số (đảm bảo giá trị từ 0-1, với 1 là tốt nhất)
                max_score = max(score for _, score in dense_results)
                min_score = min(score for _, score in dense_results)
                score_range = max_score - min_score if max_score > min_score else 1.0

                dense_normalized = [
                    (doc, (score - min_score) / score_range)
                    for doc, score in dense_results
                ]
            else:
                dense_normalized = []
        except Exception as e:
            print(f"⚠️ Lỗi khi thực hiện dense retrieval: {str(e)}")
            dense_normalized = []

        # 2. Sparse retrieval (BM25)
        sparse_normalized = []
        if self.enable_sparse and alpha < 1.0:
            try:
                sparse_results = self._sparse_search(query, k=dense_k)

                # Chuẩn hóa điểm số sparse
                if sparse_results:
                    max_score = max(score for _, score in sparse_results)
                    min_score = min(score for _, score in sparse_results)
                    score_range = (
                        max_score - min_score if max_score > min_score else 1.0
                    )

                    sparse_normalized = [
                        (doc, (score - min_score) / score_range)
                        for doc, score in sparse_results
                    ]
            except Exception as e:
                print(f"⚠️ Lỗi khi thực hiện sparse retrieval: {str(e)}")

        # 3. Kết hợp kết quả
        combined_results = {}

        # Thêm kết quả dense
        for doc, score in dense_normalized:
            doc_id = hash(doc.page_content)
            combined_results[doc_id] = {
                "doc": doc,
                "dense_score": score,
                "sparse_score": 0.0,
                "combined_score": alpha * score,
            }

        # Thêm kết quả sparse và kết hợp với dense
        for doc, score in sparse_normalized:
            doc_id = hash(doc.page_content)
            if doc_id in combined_results:
                # Đã có trong kết quả dense, cập nhật điểm
                combined_results[doc_id]["sparse_score"] = score
                combined_results[doc_id]["combined_score"] += (1 - alpha) * score
            else:
                # Chưa có trong kết quả dense, thêm mới
                combined_results[doc_id] = {
                    "doc": doc,
                    "dense_score": 0.0,
                    "sparse_score": score,
                    "combined_score": (1 - alpha) * score,
                }

        # Sắp xếp theo combined_score và lấy top k
        sorted_results = sorted(
            combined_results.values(), key=lambda x: x["combined_score"], reverse=True
        )

        # Lấy top k kết quả
        top_k_results = sorted_results[:k]

        # Thêm thông tin điểm số vào metadata
        results = []
        for item in top_k_results:
            doc = item["doc"]
            # Thêm thông tin điểm số vào metadata
            doc.metadata["dense_score"] = float(item["dense_score"])
            doc.metadata["sparse_score"] = float(item["sparse_score"])
            doc.metadata["combined_score"] = float(item["combined_score"])
            doc.metadata["retrieval_method"] = "hybrid"
            results.append(doc)

        print(f"✅ Đã tìm thấy {len(results)} tài liệu liên quan với hybrid retrieval")

        # 4. Áp dụng reranking nếu được bật
        if self.use_reranker and self.reranker and len(results) > 1:
            print(f"⏳ Đang thực hiện reranking {len(results)} tài liệu...")
            reranked_docs = self.reranker.rerank(query, results, top_k=k)
            print(
                f"✅ Đã rerank và chọn top {len(reranked_docs)} tài liệu phù hợp nhất"
            )
            return reranked_docs

        return results

    @measure_time
    def retrieve(self, query: str) -> List[Document]:
        """Triển khai lại phương thức retrieve để sử dụng hybrid_retrieve

        Args:
            query: Câu truy vấn

        Returns:
            Danh sách tài liệu liên quan
        """
        # Kiểm tra nếu sparse index đã được xây dựng
        if self.enable_sparse and self.sparse_index:
            # Sử dụng hybrid retrieval
            return self.hybrid_retrieve(query, k=self.top_k)
        else:
            # Sử dụng dense retrieval thông thường
            return super().retrieve(query)
