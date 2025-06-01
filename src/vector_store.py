from sqlalchemy import null
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

    def index_documents(self, chunks, embeddings, user_id, file_id):
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
        # Kiểm tra self.file_id nếu null thì thông báo
        if not file_id:
            if file_id:
                file_id = file_id
                print(f"[INDEX] Sử dụng file_id được cung cấp: {file_id}")
            else:
                print(
                    "[INDEX] Cảnh báo: file_id không được thiết lập và không có file_id được cung cấp"
                )
        for idx, chunk in enumerate(chunks):
            # Tạo ID ngẫu nhiên cho mỗi điểm để tránh ghi đè
            point_id = str(uuid.uuid4())

            # Đảm bảo source có trong cả payload trực tiếp và metadata
            source = chunk.get("source", "unknown")

            # Đảm bảo metadata là một dict
            if "metadata" not in chunk or not isinstance(chunk["metadata"], dict):
                chunk["metadata"] = {}

            # Đảm bảo source cũng có trong metadata
            if source and "source" not in chunk["metadata"]:
                chunk["metadata"]["source"] = source

            # Thêm timestamp để theo dõi nếu chưa có
            if "indexed_at" not in chunk["metadata"]:
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

            # Tạo payload theo cấu trúc mới
            payload = {
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "source": source,
                "file_id": file_id,
                "indexed_at": int(time.time()),
            }

            # Thêm các trường file_id nếu có trong chunk để hỗ trợ xóa chính xác
            if "file_id" in chunk:
                payload["file_id"] = chunk["file_id"]

            # Thêm file_path đầy đủ nếu có
            if "file_path" in chunk:
                payload["file_path"] = chunk["file_path"]

            points.append(
                PointStruct(
                    id=point_id,
                    vector=current_embedding,
                    payload=payload,
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

        # Chuyển đổi kết quả thành định dạng chuẩn
        search_results = []
        for hit in results:
            result = {
                "text": hit.payload["text"],
                "metadata": hit.payload["metadata"],
                "score": hit.score,
            }

            # Thêm source từ payload trực tiếp nếu có
            if "source" in hit.payload:
                result["source"] = hit.payload["source"]

            # Thêm các trường khác nếu có
            for field in ["file_id", "file_path", "indexed_at"]:
                if field in hit.payload:
                    result[field] = hit.payload[field]

            search_results.append(result)

        return search_results

    def search_with_filter(
        self, query_vector, sources=None, file_id=None, user_id=None, limit=5
    ):
        """Tìm kiếm trong Qdrant với filter theo nguồn tài liệu hoặc file_id"""
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

        # Nếu không có danh sách nguồn hoặc file_id, sử dụng search thông thường
        if not sources and not file_id:
            print(f"Không có sources hoặc file_id được chỉ định, tìm kiếm trong tất cả các tài liệu.")
            return self.search(query_vector, limit, user_id)

        # Tạo các điều kiện lọc dựa vào tham số đầu vào
        should_conditions = []

        # Xử lý tìm kiếm theo sources nếu được cung cấp
        if sources:
            # Xử lý danh sách nguồn để hỗ trợ so sánh với cả tên file đơn thuần và đường dẫn
            normalized_sources = []
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

            # Tạo filter để giới hạn kết quả theo source
            for source in normalized_sources:
                should_conditions.append({"key": "source", "match": {"value": source}})
                should_conditions.append(
                    {"key": "metadata.source", "match": {"value": source}}
                )

                # Nếu source là đường dẫn đầy đủ, thêm điều kiện cho file_path
                if os.path.sep in source:
                    should_conditions.append(
                        {"key": "file_path", "match": {"value": source}}
                    )

        # Xử lý tìm kiếm theo file_id nếu được cung cấp
        if file_id:
            print(f"Tìm kiếm với file_id={file_id}")
            # Thêm điều kiện lọc theo file_id
            for fid in file_id:
                should_conditions.append({"key": "file_id", "match": {"value": fid}})

        # Tạo filter phù hợp cho Qdrant
        search_filter = {"should": should_conditions}

        # Thực hiện tìm kiếm với filter
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            with_payload=True,
            query_filter=models.Filter(**search_filter),
        )

        # Chuyển đổi kết quả thành định dạng chuẩn
        search_results = []
        for hit in results:
            result = {
                "text": hit.payload["text"],
                "metadata": hit.payload["metadata"],
                "score": hit.score,
            }

            # Thêm source từ payload trực tiếp nếu có
            if "source" in hit.payload:
                result["source"] = hit.payload["source"]

            # Thêm các trường khác nếu có
            for field in ["file_id", "file_path", "indexed_at"]:
                if field in hit.payload:
                    result[field] = hit.payload[field]

            search_results.append(result)

        return search_results

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

    def delete_by_file_path(self, file_path, user_id=None):
        """
        Xóa tất cả các điểm của một file theo đường dẫn chính xác

        Args:
            file_path (str): Đường dẫn đầy đủ của file cần xóa
            user_id (str): ID của người dùng

        Returns:
            tuple: (success: bool, message: str) - Kết quả xóa và thông báo
        """
        # Cập nhật collection_name nếu có user_id mới
        if user_id and user_id != self.user_id:
            self.collection_name = self.get_collection_name_for_user(user_id)

        if not self.collection_name:
            raise ValueError(
                "collection_name không được để trống. Cần user_id để xác định collection."
            )

        try:
            print(f"[VECTOR_STORE] Bắt đầu xóa các điểm của file: {file_path}")

            if not self.client.collection_exists(self.collection_name):
                print(
                    f"[VECTOR_STORE] Lỗi: Collection {self.collection_name} không tồn tại"
                )
                return False, "Collection không tồn tại"

            # Xác định filter chính xác theo file_path
            # Ưu tiên dùng file_path chính xác nếu có
            filter_condition = {
                "filter": {
                    "must": [{"key": "file_path", "match": {"value": file_path}}]
                }
            }

            # Đếm số điểm khớp với filter theo file_path
            try:
                count_results = self.client.count(
                    collection_name=self.collection_name,
                    count_filter=models.Filter(**filter_condition["filter"]),
                )
                file_path_points = count_results.count
                print(
                    f"[VECTOR_STORE] Số điểm khớp với file_path chính xác: {file_path_points}"
                )

                # Nếu không tìm thấy theo file_path, thử tìm theo source
                if file_path_points == 0:
                    source_filter = {
                        "filter": {
                            "must": [{"key": "source", "match": {"value": file_path}}]
                        }
                    }

                    count_results = self.client.count(
                        collection_name=self.collection_name,
                        count_filter=models.Filter(**source_filter["filter"]),
                    )
                    source_points = count_results.count
                    print(f"[VECTOR_STORE] Số điểm khớp với source: {source_points}")

                    if source_points > 0:
                        filter_condition = source_filter
            except Exception as count_e:
                print(f"[VECTOR_STORE] Lỗi khi đếm số điểm: {str(count_e)}")

            # Lấy thông tin collection trước khi xóa
            info_before = self.client.get_collection(self.collection_name)
            points_before = info_before.points_count

            # Xóa điểm từ collection theo filter
            print(f"[VECTOR_STORE] Thực hiện xóa điểm theo filter: {filter_condition}")
            result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=filter_condition["filter"]
                ),
            )

            # Sau khi xóa, kiểm tra số lượng điểm còn lại
            info_after = self.client.get_collection(self.collection_name)
            points_after = info_after.points_count
            points_deleted = points_before - points_after

            print(f"[VECTOR_STORE] Kết quả xóa điểm: {result}")
            print(f"[VECTOR_STORE] Số điểm trước khi xóa: {points_before}")
            print(f"[VECTOR_STORE] Số điểm sau khi xóa: {points_after}")
            print(f"[VECTOR_STORE] Số điểm đã xóa: {points_deleted}")

            if points_deleted > 0:
                return True, f"Đã xóa {points_deleted} điểm từ file {file_path}"
            else:
                return False, f"Không tìm thấy điểm nào thuộc file {file_path}"

        except Exception as e:
            print(f"[VECTOR_STORE] Lỗi khi xóa điểm theo file_path: {str(e)}")
            import traceback

            traceback_str = traceback.format_exc()
            print(f"[VECTOR_STORE] Traceback: {traceback_str}")
            return False, f"Lỗi khi xóa điểm theo file_path: {str(e)}"

    def delete_by_file_id(self, file_id, user_id=None):
        """
        Xóa tất cả các điểm của một file theo file_id

        Args:
            file_id (str): ID của file cần xóa (đặc biệt hữu ích khi có nhiều file cùng tên)
            user_id (str): ID của người dùng

        Returns:
            tuple: (success: bool, message: str) - Kết quả xóa và thông báo
        """
        # Cập nhật collection_name nếu có user_id mới
        if user_id and user_id != self.user_id:
            self.collection_name = self.get_collection_name_for_user(user_id)

        if not self.collection_name:
            raise ValueError(
                "collection_name không được để trống. Cần user_id để xác định collection."
            )

        try:
            print(f"[VECTOR_STORE] Bắt đầu xóa các điểm của file có ID: {file_id}")

            if not self.client.collection_exists(self.collection_name):
                print(
                    f"[VECTOR_STORE] Lỗi: Collection {self.collection_name} không tồn tại"
                )
                return False, "Collection không tồn tại"

            # Tạo filter theo file_id
            filter_condition = {
                "filter": {"must": [{"key": "file_id", "match": {"value": file_id}}]}
            }

            # Đếm số điểm khớp với filter theo file_id
            try:
                count_results = self.client.count(
                    collection_name=self.collection_name,
                    count_filter=models.Filter(**filter_condition["filter"]),
                )
                file_id_points = count_results.count
                print(f"[VECTOR_STORE] Số điểm khớp với file_id: {file_id_points}")

                if file_id_points == 0:
                    return False, f"Không tìm thấy điểm nào thuộc file ID {file_id}"
            except Exception as count_e:
                print(f"[VECTOR_STORE] Lỗi khi đếm số điểm: {str(count_e)}")

            # Lấy thông tin collection trước khi xóa
            info_before = self.client.get_collection(self.collection_name)
            points_before = info_before.points_count

            # Xóa điểm từ collection theo filter
            print(f"[VECTOR_STORE] Thực hiện xóa điểm theo filter: {filter_condition}")
            result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=filter_condition["filter"]
                ),
            )

            # Sau khi xóa, kiểm tra số lượng điểm còn lại
            info_after = self.client.get_collection(self.collection_name)
            points_after = info_after.points_count
            points_deleted = points_before - points_after

            print(f"[VECTOR_STORE] Kết quả xóa điểm: {result}")
            print(f"[VECTOR_STORE] Số điểm đã xóa: {points_deleted}")

            return True, f"Đã xóa {points_deleted} điểm thuộc file ID {file_id}"

        except Exception as e:
            print(f"[VECTOR_STORE] Lỗi khi xóa điểm theo file_id: {str(e)}")
            import traceback

            traceback_str = traceback.format_exc()
            print(f"[VECTOR_STORE] Traceback: {traceback_str}")
            return False, f"Lỗi khi xóa điểm theo file_id: {str(e)}"

    def delete_by_file_uuid(self, file_uuid, user_id=None):
        """
        Xóa tất cả các điểm của một file theo UUID trong đường dẫn
        Điều này hữu ích khi đường dẫn file có chứa UUID như trong ví dụ:
        src/data/73faa408-c331-4b44-a9d7-062464ac4144/Ten_file.pdf

        Args:
            file_uuid (str): UUID của file cần xóa (nằm trong đường dẫn)
            user_id (str): ID của người dùng

        Returns:
            tuple: (success: bool, message: str) - Kết quả xóa và thông báo
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
                f"[VECTOR_STORE] Bắt đầu xóa các điểm của file có UUID: {file_uuid} trong đường dẫn"
            )

            if not self.client.collection_exists(self.collection_name):
                print(
                    f"[VECTOR_STORE] Lỗi: Collection {self.collection_name} không tồn tại"
                )
                return False, "Collection không tồn tại"

            # Tạo filter cho source chứa UUID
            filter_condition = {
                "filter": {"must": [{"key": "source", "match": {"text": file_uuid}}]}
            }

            # Thử lọc theo file_path nếu có
            alternate_filter = {
                "filter": {"must": [{"key": "file_path", "match": {"text": file_uuid}}]}
            }

            # Kiểm tra số lượng điểm khớp với filter
            try:
                # Đếm theo source trước
                count_results = self.client.count(
                    collection_name=self.collection_name,
                    count_filter=models.Filter(**filter_condition["filter"]),
                )
                source_points = count_results.count
                print(
                    f"[VECTOR_STORE] Số điểm khớp với UUID trong source: {source_points}"
                )

                # Nếu không tìm thấy, thử đếm theo file_path
                if source_points == 0:
                    count_results = self.client.count(
                        collection_name=self.collection_name,
                        count_filter=models.Filter(**alternate_filter["filter"]),
                    )
                    path_points = count_results.count
                    print(
                        f"[VECTOR_STORE] Số điểm khớp với UUID trong file_path: {path_points}"
                    )

                    if path_points > 0:
                        filter_condition = alternate_filter
                        source_points = path_points

                # Nếu không tìm thấy theo cả hai cách
                if source_points == 0:
                    return (
                        False,
                        f"Không tìm thấy điểm nào thuộc file có UUID {file_uuid}",
                    )

            except Exception as count_e:
                print(f"[VECTOR_STORE] Lỗi khi đếm số điểm: {str(count_e)}")

            # Lấy thông tin collection trước khi xóa
            info_before = self.client.get_collection(self.collection_name)
            points_before = info_before.points_count

            # Xóa điểm từ collection theo filter
            print(
                f"[VECTOR_STORE] Thực hiện xóa điểm theo filter UUID: {filter_condition}"
            )
            result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=filter_condition["filter"]
                ),
            )

            # Sau khi xóa, kiểm tra số lượng điểm còn lại
            info_after = self.client.get_collection(self.collection_name)
            points_after = info_after.points_count
            points_deleted = points_before - points_after

            print(f"[VECTOR_STORE] Kết quả xóa điểm: {result}")
            print(f"[VECTOR_STORE] Số điểm trước khi xóa: {points_before}")
            print(f"[VECTOR_STORE] Số điểm sau khi xóa: {points_after}")
            print(f"[VECTOR_STORE] Số điểm đã xóa: {points_deleted}")

            return True, f"Đã xóa {points_deleted} điểm thuộc file có UUID {file_uuid}"

        except Exception as e:
            print(f"[VECTOR_STORE] Lỗi khi xóa điểm theo UUID: {str(e)}")
            import traceback

            traceback_str = traceback.format_exc()
            print(f"[VECTOR_STORE] Traceback: {traceback_str}")
            return False, f"Lỗi khi xóa điểm theo UUID: {str(e)}"
