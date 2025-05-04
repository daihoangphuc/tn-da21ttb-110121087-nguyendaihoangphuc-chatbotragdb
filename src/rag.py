from typing import List, Dict
from src.embedding import EmbeddingModel
from src.llm import GeminiLLM
from src.vector_store import VectorStore
from src.document_processor import DocumentProcessor
from src.prompt_manager import PromptManager
from src.search import SearchManager
from src.query_processor import QueryProcessor
import os
from dotenv import load_dotenv

# Load biến môi trường từ .env
load_dotenv()


class AdvancedDatabaseRAG:
    """Lớp chính kết hợp tất cả các thành phần của hệ thống RAG"""

    def __init__(
        self, api_key=None, enable_layout_detection=True, enable_query_expansion=True
    ):
        """Khởi tạo hệ thống RAG"""
        # Khởi tạo các thành phần riêng biệt
        self.embedding_model = EmbeddingModel()
        self.llm = GeminiLLM(api_key)
        self.vector_store = VectorStore()
        self.document_processor = DocumentProcessor(
            enable_layout_detection=enable_layout_detection
        )
        self.prompt_manager = PromptManager()
        self.search_manager = SearchManager(self.vector_store, self.embedding_model)

        # Khởi tạo QueryProcessor cho query expansion
        self.enable_query_expansion = enable_query_expansion
        synonyms_file = os.getenv("SYNONYMS_FILE", "src/data/synonyms/synonyms.json")
        if enable_query_expansion:
            print("Đang khởi tạo QueryProcessor cho query expansion...")
            self.query_processor = QueryProcessor(
                synonyms_file=synonyms_file if os.path.exists(synonyms_file) else None,
                use_model=True,  # Sử dụng model để tạo biến thể query
            )
            print("Đã khởi tạo xong QueryProcessor")
        else:
            self.query_processor = None
            print("Query expansion bị tắt")

        # Lưu trạng thái layout detection
        self.enable_layout_detection = enable_layout_detection

        # Đảm bảo collection tồn tại
        self.vector_store.ensure_collection_exists(self.embedding_model.get_dimension())

    def load_documents(self, data_dir: str) -> List[Dict]:
        """Tải tài liệu từ thư mục"""
        return self.document_processor.load_documents(data_dir)

    def process_documents(self, documents: List[Dict]) -> List[Dict]:
        """Xử lý và chia nhỏ tài liệu"""
        return self.document_processor.process_documents(documents)

    def index_to_qdrant(self, chunks: List[Dict]) -> None:
        """Index dữ liệu lên Qdrant"""
        embeddings = self.embedding_model.encode(
            [chunk["text"] for chunk in chunks], batch_size=32, show_progress=True
        )
        self.vector_store.index_documents(chunks, embeddings)

    def semantic_search(
        self, query: str, k: int = 5, sources: List[str] = None
    ) -> List[Dict]:
        """Tìm kiếm ngữ nghĩa"""
        # Sử dụng query expansion nếu được bật
        if self.enable_query_expansion and self.query_processor:
            print(f"Sử dụng query expansion cho truy vấn: '{query}'")
            expanded_results = self.query_processor.hybrid_search_with_expansion(
                search_func=self.search_manager.semantic_search,
                query=query,
                k=k,
                sources=sources,
            )

            # Trả về kết quả hợp nhất từ tất cả các truy vấn mở rộng
            return expanded_results["results"][:k]  # Chỉ lấy top-k kết quả

        # Truy vấn bình thường nếu không sử dụng query expansion
        return self.search_manager.semantic_search(query, k, sources)

    def hybrid_search(
        self, query: str, k: int = 15, alpha: float = 0.7, sources: List[str] = None
    ) -> List[Dict]:
        """Tìm kiếm kết hợp ngữ nghĩa và keyword (ưu tiên ngữ nghĩa nhiều hơn với alpha=0.7)"""
        # Sử dụng query expansion nếu được bật
        if self.enable_query_expansion and self.query_processor:
            print(f"Sử dụng query expansion cho truy vấn hybrid: '{query}'")

            # Tạo một hàm wrapper cho hybrid_search của search_manager
            def hybrid_search_func(q, **kwargs):
                return self.search_manager.hybrid_search(
                    query=q,
                    k=kwargs.get("k", k),
                    alpha=kwargs.get("alpha", alpha),
                    sources=kwargs.get("sources", sources),
                )

            expanded_results = self.query_processor.hybrid_search_with_expansion(
                search_func=hybrid_search_func,
                query=query,
                k=k * 2,  # Lấy nhiều kết quả hơn để rerank
                alpha=alpha,
                sources=sources,
            )

            # Rerank kết quả hợp nhất
            results = expanded_results["results"]
            if results:
                results = self.search_manager.rerank_results(query, results)
                results = results[:k]  # Giới hạn số lượng kết quả

            return results

        # Phương pháp cũ nếu không sử dụng query expansion
        results = self.search_manager.hybrid_search(
            query, k=k * 2, alpha=alpha, sources=sources
        )  # Lấy nhiều kết quả hơn để rerank

        # Tái xếp hạng để lấy kết quả phù hợp nhất
        if results:
            # Rerank để tăng độ chính xác
            results = self.search_manager.rerank_results(query, results)

            # Giới hạn số lượng kết quả trả về
            results = results[:k]

        return results

    def rerank_results(self, query: str, results: List[Dict]) -> List[Dict]:
        """Tái xếp hạng kết quả"""
        return self.search_manager.rerank_results(query, results)

    def generate_response(
        self,
        query: str,
        search_type: str = "hybrid",
        alpha: float = 0.7,
        sources: List[str] = None,
    ) -> str:
        """Tạo câu trả lời dựa trên query"""
        # Xác định loại tìm kiếm
        if search_type == "semantic":
            retrieved = self.semantic_search(query, sources=sources)
        elif search_type == "keyword":
            retrieved = self.search_manager.keyword_search(query, sources=sources)
        else:
            retrieved = self.hybrid_search(query, alpha=alpha, sources=sources)

        # Nếu không có kết quả tìm kiếm, trả về thông báo không tìm thấy
        if not retrieved:
            return "Không tìm thấy thông tin liên quan đến câu hỏi này trong cơ sở dữ liệu. Vui lòng thử lại với câu hỏi khác hoặc tải thêm tài liệu vào hệ thống."

        # Tái xếp hạng kết quả
        retrieved = self.rerank_results(query, retrieved)

        # Xác định loại câu hỏi
        question_type = self.prompt_manager.classify_question(query)

        # Tạo prompt phù hợp
        prompt = self.prompt_manager.create_prompt(query, retrieved, question_type)

        # Thêm yêu cầu định dạng Markdown
        prompt += """
        
        ĐỊNH DẠNG MARKDOWN:
        Hãy định dạng câu trả lời của bạn bằng Markdown để dễ hiển thị ở frontend:
        - Sử dụng **in đậm** cho các thuật ngữ và điểm quan trọng
        - Sử dụng *in nghiêng* cho các nhấn mạnh
        - Sử dụng ## cho tiêu đề cấp 2, ### cho tiêu đề cấp 3
        - Sử dụng danh sách có dấu gạch đầu dòng (- item) hoặc số (1. item)
        - Sử dụng ```code``` cho các đoạn mã, lệnh SQL, cú pháp
        - Sử dụng bảng Markdown khi cần so sánh thông tin
        - Sử dụng > cho các trích dẫn
        
        Đảm bảo câu trả lời có cấu trúc rõ ràng, dễ đọc và trực quan.
        """

        # Gọi LLM
        response = self.llm.invoke(prompt)

        return response.content

    def query_with_sources(
        self,
        query: str,
        search_type: str = "hybrid",
        alpha: float = 0.7,
        sources: List[str] = None,
    ) -> Dict:
        """Trả lời câu hỏi kèm nguồn tham khảo"""
        # Điều chỉnh số lượng kết quả cần lấy
        max_results = 15  # Tăng số lượng kết quả tổng hợp

        # Lưu lại truy vấn gốc
        original_query = query
        expanded_info = None

        # Xác định loại tìm kiếm
        print(f"\n=== Đang xử lý câu hỏi với phương pháp tìm kiếm: {search_type} ===")

        if search_type == "semantic":
            print(f"Thực hiện tìm kiếm ngữ nghĩa (semantic search)")
            retrieved = self.semantic_search(query, k=max_results, sources=sources)

            # Lưu thông tin query expansion nếu có
            if self.enable_query_expansion and self.query_processor:
                expanded_info = {
                    "expanded_queries": self.query_processor.expand_query(query),
                }

        elif search_type == "keyword":
            print(f"Thực hiện tìm kiếm từ khóa (keyword search)")
            retrieved = self.search_manager.keyword_search(
                query, k=max_results, sources=sources
            )

            # Lưu thông tin query expansion nếu có
            if self.enable_query_expansion and self.query_processor:
                expanded_info = {
                    "expanded_queries": self.query_processor.expand_query(query),
                }

        else:
            # Với hybrid search, sử dụng phương thức hybrid_search đã được nâng cao
            print(f"Thực hiện tìm kiếm kết hợp (hybrid search) với alpha={alpha}")
            retrieved = self.hybrid_search(
                query, k=max_results, alpha=alpha, sources=sources
            )

            # Lưu thông tin query expansion nếu có
            if self.enable_query_expansion and self.query_processor:
                expanded_info = {
                    "expanded_queries": self.query_processor.expand_query(query),
                }

        # Kiểm tra xem vector store có dữ liệu không
        collection_info = self.vector_store.get_collection_info()
        has_data = collection_info and collection_info.get("points_count", 0) > 0

        # Nếu không có kết quả tìm kiếm hoặc vector store trống
        if not retrieved or not has_data:
            return {
                "question": original_query,
                "answer": "Không tìm thấy thông tin liên quan đến câu hỏi này trong cơ sở dữ liệu. Vui lòng thử lại với câu hỏi khác hoặc tải thêm tài liệu vào hệ thống.",
                "sources": [],
                "search_method": search_type,
                "filtered_sources": sources if sources else [],
                "query_expansion": expanded_info,
            }

        # Tái xếp hạng tất cả kết quả
        reranked_results = self.rerank_results(query, retrieved)

        # Lưu lại tổng số kết quả sau khi rerank để trả về trong response
        total_reranked = len(reranked_results)

        # Sử dụng top 5 kết quả để tạo câu trả lời
        top_context_results = reranked_results[:5]
        answer = self.generate_response_with_context(
            query, top_context_results, search_type
        )

        # Lấy tất cả nguồn tham khảo từ kết quả đã rerank
        sources_info = []
        for doc in reranked_results:
            # Lấy thông tin vị trí
            page_info = doc["metadata"].get("page", "không xác định")
            section_info = doc["metadata"].get("chunk_type", "không xác định")

            # Tạo thông tin chi tiết về nguồn
            source_detail = {
                "source": doc["metadata"].get("source", "unknown"),
                "page": page_info,
                "section": section_info,
                "score": doc.get("rerank_score", doc.get("score", 0)),
                "content_snippet": doc["text"][:200] + "...",
            }
            sources_info.append(source_detail)

        # Tạo đối tượng kết quả với thông tin query expansion
        result = {
            "question": original_query,
            "answer": answer,
            "sources": sources_info,
            "search_method": search_type,
            "total_reranked": total_reranked,
            "filtered_sources": sources if sources else [],
        }

        # Thêm thông tin query expansion nếu có
        if expanded_info:
            result["query_expansion"] = expanded_info

        return result

    def generate_response_with_context(
        self, query: str, retrieved: List[Dict], search_type: str = "hybrid"
    ) -> str:
        """Tạo câu trả lời dựa trên ngữ cảnh từ các kết quả tìm kiếm"""
        if not retrieved:
            return "Không tìm thấy thông tin liên quan đến câu hỏi này trong cơ sở dữ liệu."

        # Giới hạn số lượng tài liệu ngữ cảnh để tận dụng tối đa khả năng của LLM
        # đồng thời không vượt quá ngưỡng context window
        # Tăng từ mặc định (thường là 3 được sử dụng trong prompt_manager) lên 5
        context_docs = retrieved[:5]

        # Xác định loại câu hỏi
        question_type = self.prompt_manager.classify_question(query)

        # Tạo prompt phù hợp
        prompt = self.prompt_manager.create_prompt(query, context_docs, question_type)

        # Thêm yêu cầu định dạng Markdown
        prompt += """
        
        ĐỊNH DẠNG MARKDOWN:
        Hãy định dạng câu trả lời của bạn bằng Markdown để dễ hiển thị ở frontend:
        - Sử dụng **in đậm** cho các thuật ngữ và điểm quan trọng
        - Sử dụng *in nghiêng* cho các nhấn mạnh
        - Sử dụng ## cho tiêu đề cấp 2, ### cho tiêu đề cấp 3
        - Sử dụng danh sách có dấu gạch đầu dòng (- item) hoặc số (1. item)
        - Sử dụng ```code``` cho các đoạn mã, lệnh SQL, cú pháp
        - Sử dụng bảng Markdown khi cần so sánh thông tin
        - Sử dụng > cho các trích dẫn
        
        Đảm bảo câu trả lời có cấu trúc rõ ràng, dễ đọc và trực quan.
        """

        # Gọi LLM
        response = self.llm.invoke(prompt)

        return response.content

    def delete_collection(self) -> None:
        """Xóa collection trong Qdrant"""
        self.vector_store.delete_collection()

    def get_collection_info(self) -> Dict:
        """Lấy thông tin collection"""
        return self.vector_store.get_collection_info()

    def _generate_answer(self, query, relevant_docs, **kwargs):
        """Sinh câu trả lời từ LLM dựa trên context và query"""
        # Tạo context từ các tài liệu liên quan
        context = "\n---\n".join([doc["text"] for doc in relevant_docs])

        # Tạo prompt với template phù hợp
        prompt = self.prompt_manager.templates["query_with_context"].format(
            context=context, query=query
        )

        # Thêm yêu cầu định dạng Markdown trong prompt
        prompt += "\n\nVui lòng trả lời câu hỏi trong định dạng Markdown rõ ràng để dễ hiển thị ở frontend. Sử dụng các thẻ như **in đậm**, *in nghiêng*, ## tiêu đề, - danh sách, ```code``` và các bảng khi cần thiết."

        # In prompt để debug
        # print(f"=== PROMPT ===\n{prompt}\n=== END PROMPT ===")

        # Gọi LLM và lấy kết quả
        response = self.llm.invoke(prompt)
        return response.content
