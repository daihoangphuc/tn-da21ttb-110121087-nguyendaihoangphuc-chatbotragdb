from qdrant_client import QdrantClient, models
import logging
import numpy as np

# Cấu hình logging
logging.basicConfig(format="[Vector Store] %(message)s", level=logging.INFO)
# Ghi đè hàm print để thêm prefix
original_print = print


def print(*args, **kwargs):
    prefix = "[Vector Store] "
    original_print(prefix + " ".join(map(str, args)), **kwargs)


logger = logging.getLogger(__name__)
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
        user_id=None,
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

        # Lưu user_id và collection_name nếu có
        self.user_id = user_id
        self.collection_name = collection_name

        # Nếu đã có cả user_id và collection_name, thì ghi log
        if user_id and collection_name:
            print(
                f"Khởi tạo Vector Store với collection: {self.collection_name} cho user: {user_id}"
            )
        # Nếu chỉ có user_id, tạo collection_name từ user_id
        elif user_id:
            self.collection_name = f"user_{user_id}"
            print(f"Khởi tạo Vector Store với collection: {self.collection_name}")
        # Nếu không có gì cả, chỉ khởi tạo client
        else:
            print(
                "Khởi tạo Vector Store mà không chỉ định collection. Collection sẽ được xác định khi thao tác với cụ thể user_id."
            )

    def get_collection_name_for_user(self, user_id):
        """Lấy tên collection cho user_id cụ thể"""
        if not user_id:
            raise ValueError("user_id là bắt buộc để xác định collection")

        # Cập nhật user_id và collection_name hiện tại
        if self.user_id != user_id:
            self.user_id = user_id
            self.collection_name = f"user_{user_id}"

        return self.collection_name

    def ensure_collection_exists(self, vector_size, user_id=None):
        """Đảm bảo collection tồn tại trong Qdrant"""
        # Nếu có user_id mới, cập nhật collection_name
        if user_id and user_id != self.user_id:
            self.collection_name = self.get_collection_name_for_user(user_id)

        # Nếu không có collection_name, không thực hiện gì cả và trả về False
        if not self.collection_name:
            print(
                "THÔNG BÁO: Bỏ qua tạo collection vì chưa có collection_name hoặc user_id"
            )
            return False

        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            print(
                f"Tạo collection mới: {self.collection_name} với vector_size={vector_size}"
            )
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            return True
        else:
            print(f"Collection {self.collection_name} đã tồn tại")
            return True

    def index_documents(self, chunks, embeddings, user_id):
        """Index dữ liệu lên Qdrant"""
        start_time = time.time()

        # Kiểm tra user_id phải được cung cấp
        if not user_id:
            raise ValueError(
                "user_id là bắt buộc để xác định collection cho từng người dùng"
            )

        # Cập nhật collection_name nếu user_id khác hoặc chưa có collection_name
        if self.user_id != user_id or not self.collection_name:
            self.collection_name = self.get_collection_name_for_user(user_id)
            print(
                f"[INDEX] Sử dụng collection: {self.collection_name} cho user_id: {user_id}"
            )

        print(
            f"[INDEX] Bắt đầu index {len(chunks)} chunks vào collection {self.collection_name}"
        )

        # Đảm bảo collection có tồn tại
        if not self.client.collection_exists(self.collection_name):
            # Lấy kích thước vector an toàn
            vector_size = 768  # Giá trị mặc định
            if embeddings is not None and len(embeddings) > 0:
                if isinstance(embeddings[0], (list, np.ndarray)):
                    # Kiểm tra xem embeddings[0] có phải là mảng hoặc danh sách
                    vector_size = len(embeddings[0])
                else:
                    print(
                        "[INDEX] Cảnh báo: embeddings[0] không phải là mảng như mong đợi"
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

            # Đảm bảo source cũng có trong metadata
            chunk["metadata"]["source"] = source
            # Thêm timestamp để theo dõi
            chunk["metadata"]["indexed_at"] = int(time.time())

            # In thông tin để debug nếu là chunk đầu tiên hoặc mỗi 50 chunks
            if idx == 0 or idx % 50 == 0 or idx == len(chunks) - 1:
                print(
                    f"[INDEX] Indexing chunk {idx}/{len(chunks)}: id={point_id}, source={source}"
                )

            # Đảm bảo embedding là danh sách trước khi thêm vào points
            current_embedding = embeddings[idx]
            if isinstance(current_embedding, np.ndarray):
                current_embedding = current_embedding.tolist()

            points.append(
                PointStruct(
                    id=point_id,  # Sử dụng ID ngẫu nhiên
                    vector=current_embedding,
                    payload={
                        "text": chunk["text"],
                        "metadata": chunk["metadata"],
                        "source": source,  # Lưu source trực tiếp trong payload
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

    def search(self, query_vector, limit=5, user_id=None):
        """Tìm kiếm trong Qdrant"""
        # Cập nhật collection_name nếu có user_id mới
        if user_id and user_id != self.user_id:
            self.collection_name = self.get_collection_name_for_user(user_id)

        if not self.collection_name:
            raise ValueError(
                "collection_name không được để trống. Cần user_id để xác định collection."
            )

        if not self.client.collection_exists(self.collection_name):
            print(f"Collection {self.collection_name} không tồn tại")
            return []

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
        """Tìm kiếm trong Qdrant với filter theo nguồn tài liệu"""
        # Cập nhật collection_name nếu có user_id mới
        if user_id and user_id != self.user_id:
            self.collection_name = self.get_collection_name_for_user(user_id)

        if not self.collection_name:
            raise ValueError(
                "collection_name không được để trống. Cần user_id để xác định collection."
            )

        if not self.client.collection_exists(self.collection_name):
            print(f"Collection {self.collection_name} không tồn tại")
            return []

        # Nếu không có danh sách nguồn, sử dụng search thông thường
        if not sources:
            return self.search(query_vector, limit, user_id)

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
            f"Tìm kiếm với sources={sources}, normalized_sources={normalized_sources}"
        )

        # Lấy nhiều kết quả hơn để đảm bảo đủ sau khi lọc
        results = self.search(query_vector, limit=limit * 3, user_id=user_id)

        # Lọc kết quả theo nguồn
        filtered_results = []
        for result in results:
            # Kiểm tra source trong cả metadata và trực tiếp trong kết quả
            meta_source = result.get("metadata", {}).get("source", "unknown")
            direct_source = result.get("source", "unknown")

            # Extract filename từ source nếu có đường dẫn
            meta_filename = (
                os.path.basename(meta_source) if meta_source != "unknown" else "unknown"
            )
            direct_filename = (
                os.path.basename(direct_source)
                if direct_source != "unknown"
                else "unknown"
            )

            # Kiểm tra điều kiện source
            source_match = (
                meta_source in normalized_sources
                or direct_source in normalized_sources
                or meta_filename in normalized_sources
                or direct_filename in normalized_sources
            )

            # Nếu thỏa mãn điều kiện
            if source_match:
                filtered_results.append(result)

                # Nếu đã đủ số kết quả cần thiết, dừng lại
                if len(filtered_results) >= limit:
                    break

        return filtered_results

    def get_all_documents(self, limit=1000, user_id=None):
        """Lấy tất cả tài liệu từ collection"""
        # Cập nhật collection_name nếu có user_id mới
        if user_id and user_id != self.user_id:
            self.collection_name = self.get_collection_name_for_user(user_id)

        if not self.collection_name:
            raise ValueError(
                "collection_name không được để trống. Cần user_id để xác định collection."
            )

        try:
            # Kiểm tra xem collection có tồn tại không
            if not self.client.collection_exists(self.collection_name):
                print(f"Collection {self.collection_name} không tồn tại")
                return []

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

    def delete_collection(self, user_id=None):
        """Xóa collection trong Qdrant"""
        # Cập nhật collection_name nếu có user_id mới
        if user_id and user_id != self.user_id:
            self.collection_name = self.get_collection_name_for_user(user_id)

        if not self.collection_name:
            raise ValueError(
                "collection_name không được để trống. Cần user_id để xác định collection."
            )

        if not self.client.collection_exists(self.collection_name):
            print(f"Collection {self.collection_name} không tồn tại, không cần xóa")
            return

        self.client.delete_collection(self.collection_name)
        print(f"Đã xóa collection {self.collection_name}")

    def get_collection_info(self, user_id=None):
        """Lấy thông tin collection"""
        # Cập nhật collection_name nếu có user_id mới
        if user_id and user_id != self.user_id:
            self.collection_name = self.get_collection_name_for_user(user_id)

        if not self.collection_name:
            raise ValueError(
                "collection_name không được để trống. Cần user_id để xác định collection."
            )

        try:
            if not self.client.collection_exists(self.collection_name):
                print(f"Collection {self.collection_name} không tồn tại")
                return None

            collection_info = self.client.get_collection(self.collection_name)
            return collection_info.dict()
        except Exception as e:
            print(f"Lỗi khi lấy thông tin collection: {str(e)}")
            return None

    def get_document_by_category(self, category, limit=100, user_id=None):
        """Lấy tài liệu theo danh mục (SQL, NoSQL, ...)"""
        # Cập nhật collection_name nếu có user_id mới
        if user_id and user_id != self.user_id:
            self.collection_name = self.get_collection_name_for_user(user_id)

        if not self.collection_name:
            raise ValueError(
                "collection_name không được để trống. Cần user_id để xác định collection."
            )

        if not self.client.collection_exists(self.collection_name):
            print(f"Collection {self.collection_name} không tồn tại")
            return []

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

    def delete_points(self, point_ids: List[str], user_id=None) -> bool:
        """
        Xóa các điểm cụ thể từ collection theo danh sách ID
        """
        # Cập nhật collection_name nếu có user_id mới
        if user_id and user_id != self.user_id:
            self.collection_name = self.get_collection_name_for_user(user_id)

        if not self.collection_name:
            raise ValueError(
                "collection_name không được để trống. Cần user_id để xác định collection."
            )

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

    def delete_points_by_filter(self, filter_dict, user_id=None):
        """
        Xóa các điểm theo filter
        """
        # Cập nhật collection_name nếu có user_id mới
        if user_id and user_id != self.user_id:
            self.collection_name = self.get_collection_name_for_user(user_id)

        if not self.collection_name:
            raise ValueError(
                "collection_name không được để trống. Cần user_id để xác định collection."
            )

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
