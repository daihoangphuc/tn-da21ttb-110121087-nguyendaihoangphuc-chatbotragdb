import logging

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

        # Tạo search manager dùng chung
        temp_vector_store = VectorStore()  # Tạm thời tạo để khởi tạo SearchManager
        global_search_manager = SearchManager(temp_vector_store, global_embedding_model)
        print("Đã khởi tạo Search Manager toàn cục (BM25, reranker)")

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
            # Gán search_manager toàn cục nhưng cập nhật vector_store
            self.search_manager = search_manager
            self.search_manager.vector_store = self.vector_store
            print("Sử dụng Search Manager toàn cục (cập nhật vector_store cho user)")
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
        """Tìm kiếm ngữ nghĩa"""
        # Loại bỏ hoàn toàn chức năng mở rộng truy vấn
        return self.search_manager.semantic_search(query, k, sources, file_id)

    def hybrid_search(
        self,
        query: str,
        k: int = 15,
        alpha: float = None,
        sources: List[str] = None,
        file_id: List[str] = None,
    ) -> List[Dict]:
        """Tìm kiếm kết hợp ngữ nghĩa và keyword (ưu tiên ngữ nghĩa nhiều hơn với alpha=0.7)"""
        # Sử dụng alpha mặc định từ biến môi trường nếu không được chỉ định
        if alpha is None:
            alpha = self.default_alpha

        # Nhận biết loại truy vấn để điều chỉnh alpha
        query_lower = query.lower()

        # Phát hiện các truy vấn liên quan đến cú pháp, định nghĩa để tăng trọng số cho keyword search
        is_syntax_or_definition_query = False

        syntax_patterns = [
            r"\b(cú pháp|syntax|format|statement)\b",
            r"\b(SELECT|CREATE|ALTER|DROP|INSERT|UPDATE|DELETE)\b",
            r"\bcách\s+(viết|sử dụng|dùng)\b",
        ]

        definition_patterns = [
            r"\b(định nghĩa|khái niệm|là gì|what is|define)\b",
            r"\bnghĩa của\b",
        ]

        # Kiểm tra các pattern cú pháp
        for pattern in syntax_patterns:
            if re.search(pattern, query_lower):
                is_syntax_or_definition_query = True
                print(f"Phát hiện truy vấn liên quan đến CÚ PHÁP: '{query}'")
                # Giảm alpha để tăng trọng số cho keyword search
                alpha = 0.5  # 50% semantic + 50% keyword
                break

        # Kiểm tra các pattern định nghĩa nếu chưa phát hiện được cú pháp
        if not is_syntax_or_definition_query:
            for pattern in definition_patterns:
                if re.search(pattern, query_lower):
                    is_syntax_or_definition_query = True
                    print(f"Phát hiện truy vấn liên quan đến ĐỊNH NGHĨA: '{query}'")
                    # Giảm alpha một chút để tăng trọng số cho keyword search
                    alpha = 0.6  # 60% semantic + 40% keyword
                    break

        print(f"=== Bắt đầu hybrid search với alpha={alpha} ===")

        # Tăng số lượng kết quả tìm kiếm đầu vào để có nhiều hơn cho reranking
        initial_k = k * 3  # Lấy gấp 3 lần số kết quả cần thiết

        semantic = self.search_manager.semantic_search(
            query, k=initial_k, sources=sources, file_id=file_id
        )
        print(f"Đã tìm được {len(semantic)} kết quả từ semantic search")

        keyword = self.search_manager.keyword_search(
            query, k=initial_k, sources=sources, file_id=file_id
        )
        print(f"Đã tìm được {len(keyword)} kết quả từ keyword search")

        combined = {}
        for res in semantic:
            combined[res["text"]] = {**res, "score": alpha * res["score"]}

        for res in keyword:
            if res["text"] in combined:
                combined[res["text"]]["score"] += (1 - alpha) * res["score"]
                print(f"Đã kết hợp kết quả trùng lặp: {res['text'][:50]}...")
            else:
                combined[res["text"]] = {**res, "score": (1 - alpha) * res["score"]}

        sorted_results = sorted(
            combined.values(), key=lambda x: x["score"], reverse=True
        )

        # Lấy nhiều kết quả hơn để reranking
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

    def generate_response(
        self,
        query: str,
        search_type: str = "hybrid",
        alpha: float = None,
        sources: List[str] = None,
    ) -> str:
        """Tạo câu trả lời dựa trên query"""
        # Sử dụng alpha mặc định nếu không được chỉ định
        if alpha is None:
            alpha = self.default_alpha

        # Xác định loại tìm kiếm
        print(f"=== Bắt đầu tạo câu trả lời cho: '{query}' ===")

        # Tăng k cho tất cả các phương pháp tìm kiếm để có nhiều kết quả cho reranking
        search_k = 20  # Tăng lên 20 để có nhiều kết quả

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

        # Nếu không có kết quả tìm kiếm, trả về thông báo không tìm thấy
        if not retrieved:
            return "Không tìm thấy thông tin liên quan đến câu hỏi này trong cơ sở dữ liệu. Vui lòng thử lại với câu hỏi khác hoặc tải thêm tài liệu vào hệ thống."

        # Lưu thông tin về số lượng kết quả được rerank để báo cáo
        total_reranked = len(retrieved)
        retrieved_before_rerank = retrieved

        # Chỉ rerank nếu không phải kết quả từ hybrid search (đã được rerank)
        if search_type != "hybrid":
            # Tái xếp hạng kết quả
            print(f"Đang rerank {len(retrieved)} kết quả...")
        retrieved = self.rerank_results(query, retrieved)
        # Giới hạn số lượng kết quả sau rerank
        retrieved = retrieved[:10]

        # Xác định loại câu hỏi
        question_type = self.prompt_manager.classify_question(query)
        print(f"Loại câu hỏi được phát hiện: {question_type}")

        # Tạo prompt phù hợp
        prompt = self.prompt_manager.create_prompt(query, retrieved, question_type)

        # Gọi LLM để tạo câu trả lời
        start_time = time.time()
        response = self.llm.invoke(prompt)
        end_time = time.time()
        print(f"Thời gian tạo câu trả lời LLM: {end_time - start_time:.2f}s")

        print(
            f"=== Kết thúc tạo câu trả lời, độ dài: {len(response.content)} ký tự ==="
        )
        return response.content

    def fact_check_response(self, response: str, relevant_docs: List[Dict]) -> Dict:
        """
        Kiểm tra tính chính xác của câu trả lời so với các tài liệu nguồn

        Args:
            response: Câu trả lời được tạo bởi LLM
            relevant_docs: Danh sách các tài liệu liên quan

        Returns:
            Kết quả đánh giá và phiên bản đã sửa (nếu có)
        """
        if not self.enable_fact_checking:
            return {"verified": True, "response": response}

        try:
            print("Đang thực hiện fact checking...")

            # 1. Tách câu trả lời thành các câu riêng biệt để kiểm tra
            sentences = re.split(r"(?<=[.!?])\s+", response)
            sentences = [s.strip() for s in sentences if s.strip()]

            # 2. Tạo văn bản nguồn từ relevant_docs
            source_text = "\n\n".join([doc["text"] for doc in relevant_docs])

            # 3. Chuyển đổi sentences và source_text thành vector embeddings
            # để so sánh ngữ nghĩa thay vì so sánh từng từ
            sentence_embeddings = self.embedding_model.encode(sentences)
            source_embedding = self.embedding_model.encode(source_text)

            # 4. Kiểm tra từng câu có nguồn hỗ trợ không
            fact_check_results = []
            for i, (sentence, embedding) in enumerate(
                zip(sentences, sentence_embeddings)
            ):
                # Tính điểm tương đồng ngữ nghĩa giữa câu và nguồn
                similarity = float(
                    self.search_manager.reranker.predict([(sentence, source_text)])
                )

                # Đánh giá dựa trên ngưỡng
                is_verified = similarity >= self.fact_checking_threshold

                # Lưu kết quả kiểm tra
                fact_check_results.append(
                    {"sentence": sentence, "score": similarity, "verified": is_verified}
                )

                print(
                    f"Câu {i+1}: {'✓' if is_verified else '✗'} (score={similarity:.3f})"
                )

            # 5. Tổng hợp kết quả
            unverified_sentences = [r for r in fact_check_results if not r["verified"]]
            verified_ratio = (
                len(fact_check_results) - len(unverified_sentences)
            ) / len(fact_check_results)

            # 6. Đưa ra đánh giá tổng thể
            if verified_ratio >= 0.8:  # Nếu 80% trở lên đúng
                final_status = "verified"
                final_response = response
            elif verified_ratio >= 0.5:  # Nếu 50-80% đúng
                # Thêm ghi chú về thông tin chưa được xác minh
                final_status = "partially_verified"
                warning = "\n\n**Lưu ý**: Một số thông tin trong câu trả lời không được tìm thấy trong nguồn tài liệu. Vui lòng kiểm tra lại các nguồn bổ sung."
                final_response = response + warning
            else:  # Nếu dưới 50% đúng
                # Tạo câu trả lời mới, bỏ qua các câu không xác minh được
                final_status = "mostly_unverified"
                verified_sentences = [
                    r["sentence"] for r in fact_check_results if r["verified"]
                ]

                if verified_sentences:
                    verified_response = " ".join(verified_sentences)
                    warning = "\n\n**Cảnh báo**: Phần lớn thông tin trong câu trả lời ban đầu không được tìm thấy trong nguồn tài liệu. Câu trả lời đã được điều chỉnh để chỉ bao gồm thông tin đã xác minh."
                    final_response = verified_response + warning
                else:
                    final_response = "Không thể xác minh thông tin trong câu trả lời từ các nguồn tài liệu. Vui lòng tham khảo nguồn tài liệu trực tiếp hoặc hỏi lại với câu hỏi cụ thể hơn."

            return {
                "status": final_status,
                "verified_ratio": verified_ratio,
                "sentence_scores": fact_check_results,
                "response": final_response,
            }

        except Exception as e:
            print(f"Lỗi trong quá trình fact checking: {str(e)}")
            return {
                "verified": True,
                "response": response,
            }  # Trả về response gốc nếu có lỗi

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

        # Tăng số lượng kết quả ban đầu để có nhiều hơn cho reranking
        search_k = 25  # Tăng lên 25 kết quả đầu vào

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

        # Phân loại lại câu hỏi
        final_query_type = self.query_router.classify_query(query)
        print(f"Phân loại cuối cùng: '{final_query_type}'")

        # Nếu là realtime_question, trả về ngay
        if final_query_type == "realtime_question":
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
                "answer": "Không tìm thấy thông tin liên quan đến câu hỏi này trong cơ sở dữ liệu.",
                "sources": [],
                "question": original_query,
                "search_method": search_type,
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

            # Tính điểm nâng cao từ metadata nếu có
            metadata_boost = doc.get("metadata_boost", 0.0)

            # Kiểm tra các metadata đặc biệt
            special_metadata = {}
            for key in [
                "chứa_định_nghĩa",
                "chứa_cú_pháp",
                "chứa_mẫu_code",
                "chứa_cú_pháp_select",
                "chứa_cú_pháp_join",
                "chứa_cú_pháp_ddl",
                "chứa_cú_pháp_dml",
            ]:
                if key in metadata and metadata[key]:
                    special_metadata[key] = True

            # Cải thiện thông tin trang để hiển thị chính xác
            page_info = metadata.get("page", "Unknown")
            page_source = metadata.get("page_source", "unknown")
            section_in_page = metadata.get("section_in_page", "")

            # Định dạng thông tin trang dựa trên nguồn
            if page_source == "original_document":
                # Nếu là trang gốc từ tài liệu, hiển thị rõ ràng
                formatted_page = f"Trang {page_info}"
                if section_in_page:
                    formatted_page += f" (Phần {section_in_page})"
            elif page_source == "auto_generated":
                # Nếu là trang tự động tạo, đánh dấu rõ
                formatted_page = f"{page_info} (tự động tạo)"
            else:
                # Trường hợp khác
                formatted_page = f"{page_info}"

            source_info = {
                "source": metadata.get("source", doc.get("source", "Unknown")),
                "page": formatted_page,
                "original_page": metadata.get("original_page", page_info),
                "section": metadata.get(
                    "position", metadata.get("chunk_type", "Unknown")
                ),
                "content_snippet": doc["text"][:300] + "...",  # Hiển thị preview
                "score": doc.get("score", 0.0),
                "rerank_score": doc.get("rerank_score", 0.0),  # Điểm sau rerank
                "metadata_boost": metadata_boost,  # Thêm thông tin về điểm nâng cao từ metadata
                "special_metadata": special_metadata,  # Các metadata đặc biệt
            }
            sources_info.append(source_info)

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
        k: int = 10,
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
            file_id: Danh sách các file_id cần tìm kiếm (cách mới)
            conversation_history: Lịch sử hội thoại

        Returns:
            AsyncGenerator trả về từng phần của câu trả lời
        """
        print(f"Đang xử lý câu hỏi (stream): '{query}'")
        print(f"Phương pháp tìm kiếm: {search_type}")
        print(f"Alpha: {alpha if alpha is not None else self.default_alpha}")
        print(f"Tìm kiếm với file_id: {file_id}")

        # Bắt đầu đo thời gian xử lý
        start_time = time.time()

        # Xử lý query với QueryProcessor nếu có conversation_history
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

        # Trả về ngay nếu là câu hỏi thời gian thực
        if query_type == "realtime_question":
            # Trả về thông báo bắt đầu
            yield {
                "type": "start",
                "data": {
                    "query_type": query_type,
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
            response = self.query_router.prepare_realtime_response(query)
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
            search_results = self.hybrid_search(
                query_to_use,
                k=k,
                alpha=alpha if alpha is not None else self.default_alpha,
                sources=sources,
                file_id=file_id,
            )

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
        for i, result in enumerate(reranked_results[:5]):  # Chỉ lấy top 5 kết quả
            # Chuẩn bị metadata
            metadata = result.get("metadata", {})
            source = metadata.get("source", "unknown")
            page = metadata.get("page", "N/A")
            section = metadata.get("section", "N/A")

            # Thêm vào danh sách context
            context_docs.append(
                {
                    "content": result["text"],
                    "source": source,
                    "page": page,
                    "section": section,
                    "score": result.get("score", 0.0),
                }
            )

        # Chuẩn bị danh sách nguồn tham khảo
        sources_list = []
        for i, doc in enumerate(reranked_results):
            # Trích xuất thông tin từ metadata
            metadata = doc.get("metadata", {})
            source = metadata.get("source", "unknown")
            page = metadata.get("page", "N/A")
            section = metadata.get("section", "N/A")
            result_file_id = doc.get("file_id", "unknown")  # Lấy file_id từ kết quả

            # Tạo snippet từ nội dung
            content = doc["text"]
            snippet = content[:200] + "..." if len(content) > 200 else content

            # Thêm vào danh sách nguồn
            sources_list.append(
                {
                    "source": source,
                    "page": page,
                    "section": section,
                    "score": doc.get("score", 0.0),
                    "content_snippet": snippet,
                    "file_id": result_file_id,  # Thêm file_id vào kết quả
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

        # Thêm lưu ý về độ dài và định dạng
        prompt += """
        
        LƯU Ý QUAN TRỌNG:
        - Trả lời phải ngắn gọn, tối đa 3-4 đoạn văn
        - Sử dụng định dạng Markdown: ## cho tiêu đề, **in đậm** cho điểm quan trọng
        - Đặt code SQL trong ```sql và ```
        - Nếu cần bảng so sánh, tạo bảng đơn giản với tối đa 3 cột
        - KHÔNG sử dụng HTML, chỉ dùng Markdown
        """

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
        )

        # Thêm yêu cầu định dạng Markdown trong prompt
        prompt += "\n\nVui lòng trả lời câu hỏi trong định dạng Markdown rõ ràng để dễ hiển thị ở frontend. Sử dụng các thẻ như **in đậm**, *in nghiêng*, ## tiêu đề, - danh sách, ```code``` và các bảng khi cần thiết."

        # In prompt để debug
        # print(f"=== PROMPT ===\n{prompt}\n=== END PROMPT ===")

        # Gọi LLM và lấy kết quả
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
