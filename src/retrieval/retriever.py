from typing import List
from langchain.schema import Document
from langchain.vectorstores import VectorStore

from src.config import RETRIEVAL_SEARCH_TYPE, RETRIEVAL_TOP_K
from src.utils import measure_time, print_document_info, format_context_for_llm


class Retriever:
    """Lớp quản lý việc truy xuất tài liệu từ vector store"""

    def __init__(self, vectorstore: VectorStore):
        """Khởi tạo Retriever"""
        self.vectorstore = vectorstore
        self.search_type = RETRIEVAL_SEARCH_TYPE
        self.top_k = RETRIEVAL_TOP_K

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
                docs = self.vectorstore.similarity_search(query, k=self.top_k)
            elif self.search_type == "mmr":
                docs = self.vectorstore.max_marginal_relevance_search(
                    query, k=self.top_k, fetch_k=self.top_k * 3
                )
            else:
                # Mặc định dùng similarity search
                docs = self.vectorstore.similarity_search(query, k=self.top_k)

            print(f"✅ Tìm thấy {len(docs)} tài liệu liên quan")

            # Nếu không tìm thấy tài liệu nào, trả về danh sách rỗng
            if len(docs) == 0:
                return []

            return docs
        except Exception as e:
            print(f"⚠️ Lỗi khi truy xuất tài liệu: {str(e)}")
            return []
