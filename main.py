import os
import warnings
from dotenv import load_dotenv
from src.rag import AdvancedDatabaseRAG

warnings.filterwarnings("ignore")
load_dotenv()

# Sử dụng hệ thống
if __name__ == "__main__":
    # Khởi tạo hệ thống
    rag = AdvancedDatabaseRAG()

    # Bước 1: Tải và index dữ liệu (chỉ chạy lần đầu)
    print("Đang tải và xử lý tài liệu...")
    documents = rag.load_documents("D:/DATN/V4/src/data")
    processed_chunks = rag.process_documents(documents)
    print(f"Đã xử lý {len(processed_chunks)} chunks")

    print("Đang index lên Qdrant...")
    rag.index_to_qdrant(processed_chunks)
    print("Index hoàn tất!")

    # Bước 2: Thử nghiệm hệ thống
    questions = ["Cú pháp câu lệnh FOREIGN KEY?"]

    for question in questions:
        print(f"\nCâu hỏi: {question}")
        result = rag.query_with_sources(question)
        print(f"\nCâu trả lời: {result['answer']}")
        print("\nNguồn tham khảo:")
        for source in result["sources"]:
            print(f"- {source['source']} (score: {source['score']:.2f})")
            print(f"  {source['content_snippet']}")

    # Xem thông tin collection
    print("\nThông tin collection:")
    print(rag.get_collection_info())
