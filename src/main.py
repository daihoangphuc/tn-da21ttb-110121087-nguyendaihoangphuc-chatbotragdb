import argparse
import os
from src.app import RAGPipeline


def parse_args():
    """Phân tích tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description="RAG Pipeline cho cơ sở dữ liệu")

    subparsers = parser.add_subparsers(dest="command", help="Lệnh cần thực hiện")

    # Lệnh index
    index_parser = subparsers.add_parser("index", help="Index dữ liệu")
    index_parser.add_argument(
        "--data-dir", type=str, required=True, help="Đường dẫn đến thư mục chứa dữ liệu"
    )

    # Lệnh query
    query_parser = subparsers.add_parser("query", help="Truy vấn dữ liệu")
    query_parser.add_argument("--query", type=str, help="Câu truy vấn")

    # Lệnh delete-index
    delete_parser = subparsers.add_parser("delete-index", help="Xóa toàn bộ index")
    delete_parser.add_argument(
        "--collection",
        type=str,
        help="Tên collection cần xóa (mặc định là cấu hình trong config.py)",
    )

    return parser.parse_args()


def main():
    """Hàm main của ứng dụng"""
    args = parse_args()

    # Khởi tạo pipeline
    pipeline = RAGPipeline()

    if args.command == "index":
        # Kiểm tra thư mục dữ liệu
        if not os.path.exists(args.data_dir):
            print(f"❌ Thư mục dữ liệu không tồn tại: {args.data_dir}")
            return

        # Thực hiện indexing
        pipeline.index_data(args.data_dir)

    elif args.command == "query":
        # Nếu không có tham số --query, yêu cầu nhập
        query = args.query
        if not query:
            query = input("Nhập câu truy vấn của bạn: ")

        # Thực hiện truy vấn
        response = pipeline.query(query)

        # In kết quả
        print("\n💬 Kết quả:")
        print(response)

    elif args.command == "delete-index":
        # Xóa index
        collection_name = args.collection
        # Xác nhận từ người dùng
        confirm = input(f"Bạn có chắc muốn xóa toàn bộ index? (y/n): ")
        if confirm.lower() == "y":
            try:
                pipeline.delete_index(collection_name)
                print("✅ Đã xóa index thành công.")
                # Thông báo về việc khởi động lại ứng dụng
                print(
                    "⚠️ Để đảm bảo hệ thống hoạt động đúng sau khi xóa index, vui lòng khởi động lại ứng dụng trước khi sử dụng lệnh query."
                )
            except Exception as e:
                print(f"❌ Lỗi khi xóa index: {str(e)}")
        else:
            print("❌ Đã hủy thao tác xóa index.")

    else:
        print("❌ Vui lòng chọn lệnh 'index', 'query' hoặc 'delete-index'")
        print("Ví dụ: python -m src.main index --data-dir ./data")
        print("Ví dụ: python -m src.main query --query 'Câu lệnh thao tác dữ liệu?'")
        print("Ví dụ: python -m src.main delete-index")


if __name__ == "__main__":
    main()
