import os
import glob
from dotenv import load_dotenv
from src.rag import AdvancedDatabaseRAG

# Load biến môi trường
load_dotenv()

def reindex_documents():
    """Tái index tài liệu vào Qdrant"""
    print("=== Tái index tài liệu vào Qdrant ===")
    
    # Tạo RAG với user_id cụ thể
    user_id = "5da861da-3d8f-454d-aec1-ca40b9e47f53"
    rag = AdvancedDatabaseRAG(user_id=user_id)
    
    # Đường dẫn đến thư mục chứa tài liệu
    upload_dir = os.getenv("UPLOAD_DIR", "src/data")
    data_dir = os.path.join(upload_dir, user_id) if user_id else upload_dir
    
    print(f"Tìm kiếm tài liệu trong thư mục: {data_dir}")
    
    # Kiểm tra xem thư mục có tồn tại không
    if not os.path.exists(data_dir):
        print(f"Thư mục {data_dir} không tồn tại!")
        return
    
    # Liệt kê các file trong thư mục
    files = []
    for ext in ["*.pdf", "*.docx", "*.txt"]:
        files.extend(glob.glob(os.path.join(data_dir, ext)))
    
    print(f"Tìm thấy {len(files)} tài liệu: {files}")
    
    # Nếu không tìm thấy file nào, kiểm tra thư mục gốc
    if not files and user_id:
        print(f"Không tìm thấy tài liệu trong thư mục người dùng, kiểm tra thư mục gốc: {upload_dir}")
        for ext in ["*.pdf", "*.docx", "*.txt"]:
            files.extend(glob.glob(os.path.join(upload_dir, ext)))
        print(f"Tìm thấy {len(files)} tài liệu trong thư mục gốc: {files}")
    
    if not files:
        print("Không tìm thấy tài liệu nào để index!")
        return
    
    # Load và index tài liệu
    print(f"Bắt đầu index {len(files)} tài liệu...")
    rag.load_documents(data_dir)
    print("Hoàn thành index tài liệu")

if __name__ == "__main__":
    reindex_documents() 