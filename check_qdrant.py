import os
from dotenv import load_dotenv
from src.vector_store import VectorStore
from src.search import SearchManager
from src.embedding import EmbeddingModel

# Load biến môi trường
load_dotenv()

def check_collection_info():
    """Kiểm tra thông tin collection trong Qdrant"""
    print("=== Kiểm tra thông tin collection trong Qdrant ===")
    
    # Tạo Vector Store với user_id cụ thể
    user_id = "5da861da-3d8f-454d-aec1-ca40b9e47f53"
    vector_store = VectorStore(user_id=user_id)
    
    # Lấy thông tin collection
    info = vector_store.get_collection_info()
    print(f"Collection info: {info}")
    
    # Lấy tất cả tài liệu để xem collection có dữ liệu không
    docs = vector_store.get_all_documents(limit=5)
    print(f"Documents count: {len(docs)}")
    if docs:
        print(f"Sample document: {docs[0]}")
    else:
        print("Collection không chứa dữ liệu!")
    
    # Kiểm tra file cụ thể
    file_id = "1feec30a-791e-4365-b64b-b7cfb6c66cf2"
    print(f"\nKiểm tra file với ID: {file_id}")
    
    # Tìm kiếm với file_id cụ thể
    embedding_model = EmbeddingModel()
    query_vector = embedding_model.encode("Khái niệm cơ sở dữ liệu là gì?")
    
    results = vector_store.search_with_filter(
        query_vector=query_vector,
        file_id=[file_id],
        limit=5
    )
    
    print(f"Kết quả tìm kiếm với file_id={file_id}: {len(results)} kết quả")
    if results:
        print(f"Sample result: {results[0]}")
    else:
        print(f"Không tìm thấy dữ liệu cho file_id={file_id}")

def update_bm25_index():
    """Cập nhật BM25 index"""
    print("\n=== Cập nhật BM25 index ===")
    
    # Tạo các thành phần cần thiết
    user_id = "5da861da-3d8f-454d-aec1-ca40b9e47f53"
    vector_store = VectorStore(user_id=user_id)
    embedding_model = EmbeddingModel()
    search_manager = SearchManager(vector_store, embedding_model)
    
    # Cập nhật BM25 index
    search_manager.update_bm25_index()
    print("Đã cập nhật BM25 index")

if __name__ == "__main__":
    check_collection_info()
    update_bm25_index() 