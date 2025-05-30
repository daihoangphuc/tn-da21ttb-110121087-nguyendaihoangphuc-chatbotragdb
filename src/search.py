from typing import List, Dict
import logging

# Cấu hình logging
logging.basicConfig(format="[Search] %(message)s", level=logging.INFO)
# Ghi đè hàm print để thêm prefix
original_print = print


def print(*args, **kwargs):
    prefix = "[Search] "
    original_print(prefix + " ".join(map(str, args)), **kwargs)


logger = logging.getLogger(__name__)
from rank_bm25 import BM25Okapi
import re
import numpy as np
from sentence_transformers import CrossEncoder
import os
import pickle
import json
from dotenv import load_dotenv

# Load biến môi trường từ .env
load_dotenv()


class SearchManager:
    """Lớp quản lý các phương pháp tìm kiếm khác nhau"""

    def __init__(self, vector_store, embedding_model):
        """Khởi tạo search manager"""
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.corpus = []
        self.doc_mappings = []
        self.bm25 = None
        self.bm25_initialized = False

        # Đường dẫn lưu BM25 index
        data_dir = os.getenv("UPLOAD_DIR", "src/data")
        
        # Lấy user_id từ vector_store
        user_id = self.vector_store.user_id if hasattr(self.vector_store, 'user_id') else None
        
        if user_id:
            # Tạo thư mục bm25_index trong thư mục của người dùng
            user_specific_dir = os.path.join(data_dir, user_id)
            self.bm25_index_dir = os.path.join(user_specific_dir, "bm25_index")
            print(f"Sử dụng thư mục BM25 index trong thư mục người dùng: {self.bm25_index_dir}")
            os.makedirs(self.bm25_index_dir, exist_ok=True)
            self.bm25_index_path = os.path.join(self.bm25_index_dir, "bm25_index.pkl")
            self.corpus_path = os.path.join(self.bm25_index_dir, "corpus.pkl")
            self.doc_mappings_path = os.path.join(self.bm25_index_dir, "doc_mappings.pkl")
            self.metadata_path = os.path.join(self.bm25_index_dir, "bm25_metadata.json")
            # Không tải BM25 index ở đây, sẽ được tải/khởi tạo khi set_vector_store_and_reload_bm25 được gọi
        else:
            # Không có user_id khi khởi tạo, các đường dẫn BM25 sẽ là None
            # Không tạo thư mục bm25_index mặc định
            print("SearchManager khởi tạo không có user_id. BM25 index sẽ được xử lý khi có user context.")
            self.bm25_index_dir = None
            self.bm25_index_path = None
            self.corpus_path = None
            self.doc_mappings_path = None
            self.metadata_path = None

        # Tải trước model reranking để tránh tải lại mỗi lần cần rerank
        print("Đang tải model reranking...")

        # Sử dụng model tốt hơn cho reranking tài liệu học thuật/kỹ thuật
        # Một số model phù hợp:
        # - "cross-encoder/ms-marco-MiniLM-L-12-v2" (tốt hơn L-6)
        # - "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1" (hỗ trợ đa ngôn ngữ tốt, phù hợp tiếng Việt)
        # - "cross-encoder/stsb-roberta-large" (chất lượng cao cho semantic similarity)
        # - "vblagoje/dres-cross-encoder-roberta-base" (được tinh chỉnh cho tìm kiếm tài liệu)

        # Cho phép cấu hình model thông qua biến môi trường
        default_reranker_model = "ms-marco-MiniLM-L-12-v2"  
        reranker_model = os.getenv("RERANKER_MODEL", default_reranker_model)

        try:
            self.reranker = CrossEncoder(reranker_model)
            print(f"Đã tải xong model reranking: {reranker_model}")
        except Exception as e:
            print(f"Lỗi khi tải model reranking {reranker_model}: {str(e)}")
            print(f"Sử dụng model dự phòng...")
            # Sử dụng model dự phòng nếu có lỗi
            backup_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
            self.reranker = CrossEncoder(backup_model)
            print(f"Đã tải model dự phòng: {backup_model}")

        # Lưu thông tin về model đang sử dụng
        self.reranker_model_name = reranker_model

    def _try_load_bm25_index(self):
        """Thử tải BM25 index từ file nếu tồn tại"""
        if not all([self.bm25_index_path, self.corpus_path, self.doc_mappings_path]):
            print(f"=== BM25 DEBUG === Đường dẫn BM25 chưa được thiết lập, không thể tải index.")
            return False
            
        try:
            user_id = self.vector_store.user_id if hasattr(self.vector_store, 'user_id') else None
            print(f"=== BM25 DEBUG === Đang thử tải BM25 index cho user_id: {user_id}")
            print(f"=== BM25 DEBUG === Đường dẫn BM25 index dir: {self.bm25_index_dir}")
            
            if (
                os.path.exists(self.bm25_index_path)
                and os.path.exists(self.corpus_path)
                and os.path.exists(self.doc_mappings_path)
            ):
                # Kiểm tra kích thước file
                bm25_file_size = os.path.getsize(self.bm25_index_path)
                corpus_file_size = os.path.getsize(self.corpus_path)
                mappings_file_size = os.path.getsize(self.doc_mappings_path)
                
                print(f"=== BM25 DEBUG === Kích thước file bm25_index.pkl: {bm25_file_size} bytes")
                print(f"=== BM25 DEBUG === Kích thước file corpus.pkl: {corpus_file_size} bytes")
                print(f"=== BM25 DEBUG === Kích thước file doc_mappings.pkl: {mappings_file_size} bytes")
                
                if bm25_file_size == 0 or corpus_file_size == 0 or mappings_file_size == 0:
                    print(f"=== BM25 DEBUG === Phát hiện file trống, không thể tải BM25 index")
                    return False

                print("Đang tải BM25 index từ file...")

                with open(self.bm25_index_path, "rb") as f:
                    self.bm25 = pickle.load(f)
                print(f"=== BM25 DEBUG === Đã tải xong bm25_index.pkl")

                with open(self.corpus_path, "rb") as f:
                    self.corpus = pickle.load(f)
                print(f"=== BM25 DEBUG === Đã tải xong corpus.pkl, số lượng tài liệu: {len(self.corpus)}")

                with open(self.doc_mappings_path, "rb") as f:
                    self.doc_mappings = pickle.load(f)
                print(f"=== BM25 DEBUG === Đã tải xong doc_mappings.pkl, số lượng tài liệu: {len(self.doc_mappings)}")

                self.bm25_initialized = True
                print("Đã tải xong BM25 index từ file")
                print(f"=== BM25 DEBUG === BM25 đã được khởi tạo thành công từ file")
                return True
            else:
                missing_files = []
                if not os.path.exists(self.bm25_index_path):
                    missing_files.append("bm25_index.pkl")
                if not os.path.exists(self.corpus_path):
                    missing_files.append("corpus.pkl")
                if not os.path.exists(self.doc_mappings_path):
                    missing_files.append("doc_mappings.pkl")
                    
                print(f"=== BM25 DEBUG === Không tìm thấy các file cần thiết: {', '.join(missing_files)}")
                return False
        except Exception as e:
            print(f"Lỗi khi tải BM25 index: {str(e)}")
            # Nếu lỗi, reset các biến và tiếp tục như trước
            self.bm25 = None
            self.corpus = []
            self.doc_mappings = []
            self.bm25_initialized = False
            
            print(f"=== BM25 DEBUG === Lỗi khi tải BM25 index: {str(e)}")
            import traceback
            print(f"=== BM25 DEBUG === Stack trace: {traceback.format_exc()}")

        return False

    def _save_bm25_index(self):
        """Lưu BM25 index, corpus và doc_mappings vào file"""
        if not all([self.bm25_index_path, self.corpus_path, self.doc_mappings_path, self.metadata_path]):
            print(f"=== BM25 DEBUG === Đường dẫn BM25 chưa được thiết lập, không thể lưu index.")
            return False
        try:
            if self.bm25_initialized and self.bm25 is not None:
                print("Đang lưu BM25 index...")

                with open(self.bm25_index_path, "wb") as f:
                    pickle.dump(self.bm25, f)

                with open(self.corpus_path, "wb") as f:
                    pickle.dump(self.corpus, f)

                with open(self.doc_mappings_path, "wb") as f:
                    pickle.dump(self.doc_mappings, f)

                print("Đã lưu xong BM25 index")
                return True
        except Exception as e:
            print(f"Lỗi khi lưu BM25 index: {str(e)}")

        return False

    def _initialize_bm25(self):
        """Khởi tạo BM25 từ các tài liệu trong vector store và lưu vào file"""
        try:
            # Lấy user_id từ vector_store hiện tại
            user_id_for_init = self.vector_store.user_id if hasattr(self.vector_store, 'user_id') else None
            print(f"=== BM25 DEBUG === (_initialize_bm25) Bắt đầu khởi tạo BM25 cho user_id: {user_id_for_init}")

            if not user_id_for_init:
                print(f"=== BM25 DEBUG === (_initialize_bm25) Không có user_id trong vector_store, không thể khởi tạo BM25.")
                self.bm25 = None
                self.corpus = []
                self.doc_mappings = []
                self.bm25_initialized = False
                return False

            # --- CẬP NHẬT ĐƯỜNG DẪN DỰA TRÊN USER_ID HIỆN TẠI ---
            # Đường dẫn đã được thiết lập chính xác trong set_vector_store_and_reload_bm25
            # hoặc trong __init__ nếu user_id có sẵn ngay từ đầu (trường hợp ít xảy ra hơn với logic mới)
            # Chỉ cần đảm bảo thư mục tồn tại
            if not self.bm25_index_dir: # Kiểm tra lại phòng trường hợp bất thường
                print(f"=== BM25 DEBUG === (_initialize_bm25) Lỗi: bm25_index_dir is None dù có user_id. Không thể tiếp tục.")
                return False
            os.makedirs(self.bm25_index_dir, exist_ok=True)
            print(f"=== BM25 DEBUG === (_initialize_bm25) Đường dẫn BM25 index được sử dụng: {self.bm25_index_dir}")
            # --- KẾT THÚC CẬP NHẬT ĐƯỜNG DẪN ---
            
            collection_info = self.vector_store.get_collection_info()
            # Xử lý trường hợp collection_info là None hoặc không chứa 'points_count'
            current_points_count = 0
            if collection_info and isinstance(collection_info, dict):
                 current_points_count = collection_info.get("points_count", 0)
            
            print(f"=== BM25 DEBUG === (_initialize_bm25) Số lượng points hiện tại trong collection: {current_points_count}")

            previous_points_count = 0
            if os.path.exists(self.metadata_path):
                try:
                    with open(self.metadata_path, "r") as f:
                        metadata = json.load(f)
                        previous_points_count = metadata.get("points_count", 0)
                    print(f"=== BM25 DEBUG === (_initialize_bm25) Số lượng points trong metadata trước đó: {previous_points_count}")
                except Exception as e:
                    print(f"=== BM25 DEBUG === (_initialize_bm25) Lỗi khi đọc metadata: {str(e)}")
                    previous_points_count = 0
            else:
                print(f"=== BM25 DEBUG === (_initialize_bm25) Không tìm thấy file metadata: {self.metadata_path}")

            pkl_files_exist = os.path.exists(self.bm25_index_path) and os.path.exists(self.corpus_path) and os.path.exists(self.doc_mappings_path)
            print(f"=== BM25 DEBUG === (_initialize_bm25) Các file pkl tồn tại: {pkl_files_exist}")

            if (
                current_points_count == previous_points_count
                and current_points_count > 0
                and self.bm25_initialized # Kiểm tra xem BM25 đã được khởi tạo trước đó chưa (có thể từ file)
                and pkl_files_exist # Đảm bảo các file thực sự tồn tại
            ):
                print(
                    f"=== BM25 DEBUG === (_initialize_bm25) Số lượng points không thay đổi ({current_points_count}), và BM25 đã được khởi tạo, sử dụng BM25 index đã có"
                )
                # Nếu các file đã tồn tại và số lượng points không đổi, thử tải lại nếu self.bm25 là None
                if self.bm25 is None:
                    print(f"=== BM25 DEBUG === (_initialize_bm25) self.bm25 is None, thử tải lại từ file...")
                    if self._try_load_bm25_index(): # Thử tải lại, nếu thành công thì return
                        return True
                    else: # Nếu tải lại thất bại, thì cần phải re-index
                         print(f"=== BM25 DEBUG === (_initialize_bm25) Tải lại từ file thất bại, sẽ tiến hành re-index.")
                else:
                    return True # BM25 đã được load và không có gì thay đổi

            if current_points_count == 0:
                print(f"=== BM25 DEBUG === (_initialize_bm25) Collection không có points, không thể khởi tạo BM25")
                # Reset trạng thái BM25 nếu không có dữ liệu
                self.bm25 = None
                self.corpus = []
                self.doc_mappings = []
                self.bm25_initialized = False
                return False

            print(f"=== BM25 DEBUG === (_initialize_bm25) Bắt đầu lấy tất cả tài liệu từ vector store")
            all_docs = self.vector_store.get_all_documents()
            print(f"=== BM25 DEBUG === (_initialize_bm25) Đã lấy được {len(all_docs) if all_docs else 0} tài liệu từ vector store")

            if not all_docs:
                print(f"=== BM25 DEBUG === (_initialize_bm25) Vector store không trả về tài liệu nào")
                self.bm25 = None
                self.corpus = []
                self.doc_mappings = []
                self.bm25_initialized = False
                return False

            corpus = []
            doc_mappings = []
            for i, doc in enumerate(all_docs):
                if 'text' not in doc or not doc['text']:
                    print(f"=== BM25 DEBUG === (_initialize_bm25) Tài liệu thứ {i} không có trường 'text' hoặc text rỗng")
                    continue
                
                # Xử lý văn bản cho tiếng Việt
                text = doc["text"].lower()
                
                # Tiền xử lý nhẹ nhàng hơn để giữ lại các ký tự tiếng Việt
                # Thay vì loại bỏ tất cả các ký tự đặc biệt, chỉ loại bỏ dấu câu
                # và giữ lại tất cả các ký tự Unicode của tiếng Việt
                text = re.sub(r'[.,;:!?()[\]{}"\'-]', ' ', text)  # Loại bỏ dấu câu thông dụng
                
                # Loại bỏ nhiều khoảng trắng liên tiếp
                text = re.sub(r'\s+', ' ', text)
                
                # Loại bỏ khoảng trắng ở đầu và cuối
                text = text.strip()
                
                tokens = text.split()
                if i == 0: # Log mẫu token của tài liệu đầu tiên
                    print(f"=== BM25 DEBUG === (_initialize_bm25) Mẫu tokens sau khi tiền xử lý (doc 0): {tokens[:20]}")
                
                corpus.append(tokens)
                doc_mappings.append(doc)

            print(f"=== BM25 DEBUG === (_initialize_bm25) Đã tiền xử lý xong {len(corpus)} tài liệu cho BM25.")
            if len(corpus) == 0:
                print(f"=== BM25 DEBUG === (_initialize_bm25) Corpus rỗng sau khi tiền xử lý, không thể khởi tạo BM25")
                self.bm25 = None
                self.corpus = [] # Đảm bảo self.corpus cũng rỗng
                self.doc_mappings = []
                self.bm25_initialized = False
                return False

            print(f"=== BM25 DEBUG === (_initialize_bm25) Bắt đầu khởi tạo BM25Okapi với {len(corpus)} tài liệu")
            self.bm25 = BM25Okapi(corpus)
            self.corpus = corpus # Lưu lại corpus đã được tokenized
            self.doc_mappings = doc_mappings
            self.bm25_initialized = True
            print(f"=== BM25 DEBUG === (_initialize_bm25) Đã khởi tạo thành công BM25 với {len(self.corpus)} tài liệu")

            print(f"=== BM25 DEBUG === (_initialize_bm25) Bắt đầu lưu BM25 index vào {self.bm25_index_path}")
            save_success = self._save_bm25_index()
            print(f"=== BM25 DEBUG === (_initialize_bm25) Kết quả lưu BM25 index: {'Thành công' if save_success else 'Thất bại'}")

            try:
                with open(self.metadata_path, "w") as f:
                    json.dump({"points_count": current_points_count, "corpus_len": len(self.corpus)}, f)
                print(f"=== BM25 DEBUG === (_initialize_bm25) Đã lưu metadata với points_count={current_points_count}, corpus_len={len(self.corpus)}")
            except Exception as e:
                print(f"=== BM25 DEBUG === (_initialize_bm25) Lỗi khi lưu metadata: {str(e)}")

            return True
        except Exception as e:
            print(f"=== BM25 DEBUG === (_initialize_bm25) Lỗi nghiêm trọng khi khởi tạo BM25: {str(e)}")
            import traceback
            print(f"=== BM25 DEBUG === (_initialize_bm25) Stack trace: {traceback.format_exc()}")
            # Đặt lại trạng thái nếu có lỗi nghiêm trọng
            self.bm25 = None
            self.corpus = []
            self.doc_mappings = []
            self.bm25_initialized = False
            return False


    def semantic_search(
        self,
        query: str,
        k: int = 5,
        sources: List[str] = None,
        file_id: List[str] = None,
    ) -> List[Dict]:
        """Tìm kiếm ngữ nghĩa trên vector store"""
        query_vector = self.embedding_model.encode(query).tolist()

        # Sử dụng search_with_filter nếu có danh sách nguồn hoặc file_id
        if sources:
            print(f"Semantic search với sources={sources}")
            results = self.vector_store.search_with_filter(
                query_vector, sources=sources, limit=k
            )
        elif file_id:
            print(f"Semantic search với file_id={file_id}")
            results = self.vector_store.search_with_filter(
                query_vector, file_id=file_id, limit=k
            )
        else:
            results = self.vector_store.search(query_vector, limit=k)

        # In thông tin để debug
        if results and len(results) > 0:
            first_result = results[0]
            result_file_id = first_result.get("file_id", "unknown")
            print(
                f"Sample result: metadata.source={first_result.get('metadata', {}).get('source')}, "
                f"direct source={first_result.get('source')}, file_id={result_file_id}"
            )

        return results

    def keyword_search(
        self,
        query: str,
        k: int = 5,
        sources: List[str] = None,
        file_id: List[str] = None,
    ) -> List[Dict]:
        """Tìm kiếm từ khóa sử dụng BM25"""
        print(f"=== BM25 DEBUG === Bắt đầu tìm kiếm từ khóa với query: '{query}'")

        current_user_id = self.vector_store.user_id if hasattr(self.vector_store, 'user_id') else None
        print(f"=== BM25 DEBUG === user_id trong vector_store TRONG keyword_search: {current_user_id}")
        
        if not current_user_id:
            print(f"=== BM25 DEBUG === Không có user_id trong vector_store, không thể thực hiện keyword search.")
            return []
        
        if not self.bm25_index_dir:
            print(f"=== BM25 DEBUG === Đường dẫn BM25 chưa được thiết lập. Gọi set_vector_store_and_reload_bm25 trước.")
            if hasattr(self.vector_store, 'user_id') and self.vector_store.user_id:
                 print(f"=== BM25 DEBUG === Thử gọi set_vector_store_and_reload_bm25 nội bộ.")
                 self.set_vector_store_and_reload_bm25(self.vector_store)
            else:
                 print(f"=== BM25 DEBUG === Không thể tự động set_vector_store_and_reload_bm25 do thiếu user_id.")
                 return []

        print(f"=== BM25 DEBUG === Trạng thái BM25: bm25_initialized={self.bm25_initialized}, bm25 is None={self.bm25 is None}")
        
        if not self.bm25_initialized:
            print(f"=== BM25 DEBUG === BM25 chưa được khởi tạo, đang thử khởi tạo...")
            initialized = self._initialize_bm25()
            if not initialized:
                print(f"=== BM25 DEBUG === Không thể khởi tạo BM25, không có kết quả từ keyword search")
                return []
        
        if self.bm25 is None:
            print(f"=== BM25 DEBUG === self.bm25 vẫn là None sau khi thử khởi tạo (ví dụ, corpus rỗng). Trả về danh sách rỗng.")
            return []

        query_tokens = [] # Khởi tạo để đảm bảo luôn là list
        try:
            print(f"=== BM25 DEBUG === (Preprocessing Query) Bắt đầu tiền xử lý query: '{query}' (type: {type(query)})")
            if not query or not isinstance(query, str) or len(query.strip()) == 0:
                print(f"=== BM25 DEBUG === Câu truy vấn rỗng hoặc không phải string, không thể tìm kiếm")
                return []

            # Xử lý văn bản tiếng Việt cho query giống như đã làm với corpus
            processed_query = query.lower()
            print(f"=== BM25 DEBUG === (Preprocessing Query) Query sau lower(): '{processed_query}'")
            
            # Sử dụng regex giống như trong phương thức _initialize_bm25
            processed_query = re.sub(r'[.,;:!?()[\]{}"\'-]', ' ', processed_query)  # Loại bỏ dấu câu thông dụng
            processed_query = re.sub(r'\s+', ' ', processed_query)  # Loại bỏ nhiều khoảng trắng liên tiếp
            processed_query = processed_query.strip()  # Loại bỏ khoảng trắng ở đầu và cuối
            
            print(f"=== BM25 DEBUG === (Preprocessing Query) Query sau regex sub: '{processed_query}'")
            query_tokens = processed_query.split()
            
            print(f"=== BM25 DEBUG === Câu truy vấn sau khi tiền xử lý: '{processed_query}'")
            print(f"=== BM25 DEBUG === Tokens của câu truy vấn: {query_tokens}")
            
            if len(query_tokens) == 0:
                print(f"=== BM25 DEBUG === Không có tokens hợp lệ sau khi tiền xử lý câu truy vấn")
                return []
        except Exception as e_preprocess:
            print(f"=== BM25 DEBUG === Lỗi nghiêm trọng trong quá trình tiền xử lý query: {str(e_preprocess)}")
            import traceback
            print(f"=== BM25 DEBUG === Stack trace (query preprocessing): {traceback.format_exc()}")
            return []


        try:
            # Lấy điểm BM25 cho mỗi tài liệu
            # Đảm bảo self.corpus không rỗng và self.bm25 đã được fit
            if not self.corpus or len(self.corpus) == 0:
                print(f"=== BM25 DEBUG === Corpus rỗng, không thể lấy điểm BM25.")
                return []
            
            print(f"=== BM25 DEBUG === Bắt đầu lấy điểm BM25 với {len(query_tokens)} query tokens và {len(self.corpus)} tài liệu trong corpus.")
            bm25_scores = self.bm25.get_scores(query_tokens)

            # Tạo danh sách kết quả
            results = []
            for idx, score in enumerate(bm25_scores):
                # Lấy văn bản gốc từ doc_mappings thay vì sử dụng tokens từ corpus
                original_text = self.doc_mappings[idx].get("text", "")
                # Nếu không có text gốc trong doc_mappings, chuyển đổi tokens thành string
                if not original_text:
                    original_text = " ".join(self.corpus[idx]) if self.corpus[idx] else ""
                
                result = {
                    "text": original_text,  # Sử dụng text gốc thay vì tokens
                    "score": score,
                    "file_id": self.doc_mappings[idx].get("file_id", "unknown"),
                    "metadata": self.doc_mappings[idx].get("metadata", {}),
                }
                results.append(result)

            # Sắp xếp kết quả theo điểm số
            results.sort(key=lambda x: x["score"], reverse=True)

            # Trả về kết quả đã sắp xếp
            return results[:k]
        except Exception as e_get_scores:
            print(f"=== BM25 DEBUG === Lỗi nghiêm trọng trong quá trình lấy điểm BM25: {str(e_get_scores)}")
            import traceback
            print(f"=== BM25 DEBUG === Stack trace (get_scores): {traceback.format_exc()}")
            return []

    # Phương thức được gọi sau khi indexing tài liệu mới để cập nhật BM25
    def update_bm25_index(self):
        """Cập nhật lại BM25 index sau khi có thay đổi trong vector store"""
        print("Đang cập nhật BM25 index...")

        current_user_id = self.vector_store.user_id if hasattr(self.vector_store, 'user_id') else None
        if not current_user_id:
            print(f"=== BM25 DEBUG === (update_bm25_index) Không có user_id, không thể cập nhật BM25.")
            return False
        
        if not self.bm25_index_dir: # Phải có thư mục index của user mới cập nhật được
             print(f"=== BM25 DEBUG === (update_bm25_index) Đường dẫn BM25 chưa được thiết lập cho user {current_user_id}. Không thể cập nhật.")
             return False

        # Reset lại trạng thái để buộc tạo lại index
        self.bm25_initialized = False
        self.bm25 = None
        self.corpus = []
        self.doc_mappings = []

        # Xóa các file index cũ nếu có
        if os.path.exists(self.bm25_index_path):
            os.remove(self.bm25_index_path)
        if os.path.exists(self.corpus_path):
            os.remove(self.corpus_path)
        if os.path.exists(self.doc_mappings_path):
            os.remove(self.doc_mappings_path)

        # Khởi tạo lại BM25
        return self._initialize_bm25()

    # def hybrid_search(
    #     self,
    #     query: str,
    #     k: int = 5,
    #     alpha: float = 0.7,
    #     sources: List[str] = None,
    #     file_id: List[str] = None,
    #     ) -> List[Dict]:
    #     """Kết hợp tìm kiếm ngữ nghĩa và keyword"""
    #     print(f"=== Bắt đầu hybrid search với alpha={alpha} ===")

    #     semantic = self.semantic_search(query, k=k, sources=sources, file_id=file_id)
    #     print(f"Đã tìm được {len(semantic)} kết quả từ semantic search")

    #     keyword = self.keyword_search(query, k=k, sources=sources, file_id=file_id)
    #     print(f"Đã tìm được {len(keyword)} kết quả từ keyword search")

    #     combined = {}
    #     for res in semantic:
    #         combined[res["text"]] = {**res, "score": alpha * res["score"]}

    #     for res in keyword:
    #         if res["text"] in combined:
    #             combined[res["text"]]["score"] += (1 - alpha) * res["score"]
    #             print(f"Đã kết hợp kết quả trùng lặp: {res['text'][:50]}...")
    #         else:
    #             combined[res["text"]] = {**res, "score": (1 - alpha) * res["score"]}

    #     sorted_results = sorted(
    #         combined.values(), key=lambda x: x["score"], reverse=True
    #     )

    #     print(
    #         f"=== Kết thúc hybrid search: {len(sorted_results[:k])}/{len(combined)} kết quả ==="
    #     )

    #     return sorted_results[:k]

    def rerank_results(self, query: str, results: List[Dict]) -> List[Dict]:
        """Tái xếp hạng kết quả sử dụng cross-encoder và metadata phong phú"""
        if not results:
            return results

        # Đọc batch_size từ biến môi trường hoặc sử dụng giá trị mặc định cao hơn
        batch_size = int(os.getenv("RERANK_BATCH_SIZE", "16"))
        print(f"Đang rerank với batch_size={batch_size}")

        # Sử dụng model reranker đã được tải trước đó
        pairs = [(query, result["text"]) for result in results]
        scores = self.reranker.predict(pairs, batch_size=batch_size)

        # Nhận dạng loại truy vấn (definition, syntax, example, etc.)
        query_type = self._detect_query_type(query)
        print(f"Loại truy vấn được phát hiện: {query_type}")

        # Cập nhật điểm số và sắp xếp lại
        for idx, result in enumerate(results):
            # Điểm gốc từ reranker
            base_score = float(scores[idx])
            result["rerank_score"] = base_score

            # Tăng điểm dựa trên metadata phong phú nếu phù hợp với loại truy vấn
            metadata = result.get("metadata", {})
            score_boost = 0.0

            # Tăng trọng số cho các chunk phù hợp với loại truy vấn
            if query_type == "definition" and metadata.get("chứa_định_nghĩa", False):
                score_boost += 0.2  # Tăng 20%

            elif query_type == "syntax" and metadata.get("chứa_cú_pháp", False):
                score_boost += 0.25  # Tăng 25%

                # Tăng thêm điểm cho các loại cú pháp SQL cụ thể
                if "SELECT" in query and metadata.get("chứa_cú_pháp_select", False):
                    score_boost += 0.1
                elif "JOIN" in query and metadata.get("chứa_cú_pháp_join", False):
                    score_boost += 0.1
                elif ("CREATE" in query or "ALTER" in query) and metadata.get(
                    "chứa_cú_pháp_ddl", False
                ):
                    score_boost += 0.1
                elif (
                    "INSERT" in query or "UPDATE" in query or "DELETE" in query
                ) and metadata.get("chứa_cú_pháp_dml", False):
                    score_boost += 0.1

            elif query_type == "example" and metadata.get("chứa_mẫu_code", False):
                score_boost += 0.2  # Tăng 20%

            # Tăng điểm cho chunk có bảng nếu truy vấn liên quan đến tổ chức dữ liệu
            if ("bảng" in query.lower() or "table" in query.lower()) and metadata.get(
                "chứa_bảng", False
            ):
                score_boost += 0.15  # Tăng 15%

            # Áp dụng điểm tăng thêm
            if score_boost > 0:
                result["metadata_boost"] = score_boost  # Lưu giá trị tăng để debug
                result["rerank_score"] = base_score * (
                    1 + score_boost
                )  # Tăng theo phần trăm

            # In thông tin boost để debug
            if score_boost > 0:
                print(f"Tăng điểm {score_boost:.2f} cho chunk có metadata phù hợp.")

        return sorted(results, key=lambda x: x["rerank_score"], reverse=True)
        
    def set_vector_store_and_reload_bm25(self, new_vector_store):
        """
        Cập nhật vector_store và tải lại BM25 index phù hợp với user_id mới.
        Sử dụng khi chuyển đổi giữa các user_id khác nhau trong cùng một SearchManager toàn cục.
        """
        old_user_id = self.vector_store.user_id if hasattr(self.vector_store, 'user_id') else None
        new_user_id = new_vector_store.user_id if hasattr(new_vector_store, 'user_id') else None
        
        print(f"=== BM25 DEBUG === set_vector_store_and_reload_bm25: Từ user_id={old_user_id} sang user_id={new_user_id}")
        
        # Cập nhật vector_store trước, bất kể user_id có thay đổi hay không
        # để đảm bảo SearchManager luôn tham chiếu đến vector_store đúng
        self.vector_store = new_vector_store
        print(f"=== BM25 DEBUG === Đã cập nhật self.vector_store sang user_id={new_user_id}")

        if old_user_id != new_user_id or not self.bm25_initialized: # Cũng reload nếu chưa từng initialized
            if not new_user_id:
                print(f"=== BM25 DEBUG === User_id mới là None. Resetting BM25 state.")
                self.bm25_initialized = False
                self.bm25 = None
                self.corpus = []
                self.doc_mappings = []
                self.bm25_index_dir = None
                self.bm25_index_path = None
                self.corpus_path = None
                self.doc_mappings_path = None
                self.metadata_path = None
                return True # Trạng thái đã được reset

            print(f"Chuyển đổi SearchManager hoặc khởi tạo lần đầu cho user_id={new_user_id}")
            
            # Cập nhật đường dẫn BM25 index cho user_id mới
            data_dir = os.getenv("UPLOAD_DIR", "src/data")
            
            user_dir = os.path.join(data_dir, new_user_id)
            self.bm25_index_dir = os.path.join(user_dir, "bm25_index")
            print(f"Sử dụng thư mục BM25 index trong thư mục người dùng: {self.bm25_index_dir}")
                
            os.makedirs(self.bm25_index_dir, exist_ok=True) # Đảm bảo thư mục của user tồn tại
            
            # Cập nhật đường dẫn file
            self.bm25_index_path = os.path.join(self.bm25_index_dir, "bm25_index.pkl")
            self.corpus_path = os.path.join(self.bm25_index_dir, "corpus.pkl")
            self.doc_mappings_path = os.path.join(self.bm25_index_dir, "doc_mappings.pkl")
            self.metadata_path = os.path.join(self.bm25_index_dir, "bm25_metadata.json")
            
            print(f"=== BM25 DEBUG === Đã cập nhật đường dẫn: {self.bm25_index_path}")
            
             # Đặt lại trạng thái bm25_initialized và bm25 trước khi thử tải/khởi tạo
            self.bm25_initialized = False
            self.bm25 = None
            self.corpus = [] # Quan trọng: reset corpus và doc_mappings
            self.doc_mappings = []
            print(f"=== BM25 DEBUG === Đã đặt lại trạng thái bm25_initialized=False, bm25=None, corpus/mappings rỗng")

            # Thử tải BM25 index cho user_id mới
            loaded = self._try_load_bm25_index()
            print(f"=== BM25 DEBUG === Kết quả tải BM25 index: {'Thành công' if loaded else 'Thất bại'}")
            
            # Nếu không tải được, thử khởi tạo mới
            if not loaded:
                print(f"=== BM25 DEBUG === Không tải được BM25 index, thử khởi tạo mới...")
                initialized = self._initialize_bm25() # _initialize_bm25 sẽ sử dụng user_id từ self.vector_store
                print(f"=== BM25 DEBUG === Kết quả khởi tạo BM25 index: {'Thành công' if initialized else 'Thất bại'}")
            
            return True
        else:
            print(f"=== BM25 DEBUG === User_id không thay đổi ({new_user_id}) và BM25 đã được khởi tạo, không cần tải lại BM25 index")
            # Đảm bảo vector_store được cập nhật ngay cả khi user_id không đổi, đã làm ở trên.
            return False

    def _detect_query_type(self, query: str) -> str:
        """Phát hiện loại truy vấn: định nghĩa, cú pháp, hoặc ví dụ"""
        query_lower = query.lower()

        # Phát hiện truy vấn cú pháp (ưu tiên cao hơn) - liên quan đến SQL và các lệnh
        syntax_patterns = [
            r"\b(cú\s*pháp|syntax|format|khai\s*báo|declaration|statement)\b",
            r"\b(sử\s*dụng|cách\s*sử\s*dụng|usage|how\s*to\s*use)\b",
            r"\b(select|create|alter|insert|update|delete|procedure|function|trigger|view|index)\b",
            r"\b(sql|database|db|query|truy\s*vấn)\b.*\b(viết|tạo|thực\s*hiện)\b",
            r"\b(viết|write|code|lập\s*trình)\b.*\b(câu\s*lệnh|lệnh|command|statement|query)\b",
            r"\b(lệnh|câu\s*lệnh|command)\b.*\b(như\s*thế\s*nào|ra\s*sao|thế\s*nào)\b",
            r"\b(query|truy\s*vấn|câu\s*truy\s*vấn)\b",
        ]

        # Phát hiện truy vấn định nghĩa
        definition_patterns = [
            r"\b(định\s*nghĩa|khái\s*niệm|là\s*gì|what\s*is|define|mean\s*by)\b",
            r"\b(nghĩa\s*của|ý\s*nghĩa|meaning\s*of)\b",
            r"\b(giải\s*thích|explain|mô\s*tả|describe)\b",
        ]

        # Phát hiện truy vấn ví dụ
        example_patterns = [
            r"\b(ví\s*dụ|minh\s*họa|example|demonstrate|sample|mẫu)\b",
            r"\b(cho\s*xem|show\s*me|đưa\s*ra)\b",
            r"\b(demo|demonstration)\b",
        ]

        # Kiểm tra truy vấn cú pháp trước (ưu tiên cao hơn vì cần chính xác)
        for pattern in syntax_patterns:
            if re.search(pattern, query_lower):
                return "syntax"

        # Kiểm tra các từ khóa SQL cụ thể
        sql_keywords = [
            "SELECT", "FROM", "WHERE", "JOIN", "GROUP BY", "HAVING", "ORDER BY",
            "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP",
            "PROCEDURE", "FUNCTION", "TRIGGER", "VIEW", "INDEX", "TABLE"
        ]

        for keyword in sql_keywords:
            if keyword.lower() in query_lower or keyword in query:
                return "syntax"  # Nếu truy vấn chứa từ khóa SQL, coi như truy vấn cú pháp

        # Kiểm tra truy vấn ví dụ
        for pattern in example_patterns:
            if re.search(pattern, query_lower):
                return "example"

        # Kiểm tra truy vấn định nghĩa
        for pattern in definition_patterns:
            if re.search(pattern, query_lower):
                return "definition"

        # Mặc định trả về general nếu không phát hiện loại cụ thể
        return "general"

    def get_bm25_status(self):
        """Trả về thông tin chi tiết về trạng thái của BM25 để debug"""
        status = {
            "bm25_initialized": self.bm25_initialized,
            "bm25_is_none": self.bm25 is None,
            "corpus_length": len(self.corpus) if self.corpus else 0,
            "doc_mappings_length": len(self.doc_mappings) if self.doc_mappings else 0,
            "user_id": self.vector_store.user_id if hasattr(self.vector_store, 'user_id') else None,
            "bm25_index_dir": self.bm25_index_dir,
            "bm25_index_path": self.bm25_index_path,
            "corpus_path": self.corpus_path,
            "doc_mappings_path": self.doc_mappings_path,
            "metadata_path": self.metadata_path,
            "file_exists": {
                "bm25_index_path": os.path.exists(self.bm25_index_path),
                "corpus_path": os.path.exists(self.corpus_path),
                "doc_mappings_path": os.path.exists(self.doc_mappings_path),
                "metadata_path": os.path.exists(self.metadata_path),
            }
        }
        
        # Kiểm tra thêm về kích thước file
        if os.path.exists(self.bm25_index_path):
            status["bm25_index_size"] = os.path.getsize(self.bm25_index_path)
        if os.path.exists(self.corpus_path):
            status["corpus_size"] = os.path.getsize(self.corpus_path)
        if os.path.exists(self.doc_mappings_path):
            status["doc_mappings_size"] = os.path.getsize(self.doc_mappings_path)
            
        # Thêm thông tin metadata nếu có
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, "r") as f:
                    metadata = json.load(f)
                status["metadata"] = metadata
            except Exception as e:
                status["metadata_error"] = str(e)
                
        # Thêm thông tin về vector_store
        try:
            collection_info = self.vector_store.get_collection_info()
            if collection_info:
                status["collection_info"] = {
                    "points_count": collection_info.get("points_count", 0),
                    "collection_name": collection_info.get("name", "")
                }
        except Exception as e:
            status["collection_info_error"] = str(e)
            
        # Log thông tin status
        print(f"=== BM25 DEBUG === BM25 Status: {status}")
        
        return status
