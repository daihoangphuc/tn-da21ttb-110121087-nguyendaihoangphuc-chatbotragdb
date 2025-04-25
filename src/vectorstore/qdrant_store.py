from typing import List, Dict, Any, Optional
from langchain.schema import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

from src.config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME, QDRANT_BATCH_SIZE
from src.utils import measure_time


class VectorStoreManager:
    """Lớp quản lý vector store Qdrant"""

    def __init__(self, embeddings):
        """Khởi tạo kết nối đến Qdrant"""
        self.embeddings = embeddings
        self.client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        self.collection_name = COLLECTION_NAME

    def initialize_collection(self):
        """Khởi tạo collection nếu chưa tồn tại"""
        if not self.client.collection_exists(self.collection_name):
            embedding_size = len(self.embeddings.embed_query("test"))
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=embedding_size, distance=Distance.COSINE
                ),
            )
            print(f"✅ Đã tạo collection mới: {self.collection_name}")
        else:
            print(f"ℹ️ Collection {self.collection_name} đã tồn tại.")

    @measure_time
    def delete_collection(self, collection_name=None):
        """Xóa toàn bộ index trong vector store"""
        target_collection = collection_name or self.collection_name
        if self.client.collection_exists(target_collection):
            self.client.delete_collection(collection_name=target_collection)
            print(f"✅ Đã xóa collection: {target_collection}")
        else:
            print(f"ℹ️ Collection {target_collection} không tồn tại.")

    @measure_time
    def upload_documents(self, docs: List[Document], batch_size=None):
        """Upload tài liệu vào vector store với batching

        Args:
            docs: Danh sách tài liệu cần upload
            batch_size: Kích thước batch, mặc định sử dụng từ cấu hình
        """
        # Sử dụng giá trị từ cấu hình nếu không chỉ định batch_size
        if batch_size is None:
            batch_size = QDRANT_BATCH_SIZE

        print(
            f"⏳ Đang upsert {len(docs)} tài liệu vào Qdrant (batch size: {batch_size})..."
        )

        # Đảm bảo collection tồn tại
        self.initialize_collection()

        # Xử lý theo batch để tăng hiệu suất
        for i in range(0, len(docs), batch_size):
            batch_docs = docs[i : i + batch_size]

            # Thực hiện embedding cho batch hiện tại
            batch_texts = [doc.page_content for doc in batch_docs]
            batch_embeddings = self.embeddings.embed_documents(batch_texts)

        # Tạo các point để upsert
        points = [
            PointStruct(
                id=i + j,  # Tính ID tương đối với vị trí trong toàn bộ danh sách
                vector=embedding,
                payload={
                    "text": doc.page_content,
                    # Lưu thêm thông tin nguồn gốc từ metadata
                    "source_file": doc.metadata.get("source", ""),
                    "source_path": doc.metadata.get("source_path", ""),
                    "file_path": doc.metadata.get("file_path", ""),
                    "metadata": doc.metadata,
                },
            )
            for j, (doc, embedding) in enumerate(zip(batch_docs, batch_embeddings))
        ]

        # Upsert batch vào Qdrant
        self.client.upsert(collection_name=self.collection_name, points=points)

        # In tiến độ
        print(f"  ↳ Đã xử lý {min(i+batch_size, len(docs))}/{len(docs)} tài liệu")

        print(f"✅ Hoàn thành upsert {len(docs)} tài liệu vào Qdrant.")

    @measure_time
    def delete_points_by_file(self, file_path: str) -> int:
        """Xóa các point dựa trên đường dẫn file

        Args:
            file_path: Đường dẫn file cần xóa các point tương ứng

        Returns:
            Số lượng point đã xóa
        """
        print(f"⏳ Đang xóa các point của file: {file_path}")

        # Kiểm tra collection có tồn tại không
        if not self.client.collection_exists(self.collection_name):
            print(f"ℹ️ Collection {self.collection_name} không tồn tại.")
            return 0

        # Tạo filter để xóa theo đường dẫn file
        file_filter = Filter(
            should=[
                FieldCondition(key="file_path", match=MatchValue(value=file_path)),
                FieldCondition(key="source_path", match=MatchValue(value=file_path)),
            ]
        )

        # Lấy số lượng point trước khi xóa
        before_count = self.client.count(
            collection_name=self.collection_name, count_filter=file_filter
        ).count

        if before_count == 0:
            print(f"ℹ️ Không tìm thấy point nào từ file: {file_path}")
            return 0

        # Thực hiện xóa các point
        self.client.delete(
            collection_name=self.collection_name, points_selector=file_filter
        )

        # Kiểm tra số lượng point sau khi xóa
        after_count = self.client.count(
            collection_name=self.collection_name, count_filter=file_filter
        ).count

        deleted_count = before_count - after_count
        print(f"✅ Đã xóa {deleted_count} point của file: {file_path}")

        return deleted_count

    @measure_time
    def search_by_file(self, file_path: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Tìm kiếm các point được tạo từ một file cụ thể

        Args:
            file_path: Đường dẫn file cần tìm
            limit: Số lượng point tối đa cần trả về

        Returns:
            Danh sách các point được tìm thấy
        """
        # Kiểm tra collection có tồn tại không
        if not self.client.collection_exists(self.collection_name):
            print(f"ℹ️ Collection {self.collection_name} không tồn tại.")
            return []

        # Tạo filter để tìm kiếm theo đường dẫn file
        file_filter = Filter(
            should=[
                FieldCondition(key="file_path", match=MatchValue(value=file_path)),
                FieldCondition(key="source_path", match=MatchValue(value=file_path)),
            ]
        )

        # Thực hiện tìm kiếm
        results = self.client.scroll(
            collection_name=self.collection_name, scroll_filter=file_filter, limit=limit
        )[0]

        print(f"ℹ️ Tìm thấy {len(results)} point từ file: {file_path}")

        return results

    def get_vectorstore(self) -> QdrantVectorStore:
        """Trả về QdrantVectorStore để sử dụng làm retriever"""
        try:
            # Chỉ tạo QdrantVectorStore nếu collection tồn tại
            if not self.client.collection_exists(self.collection_name):
                print(
                    f"⚠️ Collection {self.collection_name} chưa tồn tại, hệ thống sẽ tự động tạo khi index dữ liệu."
                )
                # Tạo collection trống
                self.initialize_collection()

            return QdrantVectorStore(
                client=self.client,
                collection_name=self.collection_name,
                embedding=self.embeddings,
                content_payload_key="text",
            )
        except Exception as e:
            print(f"⚠️ Lỗi khi tạo vector store: {str(e)}")
            # Trả về một vectorstore giả để tránh lỗi
            return None
