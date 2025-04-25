from src.embeddings import initialize_embeddings
from src.loaders import DocumentLoader
from src.processors import DocumentProcessor
from src.vectorstore import VectorStoreManager
from src.retrieval import Retriever
from src.llm import GeminiLLM
from src.utils import measure_time


class RAGPipeline:
    """Lớp chính quản lý toàn bộ pipeline RAG"""

    def __init__(self):
        """Khởi tạo các thành phần của pipeline"""
        print("⏳ Đang khởi tạo RAG Pipeline...")
        # Khởi tạo và kiểm tra các thành phần của pipeline
        self.embeddings = initialize_embeddings()
        self.processor = DocumentProcessor(self.embeddings)
        self.vector_store_manager = VectorStoreManager(self.embeddings)
        self.vectorstore = self.vector_store_manager.get_vectorstore()
        self.retriever = Retriever(self.vectorstore)
        self.llm = GeminiLLM()
        print("✅ RAG Pipeline đã được khởi tạo thành công!")

    def _reinitialize_vectorstore(self):
        """Khởi tạo lại vectorstore và retriever"""
        print("🔄 Đang khởi tạo lại vector store...")
        self.vectorstore = self.vector_store_manager.get_vectorstore()
        self.retriever = Retriever(self.vectorstore)
        print("✅ Đã khởi tạo lại vector store!")

    @measure_time
    def index_data(self, data_directory: str):
        """Thực hiện quá trình indexing dữ liệu"""
        # 1. Load tài liệu
        documents = DocumentLoader.load_documents(data_directory)

        # 2. Chunk tài liệu
        chunks = self.processor.chunk_documents(documents)

        # 3. Cluster & merge để cải thiện chất lượng
        merged_docs = self.processor.cluster_and_merge(chunks)

        # 4. Upload vào vector store
        self.vector_store_manager.upload_documents(merged_docs)

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

        # Khởi tạo lại vectorstore nếu có point bị xóa
        if deleted_count > 0:
            self._reinitialize_vectorstore()

        print(f"✅ Đã xóa {deleted_count} point liên quan đến file: {file_path}")

        return deleted_count

    @measure_time
    def delete_index(self, collection_name=None):
        """Xóa toàn bộ index trong vector store"""
        self.vector_store_manager.delete_collection(collection_name)
        # Khởi tạo lại vectorstore
        self._reinitialize_vectorstore()
        print("⚠️ Lưu ý: Bạn cần tạo lại index trước khi thực hiện truy vấn.")

    @measure_time
    def query(self, query_text: str) -> str:
        """Truy vấn RAG Pipeline"""
        # Kiểm tra xem collection có tồn tại không
        if not self.vector_store_manager.client.collection_exists(
            self.vector_store_manager.collection_name
        ):
            print(
                f"⚠️ Collection {self.vector_store_manager.collection_name} không tồn tại. Vui lòng tạo index trước."
            )
            return "Không thể truy vấn vì chưa có dữ liệu. Vui lòng tạo index trước bằng lệnh: python -m src.main index --data-dir ./data"

        # Đảm bảo vectorstore đã được khởi tạo
        if self.vectorstore is None:
            self._reinitialize_vectorstore()
            # Nếu vẫn không khởi tạo được
            if self.vectorstore is None:
                return "Không thể kết nối đến vector store. Vui lòng kiểm tra lại cấu hình và kết nối."

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
                return "Không thể truy vấn vì chưa có dữ liệu trong vector store. Vui lòng upload và index tài liệu trước."
        except Exception as e:
            print(f"⚠️ Lỗi khi kiểm tra dữ liệu trong collection: {str(e)}")

        # 1. Lấy tài liệu liên quan
        relevant_docs = self.retriever.retrieve(query_text)

        # 2. Tạo câu trả lời với LLM
        response = self.llm.generate_response(query_text, relevant_docs)

        return response
