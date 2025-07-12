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
from backend.embedding import EmbeddingModel
from backend.llm import GeminiLLM
from backend.vector_store import VectorStore
from backend.document_processor import DocumentProcessor
from backend.prompt_manager import PromptManager
from backend.search import SearchManager
from backend.suggestion_manager import SuggestionManager
# from backend.query_processor import QueryProcessor
# from backend.query_router import QueryRouter
from backend.query_handler import QueryHandler
import os
import re
import concurrent.futures
from dotenv import load_dotenv
import time
import asyncio
import requests
import uuid
import json

# Import Google_Search
from backend.tools.Google_Search import run_query_with_sources as google_agent_search, get_raw_search_results

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

        # Search manager sẽ được tạo riêng cho từng user để tránh conflict
        # Không tạo global search manager để tránh vấn đề với BM25 index
        global_search_manager = None
        print("Search Manager sẽ được tạo riêng cho từng user khi cần thiết")

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
            # # Thay vì chỉ gán vector_store, gọi phương thức để cập nhật và tải lại BM25 index phù hợp
            # self.search_manager.set_vector_store_and_reload_bm25(self.vector_store)
            # print("Sử dụng Search Manager toàn cục (đã cập nhật vector_store và BM25 index cho user)")
        else:
            print("Khởi tạo Search Manager mới")
            self.search_manager = SearchManager(self.vector_store, self.embedding_model)

        # # Thêm QueryProcessor cho việc xử lý đồng tham chiếu
        # self.query_processor = QueryProcessor()
        # print("Đã khởi tạo QueryProcessor với khả năng xử lý đồng tham chiếu")

        # # Thêm QueryRouter cho việc phân loại câu hỏi
        # self.query_router = QueryRouter()
        # print("Đã khởi tạo QueryRouter để phân loại câu hỏi thành 3 loại")

                # Hợp nhất QueryProcessor và QueryRouter thành QueryHandler
        self.query_handler = QueryHandler()
        print("Đã khởi tạo QueryHandler để xử lý và phân loại câu hỏi")

        # Khởi tạo SuggestionManager cho việc tạo câu hỏi liên quan
        self.suggestion_manager = SuggestionManager(llm=self.llm)
        print("Đã khởi tạo SuggestionManager để tạo câu hỏi gợi ý")

        # Tính toán và lưu các giá trị khác nếu cần
        self.enable_fact_checking = (
            False  # Tính năng kiểm tra sự kiện (có thể kích hoạt sau)
        )

        self.confidence_threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))

        # Cài đặt cơ chế xử lý song song
        self.max_workers = int(os.getenv("MAX_PARALLEL_WORKERS", "4"))

    async def load_documents_async(self, data_dir: str) -> List[Dict]:
        """Tải tài liệu từ thư mục (bất đồng bộ)"""
        return await self.document_processor.load_documents(data_dir)

    def load_documents(self, data_dir: str) -> List[Dict]:
        """Tải tài liệu từ thư mục (đồng bộ)"""
        return self.document_processor.load_documents_sync(data_dir)

    async def process_documents_async(self, documents: List[Dict]) -> List[Dict]:
        """Xử lý và chia nhỏ tài liệu với xử lý song song (bất đồng bộ)"""
        # Xử lý song song nếu có nhiều tài liệu
        if len(documents) > 5:  # Chỉ xử lý song song khi có nhiều tài liệu
            print(
                f"Xử lý song song {len(documents)} tài liệu với {self.max_workers} workers"
            )
            chunks = []

            # Sử dụng asyncio để xử lý song song
            tasks = []
            semaphore = asyncio.Semaphore(self.max_workers)
            
            async def process_with_semaphore(doc):
                async with semaphore:
                    return await self._process_single_document_async(doc)
            
            for doc in documents:
                task = asyncio.create_task(process_with_semaphore(doc))
                tasks.append(task)
            
            # Chờ tất cả tasks hoàn thành
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"Lỗi khi xử lý tài liệu {i}: {str(result)}")
                else:
                    chunks.extend(result)

            print(f"Đã xử lý xong {len(documents)} tài liệu, tạo ra {len(chunks)} chunks")
            return chunks

        else:
            # Xử lý tuần tự cho ít tài liệu
            print(f"Xử lý tuần tự {len(documents)} tài liệu")
            all_chunks = []
            for doc in documents:
                chunks = await self._process_single_document_async(doc)
                all_chunks.extend(chunks)

            print(f"Đã xử lý xong {len(documents)} tài liệu, tạo ra {len(all_chunks)} chunks")
            return all_chunks

    def process_documents(self, documents: List[Dict]) -> List[Dict]:
        """Xử lý và chia nhỏ tài liệu với xử lý song song (đồng bộ)"""
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
                        doc_chunks = future.result()
                        chunks.extend(doc_chunks)
                        print(f"Đã xử lý xong tài liệu {doc_index}")
                    except Exception as exc:
                        print(f"Lỗi khi xử lý tài liệu {doc_index}: {exc}")

            print(f"Đã xử lý xong {len(documents)} tài liệu, tạo ra {len(chunks)} chunks")
            return chunks

        else:
            # Xử lý tuần tự cho ít tài liệu
            print(f"Xử lý tuần tự {len(documents)} tài liệu")
            all_chunks = []
            for doc in documents:
                chunks = self._process_single_document(doc)
                all_chunks.extend(chunks)

            print(f"Đã xử lý xong {len(documents)} tài liệu, tạo ra {len(all_chunks)} chunks")
            return all_chunks

    async def _process_single_document_async(self, document: Dict) -> List[Dict]:
        """Xử lý một tài liệu đơn lẻ (bất đồng bộ)"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self._process_single_document, document
        )

    def _process_single_document(self, document: Dict) -> List[Dict]:
        """Xử lý một tài liệu đơn lẻ"""
        return self.document_processor.chunk_documents_sync([document])

    async def index_to_qdrant_async(self, chunks: List[Dict], user_id) -> None:
        """Index chunks lên Qdrant (bất đồng bộ)"""
        if not chunks:
            print("Không có chunks nào để index")
            return

        start_time = time.time()
        print(f"Bắt đầu index {len(chunks)} chunks lên Qdrant cho user_id={user_id}")

        try:
            # Tạo embeddings batch để tối ưu tốc độ
            texts = [chunk["text"] for chunk in chunks]
            print(f"Đang tạo embeddings cho {len(texts)} texts...")

            # Sử dụng async batch encoding
            embeddings = await self.embedding_model.encode_batch(texts)
            print(f"Đã tạo xong {len(embeddings)} embeddings")

            # Lấy file_id từ chunk đầu tiên (giả sử tất cả chunks thuộc cùng một file)
            file_id = chunks[0].get("file_id", str(uuid.uuid4()))

            # Index lên vector store
            await self.vector_store.index_documents(chunks, embeddings, user_id, file_id)

            end_time = time.time()
            processing_time = end_time - start_time
            print(
                f"Hoàn thành index {len(chunks)} chunks trong {processing_time:.2f}s "
                f"(trung bình {processing_time/len(chunks):.3f}s/chunk)"
            )

        except Exception as e:
            print(f"Lỗi khi index chunks: {str(e)}")
            raise

    def index_to_qdrant(self, chunks: List[Dict], user_id) -> None:
        """Index chunks lên Qdrant (đồng bộ)"""
        if not chunks:
            print("Không có chunks nào để index")
            return

        start_time = time.time()
        print(f"Bắt đầu index {len(chunks)} chunks lên Qdrant cho user_id={user_id}")

        try:
            # Tạo embeddings batch để tối ưu tốc độ
            texts = [chunk["text"] for chunk in chunks]
            print(f"Đang tạo embeddings cho {len(texts)} texts...")

            # Sử dụng sync batch encoding
            embeddings = self.embedding_model.encode_batch_sync(texts)
            print(f"Đã tạo xong {len(embeddings)} embeddings")

            # Lấy file_id từ chunk đầu tiên (giả sử tất cả chunks thuộc cùng một file)
            file_id = chunks[0].get("file_id", str(uuid.uuid4()))

            # Index lên vector store
            self.vector_store.index_documents_sync(chunks, embeddings, user_id, file_id)

            end_time = time.time()
            processing_time = end_time - start_time
            print(
                f"Hoàn thành index {len(chunks)} chunks trong {processing_time:.2f}s "
                f"(trung bình {processing_time/len(chunks):.3f}s/chunk)"
            )

        except Exception as e:
            print(f"Lỗi khi index chunks: {str(e)}")
            raise

    async def semantic_search_async(
        self,
        query: str,
        k: int = 20,
        sources: List[str] = None,
        file_id: List[str] = None,
    ) -> List[Dict]:
        """Tìm kiếm ngữ nghĩa (bất đồng bộ)"""
        print(f"Semantic search với query='{query}', k={k}")
        
        if sources:
            print(f"Filtering by sources: {sources}")
        if file_id:
            print(f"Filtering by file_id: {file_id}")

        try:
            # Sử dụng search manager với async
            results = await self.search_manager.semantic_search(
                query=query,
                k=k,
                sources=sources,
                file_id=file_id,
            )

            print(f"Tìm thấy {len(results)} kết quả từ semantic search")

            # Log thông tin kết quả để debug
            if results:
                for i, result in enumerate(results[:3]):  # Log 3 kết quả đầu
                    score = result.get("score", 0)
                    source = result.get("source", "unknown")
                    text_preview = result.get("text", "")[:100] + "..." if result.get("text", "") else ""
                    print(f"  Result {i+1}: score={score:.4f}, source={source}, text={text_preview}")

            return results

        except Exception as e:
            print(f"Lỗi trong semantic search: {str(e)}")
            import traceback
            print(f"Chi tiết lỗi: {traceback.format_exc()}")
            return []

    def semantic_search(
        self,
        query: str,
        k: int = 20,
        sources: List[str] = None,
        file_id: List[str] = None,
    ) -> List[Dict]:
        """Tìm kiếm ngữ nghĩa (đồng bộ)"""
        print(f"Semantic search với query='{query}', k={k}")
        
        if sources:
            print(f"Filtering by sources: {sources}")
        if file_id:
            print(f"Filtering by file_id: {file_id}")

        try:
            # Sử dụng search manager với sync
            results = self.search_manager.semantic_search_sync(
                query=query,
                k=k,
                sources=sources,
                file_id=file_id,
            )

            print(f"Tìm thấy {len(results)} kết quả từ semantic search")

            # Log thông tin kết quả để debug
            if results:
                for i, result in enumerate(results[:3]):  # Log 3 kết quả đầu
                    score = result.get("score", 0)
                    source = result.get("source", "unknown")
                    text_preview = result.get("text", "")[:100] + "..." if result.get("text", "") else ""
                    print(f"  Result {i+1}: score={score:.4f}, source={source}, text={text_preview}")

            return results

        except Exception as e:
            print(f"Lỗi trong semantic search: {str(e)}")
            import traceback
            print(f"Chi tiết lỗi: {traceback.format_exc()}")
            return []

    async def rerank_results_async(self, query: str, results: List[Dict]) -> List[Dict]:
        """Tái xếp hạng kết quả (bất đồng bộ)"""
        return await self.search_manager.rerank_results(query, results)

    def rerank_results(self, query: str, results: List[Dict]) -> List[Dict]:
        """Tái xếp hạng kết quả (đồng bộ)"""
        return self.search_manager.rerank_results_sync(query, results)

    async def query_with_sources_streaming(
        self,
        query: str,
        k: int = 20,
        sources: List[str] = None,
        file_id: List[str] = None,
        conversation_history: str = None,
    ) -> AsyncGenerator[Dict, None]:
        """
        Truy vấn hệ thống RAG với các nguồn và trả về kết quả dưới dạng stream

        Args:
            query: Câu hỏi người dùng
            k: Số lượng kết quả trả về
            sources: Danh sách các file nguồn cần tìm kiếm (cách cũ, sử dụng file_id thay thế)
            file_id: Danh sách các file_id cần tìm kiếm (cách mới). Nếu là None hoặc rỗng, sẽ tìm kiếm trong tất cả các file
            conversation_history: Lịch sử hội thoại

        Returns:
            AsyncGenerator trả về từng phần của câu trả lời
        """
        print(f"Đang xử lý câu hỏi (stream): '{query}'")
        
        if file_id is None or len(file_id) == 0:
            print("file_id là None hoặc danh sách rỗng. Tìm kiếm sẽ được thực hiện trên toàn bộ tài liệu.")
            # Đặt file_id thành None để semantic_search hiểu là tìm kiếm trên tất cả tài liệu
            file_id = None
        else:
            print(f"Tìm kiếm với file_id: {file_id}")

        # Bắt đầu đo thời gian xử lý
        start_time = time.time()

        # Xử lý và phân loại câu hỏi trong một lệnh gọi LLM duy nhất
        original_query = query
        expanded_query, query_type = await self.query_handler.expand_and_classify_query(
            query, conversation_history
        )
        query_to_use = expanded_query
        print(f"Câu hỏi đã xử lý: '{query_to_use}', Loại: '{query_type}'")

        # Trả về ngay nếu là câu hỏi không liên quan đến cơ sở dữ liệu
        if query_type == "other_question":
            # Trả về thông báo bắt đầu
            yield {
                "type": "start",
                "data": {
                    "query_type": query_type,
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

            # Trả về nội dung - đã định dạng Markdown
            response = await self.query_handler.get_response_for_other_question(query)
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
                    "search_type": "google_raw_search",
                    "file_id": file_id,
                },
            }

            # Sử dụng Google Search để tìm kiếm (kết quả thô)
            try:
                # Lấy kết quả thô từ Google Search
                raw_search_content, gas_urls = get_raw_search_results(query_to_use)
                
                # Chuẩn bị danh sách nguồn từ Google Search
                gas_sources_list = []
                if gas_urls:
                    for url_idx, url in enumerate(gas_urls):
                        gas_sources_list.append({
                            "source": url,  # URL thực tế
                            "page": f"Web Search {url_idx+1}",
                            "section": "Online Source",
                            "score": 1.0,
                            "content_snippet": url,  # Hiển thị URL làm snippet
                            "file_id": "web_search",
                            "is_web_search": True,
                            "url": url  # Thêm field url riêng
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

                # Sử dụng template REALTIME_QUESTION để tạo prompt
                prompt = self.prompt_manager.get_realtime_question_prompt(
                    query=query_to_use,
                    search_results=raw_search_content,
                    conversation_history=conversation_history
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
                print(f"Lỗi khi sử dụng Google Search (stream): {str(e)}")
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
                yield {"type": "content", "data": {"content": f"Không thể sử dụng Google Search: {str(e)}. Vui lòng kiểm tra lại API key hoặc cấu hình."}}

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
        RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "50"))
        
        # Khởi tạo biến để lưu trữ kết quả Google Search cho question_from_document
        google_search_content = ""
        google_search_urls = []
        google_search_used = False
        
        # Nếu là question_from_document, thực hiện search song song
        if query_type == "question_from_document":
            print(f"🔍 Thực hiện tìm kiếm song song cho question_from_document: '{query_to_use}'")
            
            # Tạo tasks để chạy song song
            search_tasks = []
            
            # Task 1: Semantic search trong tài liệu
            semantic_task = asyncio.create_task(
                self.semantic_search_async(
                    query_to_use, k=RETRIEVAL_K, sources=sources, file_id=file_id
                )
            )
            search_tasks.append(('semantic', semantic_task))
            
            # Task 2: Google Search
            async def google_search_task():
                try:
                    # Chạy Google Search trong thread pool để tránh blocking
                    loop = asyncio.get_event_loop()
                    content, urls = await loop.run_in_executor(None, get_raw_search_results, query_to_use)
                    return content, urls
                except Exception as e:
                    print(f"Lỗi khi thực hiện Google Search: {str(e)}")
                    return "", []
            
            google_task = asyncio.create_task(google_search_task())
            search_tasks.append(('google', google_task))
            
            # Chờ tất cả tasks hoàn thành
            completed_tasks = await asyncio.gather(*[task for _, task in search_tasks], return_exceptions=True)
            
            # Xử lý kết quả semantic search
            search_results = completed_tasks[0] if not isinstance(completed_tasks[0], Exception) else []
            if isinstance(completed_tasks[0], Exception):
                print(f"Lỗi trong semantic search: {completed_tasks[0]}")
                search_results = []
            
            # Xử lý kết quả Google search
            if not isinstance(completed_tasks[1], Exception):
                google_search_content, google_search_urls = completed_tasks[1]
                if google_search_content and google_search_content != "Không tìm thấy thông tin liên quan đến truy vấn này.":
                    google_search_used = True
                    print(f"✅ Google Search hoàn thành: {len(google_search_urls)} URLs")
                else:
                    print("⚠️ Google Search không tìm thấy kết quả")
            else:
                print(f"❌ Lỗi trong Google Search: {completed_tasks[1]}")
                google_search_content, google_search_urls = "", []
        else:
            # Thực hiện semantic search thông thường cho các loại khác
            search_results = await self.semantic_search_async(
                query_to_use, k=RETRIEVAL_K, sources=sources, file_id=file_id
            )
        
        # Fallback mechanism cho streaming (chỉ áp dụng khi không có kết quả RAG và không phải question_from_document)
        perform_fallback_stream = not search_results or len(search_results) == 0
        gas_fallback_used = False
        
        if perform_fallback_stream and query_type != "question_from_document":
            print(f"Không có kết quả RAG (stream). Thực hiện fallback với Google Search cho: '{query_to_use}'")
            try:
                # Khởi tạo sources_list trước khi sử dụng
                sources_list = []
                # Chạy Google Search trong thread pool để tránh blocking
                loop = asyncio.get_event_loop()
                fallback_content, fallback_urls = await loop.run_in_executor(None, get_raw_search_results, query_to_use)
                
                if fallback_content and fallback_content != "Không tìm thấy thông tin liên quan đến truy vấn này.":
                    gas_fallback_used = True
                    print(f"Đã tìm thấy kết quả fallback: {fallback_content[:100]}...")
                    
                    # Tạo một doc giả cho fallback để đưa vào context LLM
                    fallback_doc = {
                        "text": fallback_content,
                        "metadata": {
                            "source": "Google Search",
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
                            "source": url,  # URL thực tế
                            "page": f"Fallback Search {url_idx+1}",
                            "section": "Online Source",
                            "score": 0.9,
                            "content_snippet": url,  # Hiển thị URL làm snippet
                            "file_id": "web_search_fallback",
                            "is_web_search": True,
                            "url": url  # Thêm field url riêng
                        })
                else:
                    print("Google Search không tìm thấy kết quả fallback.")
            except Exception as e:
                print(f"Lỗi khi thực hiện fallback với Google Search: {str(e)}")
                # Tiếp tục với kết quả hiện tại

        # Xử lý trường hợp không có kết quả từ cả hai nguồn
        if (not search_results or len(search_results) == 0) and not google_search_used:
            # Trả về thông báo bắt đầu
            yield {
                "type": "start",
                "data": {
                    "query_type": "no_results",
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
            response = "Không tìm thấy thông tin liên quan đến câu hỏi của bạn trong tài liệu và cũng không thể tìm kiếm thông tin bổ sung từ Internet. Vui lòng thử lại với câu hỏi khác hoặc điều chỉnh từ khóa tìm kiếm."
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

        # Xử lý trường hợp đặc biệt: chỉ có Google Search results (không có document results)
        if (not search_results or len(search_results) == 0) and google_search_used and query_type == "question_from_document":
            print(f"⚠️ Chỉ có kết quả từ Google Search, không có kết quả từ tài liệu cho question_from_document")
            # Tạo context trống cho tài liệu
            context_docs = []
            
            # Tạo sources list chỉ từ Google Search
            sources_list = []
            for url_idx, url in enumerate(google_search_urls):
                sources_list.append({
                    "source": url,
                    "page": f"Internet Search {url_idx+1}",
                    "section": "Online Source",
                    "score": 0.8,
                    "content_snippet": url,
                    "file_id": "internet_search",
                    "is_web_search": True,
                    "url": url,
                    "source_type": "internet"
                })

            # Trả về thông báo bắt đầu
            yield {
                "type": "start",
                "data": {
                    "query_type": query_type,
                    "file_id": file_id,
                    "total_results": 0,
                    "total_reranked": 0,
                    "google_search_used": True,
                    "google_search_urls_count": len(google_search_urls),
                    "only_internet_results": True,
                },
            }

            # Trả về nguồn tham khảo
            yield {
                "type": "sources",
                "data": {
                    "sources": sources_list,
                    "filtered_sources": [],
                    "filtered_file_id": file_id if file_id else [],
                    "google_search_used": True,
                },
            }

            # Sử dụng prompt đặc biệt với chỉ có Google search content
            prompt = self.prompt_manager.create_prompt_with_google_search(
                query_to_use, 
                [],  # Context trống
                google_search_content,
                conversation_history=conversation_history
            )

            # Gọi LLM để trả lời
            try:
                async for content in self.llm.stream(prompt):
                    yield {"type": "content", "data": {"content": content}}
            except Exception as e:
                print(f"Lỗi khi gọi LLM stream: {str(e)}")
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
                    "google_search_used": True,
                    "only_internet_results": True,
                },
            }
            return
        RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", "15"))
        results_to_rerank = search_results[:RERANK_TOP_N] if search_results else []
        print(f"Lấy về {len(search_results) if search_results else 0} kết quả, sẽ rerank top {len(results_to_rerank)}.")

        # Rerank kết quả nếu có nhiều hơn 1 kết quả
        if len(search_results) > 0:
            reranked_results = await self.rerank_results_async(
                query_to_use, results_to_rerank
            )
            # Lấy số lượng kết quả đã rerank
            total_reranked = len(reranked_results)
        else:
            reranked_results = search_results if search_results else []
            total_reranked = len(reranked_results)

        # Chuẩn bị context từ các kết quả đã rerank
        context_docs = []
        for i, result in enumerate(reranked_results[:20]):  
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
        
        # Thêm nguồn từ RAG documents
        for i, doc in enumerate(reranked_results):
            # Trích xuất thông tin từ metadata
            metadata = doc.get("metadata", {})
            
            # Kiểm tra nếu là nguồn từ Google Search
            if metadata.get("source_type") == "web_search":
                urls_from_gas = metadata.get("urls", [])
                snippet = doc["text"]
                if urls_from_gas:
                    snippet += "\n\nNguồn tham khảo từ web:\n" + "\n".join([f"- {url}" for url in urls_from_gas])
                
                sources_list.append({
                    "source": "Google Search",
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

        # Thêm nguồn từ Google Search nếu có (cho question_from_document)
        if google_search_used and query_type == "question_from_document":
            for url_idx, url in enumerate(google_search_urls):
                sources_list.append({
                    "source": url,
                    "page": f"Internet Search {url_idx+1}",
                    "section": "Online Source",
                    "score": 0.8,  # Điểm thấp hơn nguồn tài liệu
                    "content_snippet": url,
                    "file_id": "internet_search",
                    "is_web_search": True,
                    "url": url,
                    "source_type": "internet"
                })

        # Trả về thông báo bắt đầu
        yield {
            "type": "start",
            "data": {
                "query_type": query_type,
                "file_id": file_id,
                "total_results": len(search_results) if search_results else 0,
                "total_reranked": total_reranked,
                "google_search_used": google_search_used,
                "google_search_urls_count": len(google_search_urls) if google_search_used else 0,
            },
        }

        # Trả về nguồn tham khảo
        yield {
            "type": "sources",
            "data": {
                "sources": sources_list,
                "filtered_sources": [],  # Giữ trường này để tương thích với code cũ
                "filtered_file_id": file_id if file_id else [],
                "google_search_used": google_search_used,
            },
        }

        # Chuẩn bị prompt cho LLM với cả nguồn tài liệu và Google search
        if query_type == "question_from_document" and google_search_used:
            # Sử dụng prompt đặc biệt cho question_from_document có kết hợp Google search
            prompt = self.prompt_manager.create_prompt_with_google_search(
                query_to_use, 
                context_docs, 
                google_search_content,
                conversation_history=conversation_history
            )
        else:
            # Sử dụng prompt thông thường
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
                "google_search_used": google_search_used,
            },
        }

    def delete_collection(self) -> None:
        """Xóa collection"""
        self.vector_store.delete_collection()

    def get_collection_info(self) -> Dict:
        """Lấy thông tin về collection"""
        return self.vector_store.get_collection_info()

    async def generate_related_questions(self, query: str, answer: str) -> List[str]:
        """Tạo danh sách các câu hỏi gợi ý liên quan sử dụng SuggestionManager"""
        try:
            # Tạo conversation context từ Q&A hiện tại
            conversation_context = f"Người dùng: {query}\n\nTrợ lý: {answer}"
            
            # Sử dụng SuggestionManager thay vì template
            suggestions = await self.suggestion_manager.generate_question_suggestions(
                conversation_context, num_suggestions=3
            )
            return suggestions[:3]  # Đảm bảo chỉ trả về 3 câu hỏi
            
        except Exception as e:
            print(f"Lỗi khi tạo câu hỏi liên quan: {str(e)}")
            # Trả về câu hỏi mặc định
            return [
                "Bạn muốn tìm hiểu thêm điều gì về chủ đề này?",
                "Bạn có thắc mắc nào khác liên quan đến nội dung này không?",
                "Bạn có muốn biết thêm thông tin về ứng dụng thực tế không?",
            ]

    # def _generate_answer(self, query, relevant_docs, **kwargs):
    #     """Phương thức nội bộ để tạo câu trả lời"""
    #     # Tạo context từ các tài liệu liên quan
    #     context = "\n---\n".join([doc["text"] for doc in relevant_docs])

    #     # Tạo prompt với template phù hợp
    #     prompt = self.prompt_manager.templates["query_with_context"].format(
    #         context=context, query=query
    #     ) # Gọi LLM và lấy kết quả
    #     response = self.llm.invoke(prompt)
    #     return response.content

