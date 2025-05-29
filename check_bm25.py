import os
from dotenv import load_dotenv
from src.vector_store import VectorStore
from src.search import SearchManager
from src.embedding import EmbeddingModel
import time
import sys
import json

# Load biến môi trường
load_dotenv()

def check_bm25_status(user_id=None):
    """Kiểm tra chi tiết về trạng thái BM25 index"""
    print(f"=== KIỂM TRA BM25 INDEX ===")
    print(f"Thời gian: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"User ID: {user_id}")
    
    # Tạo Vector Store với user_id cụ thể hoặc không
    if user_id:
        print(f"\n--- Kiểm tra BM25 cho user_id: {user_id} ---")
        vector_store = VectorStore(user_id=user_id)
    else:
        print(f"\n--- Kiểm tra BM25 toàn cục (không có user_id) ---")
        vector_store = VectorStore()
        
    # Tạo EmbeddingModel
    embedding_model = EmbeddingModel()
    
    # Tạo SearchManager
    search_manager = SearchManager(vector_store, embedding_model)
    
    # Lấy và hiển thị trạng thái BM25
    status = search_manager.get_bm25_status()
    
    # Hiển thị thông tin chi tiết
    print("\n=== THÔNG TIN BM25 INDEX ===")
    print(f"BM25 đã khởi tạo: {status['bm25_initialized']}")
    print(f"BM25 object là None: {status['bm25_is_none']}")
    print(f"Số lượng tài liệu trong corpus: {status['corpus_length']}")
    print(f"Số lượng tài liệu trong doc_mappings: {status['doc_mappings_length']}")
    print(f"User ID: {status['user_id']}")
    
    print(f"\nĐường dẫn BM25 index: {status['bm25_index_dir']}")
    print(f"File bm25_index.pkl tồn tại: {status['file_exists']['bm25_index_path']}")
    print(f"File corpus.pkl tồn tại: {status['file_exists']['corpus_path']}")
    print(f"File doc_mappings.pkl tồn tại: {status['file_exists']['doc_mappings_path']}")
    print(f"File bm25_metadata.json tồn tại: {status['file_exists']['metadata_path']}")
    
    # Hiển thị kích thước file nếu có
    if 'bm25_index_size' in status:
        print(f"\nKích thước file bm25_index.pkl: {status['bm25_index_size']} bytes")
    if 'corpus_size' in status:
        print(f"Kích thước file corpus.pkl: {status['corpus_size']} bytes")
    if 'doc_mappings_size' in status:
        print(f"Kích thước file doc_mappings.pkl: {status['doc_mappings_size']} bytes")
    
    # Hiển thị metadata nếu có
    if 'metadata' in status:
        print(f"\nMetadata: {status['metadata']}")
    
    # Hiển thị thông tin collection
    if 'collection_info' in status:
        print(f"\nThông tin collection:")
        print(f"  - Tên collection: {status['collection_info']['collection_name']}")
        print(f"  - Số lượng points: {status['collection_info']['points_count']}")

    # Kiểm tra và thử một câu truy vấn
    print("\n=== THỬ NGHIỆM TÌM KIẾM BM25 ===")
    test_query = "hệ quản trị cơ sở dữ liệu"
    print(f"Thử tìm kiếm với câu truy vấn: '{test_query}'")
    
    # Thử khởi tạo BM25 nếu chưa được khởi tạo
    if not search_manager.bm25_initialized:
        print("BM25 chưa được khởi tạo, đang thử khởi tạo...")
        initialized = search_manager._initialize_bm25()
        print(f"Kết quả khởi tạo BM25: {'Thành công' if initialized else 'Thất bại'}")
    
    # Thử tìm kiếm
    results = search_manager.keyword_search(test_query, k=5)
    
    if results:
        print(f"Tìm thấy {len(results)} kết quả BM25 cho '{test_query}'")
        for i, result in enumerate(results[:3], 1):  # Chỉ hiển thị 3 kết quả đầu tiên
            print(f"\nKết quả #{i}:")
            print(f"  - Score: {result.get('score')}")
            text = result.get('text', '')
            text_preview = text[:100] + "..." if len(text) > 100 else text
            print(f"  - Text: {text_preview}")
    else:
        print(f"Không tìm thấy kết quả BM25 cho '{test_query}'")
        
        # Kiểm tra corpus
        print("\n=== KIỂM TRA CORPUS ===")
        if search_manager.corpus:
            print(f"Corpus có {len(search_manager.corpus)} tài liệu")
            # Hiển thị mẫu từ corpus
            if len(search_manager.corpus) > 0:
                sample_doc = search_manager.corpus[0]
                print(f"Mẫu token từ corpus[0]: {sample_doc[:30] if len(sample_doc) > 30 else sample_doc}")
                
                # Tìm kiếm trong corpus
                query_tokens = test_query.lower().split()
                print(f"Query tokens: {query_tokens}")
                
                # Đếm số lượng tài liệu có chứa ít nhất một token từ query
                matching_docs = 0
                for doc_tokens in search_manager.corpus:
                    has_match = any(token in doc_tokens for token in query_tokens)
                    if has_match:
                        matching_docs += 1
                
                print(f"Số tài liệu có chứa ít nhất một token từ query: {matching_docs}/{len(search_manager.corpus)}")
                
                if matching_docs == 0:
                    print("\nNGUYÊN NHÂN: Không có tài liệu nào trong corpus chứa các token từ câu truy vấn!")
        else:
            print("Corpus rỗng hoặc không tồn tại!")
            print("\nNGUYÊN NHÂN: Corpus rỗng, BM25 không có dữ liệu để tìm kiếm!")
    
    return status

def check_all_user_bm25():
    """Kiểm tra BM25 index cho tất cả các thư mục người dùng trong data_dir"""
    data_dir = os.getenv("UPLOAD_DIR", "src/data")
    print(f"Kiểm tra BM25 cho tất cả người dùng trong: {data_dir}")
    
    # Kiểm tra thư mục data_dir có tồn tại không
    if not os.path.exists(data_dir):
        print(f"Thư mục {data_dir} không tồn tại!")
        return
    
    # Lấy danh sách thư mục con (các user_id)
    user_dirs = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
    
    if not user_dirs:
        print(f"Không tìm thấy thư mục người dùng nào trong {data_dir}")
        return
    
    print(f"Tìm thấy {len(user_dirs)} thư mục người dùng")
    
    # Kiểm tra BM25 cho từng user_id
    for user_id in user_dirs:
        if user_id == "bm25_index":  # Bỏ qua thư mục bm25_index nếu có
            continue
        print(f"\n{'='*50}")
        print(f"Kiểm tra BM25 cho user_id: {user_id}")
        check_bm25_status(user_id)

if __name__ == "__main__":
    # Xử lý tham số dòng lệnh
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            check_all_user_bm25()
        else:
            check_bm25_status(sys.argv[1])
    else:
        # Mặc định kiểm tra BM25 toàn cục (không có user_id)
        check_bm25_status()
        print("\nĐể kiểm tra BM25 cho một user_id cụ thể, sử dụng: python check_bm25.py <user_id>")
        print("Để kiểm tra BM25 cho tất cả người dùng, sử dụng: python check_bm25.py --all") 