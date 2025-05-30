"""
Script kiểm tra và tái khởi tạo BM25 index cho một user_id cụ thể
"""

import os
from dotenv import load_dotenv
from src.rag import AdvancedDatabaseRAG, initialize_global_resources
from src.vector_store import VectorStore
from src.search import SearchManager

# Load biến môi trường
load_dotenv()

def check_bm25_index(user_id):
    """Kiểm tra BM25 index cho user_id cụ thể"""
    print(f"=== Kiểm tra BM25 index cho user_id: {user_id} ===")
    
    # Khởi tạo tài nguyên toàn cục
    resources = initialize_global_resources()
    
    # Tạo vector store với user_id cụ thể
    vector_store = VectorStore(user_id=user_id)
    vector_store.collection_name = f"user_{user_id}"
    
    # Lấy SearchManager từ resources
    search_manager = resources["search_manager"]
    
    # Kiểm tra trạng thái hiện tại
    print("Trạng thái SearchManager trước khi cập nhật:")
    if hasattr(search_manager.vector_store, 'user_id'):
        print(f"  - vector_store.user_id: {search_manager.vector_store.user_id}")
    else:
        print("  - vector_store.user_id: None")
    print(f"  - bm25_initialized: {search_manager.bm25_initialized}")
    print(f"  - bm25 is None: {search_manager.bm25 is None}")
    
    # Cập nhật vector_store và tải lại BM25 index
    print("\nCập nhật vector_store và tải lại BM25 index...")
    search_manager.set_vector_store_and_reload_bm25(vector_store)
    
    # Kiểm tra lại trạng thái
    print("\nTrạng thái SearchManager sau khi cập nhật:")
    if hasattr(search_manager.vector_store, 'user_id'):
        print(f"  - vector_store.user_id: {search_manager.vector_store.user_id}")
    else:
        print("  - vector_store.user_id: None")
    print(f"  - bm25_initialized: {search_manager.bm25_initialized}")
    print(f"  - bm25 is None: {search_manager.bm25 is None}")
    
    # Lấy thông tin chi tiết về BM25 status
    print("\nThông tin chi tiết về BM25 status:")
    bm25_status = search_manager.get_bm25_status()
    for key, value in bm25_status.items():
        if isinstance(value, dict):
            print(f"  - {key}:")
            for subkey, subvalue in value.items():
                print(f"    - {subkey}: {subvalue}")
        else:
            print(f"  - {key}: {value}")
    
    # Khởi tạo RAG với user_id cụ thể
    rag = AdvancedDatabaseRAG(user_id=user_id)
    
    # Kiểm tra xem RAG có sử dụng đúng SearchManager không
    print("\nKiểm tra RAG:")
    if hasattr(rag.search_manager.vector_store, 'user_id'):
        print(f"  - rag.search_manager.vector_store.user_id: {rag.search_manager.vector_store.user_id}")
    else:
        print("  - rag.search_manager.vector_store.user_id: None")
    print(f"  - rag.search_manager.bm25_initialized: {rag.search_manager.bm25_initialized}")
    
    # Tạo query test
    print("\nThử nghiệm một query đơn giản...")
    query = "Các loại ràng buộc trong cơ sở dữ liệu"
    keyword_results = search_manager.keyword_search(query, k=5)
    print(f"Số kết quả từ keyword search: {len(keyword_results)}")
    
    # Nếu không có kết quả, thử cập nhật BM25 index
    if len(keyword_results) == 0:
        print("\nKhông tìm thấy kết quả, thử cập nhật BM25 index...")
        search_manager.update_bm25_index()
        
        # Thử lại query
        print("\nThử lại query sau khi cập nhật BM25 index...")
        keyword_results = search_manager.keyword_search(query, k=5)
        print(f"Số kết quả từ keyword search sau khi cập nhật: {len(keyword_results)}")
    
    print("\n=== Kết thúc kiểm tra ===")

if __name__ == "__main__":
    # Chỉ định user_id cần kiểm tra
    user_id = "5da861da-3d8f-454d-aec1-ca40b9e47f53"
    check_bm25_index(user_id) 