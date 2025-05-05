import os
import sys
from PIL import Image
import cv2
import numpy as np
import layoutparser as lp

print("=== Kiểm tra LayoutParser với phương pháp offline ===")

# Tạo thư mục cache
os.makedirs("./model_cache", exist_ok=True)

print("\n=== Tạo Mock Layout Model ===")
try:
    # Tạo class mô hình giả lập
    class MockLayoutModel:
        def __init__(self):
            self.name = "MockLayoutModel"

        def detect(self, image):
            height, width = image.shape[:2]
            print(f"Phát hiện layout cho ảnh {width}x{height}")

            # Tạo layout trống với 1 vùng text chiếm toàn bộ trang
            layout = lp.Layout(
                [
                    lp.TextBlock(
                        block=lp.Rectangle(0, 0, width, height), type="Text", score=1.0
                    )
                ]
            )
            return layout

    # Khởi tạo mô hình
    mock_model = MockLayoutModel()
    print("✓ Tạo thành công MockLayoutModel với phương thức detect tùy chỉnh")
except Exception as e:
    print(f"✗ Không thể tạo MockLayoutModel: {str(e)}")
    sys.exit(1)

# Tạo ảnh mẫu để kiểm tra
print("\n=== Tạo ảnh mẫu để kiểm tra ===")
try:
    # Tạo ảnh trắng kích thước 800x1000
    image = np.ones((1000, 800, 3), dtype=np.uint8) * 255

    # Vẽ một số vùng văn bản giả lập
    cv2.rectangle(image, (100, 100), (700, 200), (200, 200, 200), -1)  # Title
    cv2.rectangle(image, (100, 250), (700, 800), (230, 230, 230), -1)  # Text

    # Lưu ảnh
    cv2.imwrite("sample_page.jpg", image)
    print("✓ Đã tạo ảnh mẫu tại sample_page.jpg")
except Exception as e:
    print(f"✗ Không thể tạo ảnh mẫu: {str(e)}")
    sys.exit(1)

# Phát hiện layout
print("\n=== Phát hiện layout từ ảnh mẫu ===")
try:
    # Đọc ảnh
    image = cv2.imread("sample_page.jpg")
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Phát hiện layout
    layout = mock_model.detect(image)
    print(f"Đã phát hiện {len(layout)} vùng layout")

    # In chi tiết về các vùng
    for i, block in enumerate(layout):
        print(f"Vùng {i}: {block.type}, Score: {block.score:.2f}, Bbox: {block.block}")

    print("\n✓ Phát hiện layout thành công với phương pháp giả lập!")
except Exception as e:
    print(f"✗ Lỗi khi phát hiện layout: {str(e)}")
    import traceback

    traceback.print_exc()

print("\n=== Kết thúc kiểm tra ===")
print(
    "Giải pháp giả lập đã sẵn sàng. Khi cài đặt layout detection trong document_processor.py,"
)
print(
    "hệ thống sẽ cố gắng tải mô hình chính, nếu không được sẽ dùng phương pháp giả lập này."
)
print(
    "Mọi tài liệu PDF sẽ được xử lý với giả định mỗi trang là một vùng text duy nhất."
)
