import requests
import json
import time

# URL cơ sở của API
BASE_URL = "http://localhost:8000/api"


def test_ask_question():
    """Kiểm tra API đặt câu hỏi"""
    url = f"{BASE_URL}/ask"

    # Các loại tìm kiếm khác nhau để thử nghiệm
    for search_type in ["hybrid", "semantic", "keyword"]:
        print(f"\n=== Kiểm tra tìm kiếm {search_type.upper()} ===")

        # Chuẩn bị dữ liệu
        data = {
            "question": "Cú pháp câu lệnh FOREIGN KEY là gì?",
            "search_type": search_type,
        }

        # Gọi API
        response = requests.post(url, json=data)

        # Kiểm tra kết quả
        if response.status_code == 200:
            result = response.json()
            print(f"Question ID: {result.get('question_id', 'N/A')}")
            print(f"Câu hỏi: {result['question']}")
            print(f"Phương pháp tìm kiếm: {result['search_method']}")
            print(f"Câu trả lời: {result['answer'][:200]}...")
            print(f"Số nguồn tham khảo: {len(result['sources'])}")
            if "total_reranked" in result:
                print(f"Tổng số kết quả rerank: {result['total_reranked']}")

            # In nguồn tham khảo
            print("\nNguồn tham khảo:")
            for i, source in enumerate(result["sources"], 1):
                print(f"  {i}. {source['source']} (Score: {source['score']:.4f})")

            # Lưu question_id để kiểm tra feedback
            if search_type == "hybrid":
                global last_question_id
                last_question_id = result.get("question_id")
        else:
            print(f"Lỗi {response.status_code}: {response.text}")


def test_semantic_search():
    """Kiểm tra API tìm kiếm ngữ nghĩa"""
    url = f"{BASE_URL}/search/semantic"

    # Chuẩn bị dữ liệu
    data = {"question": "Cú pháp câu lệnh FOREIGN KEY là gì?"}

    # Gọi API
    response = requests.post(url, json=data)

    # Kiểm tra kết quả
    if response.status_code == 200:
        result = response.json()
        print("\n=== Kết quả tìm kiếm ngữ nghĩa ===")
        print(f"Câu truy vấn: {result['query']}")
        print(f"Số kết quả: {len(result['results'])}")

        # In kết quả
        for i, item in enumerate(result["results"], 1):
            print(f"\n  {i}. Score: {item['score']:.4f}")
            print(f"     Source: {item['metadata'].get('source', 'unknown')}")
            print(f"     Category: {item['metadata'].get('category', 'general')}")
            print(f"     Nội dung: {item['text'][:150]}...")
    else:
        print(f"Lỗi {response.status_code}: {response.text}")


def test_hybrid_search():
    """Kiểm tra API tìm kiếm hybrid"""
    url = f"{BASE_URL}/search/hybrid"

    # Chuẩn bị dữ liệu
    data = {"question": "Cú pháp câu lệnh FOREIGN KEY là gì?"}

    # Tham số truy vấn
    params = {"k": 3, "alpha": 0.8}

    # Gọi API
    response = requests.post(url, json=data, params=params)

    # Kiểm tra kết quả
    if response.status_code == 200:
        result = response.json()
        print("\n=== Kết quả tìm kiếm hybrid (80% semantic + 20% keyword) ===")
        print(f"Câu truy vấn: {result['query']}")
        print(f"Số kết quả: {len(result['results'])}")

        # In kết quả
        for i, item in enumerate(result["results"], 1):
            print(f"\n  {i}. Score: {item['score']:.4f}")
            print(f"     Source: {item['metadata'].get('source', 'unknown')}")
            print(f"     Category: {item['metadata'].get('category', 'general')}")
            print(f"     Nội dung: {item['text'][:150]}...")
    else:
        print(f"Lỗi {response.status_code}: {response.text}")


def test_collection_info():
    """Kiểm tra API lấy thông tin collection"""
    url = f"{BASE_URL}/collection/info"

    # Gọi API
    response = requests.get(url)

    # Kiểm tra kết quả
    if response.status_code == 200:
        result = response.json()
        print("\n=== Thông tin collection ===")
        print(f"Tên collection: {result.get('name')}")
        print(f"Số points: {result.get('points_count')}")

        vectors_config = result.get("config", {}).get("params", {})
        if vectors_config:
            print(f"Kích thước vector: {vectors_config.get('size')}")
            print(f"Distance function: {vectors_config.get('distance')}")
    else:
        print(f"Lỗi {response.status_code}: {response.text}")


def test_index_status():
    """Kiểm tra API trạng thái indexing"""
    url = f"{BASE_URL}/index/status"

    # Gọi API
    response = requests.get(url)

    # Kiểm tra kết quả
    if response.status_code == 200:
        result = response.json()
        print("\n=== Trạng thái indexing ===")
        print(f"Trạng thái: {result['status']}")
        print(f"Thông báo: {result['message']}")
        print(f"Số tài liệu đã xử lý: {result['processed_files']}")
    else:
        print(f"Lỗi {response.status_code}: {response.text}")


def test_analyze_sql():
    """Kiểm tra API phân tích SQL"""
    url = f"{BASE_URL}/analyze/sql"

    # Chuẩn bị dữ liệu
    query = """
    SELECT p.product_name, c.category_name, SUM(od.quantity * od.unit_price) as revenue
    FROM products p
    JOIN order_details od ON p.product_id = od.product_id
    JOIN categories c ON p.category_id = c.category_id
    JOIN orders o ON od.order_id = o.order_id
    WHERE o.order_date BETWEEN '2023-01-01' AND '2023-12-31'
    GROUP BY p.product_name, c.category_name
    ORDER BY revenue DESC
    """

    data = {
        "sql_query": query,
        "database_context": "Hệ thống bán hàng với bảng products, orders, order_details, categories",
    }

    # Gọi API
    response = requests.post(url, json=data)

    # Kiểm tra kết quả
    if response.status_code == 200:
        result = response.json()
        print("\n=== Phân tích SQL ===")
        print(f"Truy vấn gốc: {result['query'][:100]}...")
        print(f"\nSố đề xuất: {len(result['suggestions'])}")
        print(f"\nĐề xuất cải tiến:")
        for i, suggestion in enumerate(result["suggestions"], 1):
            print(f"  {i}. {suggestion}")

        if result.get("optimized_query"):
            print(f"\nTruy vấn đã tối ưu:")
            print(result["optimized_query"])
        else:
            print("\nKhông có truy vấn tối ưu được đề xuất")
    else:
        print(f"Lỗi {response.status_code}: {response.text}")


def test_categories():
    """Kiểm tra API danh mục tài liệu"""
    url = f"{BASE_URL}/categories"

    # Gọi API
    response = requests.get(url)

    # Kiểm tra kết quả
    if response.status_code == 200:
        result = response.json()
        print("\n=== Thống kê danh mục tài liệu ===")
        print(f"Tổng số tài liệu: {result['total_documents']}")
        print(f"Các danh mục: {', '.join(result['categories'])}")
        print("\nSố lượng tài liệu theo danh mục:")
        for category, count in result["documents_by_category"].items():
            print(f"  - {category}: {count} tài liệu")
    else:
        print(f"Lỗi {response.status_code}: {response.text}")


def test_submit_feedback():
    """Kiểm tra API gửi phản hồi"""
    # Cần có question_id từ câu hỏi trước đó
    global last_question_id
    if not globals().get("last_question_id"):
        print("\n=== Không thể kiểm tra gửi phản hồi: Không có question_id ===")
        return

    url = f"{BASE_URL}/feedback"

    # Chuẩn bị dữ liệu
    feedback_data = {
        "question_id": last_question_id,
        "rating": 4,
        "is_helpful": True,
        "comment": "Câu trả lời rất hữu ích, cung cấp đủ thông tin tôi cần.",
        "specific_feedback": {"accuracy": 4, "completeness": 4, "clarity": 5},
    }

    # Gọi API
    response = requests.post(url, json=feedback_data)

    # Kiểm tra kết quả
    if response.status_code == 200:
        result = response.json()
        print("\n=== Gửi phản hồi ===")
        print(f"Trạng thái: {result['status']}")
        print(f"Thông báo: {result['message']}")
    else:
        print(f"Lỗi {response.status_code}: {response.text}")


def test_feedback_stats():
    """Kiểm tra API thống kê phản hồi"""
    url = f"{BASE_URL}/feedback/stats"

    # Gọi API
    response = requests.get(url)

    # Kiểm tra kết quả
    if response.status_code == 200:
        result = response.json()
        print("\n=== Thống kê phản hồi ===")
        print(f"Tổng số phản hồi: {result['total_feedback']}")
        print(f"Điểm đánh giá trung bình: {result['average_rating']}/5")
        print(f"Tỷ lệ hữu ích: {result['helpful_percentage']}%")

        if "ratings_distribution" in result:
            print("\nPhân bố điểm đánh giá:")
            for rating, count in result["ratings_distribution"].items():
                print(f"  - {rating} sao: {count} phản hồi")
    else:
        print(f"Lỗi {response.status_code}: {response.text}")


def test_get_files():
    """Kiểm tra API lấy danh sách file"""
    url = f"{BASE_URL}/files"

    # Gọi API
    response = requests.get(url)

    # Kiểm tra kết quả
    if response.status_code == 200:
        result = response.json()
        print("\n=== Danh sách file đã upload ===")
        print(f"Tổng số file: {result['total_files']}")

        if result["files"]:
            print("\nDanh sách file:")
            for i, file in enumerate(result["files"], 1):
                print(f"  {i}. {file['filename']} ({file['extension']})")
                print(f"     Kích thước: {file['size']} bytes")
                print(f"     Ngày tải lên: {file['upload_date']}")
        else:
            print("Chưa có file nào được tải lên")
    else:
        print(f"Lỗi {response.status_code}: {response.text}")


def test_delete_file(filename=None):
    """Kiểm tra API xóa file"""
    if not filename:
        print("\n=== Bỏ qua kiểm tra xóa file: Không có tên file ===")
        return

    url = f"{BASE_URL}/files/{filename}"

    # Gọi API
    response = requests.delete(url)

    # Kiểm tra kết quả
    if response.status_code == 200:
        result = response.json()
        print("\n=== Xóa file ===")
        print(f"File: {result['filename']}")
        print(f"Trạng thái: {result['status']}")
        print(f"Thông báo: {result['message']}")
        print(f"Số điểm đã xóa: {result['removed_points']}")
    else:
        print(f"Lỗi {response.status_code}: {response.text}")


def test_reset_collection():
    """Kiểm tra API reset collection"""
    url = f"{BASE_URL}/collection/reset"

    # Hỏi người dùng trước khi reset
    confirm = input("\nBạn có chắc chắn muốn reset collection? (y/N): ")
    if confirm.lower() != "y":
        print("Bỏ qua reset collection")
        return

    # Gọi API
    response = requests.delete(url)

    # Kiểm tra kết quả
    if response.status_code == 200:
        result = response.json()
        print("\n=== Reset collection ===")
        print(f"Trạng thái: {result['status']}")
        print(f"Thông báo: {result['message']}")
        print(f"Kích thước vector: {result.get('vector_size')}")
    else:
        print(f"Lỗi {response.status_code}: {response.text}")


if __name__ == "__main__":
    print("=== Bắt đầu kiểm tra API Hệ thống RAG ===")
    print(f"API Base URL: {BASE_URL}")

    # Biến toàn cục để lưu question_id
    last_question_id = None

    # Kiểm tra các tính năng khác nhau
    try:
        # Kiểm tra thông tin collection trước
        test_collection_info()

        # Kiểm tra trạng thái indexing
        test_index_status()

        # Kiểm tra danh sách file
        test_get_files()

        # Kiểm tra thống kê danh mục
        test_categories()

        # Kiểm tra tìm kiếm ngữ nghĩa
        test_semantic_search()

        # Kiểm tra tìm kiếm hybrid
        test_hybrid_search()

        # Kiểm tra đặt câu hỏi với các loại tìm kiếm khác nhau
        test_ask_question()

        # Kiểm tra phân tích SQL
        test_analyze_sql()

        # Kiểm tra gửi phản hồi
        test_submit_feedback()

        # Kiểm tra thống kê phản hồi
        test_feedback_stats()

        # Tùy chọn xóa file (cần chỉ định tên file)
        # test_delete_file("tên_file.pdf")

        # Tùy chọn reset collection (sẽ hỏi trước khi thực hiện)
        # test_reset_collection()

    except requests.exceptions.ConnectionError:
        print("\nLỗi kết nối: Không thể kết nối đến API.")
        print(
            "Vui lòng chắc chắn rằng API đang chạy bằng lệnh: python -m uvicorn src.api:app --host 0.0.0.0 --port 8000"
        )

    print("\n=== Kết thúc kiểm tra API ===")
