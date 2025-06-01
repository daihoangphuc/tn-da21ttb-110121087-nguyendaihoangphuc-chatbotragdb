import logging
import asyncio

# Cấu hình logging cho cả logging và print
logging.basicConfig(format="[RAG_Pipeline] %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Ghi đè hàm print để thêm prefix
original_print = print


def print(*args, **kwargs):
    prefix = "[RAG_Pipeline] "
    original_print(prefix + " ".join(map(str, args)), **kwargs)


# Cấu hình logging
logging.basicConfig(format="[RAG_Pipeline] %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

from typing import List, Dict, AsyncGenerator
from src.embedding import EmbeddingModel
from src.llm import GeminiLLM
from src.vector_store import VectorStore
from src.document_processor import DocumentProcessor
from src.prompt_manager import PromptManager
from src.search import SearchManager
from src.query_processor import QueryProcessor
from src.query_router import QueryRouter
import os
import re
import concurrent.futures
from dotenv import load_dotenv
import time
import asyncio
import requests
import uuid
import json

# Import Google_Agents_Search
from src.tools.Google_Agents_Search import run_query_with_sources as google_agent_search

# Load biến môi trường từ .env
load_dotenv()

# Khai báo các biến toàn cục cho các tài nguyên dùng chung
global_embedding_model = None
global_llm_model = None
global_document_processor = None
global_prompt_manager = None
global_search_manager = None
global_resources_initialized = False


def initialize_global_resources():
    """Khởi tạo các tài nguyên dùng chung toàn cục một lần duy nhất"""
    global global_embedding_model, global_llm_model, global_document_processor, global_prompt_manager, global_search_manager, global_resources_initialized

    if not global_resources_initialized:
        print("Bắt đầu khởi tạo các tài nguyên toàn cục...")

        # Khởi tạo các model chỉ một lần
        global_embedding_model = EmbeddingModel()
        print("Đã khởi tạo embedding model toàn cục")

        global_llm_model = GeminiLLM()
        print("Đã khởi tạo LLM toàn cục")

        global_document_processor = DocumentProcessor()
        print("Đã khởi tạo Document Processor toàn cục")

        global_prompt_manager = PromptManager()
        print("Đã khởi tạo Prompt Manager toàn cục")

        # Tạo search manager dùng chung với VectorStore không có user_id
        # Điều này đảm bảo không tạo hay tải BM25 index không cần thiết khi khởi tạo
        # BM25 index phù hợp sẽ được tải khi user_id thực sử dụng
        empty_vector_store = VectorStore()  # VectorStore không có user_id
        global_search_manager = SearchManager(empty_vector_store, global_embedding_model)
        print("Đã khởi tạo Search Manager toàn cục (BM25, reranker)")
        print("SearchManager toàn cục sẽ tải BM25 index phù hợp khi được gán cho user_id cụ thể")

        global_resources_initialized = True
        print("Hoàn thành khởi tạo tất cả tài nguyên toàn cục")
    else:
        print("Các tài nguyên toàn cục đã được khởi tạo trước đó")

    return {
        "embedding_model": global_embedding_model,
        "llm_model": global_llm_model,
        "document_processor": global_document_processor,
        "prompt_manager": global_prompt_manager,
        "search_manager": global_search_manager,
    }


class AdvancedDatabaseRAG:
    """Lớp chính kết hợp tất cả các thành phần của hệ thống RAG"""

    def __init__(
        self,
        api_key=None,
        user_id=None,
        embedding_model=None,
        llm_model=None,
        document_processor=None,
        prompt_manager=None,
        search_manager=None,
    ):
        """Khởi tạo hệ thống RAG"""
        # Khởi tạo các thành phần riêng biệt từ bên ngoài hoặc tạo mới
        if embedding_model is not None:
            self.embedding_model = embedding_model
            print("Sử dụng embedding model được cung cấp từ bên ngoài")
        else:
            print("Khởi tạo embedding model mới")
            self.embedding_model = EmbeddingModel()

        if llm_model is not None:
            self.llm = llm_model
            print("Sử dụng LLM được cung cấp từ bên ngoài")
        else:
            print("Khởi tạo LLM mới")
            self.llm = GeminiLLM(api_key)

        # Lưu trữ user_id
        self.user_id = user_id
        # Khởi tạo vector store với user_id
        self.vector_store = VectorStore(user_id=user_id)
        print(f"Khởi tạo hệ thống RAG cho user_id={user_id}")

        if document_processor is not None:
            self.document_processor = document_processor
            print("Sử dụng Document Processor được cung cấp từ bên ngoài")
        else:
            print("Khởi tạo Document Processor mới")
            self.document_processor = DocumentProcessor()

        if prompt_manager is not None:
            self.prompt_manager = prompt_manager
            print("Sử dụng Prompt Manager được cung cấp từ bên ngoài")
        else:
            print("Khởi tạo Prompt Manager mới")
            self.prompt_manager = PromptManager()

        # Sử dụng search_manager từ bên ngoài hoặc tạo mới với vector_store của user
        if search_manager is not None:
            # Gán search_manager toàn cục và cập nhật vector_store (cùng với BM25 index tương ứng)
            self.search_manager = search_manager
            # Thay vì chỉ gán vector_store, gọi phương thức để cập nhật và tải lại BM25 index phù hợp
            self.search_manager.set_vector_store_and_reload_bm25(self.vector_store)
            print("Sử dụng Search Manager toàn cục (đã cập nhật vector_store và BM25 index cho user)")
        else:
            print("Khởi tạo Search Manager mới")
            self.search_manager = SearchManager(self.vector_store, self.embedding_model)

        # Thêm QueryProcessor cho việc xử lý đồng tham chiếu
        self.query_processor = QueryProcessor()
        print("Đã khởi tạo QueryProcessor với khả năng xử lý đồng tham chiếu")

        # Thêm QueryRouter cho việc phân loại câu hỏi
        self.query_router = QueryRouter()
        print("Đã khởi tạo QueryRouter để phân loại câu hỏi thành 3 loại")

        # Đọc tham số alpha mặc định từ biến môi trường
        try:
            default_alpha_env = os.getenv("DEFAULT_ALPHA")
            if default_alpha_env:
                self.default_alpha = float(default_alpha_env)
                print(
                    f"Sử dụng alpha mặc định từ biến môi trường: {self.default_alpha}"
                )
            else:
                self.default_alpha = 0.7  # Giá trị mặc định
                print(f"Sử dụng alpha mặc định: {self.default_alpha}")
        except ValueError:
            self.default_alpha = 0.7
            print(
                f"Lỗi đọc giá trị alpha từ biến môi trường, sử dụng mặc định: {self.default_alpha}"
            )

        # Tính toán và lưu các giá trị khác nếu cần
        self.enable_fact_checking = (
            False  # Tính năng kiểm tra sự kiện (có thể kích hoạt sau)
        )

        # Cấu hình fact checking
        self.enable_fact_checking = os.getenv(
            "ENABLE_FACT_CHECKING", "True"
        ).lower() in ["true", "1", "yes"]
        self.fact_checking_threshold = float(
            os.getenv("FACT_CHECKING_THRESHOLD", "0.6")
        )

        # Cấu hình confidence threshold cho kết quả
        self.enable_confidence_check = os.getenv(
            "ENABLE_CONFIDENCE_CHECK", "True"
        ).lower() in ["true", "1", "yes"]
        self.confidence_threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))

        # Cài đặt cơ chế xử lý song song
        self.max_workers = int(os.getenv("MAX_PARALLEL_WORKERS", "4"))

    def load_documents(self, data_dir: str) -> List[Dict]:
        """Tải tài liệu từ thư mục"""
        return self.document_processor.load_documents(data_dir)

    def process_documents(self, documents: List[Dict]) -> List[Dict]:
        """Xử lý và chia nhỏ tài liệu với xử lý song song"""
        # Xử lý song song nếu có nhiều tài liệu
        if len(documents) > 5:  # Chỉ xử lý song song khi có nhiều tài liệu
            print(
                f"Xử lý song song {len(documents)} tài liệu với {self.max_workers} workers"
            )
            chunks = []

            # Sử dụng ThreadPoolExecutor để xử lý song song
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_workers
            ) as executor:
                # Submit tác vụ xử lý cho từng tài liệu
                future_to_doc = {
                    executor.submit(self._process_single_document, doc): i
                    for i, doc in enumerate(documents)
                }

                # Thu thập kết quả khi hoàn thành
                for future in concurrent.futures.as_completed(future_to_doc):
                    doc_index = future_to_doc[future]
                    try:
                        result = future.result()
                        chunks.extend(result)
                        print(
                            f"Đã xử lý xong tài liệu {doc_index+1}/{len(documents)}: {len(result)} chunks"
                        )
                    except Exception as e:
                        print(
                            f"Lỗi khi xử lý tài liệu {doc_index+1}/{len(documents)}: {str(e)}"
                        )

            return chunks
        else:
            # Xử lý tuần tự cho ít tài liệu
            return self.document_processor.process_documents(documents)

    def _process_single_document(self, document: Dict) -> List[Dict]:
        """Xử lý một tài liệu đơn lẻ"""
        return self.document_processor.process_documents([document])

    def index_to_qdrant(self, chunks: List[Dict], user_id) -> None:
        """Index dữ liệu lên Qdrant với xử lý song song cho embedding"""
        # Sử dụng user_id được truyền vào
        if not user_id:
            raise ValueError(
                "user_id là bắt buộc để xác định collection cho từng người dùng"
            )

        current_user_id = user_id

        # Xử lý embedding song song theo batches
        texts = [chunk["text"] for chunk in chunks]
        batch_size = 32  # Số lượng văn bản xử lý trong mỗi batch

        print(f"Tính embedding cho {len(texts)} chunks với batch_size={batch_size}...")

        try:
            embeddings = self.embedding_model.encode(
                texts, batch_size=batch_size, show_progress=True
            )
            print(
                f"Đã hoàn thành embedding, shape: {embeddings.shape if hasattr(embeddings, 'shape') else 'unknown'}"
            )
        except Exception as e:
            print(f"Lỗi khi tạo embeddings: {str(e)}")
            print("Thử tạo embeddings lại với các tham số khác...")
            try:
                # Thử lại với batch nhỏ hơn
                batch_size = 16
                embeddings = self.embedding_model.encode(
                    texts, batch_size=batch_size, show_progress=True
                )
            except Exception as e2:
                print(f"Vẫn lỗi khi tạo embeddings lần 2: {str(e2)}")
                raise ValueError(
                    f"Không thể tạo embeddings cho các texts đã cung cấp: {str(e2)}"
                )

        print(
            f"Đã hoàn thành embedding, đang index lên Qdrant cho user_id={current_user_id}..."
        )

        # Chuyển danh sách embeddings thành danh sách các vector
        if hasattr(embeddings, "tolist"):
            # Nếu embeddings là một mảng NumPy
            embeddings_list = embeddings.tolist()
        elif isinstance(embeddings, list):
            # Nếu embeddings đã là một danh sách
            embeddings_list = embeddings
        else:
            print(f"Loại embeddings không rõ: {type(embeddings)}")
            # Cố gắng chuyển đổi sang danh sách nếu có thể
            try:
                embeddings_list = list(embeddings)
            except:
                raise ValueError(
                    f"Không thể chuyển đổi embeddings sang danh sách, loại: {type(embeddings)}"
                )

        self.vector_store.index_documents(
            chunks, embeddings_list, user_id=current_user_id
        )

    def semantic_search(
        self,
        query: str,
        k: int = 5,
        sources: List[str] = None,
        file_id: List[str] = None,
    ) -> List[Dict]:
        """
        Tìm kiếm ngữ nghĩa (semantic search) dựa trên embeddings

        Args:
            query: Câu hỏi người dùng
            k: Số lượng kết quả trả về
            sources: Danh sách các file nguồn cần tìm kiếm (cách cũ)
            file_id: Danh sách các file_id cần tìm kiếm (cách mới). Nếu là None, sẽ tìm kiếm trong tất cả các file

        Returns:
            Danh sách các kết quả tìm kiếm
        """
        # Embed câu truy vấn
        query_embedding = self.embedding_model.get_embedding(query)
        
        # Tìm kiếm trong vector store với filter theo nguồn hoặc file_id
        results = self.vector_store.search_with_filter(
            query_embedding, sources, file_id, limit=k
        )
        
        return results

    def _hybrid_search_task(self, query_to_use, k, alpha, sources, file_id, results):
        """Task chạy song song để thực hiện hybrid search"""
        try:
            # Hybrid search cần cả tìm kiếm ngữ nghĩa và từ khóa
            print(f"=== BM25 DEBUG === Bắt đầu hybrid_search với query: '{query_to_use}'")
            
            # Kiểm tra user_id trong SearchManager.vector_store
            sm_user_id = self.search_manager.vector_store.user_id if hasattr(self.search_manager.vector_store, 'user_id') else "N/A"
            print(f"=== BM25 DEBUG === SearchManager.vector_store.user_id TRƯỚC KHI TÌM KIẾM: {sm_user_id}")
            vs_user_id = self.vector_store.user_id if hasattr(self.vector_store, 'user_id') else "N/A"
            print(f"=== BM25 DEBUG === self.vector_store.user_id: {vs_user_id}")
            
            keyword_results = self.search_manager.keyword_search(
                query_to_use, k=k, sources=sources, file_id=file_id
            )
            
            # Ghi log số lượng kết quả từ BM25
            print(f"=== BM25 DEBUG === Số kết quả từ BM25: {len(keyword_results)}")
            if not keyword_results:
                print("Không tìm thấy kết quả với BM25, quay lại tìm kiếm ngữ nghĩa")
                # Không có kết quả từ tìm kiếm keyword, chỉ dùng tìm kiếm ngữ nghĩa
                semantic_results = self.search_manager.semantic_search(
                    query_to_use, k=k, sources=sources, file_id=file_id
                )
                results["semantic"] = semantic_results
                results["keyword"] = []  # Danh sách rỗng vẫn được lưu để biết BM25 đã được thử
                return
                
            # Cũng thực hiện tìm kiếm ngữ nghĩa
            semantic_results = self.search_manager.semantic_search(
                query_to_use, k=k, sources=sources, file_id=file_id
            )
            
            # Lưu kết quả vào biến chung
            results["keyword"] = keyword_results
            results["semantic"] = semantic_results
        except Exception as e:
            print(f"Lỗi trong hybrid_search: {str(e)}")
            # Fallback to just semantic search
            results["semantic"] = self.search_manager.semantic_search(
                query_to_use, k=k, sources=sources, file_id=file_id
            )
            results["keyword"] = []

    def hybrid_search(
        self,
        query: str,
        k: int = 15,
        alpha: float = None,
        sources: List[str] = None,
        file_id: List[str] = None,
    ) -> List[Dict]:
        """
        Tìm kiếm hybrid kết hợp cả keyword và semantic search

        Args:
            query: Câu hỏi người dùng
            k: Số lượng kết quả trả về
            alpha: Hệ số kết hợp giữa semantic và keyword search (0.7 = 70% semantic + 30% keyword)
            sources: Danh sách các file nguồn cần tìm kiếm (cách cũ, sử dụng file_id thay thế)
            file_id: Danh sách các file_id cần tìm kiếm (cách mới). Nếu là None, sẽ tìm kiếm trong tất cả các file

        Returns:
            Danh sách các kết quả tìm kiếm
        """
        if alpha is None:
            alpha = self.default_alpha  # Sử dụng alpha mặc định nếu không được chỉ định

        print(f"Đang thực hiện tìm kiếm hybrid với alpha={alpha}")
        
        if file_id is None or len(file_id) == 0:
            print("file_id là None hoặc danh sách rỗng. Sẽ tìm kiếm trong tất cả các tài liệu.")
        else:
            print(f"Tìm kiếm với file_id: {file_id}")

        # Tạo một dictionary để lưu kết quả từ các phương pháp tìm kiếm
        results = {}

        # Tăng số lượng kết quả tìm kiếm đầu vào để có nhiều hơn cho reranking
        initial_k = max(10, k * 2)  # Giảm từ k * 3 xuống k * 2

        # Thực hiện song song tìm kiếm bằng ThreadPoolExecutor thay vì asyncio
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            # Thực hiện hybrid search trong một luồng riêng biệt
            executor.submit(
                self._hybrid_search_task, 
                query, 
                initial_k, 
                alpha, 
                sources, 
                file_id, 
                results
            )
            
        # Lấy kết quả từ biến chung
        semantic = results["semantic"] or []
        keyword = results["keyword"] or []

        print(f"Đã tìm được {len(semantic)} kết quả từ semantic search")
        print(f"Đã tìm được {len(keyword)} kết quả từ keyword search")

        combined = {}
        for res in semantic:
            combined[res["text"]] = {**res, "score": alpha * res["score"]}

        for res in keyword:
            if res["text"] in combined:
                combined[res["text"]]["score"] += (1 - alpha) * res["score"]
                text_preview = (
                    res["text"][:50] + "..." if len(res["text"]) > 50 else res["text"]
                )
                print(f"Đã kết hợp kết quả trùng lặp: {text_preview}")
            else:
                combined[res["text"]] = {**res, "score": (1 - alpha) * res["score"]}

        sorted_results = sorted(
            combined.values(), key=lambda x: x["score"], reverse=True
        )

        # Lấy nhiều kết quả hơn để reranking nhưng ít hơn so với trước
        results_for_reranking = sorted_results[: min(len(sorted_results), initial_k)]

        # Tái xếp hạng để lấy kết quả phù hợp nhất
        if results_for_reranking:
            print(f"Đang rerank {len(results_for_reranking)} kết quả kết hợp...")
            # Rerank để tăng độ chính xác
            reranked_results = self.search_manager.rerank_results(
                query, results_for_reranking
            )

            # Thêm thông tin về tổng số kết quả được rerank
            for result in reranked_results:
                result["total_reranked"] = len(results_for_reranking)

            # Giới hạn số lượng kết quả trả về
            final_results = reranked_results[:k]
            print(f"Đã chọn {len(final_results)} kết quả tốt nhất sau reranking")
        else:
            final_results = []

        print(
            f"=== Kết thúc hybrid search: {len(final_results)}/{len(combined)} kết quả ==="
        )

        return final_results

    def rerank_results(self, query: str, results: List[Dict]) -> List[Dict]:
        """Tái xếp hạng kết quả"""
        return self.search_manager.rerank_results(query, results)

    def query_with_sources(
        self,
        query: str,
        search_type: str = "hybrid",
        alpha: float = None,
        sources: List[str] = None,
        conversation_history: str = None,
    ) -> Dict:
        """Tạo câu trả lời kèm theo thông tin nguồn tham khảo"""
        # Sử dụng alpha mặc định nếu không được chỉ định
        if alpha is None:
            alpha = self.default_alpha

        start_time = time.time()

        # Lưu lại câu hỏi gốc
        original_query = query

        # Mở rộng câu hỏi nếu có lịch sử hội thoại và đối tượng query_processor
        if conversation_history and self.query_processor:
            query = self.query_processor.expand_query(query, conversation_history)
            print(f"Đã mở rộng câu hỏi: '{original_query}' -> '{query}'")

        # Phân loại câu hỏi bằng QueryRouter
        query_type = self.query_router.classify_query(query)
        print(f"Phân loại ban đầu: '{query_type}'")

        # Nếu là other_question, trả về ngay
        if query_type == "other_question":
            return {
                "answer": "Vì mình là Chatbot chỉ hỗ trợ và phản hồi trong lĩnh vực cơ sở dữ liệu thôi.",
                "sources": [],
                "question": original_query,
                "search_method": "none",
                "expanded_query": query if query != original_query else None,
                "query_type": "other_question",
            }
            
        # Xử lý sql_code_task trực tiếp với LLM
        elif query_type == "sql_code_task":
            print(f"Câu hỏi được phân loại là sql_code_task: '{query}'")
            prompt_template = self.prompt_manager.templates.get("sql_code_task_prompt")
            if not prompt_template:
                # Fallback hoặc báo lỗi nếu template không tồn tại
                return {
                    "answer": "Lỗi: Không tìm thấy prompt template cho SQL code task.",
                    "sources": [],
                    "question": original_query,
                    "search_method": "none",
                    "expanded_query": query if query != original_query else None,
                    "query_type": "sql_code_task_error",
                }

            # Chuẩn bị ngữ cảnh hội thoại nếu có
            conversation_context_str = ""
            if conversation_history and conversation_history.strip():
                conversation_context_str = f"NGỮ CẢNH CUỘC HỘI THOẠI:\n{conversation_history.strip()}\n"
                
            # Format prompt với query và conversation context
            final_prompt = prompt_template.format(
                query=query,
                conversation_context=conversation_context_str
            )

            # Gọi LLM để xử lý yêu cầu SQL
            response = self.llm.invoke(final_prompt)
            answer_content = response.content

            end_time = time.time()
            total_time = end_time - start_time
            print(f"Tổng thời gian trả lời cho SQL task: {total_time:.2f}s")

            return {
                "answer": answer_content,
                "sources": [], # Không có sources từ RAG cho loại này
                "question": original_query,
                "expanded_query": query if query != original_query else None,
                "search_method": "llm_direct_sql", # Phương thức mới
                "query_type": "sql_code_task",
                "confidence_score": 1.0, # Mặc định là 1.0 vì LLM trực tiếp xử lý
                "is_low_confidence": False,
            }

        # Xử lý realtime_question với Google Agent Search
        if query_type == "realtime_question":
            print(f"Câu hỏi được phân loại là realtime, sử dụng Google Agent Search cho: '{query}'")
            try:
                gas_summary, gas_urls = google_agent_search(query)
                
                # Tạo một document từ kết quả Google Agent Search để đưa vào LLM
                summary_content = gas_summary.content if hasattr(gas_summary, 'content') else str(gas_summary)
                print(f"Google Agent Search tìm thấy: {summary_content[:100]}...")
                
                # Tạo một danh sách retrieved chỉ chứa kết quả từ Google Agent Search
                retrieved = [{
                    "text": summary_content,
                    "metadata": {
                        "source": "Google Agent Search",
                        "page": "Web Result",
                        "source_type": "web_search",
                        "urls": gas_urls
                    },
                    "score": 1.0, # Điểm cao cho nguồn từ GAS
                    "rerank_score": 1.0
                }]
                
                # Xác định loại câu hỏi
                question_type = self.prompt_manager.classify_question(query)
                
                # Tạo prompt phù hợp, bổ sung lịch sử hội thoại nếu có
                if conversation_history:
                    prompt = self.prompt_manager.create_prompt_with_history(
                        query, retrieved, question_type, conversation_history
                    )
                else:
                    prompt = self.prompt_manager.create_prompt(query, retrieved, question_type)
                
                # Gọi LLM để tạo câu trả lời
                response = self.llm.invoke(prompt)
                answer_content = response.content
                
                # Chuẩn bị phần thông tin về nguồn tham khảo
                gas_sources_info = []
                if gas_urls:
                    for url in gas_urls:
                        gas_sources_info.append({
                            "source": url,  # Sử dụng URL làm nguồn trực tiếp
                            "page": "Web Search",
                            "original_page": url,
                            "section": "N/A",
                            "content_snippet": "Thông tin từ Google Agent Search.",
                            "score": 1.0, # Điểm cao cho nguồn từ GAS
                            "rerank_score": 1.0,
                            "metadata_boost": 0.0,
                            "special_metadata": {"is_web_search": True}
                        })
                
                return {
                    "answer": answer_content,
                    "sources": gas_sources_info,
                    "question": original_query,
                    "search_method": "google_agent_search",
                    "expanded_query": query if query != original_query else None,
                    "query_type": "realtime_question",
                }
            except Exception as e:
                print(f"Lỗi khi sử dụng Google Agent Search: {str(e)}")
                # Nếu có lỗi, tiếp tục với phương pháp tìm kiếm thông thường
                print("Chuyển sang phương pháp tìm kiếm thông thường")

        # Tăng số lượng kết quả ban đầu để có nhiều hơn cho reranking
        search_k = 15

        # Xác định loại tìm kiếm
        if search_type == "semantic":
            retrieved = self.semantic_search(query, k=search_k, sources=sources)
        elif search_type == "keyword":
            retrieved = self.search_manager.keyword_search(
                query, k=search_k, sources=sources
            )
        else:
            retrieved = self.hybrid_search(
                query, k=search_k, alpha=alpha, sources=sources
            )

        # Kiểm tra độ tin cậy của kết quả RAG ban đầu
        is_low_confidence_rag = False
        if self.enable_confidence_check and retrieved:
            top_score_rag = retrieved[0].get("rerank_score", 0)
            if top_score_rag < self.confidence_threshold:
                is_low_confidence_rag = True
                print(f"Kết quả RAG có độ tin cậy thấp (score: {top_score_rag:.2f}). Sẽ thử fallback với Google Agent Search.")

        # Fallback mechanism: nếu không có kết quả RAG hoặc độ tin cậy thấp
        perform_fallback = not retrieved or is_low_confidence_rag
        
        gas_fallback_used = False
        if perform_fallback:
            print(f"Không có kết quả RAG đáng tin cậy. Thực hiện fallback với Google Agent Search cho: '{query}'")
            try:
                fallback_summary, fallback_urls = google_agent_search(query)
                
                if fallback_summary and (hasattr(fallback_summary, 'content') and fallback_summary.content != "Không tìm thấy thông tin liên quan đến truy vấn này." or not hasattr(fallback_summary, 'content') and fallback_summary != "Không tìm thấy thông tin liên quan đến truy vấn này."):
                    gas_fallback_used = True
                    summary_content = fallback_summary.content if hasattr(fallback_summary, 'content') else str(fallback_summary)
                    print(f"Google Agent Search tìm thấy: {summary_content[:100]}...")
                    fallback_doc = {
                        "text": summary_content,
                        "metadata": {
                            "source": "Google Agent Search",
                            "page": "Web Result",
                            "source_type": "web_search",
                            "urls": fallback_urls
                        },
                        "score": 0.9,
                        "rerank_score": 0.9,
                        "file_id": "web_search_fallback"
                    }
                    # Thêm kết quả fallback vào đầu danh sách retrieved
                    if not retrieved:
                        retrieved = [fallback_doc]
                    else:
                        retrieved.insert(0, fallback_doc)
                else:
                    print("Google Agent Search không tìm thấy kết quả fallback.")
            except Exception as e:
                print(f"Lỗi khi sử dụng Google Agent Search fallback: {str(e)}")
                # Tiếp tục với kết quả hiện tại

        # Phân loại lại câu hỏi
        final_query_type = self.query_router.classify_query(query)
        print(f"Phân loại cuối cùng: '{final_query_type}'")

        # Nếu là realtime_question, trả về ngay
        if final_query_type == "realtime_question" and not gas_fallback_used:
            return {
                "answer": self.query_router.prepare_realtime_response(query),
                "sources": [],
                "question": original_query,
                "search_method": search_type,
                "expanded_query": query if query != original_query else None,
                "query_type": "realtime_question",
            }

        # Nếu là other_question, trả về ngay
        if final_query_type == "other_question":
            return {
                "answer": "Vì mình là Chatbot chỉ hỗ trợ và phản hồi trong lĩnh vực cơ sở dữ liệu thôi.",
                "sources": [],
                "question": original_query,
                "search_method": search_type,
                "expanded_query": query if query != original_query else None,
                "query_type": "other_question",
            }

        # Nếu không có kết quả tìm kiếm
        if not retrieved:
            return {
                "answer": "Không tìm thấy thông tin liên quan đến câu hỏi này trong cơ sở dữ liệu hoặc từ tìm kiếm mở rộng.",
                "sources": [],
                "question": original_query,
                "search_method": search_type + ("+gas_fallback" if gas_fallback_used else ""),
                "expanded_query": query if query != original_query else None,
                "query_type": "question_from_document",
            }

        # Lưu thông tin về số lượng kết quả được rerank
        total_reranked = 0
        for result in retrieved:
            if "total_reranked" in result:
                total_reranked = max(total_reranked, result["total_reranked"])

        if total_reranked == 0:
            total_reranked = len(retrieved)

        # Chỉ rerank nếu không phải hybrid search (đã được rerank)
        if search_type != "hybrid":
            # Tái xếp hạng kết quả
            retrieved = self.rerank_results(query, retrieved)
            # Giới hạn số lượng kết quả
            retrieved = retrieved[:10]

        # Kiểm tra độ tin cậy của kết quả
        is_low_confidence = False
        confidence_message = ""
        if self.enable_confidence_check and retrieved:
            # Lấy rerank_score cao nhất của kết quả đầu tiên
            top_score = retrieved[0].get("rerank_score", 0)
            print(
                f"Top rerank_score: {top_score}, Threshold: {self.confidence_threshold}"
            )

            if top_score < self.confidence_threshold:
                is_low_confidence = True
                confidence_message = (
                    f"\n\n**Lưu ý**: Độ tin cậy của câu trả lời này thấp "
                    f"(điểm {top_score:.2f} < ngưỡng {self.confidence_threshold:.2f}). "
                    f"Thông tin có thể không đầy đủ hoặc không chính xác hoàn toàn. "
                    f"Vui lòng kiểm tra thêm thông tin từ các nguồn tham khảo."
                )

        # Xác định loại câu hỏi
        question_type = self.prompt_manager.classify_question(query)

        # Tạo prompt phù hợp, bổ sung lịch sử hội thoại nếu có
        if conversation_history:
            prompt = self.prompt_manager.create_prompt_with_history(
                query, retrieved, question_type, conversation_history
            )
        else:
            prompt = self.prompt_manager.create_prompt(query, retrieved, question_type)

        # Gọi LLM để tạo câu trả lời
        response = self.llm.invoke(prompt)
        answer_content = response.content

        # Thêm cảnh báo độ tin cậy thấp nếu cần
        if is_low_confidence:
            answer_content += confidence_message

        # Chuẩn bị phần thông tin về nguồn tham khảo
        sources_info = []
        for idx, doc in enumerate(retrieved[:10]):  # Giới hạn hiển thị 10 nguồn
            # Lấy metadata
            metadata = doc.get("metadata", {})
            
            # Kiểm tra nếu đây là nguồn từ Google Agent Search
            if metadata.get("source_type") == "web_search":
                # Xử lý nguồn từ GAS
                urls_from_gas = metadata.get("urls", [])
                snippet = doc["text"]
                if urls_from_gas:
                    snippet += "\n\nNguồn tham khảo từ web:\n" + "\n".join([f"- {url}" for url in urls_from_gas])
                
                sources_info.append({
                    "source": "Google Agent Search",
                    "page": "Web Search Result",
                    "section": "Web Content",
                    "score": doc.get("score", 0.9),
                    "content_snippet": snippet,
                    "file_id": doc.get("file_id", "web_search"),
                    "is_web_search": True
                })
            else:
                # Nguồn từ RAG thông thường
                source = metadata.get("source", "unknown")
                
                # Ưu tiên sử dụng page_label nếu có
                page = metadata.get("page_label", metadata.get("page", "N/A"))
                page_label = metadata.get("page_label", "")
                section = metadata.get("section", "N/A")
                result_file_id = doc.get("file_id", "unknown")  # Lấy file_id từ kết quả

                # Tạo snippet từ nội dung
                content = doc["text"]
                snippet = content

                # Thêm vào danh sách nguồn
                sources_info.append(
                    {
                        "source": source,
                        "page": page,
                        "page_label": page_label,  # Thêm page_label vào sources
                        "section": section,
                        "score": doc.get("score", 0.0),
                        "content_snippet": snippet,
                        "file_id": result_file_id,
                        "is_web_search": False,
                        "source_filename": os.path.basename(source) if os.path.sep in source else source,  # Thêm tên file không có đường dẫn
                    }
                )

        end_time = time.time()
        total_time = end_time - start_time
        print(f"Tổng thời gian trả lời: {total_time:.2f}s")

        return {
            "answer": answer_content,
            "sources": sources_info,
            "question": original_query,  # Trả về câu hỏi gốc
            "expanded_query": (
                query if query != original_query else None
            ),  # Thêm thông tin query đã expand
            "search_method": search_type,
            "total_reranked": total_reranked,  # Thêm tổng số kết quả được rerank
            "filtered_sources": sources,
            "is_low_confidence": is_low_confidence,  # Thêm trạng thái độ tin cậy thấp
            "confidence_score": (
                retrieved[0].get("rerank_score", 0) if retrieved else 0
            ),  # Thêm điểm tin cậy
            "query_type": final_query_type,
        }

    async def query_with_sources_streaming(
        self,
        query: str,
        search_type: str = "hybrid",
        alpha: float = None,
        k: int = 15,
        sources: List[str] = None,
        file_id: List[str] = None,
        conversation_history: str = None,
    ) -> AsyncGenerator[Dict, None]:
        """
        Truy vấn hệ thống RAG với các nguồn và trả về kết quả dưới dạng stream

        Args:
            query: Câu hỏi người dùng
            search_type: Loại tìm kiếm ("semantic", "keyword", "hybrid")
            alpha: Hệ số kết hợp giữa semantic và keyword search
            k: Số lượng kết quả trả về
            sources: Danh sách các file nguồn cần tìm kiếm (cách cũ, sử dụng file_id thay thế)
            file_id: Danh sách các file_id cần tìm kiếm (cách mới). Nếu là None, sẽ tìm kiếm trong tất cả các file
            conversation_history: Lịch sử hội thoại

        Returns:
            AsyncGenerator trả về từng phần của câu trả lời
        """
        print(f"Đang xử lý câu hỏi (stream): '{query}'")
        print(f"Phương pháp tìm kiếm: {search_type}")
        print(f"Alpha: {alpha if alpha is not None else self.default_alpha}")
        
        if file_id is None or len(file_id) == 0:
            print("file_id là None hoặc danh sách rỗng. Sẽ tìm kiếm trong tất cả các tài liệu.")
        else:
            print(f"Tìm kiếm với file_id: {file_id}")

        # Bắt đầu đo thời gian xử lý
        start_time = time.time()

        # Xử lý query với QueryProcessor nếu có conversation_history
        original_query = query  # Lưu lại câu hỏi gốc
        query_to_use = query
        
        if conversation_history and len(conversation_history.strip()) > 0:
            print(f"Lịch sử hội thoại: {conversation_history[:100]}...")
            expanded_query = self.query_processor.expand_query(
                query, conversation_history
            )
            print(f"Câu hỏi ban đầu: {query}")
            print(f"Câu hỏi mở rộng: {expanded_query}")
            query_to_use = expanded_query
        else:
            query_to_use = query

        # Phân loại câu hỏi bằng QueryRouter
        query_type = self.query_router.classify_query(query_to_use)
        print(f"Loại câu hỏi: {query_type}")

        # Trả về ngay nếu là câu hỏi không liên quan đến cơ sở dữ liệu
        if query_type == "other_question":
            # Trả về thông báo bắt đầu
            yield {
                "type": "start",
                "data": {
                    "query_type": query_type,
                    "search_type": search_type,
                    "alpha": alpha if alpha is not None else self.default_alpha,
                    "file_id": file_id
                },
            }

            # Trả về nguồn rỗng
            yield {
                "type": "sources",
                "data": {
                    "sources": [],
                    "filtered_sources": [],
                    "filtered_file_id": file_id if file_id else [],
                },
            }

            # Trả về nội dung
            response = self.query_router.get_response_for_other_question(query)
            yield {"type": "content", "data": {"content": response}}

            # Trả về kết thúc
            elapsed_time = time.time() - start_time
            yield {
                "type": "end",
                "data": {
                    "processing_time": round(elapsed_time, 2),
                    "query_type": query_type,
                },
            }
            return
            
        # Xử lý sql_code_task trực tiếp với LLM (streaming)
        elif query_type == "sql_code_task":
            print(f"Câu hỏi được phân loại là sql_code_task (stream): '{query_to_use}'")
            yield {
                "type": "start",
                "data": {
                    "query": original_query,
                    "expanded_query": query_to_use if query_to_use != original_query else None,
                    "query_type": "sql_code_task",
                    "search_type": "llm_direct_sql",
                    "file_id": file_id,
                },
            }

            yield {
                "type": "sources",
                "data": {"sources": [], "filtered_file_id": file_id if file_id else []},
            }
            
            prompt_template = self.prompt_manager.templates.get("sql_code_task_prompt")
            if not prompt_template:
                yield {"type": "content", "data": {"content": "Lỗi: Không tìm thấy prompt template cho SQL code task."}}
            else:
                # Chuẩn bị ngữ cảnh hội thoại nếu có
                conversation_context_str = ""
                if conversation_history and conversation_history.strip():
                    conversation_context_str = f"NGỮ CẢNH CUỘC HỘI THOẠI:\n{conversation_history.strip()}\n"
                
                # Format prompt với query và conversation context
                final_prompt = prompt_template.format(
                    query=query_to_use,
                    conversation_context=conversation_context_str
                )
                
                try:
                    async for content_chunk in self.llm.stream(final_prompt):
                        yield {"type": "content", "data": {"content": content_chunk}}
                except Exception as e:
                    print(f"Lỗi khi gọi LLM stream cho sql_code_task: {str(e)}")
                    yield {
                        "type": "content",
                        "data": {
                            "content": f"Xin lỗi, có lỗi xảy ra khi xử lý yêu cầu SQL của bạn: {str(e)}"
                        },
                    }
            
            elapsed_time = time.time() - start_time
            yield {
                "type": "end",
                "data": {
                    "processing_time": round(elapsed_time, 2),
                    "query_type": "sql_code_task",
                },
            }
            return

        # Trả về ngay nếu là câu hỏi thời gian thực
        if query_type == "realtime_question":
            # Trả về thông báo bắt đầu
            yield {
                "type": "start",
                "data": {
                    "query_type": query_type,
                    "search_type": "google_agent_search",
                    "alpha": alpha if alpha is not None else self.default_alpha,
                    "file_id": file_id,
                },
            }

            # Sử dụng Google Agent Search để tìm kiếm
            try:
                gas_summary, gas_urls = google_agent_search(query_to_use)
                
                # Tạo document từ kết quả Google Agent Search
                gas_content = gas_summary.content if hasattr(gas_summary, 'content') else str(gas_summary)
                
                # Tạo một danh sách retrieved chỉ chứa kết quả từ Google Agent Search
                retrieved = [{
                    "text": gas_content,
                    "metadata": {
                        "source": "Google Agent Search",
                        "page": "Web Result",
                        "source_type": "web_search",
                        "urls": gas_urls
                    },
                    "score": 1.0,
                    "rerank_score": 1.0
                }]
                
                # Chuẩn bị danh sách nguồn từ Google Agent Search
                gas_sources_list = []
                if gas_urls:
                    for url_idx, url in enumerate(gas_urls):
                        gas_sources_list.append({
                            "source": url,  # Sử dụng URL trực tiếp làm nguồn
                            "page": "Web Search",
                            "section": f"Web Source {url_idx+1}",
                            "score": 1.0,
                            "content_snippet": f"Thông tin từ web: {url}",
                            "file_id": "web_search",
                            "is_web_search": True
                        })
                
                # Trả về nguồn
                yield {
                    "type": "sources",
                    "data": {
                        "sources": gas_sources_list,
                        "filtered_sources": [],
                        "filtered_file_id": file_id if file_id else [],
                    },
                }

                # Chuẩn bị prompt cho LLM với kết quả từ Google Agent Search
                prompt = self.prompt_manager.create_prompt_with_history(
                    query_to_use, retrieved, conversation_history=conversation_history
                )

                # Gọi LLM để trả lời dưới dạng stream
                try:
                    async for content in self.llm.stream(prompt):
                        yield {"type": "content", "data": {"content": content}}
                except Exception as e:
                    print(f"Lỗi khi gọi LLM stream cho realtime_question: {str(e)}")
                    # Trả về lỗi
                    yield {
                        "type": "content",
                        "data": {
                            "content": f"Xin lỗi, có lỗi xảy ra khi xử lý câu hỏi thời gian thực: {str(e)}"
                        },
                    }
            except Exception as e:
                print(f"Lỗi khi sử dụng Google Agent Search (stream): {str(e)}")
                # Trả về nguồn rỗng
                yield {
                    "type": "sources",
                    "data": {
                        "sources": [],
                        "filtered_sources": [],
                        "filtered_file_id": file_id if file_id else [],
                    },
                }
                # Trả về thông báo lỗi
                yield {"type": "content", "data": {"content": f"Không thể sử dụng Google Agent Search: {str(e)}. Vui lòng kiểm tra lại API key hoặc cấu hình."}}

            # Trả về kết thúc
            elapsed_time = time.time() - start_time
            yield {
                "type": "end",
                "data": {
                    "processing_time": round(elapsed_time, 2),
                    "query_type": query_type,
                },
            }
            return

        # Tìm kiếm dựa trên loại tìm kiếm được chỉ định
        if search_type == "semantic":
            search_results = self.semantic_search(
                query_to_use, k=k, sources=sources, file_id=file_id
            )
        elif search_type == "keyword":
            search_results = self.search_manager.keyword_search(
                query_to_use, k=k, sources=sources, file_id=file_id
            )
        else:  # hybrid
            # Sử dụng hybrid_search đồng bộ, không còn gây lỗi asyncio.run
            search_results = self.hybrid_search(
                query_to_use,
                k=k,
                alpha=alpha if alpha is not None else self.default_alpha,
                sources=sources,
                file_id=file_id,
            )
            
        # Fallback mechanism cho streaming
        perform_fallback_stream = not search_results or len(search_results) == 0
        gas_fallback_used = False
        
        if perform_fallback_stream:
            print(f"Không có kết quả RAG (stream). Thực hiện fallback với Google Agent Search cho: '{query_to_use}'")
            try:
                # Khởi tạo sources_list trước khi sử dụng
                sources_list = []
                fallback_summary, fallback_urls = google_agent_search(query_to_use)
                fallback_content = fallback_summary.content if hasattr(fallback_summary, 'content') else str(fallback_summary)
                
                if fallback_content and fallback_content != "Không tìm thấy thông tin liên quan đến truy vấn này.":
                    gas_fallback_used = True
                    print(f"Đã tìm thấy kết quả fallback: {fallback_content[:100]}...")
                    
                    # Tạo một doc giả cho fallback để đưa vào context LLM
                    fallback_doc = {
                        "text": fallback_content,
                        "metadata": {
                            "source": "Google Agent Search",
                            "page": "Web Result",
                            "source_type": "web_search",
                            "urls": fallback_urls
                        },
                        "score": 0.9,
                        "rerank_score": 0.9,
                        "file_id": "web_search_fallback"
                    }
                    
                    # Thêm vào search_results
                    search_results = [fallback_doc]
                    
                    # Cập nhật danh sách nguồn với kết quả fallback
                    for url_idx, url in enumerate(fallback_urls):
                        sources_list.append({
                            "source": url,  # Sử dụng URL trực tiếp làm nguồn
                            "page": "Web Search",
                            "section": f"Fallback Source {url_idx+1}",
                            "score": 0.9,
                            "content_snippet": f"Thông tin bổ sung từ web: {url}",
                            "file_id": "web_search_fallback",
                            "is_web_search": True
                        })
                else:
                    print("Google Agent Search không tìm thấy kết quả fallback.")
            except Exception as e:
                print(f"Lỗi khi thực hiện fallback với Google Agent Search: {str(e)}")
                # Tiếp tục với kết quả hiện tại

        # Nếu không có kết quả tìm kiếm, trả về thông báo không tìm thấy
        if not search_results or len(search_results) == 0:
            # Trả về thông báo bắt đầu
            yield {
                "type": "start",
                "data": {
                    "query_type": "no_results",
                    "search_type": search_type,
                    "alpha": alpha if alpha is not None else self.default_alpha,
                    "file_id": file_id,
                },
            }

            # Trả về nguồn rỗng
            yield {
                "type": "sources",
                "data": {
                    "sources": [],
                    "filtered_sources": [],
                    "filtered_file_id": file_id if file_id else [],
                },
            }

            # Trả về nội dung
            response = "Không tìm thấy thông tin liên quan đến câu hỏi của bạn trong tài liệu. Vui lòng thử lại với câu hỏi khác hoặc điều chỉnh từ khóa tìm kiếm."
            yield {"type": "content", "data": {"content": response}}

            # Trả về kết thúc
            elapsed_time = time.time() - start_time
            yield {
                "type": "end",
                "data": {
                    "processing_time": round(elapsed_time, 2),
                    "query_type": "no_results",
                },
            }
            return
            
        # Rerank kết quả nếu có nhiều hơn 1 kết quả
        if len(search_results) > 1:
            reranked_results = self.search_manager.rerank_results(
                query_to_use, search_results
            )
            # Lấy số lượng kết quả đã rerank
            total_reranked = len(reranked_results)
        else:
            reranked_results = search_results
            total_reranked = 1

        # Chuẩn bị context từ các kết quả đã rerank
        context_docs = []
        for i, result in enumerate(reranked_results[:15]):  
            # Chuẩn bị metadata
            metadata = result.get("metadata", {})
            source = metadata.get("source", "unknown")
            
            # Ưu tiên sử dụng page_label nếu có
            page = metadata.get("page_label", metadata.get("page", "N/A"))
            section = metadata.get("section", "N/A")

            # Thêm vào danh sách context
            context_docs.append(
                {
                    "content": result["text"],
                    "source": source,
                    "page": page,
                    "page_label": metadata.get("page_label", ""),  # Thêm page_label vào context
                    "section": section,
                    "score": result.get("score", 0.0),
                    "metadata": metadata,  # Thêm toàn bộ metadata để sử dụng trong prompt
                }
            )

        # Chuẩn bị danh sách nguồn tham khảo
        sources_list = []
        for i, doc in enumerate(reranked_results):
            # Trích xuất thông tin từ metadata
            metadata = doc.get("metadata", {})
            
            # Kiểm tra nếu là nguồn từ Google Agent Search
            if metadata.get("source_type") == "web_search":
                urls_from_gas = metadata.get("urls", [])
                snippet = doc["text"]
                if urls_from_gas:
                    snippet += "\n\nNguồn tham khảo từ web:\n" + "\n".join([f"- {url}" for url in urls_from_gas])
                
                sources_list.append({
                    "source": "Google Agent Search",
                    "page": "Web Search Result",
                    "section": "Web Content",
                    "score": doc.get("score", 0.9),
                    "content_snippet": snippet,
                    "file_id": doc.get("file_id", "web_search"),
                    "is_web_search": True
                })
            else:
                # Nguồn từ RAG thông thường
                source = metadata.get("source", "unknown")
                
                # Ưu tiên sử dụng page_label nếu có
                page = metadata.get("page_label", metadata.get("page", "N/A"))
                page_label = metadata.get("page_label", "")
                section = metadata.get("section", "N/A")
                result_file_id = doc.get("file_id", "unknown")  # Lấy file_id từ kết quả

                # Tạo snippet từ nội dung
                content = doc["text"]
                snippet = content

                # Thêm vào danh sách nguồn
                sources_list.append(
                    {
                        "source": source,
                        "page": page,
                        "page_label": page_label,  # Thêm page_label vào sources
                        "section": section,
                        "score": doc.get("score", 0.0),
                        "content_snippet": snippet,
                        "file_id": result_file_id,
                        "is_web_search": False,
                        "source_filename": os.path.basename(source) if os.path.sep in source else source,  # Thêm tên file không có đường dẫn
                    }
                )

        # Trả về thông báo bắt đầu
        yield {
            "type": "start",
            "data": {
                "query_type": query_type,
                "search_type": search_type,
                "alpha": alpha if alpha is not None else self.default_alpha,
                "file_id": file_id,
                "total_results": len(search_results),
                "total_reranked": total_reranked,
            },
        }

        # Trả về nguồn tham khảo
        yield {
            "type": "sources",
            "data": {
                "sources": sources_list,
                "filtered_sources": [],  # Giữ trường này để tương thích với code cũ
                "filtered_file_id": file_id if file_id else [],
            },
        }

        # Chuẩn bị prompt cho LLM
        prompt = self.prompt_manager.create_prompt_with_history(
            query_to_use, context_docs, conversation_history=conversation_history
        )

        # Gọi LLM để trả lời
        try:
            # Sử dụng LLM để trả lời dưới dạng stream
            async for content in self.llm.stream(prompt):
                yield {"type": "content", "data": {"content": content}}
        except Exception as e:
            print(f"Lỗi khi gọi LLM stream: {str(e)}")
            # Trả về lỗi
            yield {
                "type": "content",
                "data": {
                    "content": f"Xin lỗi, có lỗi xảy ra khi xử lý câu hỏi: {str(e)}"
                },
            }

        # Kết thúc đo thời gian
        elapsed_time = time.time() - start_time

        # Trả về kết thúc
        yield {
            "type": "end",
            "data": {
                "processing_time": round(elapsed_time, 2),
                "query_type": query_type,
            },
        }

    def generate_response_with_context(
        self, query: str, retrieved: List[Dict], search_type: str = "hybrid"
    ) -> str:
        """Tạo câu trả lời với ngữ cảnh của kết quả tìm kiếm"""
        if not retrieved:
            return "Không tìm thấy thông tin liên quan đến câu hỏi này trong cơ sở dữ liệu."

        # Giới hạn số lượng tài liệu ngữ cảnh
        context_docs = retrieved[:5]

        # Xác định loại câu hỏi
        question_type = self.prompt_manager.classify_question(query)

        # Tạo prompt phù hợp
        prompt = self.prompt_manager.create_prompt(query, context_docs, question_type)


        # Gọi LLM
        response = self.llm.invoke(prompt)

        return response.content

    def delete_collection(self) -> None:
        """Xóa collection"""
        self.vector_store.delete_collection()

    def get_collection_info(self) -> Dict:
        """Lấy thông tin về collection"""
        return self.vector_store.get_collection_info()

    def _generate_answer(self, query, relevant_docs, **kwargs):
        """Phương thức nội bộ để tạo câu trả lời"""
        # Tạo context từ các tài liệu liên quan
        context = "\n---\n".join([doc["text"] for doc in relevant_docs])

        # Tạo prompt với template phù hợp
        prompt = self.prompt_manager.templates["query_with_context"].format(
            context=context, query=query
        ) # Gọi LLM và lấy kết quả
        response = self.llm.invoke(prompt)
        return response.content

    async def generate_related_questions(self, query: str, answer: str) -> List[str]:
        """Tạo danh sách các câu hỏi gợi ý liên quan"""
        try:
            # Tạo prompt cho việc gợi ý câu hỏi
            prompt = self.prompt_manager.create_related_questions_prompt(query, answer)

            # Gọi LLM để tạo câu hỏi gợi ý
            response = self.llm.invoke(prompt)

            # Xử lý kết quả để trích xuất các câu hỏi
            response_text = response.content.strip()

            # Tìm các câu hỏi theo định dạng "1. [câu hỏi]"
            related_questions = []

            # Sử dụng regex để trích xuất câu hỏi
            pattern = r"\d+\.\s*(.*?\?)"
            matches = re.findall(pattern, response_text)

            # Lấy tối đa 3 câu hỏi
            return matches[:3]

        except Exception as e:
            print(f"Lỗi khi tạo câu hỏi liên quan: {str(e)}")
            # Trả về một số câu hỏi mặc định nếu có lỗi
            return [
                "Bạn muốn tìm hiểu thêm điều gì về chủ đề này?",
                "Bạn có thắc mắc nào khác liên quan đến nội dung này không?",
                "Bạn có muốn biết thêm thông tin về ứng dụng thực tế của kiến thức này không?",
            ]
