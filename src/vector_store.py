from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter
from typing import List, Dict
import os
from dotenv import load_dotenv
import uuid
import time

# Load biến môi trường từ .env
load_dotenv()


class VectorStore:
    """Lớp quản lý kho lưu trữ vector với Qdrant"""

    def __init__(
        self,
        url=None,
        api_key=None,
        collection_name=None,
    ):
        """Khởi tạo Qdrant client"""
        # Lấy URL và API key từ môi trường hoặc tham số
        qdrant_url = url or os.getenv("QDRANT_URL")
        qdrant_api_key = api_key or os.getenv("QDRANT_API_KEY")

        # Kiểm tra xem có URL và API key không
        if not qdrant_url or not qdrant_api_key:
            raise ValueError(
                "QDRANT_URL và QDRANT_API_KEY phải được cung cấp trong file .env hoặc trong tham số khởi tạo"
            )

        # Khởi tạo Qdrant client
        self.client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key,
            prefer_grpc=False,
            https=True,
        )

        self.collection_name = collection_name or os.getenv(
            "QDRANT_COLLECTION_NAME", "csdl_rag_e5_base"
        )

    def ensure_collection_exists(self, vector_size):
        """Đảm bảo collection tồn tại trong Qdrant"""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

    def index_documents(self, chunks, embeddings, user_id="default_user"):
        """Index dữ liệu lên Qdrant"""
        start_time = time.time()
        print(f"[INDEX] Bắt đầu index {len(chunks)} chunks với user_id={user_id}")

        # Đảm bảo collection có tồn tại
        if not self.client.collection_exists(self.collection_name):
            vector_size = (
                len(embeddings[0]) if embeddings and len(embeddings) > 0 else 768
            )
            print(
                f"[INDEX] Collection {self.collection_name} chưa tồn tại, tạo mới với size={vector_size}"
            )
            self.ensure_collection_exists(vector_size)

        points = []
        for idx, chunk in enumerate(chunks):
            # Tạo ID ngẫu nhiên cho mỗi điểm để tránh ghi đè
            point_id = str(uuid.uuid4())

            # Đảm bảo source có trong cả payload trực tiếp và metadata
            source = chunk.get("source", "unknown")

            # Đảm bảo metadata là một dict
            if "metadata" not in chunk or not isinstance(chunk["metadata"], dict):
                chunk["metadata"] = {}

            # Đảm bảo source cũng có trong metadata và thêm user_id
            chunk["metadata"]["source"] = source
            chunk["metadata"]["user_id"] = user_id  # Thêm user_id vào metadata
            # Thêm timestamp để theo dõi
            chunk["metadata"]["indexed_at"] = int(time.time())

            # In thông tin để debug nếu là chunk đầu tiên hoặc mỗi 50 chunks
            if idx == 0 or idx % 50 == 0 or idx == len(chunks) - 1:
                print(
                    f"[INDEX] Indexing chunk {idx}/{len(chunks)}: id={point_id}, source={source}, user_id={user_id}"
                )

            points.append(
                PointStruct(
                    id=point_id,  # Sử dụng ID ngẫu nhiên
                    vector=embeddings[idx].tolist(),
                    payload={
                        "text": chunk["text"],
                        "metadata": chunk["metadata"],
                        "source": source,  # Lưu source trực tiếp trong payload
                        "user_id": user_id,  # Thêm user_id trực tiếp trong payload
                        "indexed_at": int(time.time()),  # Thêm timestamp
                    },
                )
            )

        # Upload theo batch
        batch_size = 100
        total_batches = (len(points) + batch_size - 1) // batch_size
        print(
            f"[INDEX] Uploading {len(points)} points in {total_batches} batches (batch_size={batch_size})"
        )

        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            batch_num = i // batch_size + 1
            print(
                f"[INDEX] Uploading batch {batch_num}/{total_batches} ({len(batch)} points)"
            )
            try:
                result = self.client.upsert(
                    collection_name=self.collection_name, points=batch
                )
                print(f"[INDEX] Batch {batch_num} uploaded successfully: {result}")
            except Exception as e:
                print(f"[INDEX] Error in batch {batch_num}: {str(e)}")
                # Tiếp tục với batch tiếp theo thay vì dừng lại

        # In thống kê indexing
        end_time = time.time()
        duration = end_time - start_time
        print(
            f"[INDEX] Completed indexing {len(chunks)} chunks in {duration:.2f} seconds"
        )

        # Kiểm tra số lượng điểm trong collection sau khi index
        try:
            collection_info = self.get_collection_info()
            if collection_info:
                print(
                    f"[INDEX] Collection now has {collection_info.get('points_count', 'unknown')} points"
                )
        except Exception as e:
            print(f"[INDEX] Error getting collection info: {str(e)}")

    def search(self, query_vector, limit=5):
        """Tìm kiếm trong Qdrant"""
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            with_payload=True,
        )

        return [
            {
                "text": hit.payload["text"],
                "metadata": hit.payload["metadata"],
                "score": hit.score,
            }
            for hit in results
        ]

    def search_with_filter(self, query_vector, sources=None, user_id=None, limit=5):
        """Tìm kiếm trong Qdrant với filter theo nguồn tài liệu và user_id"""
        # Nếu không có danh sách nguồn và user_id, sử dụng search thông thường
        if not sources and not user_id:
            return self.search(query_vector, limit)

        # Xử lý danh sách nguồn để hỗ trợ so sánh với cả tên file đơn thuần và đường dẫn
        normalized_sources = []
        if sources:
            for source in sources:
                normalized_sources.append(source)  # Giữ nguyên source gốc
                # Thêm tên file đơn thuần (nếu source chứa đường dẫn)
                if os.path.sep in source:
                    filename = os.path.basename(source)
                    if filename and filename not in normalized_sources:
                        normalized_sources.append(filename)

        print(
            f"Tìm kiếm với sources={sources}, normalized_sources={normalized_sources}, user_id={user_id}"
        )

        # Lấy nhiều kết quả hơn để đảm bảo đủ sau khi lọc
        results = self.search(query_vector, limit=limit * 3)

        # Lọc kết quả theo nguồn và user_id
        filtered_results = []
        for result in results:
            # Kiểm tra source trong cả metadata và trực tiếp trong kết quả
            meta_source = result.get("metadata", {}).get("source", "unknown")
            direct_source = result.get("source", "unknown")
            meta_user_id = result.get("metadata", {}).get("user_id", "unknown")
            direct_user_id = result.get("user_id", "unknown")

            # Extract filename từ source nếu có đường dẫn
            meta_filename = (
                os.path.basename(meta_source) if meta_source != "unknown" else "unknown"
            )
            direct_filename = (
                os.path.basename(direct_source)
                if direct_source != "unknown"
                else "unknown"
            )

            # Kiểm tra điều kiện user_id
            user_id_match = True
            if user_id:
                user_id_match = meta_user_id == user_id or direct_user_id == user_id

            # Kiểm tra điều kiện source
            source_match = True
            if normalized_sources:
                source_match = (
                    meta_source in normalized_sources
                    or direct_source in normalized_sources
                    or meta_filename in normalized_sources
                    or direct_filename in normalized_sources
                )

            # Nếu thỏa mãn cả hai điều kiện
            if source_match and user_id_match:
                filtered_results.append(result)

                # Nếu đã đủ số kết quả cần thiết, dừng lại
                if len(filtered_results) >= limit:
                    break

        return filtered_results

    def get_all_documents(self, limit=1000):
        """Lấy tất cả tài liệu từ collection"""
        try:
            # Kiểm tra xem collection có tồn tại không
            collection_info = self.get_collection_info()
            if not collection_info:
                print(f"Collection {self.collection_name} không tồn tại")
                return []

            points_count = collection_info.get("points_count", 0)
            if points_count == 0:
                print(f"Collection {self.collection_name} không có dữ liệu")
                return []

            # Giới hạn số lượng tài liệu trả về nếu quá lớn
            actual_limit = min(limit, points_count)

            # Scroll để lấy tất cả points
            results = self.client.scroll(
                collection_name=self.collection_name,
                limit=actual_limit,
                with_payload=True,
                with_vectors=False,  # Không cần vector vì chỉ dùng văn bản
            )

            points, next_offset = results

            # Chuyển đổi thành định dạng chuẩn
            documents = [
                {
                    "text": point.payload["text"],
                    "metadata": point.payload["metadata"],
                    "source": point.payload.get("source", "unknown"),
                }
                for point in points
            ]

            return documents

        except Exception as e:
            print(f"Lỗi khi lấy tất cả tài liệu: {str(e)}")
            return []

    def delete_collection(self):
        """Xóa collection trong Qdrant"""
        self.client.delete_collection(self.collection_name)

    def get_collection_info(self):
        """Lấy thông tin collection"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return collection_info.dict()
        except Exception as e:
            print(f"Lỗi khi lấy thông tin collection: {str(e)}")
            return None

    def get_document_by_category(self, category, limit=100):
        """Lấy tài liệu theo danh mục (SQL, NoSQL, ...)"""
        try:
            # Tạo bộ lọc theo danh mục
            category_filter = Filter(
                must=[{"key": "metadata.category", "match": {"value": category}}]
            )

            # Scroll với filter
            results = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                with_payload=True,
                with_vectors=False,
                filter=category_filter,
            )

            points, next_offset = results

            # Chuyển đổi thành định dạng chuẩn
            documents = [
                {
                    "text": point.payload["text"],
                    "metadata": point.payload["metadata"],
                    "source": point.payload.get("source", "unknown"),
                }
                for point in points
            ]

            return documents

        except Exception as e:
            print(f"Lỗi khi lấy tài liệu theo danh mục: {str(e)}")
            return []

    def delete_points(self, point_ids: List[str]) -> bool:
        """
        Xóa các điểm cụ thể từ collection theo danh sách ID

        Args:
            point_ids: Danh sách ID của các điểm cần xóa

        Returns:
            True nếu xóa thành công, False nếu có lỗi
        """
        try:
            print(
                f"[VECTOR_STORE] Bắt đầu xóa {len(point_ids)} điểm. ID mẫu: {point_ids[:3] if len(point_ids) > 3 else point_ids}"
            )

            if not self.client.collection_exists(self.collection_name):
                print(
                    f"[VECTOR_STORE] Lỗi: Collection {self.collection_name} không tồn tại"
                )
                return False

            # Xóa từng điểm từ collection
            delete_result = self.client.collection(self.collection_name).delete(
                points_selector=models.PointIdsList(
                    points=point_ids,
                )
            )
            print(f"[VECTOR_STORE] Kết quả xóa điểm: {delete_result}")
            return True
        except Exception as e:
            print(f"[VECTOR_STORE] Lỗi khi xóa điểm từ vector store: {str(e)}")
            import traceback

            traceback_str = traceback.format_exc()
            print(f"[VECTOR_STORE] Traceback: {traceback_str}")
            return False

    def delete_points_by_filter(self, filter_dict):
        """
        Xóa các điểm theo filter

        Args:
            filter_dict: Dictionary chứa filter theo định dạng của Qdrant

        Returns:
            Tuple (success, message) với success là True nếu xóa thành công
        """
        try:
            print(f"[VECTOR_STORE] Bắt đầu xóa điểm theo filter: {filter_dict}")

            if not self.client.collection_exists(self.collection_name):
                print(
                    f"[VECTOR_STORE] Lỗi: Collection {self.collection_name} không tồn tại"
                )
                return False, "Collection không tồn tại"

            # Trước khi xóa, hãy đếm số lượng điểm khớp với filter
            try:
                # Lấy thông tin collection trước khi xóa
                info_before = self.client.get_collection(self.collection_name)
                points_before = info_before.points_count
                print(f"[VECTOR_STORE] Số điểm trước khi xóa: {points_before}")

                # Thử đếm số điểm khớp với filter
                if "filter" in filter_dict:
                    print(f"[VECTOR_STORE] Đang đếm số điểm khớp với filter...")
                    count_results = self.client.count(
                        collection_name=self.collection_name,
                        count_filter=models.Filter(**filter_dict["filter"]),
                    )
                    print(
                        f"[VECTOR_STORE] Số điểm khớp với filter: {count_results.count}"
                    )
            except Exception as count_e:
                print(f"[VECTOR_STORE] Lỗi khi đếm số điểm: {str(count_e)}")

            # Xóa điểm từ collection theo filter
            print(f"[VECTOR_STORE] Thực hiện xóa điểm theo filter...")
            result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(filter=filter_dict["filter"]),
            )

            print(f"[VECTOR_STORE] Kết quả xóa điểm: {result}")

            # Sau khi xóa, kiểm tra số lượng điểm còn lại
            try:
                info_after = self.client.get_collection(self.collection_name)
                points_after = info_after.points_count
                points_deleted = points_before - points_after
                print(f"[VECTOR_STORE] Số điểm sau khi xóa: {points_after}")
                print(f"[VECTOR_STORE] Số điểm đã xóa: {points_deleted}")
                return True, f"Đã xóa {points_deleted} điểm"
            except Exception as e:
                print(f"[VECTOR_STORE] Lỗi khi kiểm tra sau khi xóa: {str(e)}")
                return True, f"Đã xóa {result.deleted} điểm"

        except Exception as e:
            print(f"[VECTOR_STORE] Lỗi khi xóa điểm theo filter: {str(e)}")
            import traceback

            traceback_str = traceback.format_exc()
            print(f"[VECTOR_STORE] Traceback: {traceback_str}")
            return False, f"Lỗi khi xóa điểm theo filter: {str(e)}"
