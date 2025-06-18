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

        # CẬP NHẬT: Cho phép user_id=None để index vào collection chung
        if user_id is not None:
            # Cập nhật collection_name nếu user_id khác hoặc chưa có collection_name
            if self.user_id != user_id or not self.collection_name:
                self.collection_name = self.get_collection_name_for_user(user_id)
                print(
                    f"[INDEX] Sử dụng collection: {self.collection_name} cho user_id: {user_id}"
                )
        else:
            # Trường hợp user_id=None, sử dụng collection đã được set từ trước
            if not self.collection_name:
                raise ValueError(
                    "collection_name phải được thiết lập khi user_id=None"
                )
            print(
                f"[INDEX] Sử dụng collection chung: {self.collection_name} (không dùng user_id)"
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
        # Kiểm tra file_id
        if not file_id:
            print(
                "[INDEX] Cảnh báo: file_id không được thiết lập"
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
                "source": source,  # Lưu trực tiếp vào root để dễ truy vấn
            }

            # CẬP NHẬT: Chỉ thêm user_id vào payload nếu user_id không phải None
            if user_id is not None:
                payload["user_id"] = user_id

            # Thêm file_id vào payload để dễ filter và delete sau này
            if file_id:
                payload["file_id"] = file_id

            # Thêm point vào danh sách
            points.append(
                PointStruct(id=point_id, vector=current_embedding, payload=payload)
            )

        # Upload toàn bộ points lên Qdrant
        try:
            operation_info = self.client.upsert(
                collection_name=self.collection_name, 
                points=points
            )
            
            # Tính thời gian xử lý
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(
                f"[INDEX] Đã index {len(points)} chunks trong {processing_time:.2f} giây. Collection: {self.collection_name}"
            )
            
            return {
                "indexed_count": len(points),
                "processing_time": processing_time,
                "collection_name": self.collection_name,
                "operation_info": operation_info
            }
            
        except Exception as e:
            print(f"[INDEX] Lỗi khi upload lên Qdrant: {str(e)}")
            raise e

    def search(self, query_vector, limit=5, user_id=None):
        """
        Tìm kiếm ngữ nghĩa trong collection

        Args:
            query_vector: Vector query để tìm kiếm
            limit: Số lượng kết quả tối đa
            user_id: ID người dùng (tùy chọn, có thể None nếu dùng collection chung)

        Returns:
            Danh sách kết quả tìm kiếm
        """
        # CẬP NHẬT: Cho phép user_id=None khi đã có collection_name
        if user_id is not None:
            # Cập nhật collection_name theo user_id nếu cần
            if self.user_id != user_id or not self.collection_name:
                self.collection_name = self.get_collection_name_for_user(user_id)
        else:
            # Trường hợp user_id=None, kiểm tra collection_name đã được thiết lập
            if not self.collection_name:
                raise ValueError(
                    "collection_name phải được thiết lập khi user_id=None"
                )

        print(f"[SEARCH] Tìm kiếm trong collection: {self.collection_name}")

        # Kiểm tra collection có tồn tại không
        if not self.client.collection_exists(self.collection_name):
            print(f"[SEARCH] Collection {self.collection_name} không tồn tại")
            return []

        try:
            # Thực hiện tìm kiếm
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )

            # Chuyển đổi kết quả thành định dạng chuẩn
            results = []
            for point in search_result:
                result = {
                    "id": point.id,
                    "score": point.score,
                    "text": point.payload.get("text", ""),
                    "metadata": point.payload.get("metadata", {}),
                    "source": point.payload.get("source", "unknown"),
                }

                # Thêm file_id vào kết quả nếu có
                if "file_id" in point.payload:
                    result["file_id"] = point.payload["file_id"]

                # CẬP NHẬT: Chỉ thêm user_id nếu có trong payload
                if "user_id" in point.payload:
                    result["user_id"] = point.payload["user_id"]

                results.append(result)

            print(f"[SEARCH] Tìm thấy {len(results)} kết quả trong collection {self.collection_name}")
            return results

        except Exception as e:
            print(f"[SEARCH] Lỗi khi tìm kiếm: {str(e)}")
            return []

    def search_with_filter(
        self, query_vector, sources=None, file_id=None, user_id=None, limit=5
    ):
        """
        Tìm kiếm với bộ lọc theo sources hoặc file_id

        Args:
            query_vector: Vector query
            sources: Danh sách các nguồn cần lọc
            file_id: Danh sách các file_id cần lọc
            user_id: ID người dùng (tùy chọn, có thể None nếu dùng collection chung)
            limit: Số lượng kết quả tối đa

        Returns:
            Danh sách kết quả tìm kiếm
        """
        # CẬP NHẬT: Cho phép user_id=None khi đã có collection_name
        if user_id is not None:
            # Cập nhật collection_name theo user_id nếu cần
            if self.user_id != user_id or not self.collection_name:
                self.collection_name = self.get_collection_name_for_user(user_id)
        else:
            # Trường hợp user_id=None, kiểm tra collection_name đã được thiết lập
            if not self.collection_name:
                raise ValueError(
                    "collection_name phải được thiết lập khi user_id=None"
                )

        print(f"[SEARCH] Tìm kiếm trong collection: {self.collection_name}")

        # Tạo filter conditions
        should_conditions = []

        # Filter theo sources nếu có
        if sources and len(sources) > 0:
            print(f"[SEARCH] Filtering by sources: {sources}")
            for source in sources:
                should_conditions.extend([
                    {"key": "source", "match": {"value": source}},
                    {"key": "metadata.source", "match": {"value": source}},
                ])

        # Filter theo file_id nếu có
        if file_id and len(file_id) > 0:
            print(f"[SEARCH] Filtering by file_id: {file_id}")
            for fid in file_id:
                should_conditions.append({"key": "file_id", "match": {"value": fid}})

        # CẬP NHẬT: Không filter theo user_id nếu user_id=None (dùng collection chung)
        if user_id is not None:
            should_conditions.append({"key": "user_id", "match": {"value": user_id}})

        # Nếu không có điều kiện filter nào, thực hiện tìm kiếm thông thường
        if not should_conditions:
            print(f"[SEARCH] Không có filter, tìm kiếm trên toàn collection")
            return self.search(query_vector, limit=limit, user_id=user_id)

        # Tạo filter object
        search_filter = Filter(should=should_conditions)

        try:
            # Thực hiện tìm kiếm với filter
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )

            # Chuyển đổi kết quả
            results = []
            for point in search_result:
                result = {
                    "id": point.id,
                    "score": point.score,
                    "text": point.payload.get("text", ""),
                    "metadata": point.payload.get("metadata", {}),
                    "source": point.payload.get("source", "unknown"),
                }

                # Thêm file_id vào kết quả nếu có
                if "file_id" in point.payload:
                    result["file_id"] = point.payload["file_id"]

                # CẬP NHẬT: Chỉ thêm user_id nếu có trong payload
                if "user_id" in point.payload:
                    result["user_id"] = point.payload["user_id"]

                results.append(result)

            print(
                f"[SEARCH] Tìm thấy {len(results)} kết quả với filter trong collection {self.collection_name}"
            )
            return results

        except Exception as e:
            print(f"[SEARCH] Lỗi khi tìm kiếm với filter: {str(e)}")
            return []

    def get_all_documents(self, limit=1000, user_id=None):
        """Lấy tất cả tài liệu từ collection"""
        # Cập nhật collection_name nếu có user_id mới
        if user_id and user_id != self.user_id:
            self.collection_name = self.get_collection_name_for_user(user_id)

        # **FIX: Chỉ yêu cầu collection_name, không bắt buộc phải có user_id**
        if not self.collection_name:
            if user_id:
                self.collection_name = self.get_collection_name_for_user(user_id)
            else:
                raise ValueError(
                    "collection_name không được để trống. Cần user_id để xác định collection hoặc đã set collection_name trước đó."
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

        # **FIX: Chỉ yêu cầu collection_name, không bắt buộc phải có user_id**
        if not self.collection_name:
            if user_id:
                self.collection_name = self.get_collection_name_for_user(user_id)
            else:
                raise ValueError(
                    "collection_name không được để trống. Cần user_id để xác định collection hoặc đã set collection_name trước đó."
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

        # **FIX: Chỉ yêu cầu collection_name, không bắt buộc phải có user_id**
        if not self.collection_name:
            if user_id:
                self.collection_name = self.get_collection_name_for_user(user_id)
            else:
                raise ValueError(
                    "collection_name không được để trống. Cần user_id để xác định collection hoặc đã set collection_name trước đó."
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

    def delete_by_file_id(self, file_id, user_id=None):
        """
        Xóa tất cả điểm dữ liệu liên quan đến file_id

        Args:
            file_id: ID của file cần xóa
            user_id: ID người dùng (tùy chọn, có thể None nếu dùng collection chung)

        Returns:
            Tuple (success: bool, message: str)
        """
        # CẬP NHẬT: Cho phép user_id=None khi đã có collection_name
        if user_id is not None:
            # Cập nhật collection_name theo user_id nếu cần
            if self.user_id != user_id or not self.collection_name:
                self.collection_name = self.get_collection_name_for_user(user_id)
        else:
            # Trường hợp user_id=None, kiểm tra collection_name đã được thiết lập
            if not self.collection_name:
                raise ValueError(
                    "collection_name phải được thiết lập khi user_id=None"
                )

        print(f"[DELETE] Xóa theo file_id: {file_id} trong collection: {self.collection_name}")

        if not file_id:
            return False, "file_id không được để trống"

        # Kiểm tra collection có tồn tại không
        if not self.client.collection_exists(self.collection_name):
            return False, f"Collection {self.collection_name} không tồn tại"

        try:
            # Tạo filter để tìm các điểm có file_id tương ứng
            delete_filter = Filter(
                must=[
                    models.FieldCondition(
                        key="file_id",
                        match=models.MatchValue(value=file_id)
                    )
                ]
            )

            # Đếm số lượng điểm sẽ bị xóa trước khi xóa
            count_result = self.client.count(
                collection_name=self.collection_name,
                count_filter=delete_filter,
                exact=True
            )
            
            points_to_delete = count_result.count

            if points_to_delete == 0:
                return False, f"Không tìm thấy điểm dữ liệu nào với file_id: {file_id}"

            # Thực hiện xóa các điểm
            delete_result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(filter=delete_filter)
            )

            if delete_result:
                message = f"Đã xóa {points_to_delete} điểm dữ liệu với file_id: {file_id}"
                print(f"[DELETE] {message}")
                return True, message
            else:
                return False, f"Không thể xóa các điểm với file_id: {file_id}"

        except Exception as e:
            error_msg = f"Lỗi khi xóa file_id {file_id}: {str(e)}"
            print(f"[DELETE] {error_msg}")
            return False, error_msg

    def delete_by_file_path(self, file_path, user_id=None):
        """
        Xóa tất cả điểm dữ liệu liên quan đến đường dẫn file

        Args:
            file_path: Đường dẫn file cần xóa
            user_id: ID người dùng (tùy chọn, có thể None nếu dùng collection chung)

        Returns:
            Tuple (success: bool, message: str)
        """
        # CẬP NHẬT: Cho phép user_id=None khi đã có collection_name
        if user_id is not None:
            # Cập nhật collection_name theo user_id nếu cần
            if self.user_id != user_id or not self.collection_name:
                self.collection_name = self.get_collection_name_for_user(user_id)
        else:
            # Trường hợp user_id=None, kiểm tra collection_name đã được thiết lập
            if not self.collection_name:
                raise ValueError(
                    "collection_name phải được thiết lập khi user_id=None"
                )

        print(f"[DELETE] Xóa theo file_path: {file_path} trong collection: {self.collection_name}")

        if not file_path:
            return False, "file_path không được để trống"

        # Kiểm tra collection có tồn tại không
        if not self.client.collection_exists(self.collection_name):
            return False, f"Collection {self.collection_name} không tồn tại"

        try:
            # Tạo filter để tìm các điểm có file_path tương ứng
            # Tìm kiếm trong cả source và metadata.source
            delete_filter = Filter(
                should=[
                    models.FieldCondition(
                        key="source",
                        match=models.MatchValue(value=file_path)
                    ),
                    models.FieldCondition(
                        key="metadata.source",
                        match=models.MatchValue(value=file_path)
                    )
                ]
            )

            # Đếm số lượng điểm sẽ bị xóa trước khi xóa
            count_result = self.client.count(
                collection_name=self.collection_name,
                count_filter=delete_filter,
                exact=True
            )
            
            points_to_delete = count_result.count

            if points_to_delete == 0:
                return False, f"Không tìm thấy điểm dữ liệu nào với file_path: {file_path}"

            # Thực hiện xóa các điểm
            delete_result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(filter=delete_filter)
            )

            if delete_result:
                message = f"Đã xóa {points_to_delete} điểm dữ liệu với file_path: {file_path}"
                print(f"[DELETE] {message}")
                return True, message
            else:
                return False, f"Không thể xóa các điểm với file_path: {file_path}"

        except Exception as e:
            error_msg = f"Lỗi khi xóa file_path {file_path}: {str(e)}"
            print(f"[DELETE] {error_msg}")
            return False, error_msg

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
