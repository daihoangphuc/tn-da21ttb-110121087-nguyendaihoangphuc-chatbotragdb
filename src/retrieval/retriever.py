from typing import List, Optional
from langchain.schema import Document
from langchain.vectorstores import VectorStore

from src.config import RETRIEVAL_SEARCH_TYPE, RETRIEVAL_TOP_K, RERANKER_ENABLED
from src.utils import measure_time, print_document_info, format_context_for_llm
from src.reranking import RerankerFactory


class Retriever:
    """Lớp quản lý việc truy xuất tài liệu từ vector store"""

    def __init__(self, vectorstore: VectorStore, use_reranker: bool = RERANKER_ENABLED):
        """Khởi tạo Retriever"""
        self.vectorstore = vectorstore
        self.search_type = RETRIEVAL_SEARCH_TYPE
        self.top_k = RETRIEVAL_TOP_K
        self.use_reranker = use_reranker
        self.reranker = None

        # Khởi tạo reranker nếu được bật
        if self.use_reranker:
            try:
                print("⏳ Đang khởi tạo reranker...")
                self.reranker = RerankerFactory.create_reranker()
                print("✅ Đã khởi tạo reranker thành công!")
            except Exception as e:
                print(f"⚠️ Lỗi khi khởi tạo reranker: {str(e)}")
                print("⚠️ Sẽ tiến hành retrieval không có reranking")
                self.use_reranker = False

    @measure_time
    def retrieve(self, query: str) -> List[Document]:
        """Truy xuất tài liệu liên quan dựa trên câu truy vấn"""
        # Kiểm tra xem vectorstore có hợp lệ không
        if self.vectorstore is None:
            print("⚠️ Vector store chưa được khởi tạo")
            return []

        print(f"⏳ Đang truy vấn: '{query}'")

        try:
            # Truy xuất tài liệu
            if self.search_type == "similarity":
                # Lấy nhiều hơn số lượng cần thiết nếu sử dụng reranker
                retrieval_k = self.top_k * 3 if self.use_reranker else self.top_k
                docs = self.vectorstore.similarity_search(query, k=retrieval_k)
            elif self.search_type == "mmr":
                # Maximum Marginal Relevance - cân bằng giữa tương đồng và đa dạng
                retrieval_k = self.top_k * 3 if self.use_reranker else self.top_k
                fetch_k = retrieval_k * 2  # Lấy nhiều hơn để đảm bảo đa dạng
                docs = self.vectorstore.max_marginal_relevance_search(
                    query, k=retrieval_k, fetch_k=fetch_k
                )
            else:
                # Mặc định dùng similarity search
                docs = self.vectorstore.similarity_search(query, k=self.top_k)

            print(f"✅ Tìm thấy {len(docs)} tài liệu liên quan trong vector store")

            # Nếu không tìm thấy tài liệu nào, trả về danh sách rỗng
            if len(docs) == 0:
                return []

            # Áp dụng reranking nếu được bật và có reranker
            if self.use_reranker and self.reranker and len(docs) > 1:
                print(f"⏳ Đang thực hiện reranking {len(docs)} tài liệu...")
                # Rerank và lấy top_k tài liệu
                reranked_docs = self.reranker.rerank(query, docs, top_k=self.top_k)
                print(
                    f"✅ Đã rerank và chọn top {len(reranked_docs)} tài liệu phù hợp nhất"
                )
                return reranked_docs
            else:
                # Nếu không sử dụng reranker, trả về k tài liệu đầu tiên
                return docs[: self.top_k]

        except Exception as e:
            print(f"⚠️ Lỗi khi truy xuất tài liệu: {str(e)}")
            return []

    @measure_time
    def hybrid_retrieve(self, query: str, alpha: float = 0.5) -> List[Document]:
        """Truy xuất tài liệu kết hợp BM25 và vector search

        Args:
            query: Câu truy vấn
            alpha: Trọng số cho việc kết hợp (0 = chỉ BM25, 1 = chỉ vector)

        Returns:
            Danh sách tài liệu liên quan
        """
        # Hiện tại chưa triển khai BM25, sẽ sử dụng similarity search
        print("⚠️ Hybrid search chưa được triển khai đầy đủ, sử dụng similarity search")
        return self.retrieve(query)
