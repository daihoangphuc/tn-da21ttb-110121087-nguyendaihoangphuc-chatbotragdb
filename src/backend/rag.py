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
from backend.tools.Google_Search import run_query_with_sources as google_agent_search

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
        # empty_vector_store = VectorStore()  # VectorStore không có user_id
        # global_search_manager = SearchManager(empty_vector_store, global_embedding_model)
        # print("Đã khởi tạo Search Manager toàn cục (BM25, reranker)")
        # print("SearchManager toàn cục sẽ tải BM25 index phù hợp khi được gán cho user_id cụ thể")

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

        # Tính toán và lưu các giá trị khác nếu cần
        self.enable_fact_checking = (
            False  # Tính năng kiểm tra sự kiện (có thể kích hoạt sau)
        )

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
        k: int = 10,
        sources: List[str] = None,
        file_id: List[str] = None,
    ) -> List[Dict]:
        """
        Tìm kiếm ngữ nghĩa với khả năng lọc theo nguồn

        Args:
            query: Câu truy vấn
            k: Số lượng kết quả trả về
            sources: Danh sách nguồn tài liệu (legacy, sử dụng file_id thay thế)
            file_id: Danh sách ID file cần tìm kiếm

        Returns:
            Danh sách kết quả tìm kiếm đã được sắp xếp theo điểm số
        """
        print(f"Thực hiện semantic search cho: '{query}'")
        print(f"Tham số: k={k}, sources={sources}, file_id={file_id}")

        # CẬP NHẬT: Không dùng user_id nữa vì sử dụng collection chung
        if sources or file_id:
            # Gọi search_with_filter trên SearchManager (không truyền user_id)
            results = self.search_manager.semantic_search(
                query=query, k=k, sources=sources, file_id=file_id
            )
        else:
            # Tìm kiếm thông thường trên toàn bộ collection (không truyền user_id)
            results = self.search_manager.semantic_search(query=query, k=k)

        print(f"Semantic search trả về {len(results)} kết quả")

        return results

    def rerank_results(self, query: str, results: List[Dict]) -> List[Dict]:
        """Tái xếp hạng kết quả"""
        return self.search_manager.rerank_results(query, results)

    async def query_with_sources_streaming(
        self,
        query: str,
        k: int = 10,
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
        expanded_query, query_type = self.query_handler.expand_and_classify_query(
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

            # Trả về nội dung
            response = self.query_handler.get_response_for_other_question(query)
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
                    "search_type": "google_agent_search",
                    "file_id": file_id,
                },
            }

            # Sử dụng Google Search để tìm kiếm
            try:
                gas_summary, gas_urls = google_agent_search(query_to_use)
                
                # Tạo document từ kết quả Google Search
                gas_content = gas_summary.content if hasattr(gas_summary, 'content') else str(gas_summary)
                
                # Tạo một danh sách retrieved chỉ chứa kết quả từ Google Search
                retrieved = [{
                    "text": gas_content,
                    "metadata": {
                        "source": "Google Search",
                        "page": "Web Result",
                        "source_type": "web_search",
                        "urls": gas_urls
                    },
                    "score": 1.0,
                    "rerank_score": 1.0
                }]
                
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

                # Chuẩn bị prompt cho LLM với kết quả từ Google Search
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

        # Thực hiện semantic search
        search_results = self.semantic_search(
            query_to_use, k=k, sources=sources, file_id=file_id
        )
        
        # Fallback mechanism cho streaming
        perform_fallback_stream = not search_results or len(search_results) == 0
        gas_fallback_used = False
        
        if perform_fallback_stream:
            print(f"Không có kết quả RAG (stream). Thực hiện fallback với Google Search cho: '{query_to_use}'")
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

        # Nếu không có kết quả tìm kiếm, trả về thông báo không tìm thấy
        if not search_results or len(search_results) == 0:
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
            reranked_results = self.rerank_results(
                query_to_use, search_results
            )
            # Lấy số lượng kết quả đã rerank
            total_reranked = len(reranked_results)
        else:
            reranked_results = search_results
            total_reranked = 1

        # Chuẩn bị context từ các kết quả đã rerank
        context_docs = []
        for i, result in enumerate(reranked_results[:10]):  
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

        # Trả về thông báo bắt đầu
        yield {
            "type": "start",
            "data": {
                "query_type": query_type,
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

    def delete_collection(self) -> None:
        """Xóa collection"""
        self.vector_store.delete_collection()

    def get_collection_info(self) -> Dict:
        """Lấy thông tin về collection"""
        return self.vector_store.get_collection_info()

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
