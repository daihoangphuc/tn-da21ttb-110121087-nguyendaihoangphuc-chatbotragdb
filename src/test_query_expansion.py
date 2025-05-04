"""
Script kiểm thử chức năng query expansion
"""

from src.query_processor import QueryProcessor
from src.rag import AdvancedDatabaseRAG
import os
from dotenv import load_dotenv

# Load biến môi trường từ .env
load_dotenv()


def test_query_processor():
    """Kiểm tra QueryProcessor"""
    print("=== Kiểm tra QueryProcessor ===")

    # Khởi tạo QueryProcessor
    qp = QueryProcessor()

    # Thử mở rộng một vài query
    test_queries = [
        "CSDL là gì",
        "Cơ sở dữ liệu là gì",
        "SQL là gì",
        "Mục đích của DBMS",
        "Khóa chính có vai trò gì",
    ]

    for query in test_queries:
        expanded = qp.expand_query(query)
        print(f"\nQuery gốc: '{query}'")
        print(f"Mở rộng thành {len(expanded)} biến thể:")
        for i, exp in enumerate(expanded):
            print(f"  {i+1}. {exp}")

    # Lưu từ điển đồng nghĩa
    synonyms_dir = os.getenv("SYNONYMS_DIR", "src/data/synonyms")
    synonyms_file = os.getenv(
        "SYNONYMS_FILE", os.path.join(synonyms_dir, "synonyms.json")
    )

    # Đảm bảo thư mục tồn tại
    os.makedirs(os.path.dirname(synonyms_file), exist_ok=True)

    # Lưu file
    qp.save_synonyms(synonyms_file)
    print(f"Đã lưu từ điển đồng nghĩa vào {synonyms_file}")


def test_rag_with_expansion():
    """Kiểm tra hệ thống RAG với query expansion"""
    print("\n=== Kiểm tra RAG với query expansion ===")

    # Khởi tạo hệ thống RAG với query expansion
    rag = AdvancedDatabaseRAG(enable_query_expansion=True)

    # Kiểm tra 2 query tương đương nhưng viết khác nhau
    test_queries = ["CSDL là gì", "Cơ sở dữ liệu là gì"]

    # Thử tìm kiếm ngữ nghĩa
    print("\n== Thử nghiệm tìm kiếm ngữ nghĩa ==")
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = rag.semantic_search(query, k=3, sources=None)
        print(f"Tìm thấy {len(results)} kết quả")
        for i, res in enumerate(results[:3]):
            print(f"  {i+1}. Score: {res.get('score', 0):.4f}")
            print(f"     Snippet: {res.get('text', '')[:100]}...")

    # Thử hybrid search
    print("\n== Thử nghiệm hybrid search ==")
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = rag.hybrid_search(query, k=3, sources=None)
        print(f"Tìm thấy {len(results)} kết quả")
        for i, res in enumerate(results[:3]):
            print(f"  {i+1}. Score: {res.get('score', 0):.4f}")
            print(f"     Snippet: {res.get('text', '')[:100]}...")


if __name__ == "__main__":
    # Kiểm tra từng phần
    test_query_processor()
    test_rag_with_expansion()
