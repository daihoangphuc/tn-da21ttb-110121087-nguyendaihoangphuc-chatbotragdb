from typing import List, Dict
from src.embedding import EmbeddingModel
from src.llm import GeminiLLM
from src.vector_store import VectorStore
from src.document_processor import DocumentProcessor
from src.prompt_manager import PromptManager
from src.search import SearchManager
from src.query_processor import QueryProcessor
import os
import re
import concurrent.futures
from dotenv import load_dotenv
import time

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

        # Đảm bảo collection tồn tại
        self.vector_store.ensure_collection_exists(self.embedding_model.get_dimension())

        # Cấu hình fact checking
        self.enable_fact_checking = os.getenv(
            "ENABLE_FACT_CHECKING", "True"
        ).lower() in ["true", "1", "yes"]
        self.fact_checking_threshold = float(
            os.getenv("FACT_CHECKING_THRESHOLD", "0.6")
        )

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

    def index_to_qdrant(self, chunks: List[Dict]) -> None:
        """Index dữ liệu lên Qdrant với xử lý song song cho embedding"""
        # Xử lý embedding song song theo batches
        texts = [chunk["text"] for chunk in chunks]
        batch_size = 32  # Số lượng văn bản xử lý trong mỗi batch

        print(f"Tính embedding cho {len(texts)} chunks với batch_size={batch_size}...")
        embeddings = self.embedding_model.encode(
            texts, batch_size=batch_size, show_progress=True
        )

        print(f"Đã hoàn thành embedding, đang index lên Qdrant...")
        self.vector_store.index_documents(chunks, embeddings)

    def semantic_search(
        self, query: str, k: int = 5, sources: List[str] = None
    ) -> List[Dict]:
        """Tìm kiếm ngữ nghĩa"""
        # Loại bỏ hoàn toàn chức năng mở rộng truy vấn
        return self.search_manager.semantic_search(query, k, sources)

    def hybrid_search(
        self, query: str, k: int = 15, alpha: float = None, sources: List[str] = None
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
            query, k=initial_k, sources=sources
        )
        print(f"Đã tìm được {len(semantic)} kết quả từ semantic search")

        keyword = self.search_manager.keyword_search(
            query, k=initial_k, sources=sources
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
    ) -> Dict:
        """Tạo câu trả lời kèm theo thông tin nguồn tham khảo"""
        # Sử dụng alpha mặc định nếu không được chỉ định
        if alpha is None:
            alpha = self.default_alpha

        start_time = time.time()

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

        # Nếu không có kết quả tìm kiếm, trả về thông báo không tìm thấy
        if not retrieved:
            return {
                "answer": "Không tìm thấy thông tin liên quan đến câu hỏi này trong cơ sở dữ liệu.",
                "sources": [],
                "question": query,
                "search_method": search_type,
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

        # Xác định loại câu hỏi
        question_type = self.prompt_manager.classify_question(query)

        # Tạo prompt phù hợp
        prompt = self.prompt_manager.create_prompt(query, retrieved, question_type)

        # Gọi LLM để tạo câu trả lời
        response = self.llm.invoke(prompt)

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

            source_info = {
                "source": metadata.get("source", doc.get("source", "Unknown")),
                "page": metadata.get("page", "Unknown"),
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
            "answer": response.content,
            "sources": sources_info,
            "question": query,
            "search_method": search_type,
            "total_reranked": total_reranked,  # Thêm tổng số kết quả được rerank
            "filtered_sources": sources,
        }

    async def query_with_sources_streaming(
        self,
        query: str,
        search_type: str = "hybrid",
        alpha: float = None,
        sources: List[str] = None,
    ):
        """Tạo câu trả lời kèm theo thông tin nguồn tham khảo dưới dạng streaming"""
        # Sử dụng alpha mặc định nếu không được chỉ định
        if alpha is None:
            alpha = self.default_alpha

        start_time = time.time()
        print(f"Bắt đầu xử lý truy vấn streaming: '{query}'")

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

        # Nếu không có kết quả tìm kiếm, trả về thông báo không tìm thấy
        if not retrieved:
            yield {
                "type": "sources",
                "data": {
                    "sources": [],
                    "question": query,
                    "search_method": search_type,
                    "message": "Không tìm thấy thông tin liên quan đến câu hỏi này trong cơ sở dữ liệu.",
                },
            }
            return

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

        # Xác định loại câu hỏi
        question_type = self.prompt_manager.classify_question(query)

        # Tạo prompt phù hợp
        prompt = self.prompt_manager.create_prompt(query, retrieved, question_type)

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

            source_info = {
                "source": metadata.get("source", doc.get("source", "Unknown")),
                "page": metadata.get("page", "Unknown"),
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

        # Đầu tiên, trả về thông tin nguồn tham khảo
        sources_data = {
            "type": "sources",
            "data": {
                "sources": sources_info,
                "question": query,
                "search_method": search_type,
                "total_reranked": total_reranked,
                "filtered_sources": sources,
            },
        }
        yield sources_data

        # Tiếp theo, gọi LLM với streaming và trả về từng phần câu trả lời
        print("Bắt đầu streaming từ LLM...")
        async for content_chunk in self.llm.invoke_streaming(prompt):
            yield {"type": "content", "data": content_chunk}

        # Báo hiệu kết thúc streaming
        end_time = time.time()
        total_time = end_time - start_time
        print(f"Tổng thời gian xử lý streaming: {total_time:.2f}s")

        yield {"type": "end", "data": {"processing_time": round(total_time, 2)}}

    def generate_response_with_context(
        self, query: str, retrieved: List[Dict], search_type: str = "hybrid"
    ) -> str:
        """Tạo câu trả lời với ngữ cảnh của kết quả tìm kiếm"""
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
