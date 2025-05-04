from src.embeddings import initialize_embeddings
from src.loaders import DocumentLoader
from src.processors import DocumentProcessor, SQLDocumentProcessor
from src.processors.code_processor import CodeDocumentProcessor
from src.processors.table_processor import TableDocumentProcessor
from src.processors.pdf_processor import PDFDocumentProcessor
from src.vectorstore import VectorStoreManager
from src.retrieval import Retriever
from src.retrieval.hybrid_retriever import HybridRetriever
from src.llm import GeminiLLM
from src.fusion import RAGFusion
from src.query_expansion.query_decomposer import MultiStepReasoner
from src.templates import (
    get_database_query_prompt,
    get_sql_generation_prompt,
    get_schema_analysis_prompt,
)
from src.utils import measure_time, get_file_extension
from src.config import (
    QUERY_EXPANSION_ENABLED,
    RERANKER_ENABLED,
    SQL_FILE_EXTENSIONS,
    USE_HYBRID_SEARCH,
    USE_SELF_QUERY,
)
from typing import Dict, Any, Union, List
import time
import os
import re


class RAGPipeline:
    """Lớp chính quản lý toàn bộ pipeline RAG"""

    def __init__(self):
        """Khởi tạo các thành phần của pipeline"""
        print("⏳ Đang khởi tạo RAG Pipeline...")
        # Khởi tạo và kiểm tra các thành phần của pipeline
        self.embeddings = initialize_embeddings()

        # Khởi tạo các processor cho nhiều loại tài liệu
        self.document_processor = DocumentProcessor(self.embeddings)
        self.sql_processor = SQLDocumentProcessor(self.embeddings)
        self.code_processor = CodeDocumentProcessor(self.embeddings)
        self.table_processor = TableDocumentProcessor(self.embeddings)
        self.pdf_processor = PDFDocumentProcessor(self.embeddings)

        # Khởi tạo vector store
        self.vector_store_manager = VectorStoreManager(self.embeddings)
        self.vectorstore = self.vector_store_manager.get_vectorstore()

        # Khởi tạo retriever (thông thường hoặc hybrid)
        if USE_HYBRID_SEARCH:
            print("⏳ Đang khởi tạo HybridRetriever...")
            self.retriever = HybridRetriever(
                self.vectorstore, use_reranker=RERANKER_ENABLED
            )
            print("✅ Đã khởi tạo HybridRetriever!")
        else:
            self.retriever = Retriever(self.vectorstore)

        # Khởi tạo RAG Fusion
        if QUERY_EXPANSION_ENABLED:
            try:
                print("⏳ Đang khởi tạo RAG Fusion...")
                self.fusion = RAGFusion(self.retriever)
                print("✅ Đã khởi tạo RAG Fusion!")
            except Exception as e:
                print(f"⚠️ Lỗi khi khởi tạo RAG Fusion: {str(e)}")
                print("⚠️ Sẽ sử dụng retriever thông thường")
                self.fusion = None
        else:
            self.fusion = None

        # Khởi tạo MultiStepReasoner nếu cần thiết
        if USE_SELF_QUERY:
            print("⏳ Đang khởi tạo MultiStepReasoner...")
            self.reasoner = MultiStepReasoner(self.retriever)
            print("✅ Đã khởi tạo MultiStepReasoner!")
        else:
            self.reasoner = None

        self.llm = GeminiLLM()
        print("✅ RAG Pipeline đã được khởi tạo thành công!")

    def _reinitialize_vectorstore(self):
        """Khởi tạo lại vectorstore và retriever"""
        print("🔄 Đang khởi tạo lại vector store...")
        self.vectorstore = self.vector_store_manager.get_vectorstore()

        # Lưu reranker cũ nếu có
        old_reranker = None
        if (
            hasattr(self, "retriever")
            and self.retriever
            and hasattr(self.retriever, "reranker")
        ):
            old_reranker = self.retriever.reranker

        # Khởi tạo retriever mới nhưng dùng lại reranker cũ nếu có
        if USE_HYBRID_SEARCH:
            self.retriever = HybridRetriever(
                self.vectorstore, use_reranker=RERANKER_ENABLED
            )

            # Xây dựng sparse index nếu là hybrid retriever
            try:
                documents = self.vector_store_manager.get_all_documents()
                if documents:
                    print(
                        f"⏳ Đang xây dựng sparse index cho {len(documents)} tài liệu..."
                    )
                    self.retriever.build_sparse_index(documents)
                else:
                    print(
                        "ℹ️ Không có tài liệu nào trong vector store để xây dựng sparse index"
                    )
            except Exception as e:
                print(f"⚠️ Không thể lấy tài liệu để xây dựng sparse index: {str(e)}")
        else:
            self.retriever = Retriever(self.vectorstore, use_reranker=RERANKER_ENABLED)

        # Gán lại reranker cũ nếu có
        if (
            old_reranker is not None
            and hasattr(self.retriever, "use_reranker")
            and self.retriever.use_reranker
        ):
            print("ℹ️ Tái sử dụng reranker đã khởi tạo trước đó")
            self.retriever.reranker = old_reranker

        # Khởi tạo lại fusion nếu có
        if QUERY_EXPANSION_ENABLED and hasattr(self, "fusion") and self.fusion:
            self.fusion = RAGFusion(self.retriever)

        # Cập nhật lại reasoner để sử dụng retriever mới
        if USE_SELF_QUERY and hasattr(self, "reasoner") and self.reasoner:
            self.reasoner.retriever = self.retriever

        print("✅ Đã khởi tạo lại vector store!")

    @measure_time
    def index_data(self, data_directory: str):
        """Thực hiện quá trình indexing dữ liệu"""
        # 1. Load tài liệu
        documents = DocumentLoader.load_documents(data_directory)

        # 2. Phân chia tài liệu theo loại
        sql_docs = []
        code_docs = []
        table_docs = []
        pdf_docs = []
        regular_docs = []

        for doc in documents:
            source_path = doc.metadata.get("source_path", "")
            ext = get_file_extension(source_path)

            # Phân loại theo extension
            if ext in SQL_FILE_EXTENSIONS:
                sql_docs.append(doc)
            elif ext in [
                ".py",
                ".js",
                ".ts",
                ".jsx",
                ".tsx",
                ".java",
                ".cs",
                ".cpp",
                ".c",
                ".h",
            ]:
                code_docs.append(doc)
            elif ext in [".csv", ".xlsx", ".xls", ".json", ".tsv"]:
                table_docs.append(doc)
            elif ext == ".pdf":
                pdf_docs.append(doc)
            else:
                regular_docs.append(doc)

        print(
            f"ℹ️ Tổng số tài liệu: {len(documents)} "
            f"(SQL: {len(sql_docs)}, Code: {len(code_docs)}, "
            f"Table: {len(table_docs)}, PDF: {len(pdf_docs)}, "
            f"Thông thường: {len(regular_docs)})"
        )

        # 3a. Xử lý các tài liệu SQL với processor đặc biệt
        if sql_docs:
            print("⏳ Đang xử lý các tài liệu SQL...")
            sql_chunks = self.sql_processor.process_sql_documents(sql_docs)
            print(
                f"✅ Đã xử lý {len(sql_chunks)} chunks từ {len(sql_docs)} tài liệu SQL"
            )
        else:
            sql_chunks = []

        # 3b. Xử lý các tài liệu code với processor đặc biệt
        if code_docs:
            print("⏳ Đang xử lý các tài liệu code...")
            code_chunks = self.code_processor.process_code_documents(code_docs)
            print(
                f"✅ Đã xử lý {len(code_chunks)} chunks từ {len(code_docs)} tài liệu code"
            )
        else:
            code_chunks = []

        # 3c. Xử lý các tài liệu dạng bảng với processor đặc biệt
        if table_docs:
            print("⏳ Đang xử lý các tài liệu dạng bảng...")
            table_chunks = self.table_processor.process_table_documents(table_docs)
            print(
                f"✅ Đã xử lý {len(table_chunks)} chunks từ {len(table_docs)} tài liệu dạng bảng"
            )
        else:
            table_chunks = []

        # 3d. Xử lý các tài liệu PDF với processor đặc biệt
        if pdf_docs:
            print("⏳ Đang xử lý các tài liệu PDF...")
            pdf_chunks = self.pdf_processor.process_pdf_documents(pdf_docs)
            print(
                f"✅ Đã xử lý {len(pdf_chunks)} chunks từ {len(pdf_docs)} tài liệu PDF"
            )
        else:
            pdf_chunks = []

        # 3e. Xử lý các tài liệu thông thường với processor thông thường
        if regular_docs:
            # Chunk tài liệu thông thường
            regular_chunks = self.document_processor.chunk_documents(regular_docs)
            # Cluster & merge để cải thiện chất lượng
            merged_regular_chunks = self.document_processor.cluster_and_merge(
                regular_chunks
            )
            print(
                f"✅ Đã xử lý {len(merged_regular_chunks)} chunks từ {len(regular_docs)} tài liệu thông thường"
            )
        else:
            merged_regular_chunks = []

        # 4. Kết hợp tất cả chunks
        all_chunks = (
            sql_chunks + code_chunks + table_chunks + pdf_chunks + merged_regular_chunks
        )
        print(f"ℹ️ Tổng số chunks để index: {len(all_chunks)}")

        # 5. Upload vào vector store
        self.vector_store_manager.upload_documents(all_chunks)

        # Khởi tạo lại vectorstore để áp dụng thay đổi
        self._reinitialize_vectorstore()

        print("✅ Hoàn thành quá trình indexing dữ liệu")

    @measure_time
    def delete_file(self, file_path: str) -> int:
        """Xóa file và các embedding tương ứng khỏi vector store

        Args:
            file_path: Đường dẫn tới file cần xóa

        Returns:
            Số lượng point đã xóa
        """
        # Xóa các point trong vector store
        deleted_count = self.vector_store_manager.delete_points_by_file(file_path)

        # Đặt lại trạng thái vectorstore về None
        if deleted_count > 0:
            self.vectorstore = None

        print(f"✅ Đã xóa {deleted_count} point liên quan đến file: {file_path}")

        return deleted_count

    @measure_time
    def delete_index(self, collection_name=None):
        """Xóa toàn bộ index trong vector store"""
        # Xóa collection
        self.vector_store_manager.delete_collection(collection_name)

        # Đặt lại trạng thái vectorstore về None
        self.vectorstore = None

        print(
            "⚠️ Vector store đã bị xóa. Bạn cần tạo lại index trước khi thực hiện truy vấn."
        )

    def _select_prompt_template(self, query: str, docs: List[Any]) -> str:
        """Chọn template prompt phù hợp dựa trên nội dung query và tài liệu

        Args:
            query: Câu truy vấn
            docs: Danh sách tài liệu liên quan

        Returns:
            Template prompt phù hợp
        """
        # Phát hiện yêu cầu tạo SQL
        sql_generation_keywords = [
            "viết sql",
            "tạo sql",
            "generate sql",
            "create query",
            "write a query",
            "viết truy vấn",
        ]
        if any(kw in query.lower() for kw in sql_generation_keywords):
            return get_sql_generation_prompt

        # Phát hiện phân tích schema
        schema_keywords = [
            "phân tích schema",
            "analyze schema",
            "đánh giá thiết kế",
            "evaluate design",
            "database design",
        ]
        if any(kw in query.lower() for kw in schema_keywords):
            return get_schema_analysis_prompt

        # Phát hiện tài liệu SQL trong context
        has_sql_docs = False
        for doc in docs:
            if "sql_document_type" in doc.metadata or "sql_type" in doc.metadata:
                has_sql_docs = True
                break

        # Sử dụng prompt CSDL nếu có tài liệu SQL
        if has_sql_docs:
            return get_database_query_prompt

        # Mặc định dùng prompt cơ sở dữ liệu vì đây là hệ thống chuyên về CSDL
        return get_database_query_prompt

    def _process_sql_in_response(self, text: str) -> str:
        """Xử lý và đánh dấu các đoạn code SQL trong câu trả lời

        Args:
            text: Văn bản câu trả lời từ LLM

        Returns:
            Văn bản đã được xử lý với các đoạn code SQL được đánh dấu
        """
        # Pattern để tìm các đoạn code nằm giữa các dấu backtick hoặc trong block code
        # Cần xử lý cả 2 trường hợp:
        # 1. ```sql ... ``` hoặc ```SQL ... ```
        # 2. ```... các lệnh SQL ...```
        # 3. `... các lệnh SQL ...`

        # Xử lý trường hợp code block có đánh dấu SQL
        sql_block_pattern = r"```(?:sql|SQL)(.*?)```"
        # Tìm tất cả các khối code đã được đánh dấu sql và đảm bảo rằng chúng vẫn được đánh dấu đúng
        processed_text = re.sub(
            sql_block_pattern, r"```sql\1```", text, flags=re.DOTALL
        )

        # Xử lý trường hợp code block không đánh dấu cụ thể ngôn ngữ
        unmarked_block_pattern = r"```(?!\w)(.*?)```"

        def process_unmarked_block(match):
            content = match.group(1)
            # Kiểm tra xem khối này có phải là SQL hay không
            sql_keywords = [
                r"\bSELECT\b",
                r"\bFROM\b",
                r"\bWHERE\b",
                r"\bJOIN\b",
                r"\bGROUP BY\b",
                r"\bORDER BY\b",
                r"\bHAVING\b",
                r"\bUNION\b",
                r"\bINSERT INTO\b",
                r"\bVALUES\b",
                r"\bUPDATE\b",
                r"\bSET\b",
                r"\bDELETE FROM\b",
                r"\bCREATE TABLE\b",
                r"\bALTER TABLE\b",
                r"\bDROP TABLE\b",
                r"\bINDEX\b",
                r"\bTRIGGER\b",
                r"\bVIEW\b",
            ]

            # Đếm số lượng từ khóa SQL trong nội dung
            sql_keyword_count = sum(
                1
                for keyword in sql_keywords
                if re.search(keyword, content, re.IGNORECASE)
            )

            # Nếu có ít nhất 2 từ khóa SQL phổ biến, thì đánh dấu là SQL
            if sql_keyword_count >= 2:
                return f"```sql{content}```"
            return f"```{content}```"

        # Áp dụng xử lý cho các code block không đánh dấu
        processed_text = re.sub(
            unmarked_block_pattern,
            process_unmarked_block,
            processed_text,
            flags=re.DOTALL,
        )

        # Xử lý các đoạn code nằm trong dấu backtick đơn
        inline_code_pattern = r"`([^`]+)`"

        def process_inline_code(match):
            content = match.group(1)
            # Kiểm tra từ khóa SQL phổ biến
            sql_keywords = [
                "SELECT",
                "FROM",
                "WHERE",
                "JOIN",
                "INSERT",
                "UPDATE",
                "DELETE",
            ]

            # Nếu đoạn code inline có vẻ là một câu lệnh SQL đơn giản
            if any(
                keyword in content.upper() for keyword in sql_keywords
            ) and re.search(
                r"\b(SELECT|INSERT|UPDATE|DELETE)\b", content, re.IGNORECASE
            ):
                # Chuyển đổi thành dấu backtick triple nếu là SQL
                return f"```sql\n{content}\n```"
            return f"`{content}`"

        # Áp dụng xử lý cho các đoạn code inline
        processed_text = re.sub(
            inline_code_pattern, process_inline_code, processed_text
        )

        return processed_text

    @measure_time
    def query(self, query_text: str) -> Dict[str, Any]:
        """Truy vấn RAG Pipeline

        Args:
            query_text: Câu truy vấn người dùng

        Returns:
            Dict chứa câu trả lời và các thông tin bổ sung
        """
        # Khởi tạo kết quả mặc định
        result = {
            "text": "",
            "sources": [],
            "prompt": "",
            "query": query_text,
            "model": "",
            "temperature": 0.0,
            "total_sources": 0,
            "retrieval_time": 0.0,
            "llm_time": 0.0,
        }

        # Kiểm tra xem collection có tồn tại không
        if not self.vector_store_manager.client.collection_exists(
            self.vector_store_manager.collection_name
        ):
            print(
                f"⚠️ Collection {self.vector_store_manager.collection_name} không tồn tại. Vui lòng tạo index trước."
            )
            result["text"] = (
                "Không thể truy vấn vì chưa có dữ liệu. Vui lòng tạo index trước bằng lệnh: python -m src.main index --data-dir ./data"
            )
            return result

        # Đảm bảo vectorstore đã được khởi tạo
        if self.vectorstore is None:
            self._reinitialize_vectorstore()
            # Nếu vẫn không khởi tạo được
            if self.vectorstore is None:
                result["text"] = (
                    "Không thể kết nối đến vector store. Vui lòng kiểm tra lại cấu hình và kết nối."
                )
                return result

        # Kiểm tra xem collection có chứa dữ liệu không
        try:
            collection_info = self.vector_store_manager.client.get_collection(
                self.vector_store_manager.collection_name
            )
            vector_count = collection_info.vectors_count
            if vector_count == 0:
                print(
                    f"⚠️ Collection {self.vector_store_manager.collection_name} rỗng (0 vectors)"
                )
                result["text"] = (
                    "Không thể truy vấn vì chưa có dữ liệu trong vector store. Vui lòng upload và index tài liệu trước."
                )
                return result
        except Exception as e:
            print(f"⚠️ Lỗi khi kiểm tra dữ liệu trong collection: {str(e)}")
            result["text"] = f"Lỗi khi kiểm tra dữ liệu: {str(e)}"
            return result

        # 1. Kiểm tra nếu cần sử dụng multi-step reasoning
        if USE_SELF_QUERY and self.reasoner:
            is_complex = self.reasoner.decomposer._is_complex_query(query_text)
            if is_complex:
                print(f"ℹ️ Phát hiện truy vấn phức tạp, sử dụng multi-step reasoning")
                reasoning_result = self.reasoner.answer_with_reasoning(query_text)

                # Xử lý và đánh dấu code SQL trong câu trả lời
                reasoning_result["answer"] = self._process_sql_in_response(
                    reasoning_result["answer"]
                )

                result["text"] = reasoning_result["answer"]
                result["reasoning_steps"] = reasoning_result.get("reasoning_steps", [])
                result["retrieval_time"] = 0
                result["llm_time"] = 0
                result["used_reasoning"] = True

                return result

        # 2. Lấy tài liệu liên quan
        retrieval_start = time.time()

        # Sử dụng RAG Fusion nếu được bật, nếu không sử dụng retriever thông thường
        if self.fusion and QUERY_EXPANSION_ENABLED:
            # Sử dụng fusion.retrieve() trong FAST_MODE để tránh rerank hai lần
            # fusion.retrieve sẽ tự động sử dụng reranker nếu RERANK_RETRIEVAL_RESULTS=True
            relevant_docs = self.fusion.retrieve(query_text)
        else:
            # Nếu sử dụng HybridRetriever, retrieve đã được override để sử dụng hybrid_retrieve
            relevant_docs = self.retriever.retrieve(query_text)

        retrieval_end = time.time()
        result["retrieval_time"] = retrieval_end - retrieval_start

        # 3. Tạo câu trả lời với LLM
        llm_start = time.time()

        # Chọn prompt template phù hợp
        prompt_template = self._select_prompt_template(query_text, relevant_docs)

        # Tạo response với LLM
        response_dict = self.llm.generate_response(
            query_text, relevant_docs, prompt_template=prompt_template
        )

        llm_end = time.time()
        result["llm_time"] = llm_end - llm_start

        # 4. Gộp kết quả từ LLM vào kết quả cuối cùng
        result.update(response_dict)

        # 5. Xử lý và đánh dấu code SQL trong câu trả lời
        if "text" in result and result["text"]:
            result["text"] = self._process_sql_in_response(result["text"])

        # 6. Bổ sung thông tin thêm
        result["query"] = query_text
        result["total_tokens"] = len(query_text.split()) + len(result["text"].split())
        result["used_reasoning"] = False

        # Thêm thông tin về phương pháp retrieval đã sử dụng
        result["retrieval_method"] = "hybrid" if USE_HYBRID_SEARCH else "vector"
        if self.fusion and QUERY_EXPANSION_ENABLED:
            result["retrieval_method"] += "_fusion"

        return result
