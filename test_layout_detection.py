import os
import sys
from PIL import Image
import layoutparser as lp
import cv2
from pdf2image import convert_from_path
import numpy as np

print("=== Kiểm tra LayoutParser ===")

# Đường dẫn đến PDF mẫu (thay thế bằng đường dẫn thực của bạn)
sample_pdf = "src/data/Li_thuyet_Hadoop.pdf"
if not os.path.exists(sample_pdf):
    print(f"Không tìm thấy file {sample_pdf}")
    sample_pdfs = [f for f in os.listdir("src/data") if f.endswith(".pdf")]
    if sample_pdfs:
        sample_pdf = os.path.join("src/data", sample_pdfs[0])
        print(f"Sử dụng file {sample_pdf}")
    else:
        print("Không tìm thấy file PDF nào trong thư mục src/data")
        print("Vui lòng tải lên một file PDF trước khi chạy script này")
        sys.exit(1)

# Kiểm tra Poppler
poppler_path = os.environ.get("POPPLER_PATH", None)
if not poppler_path:
    print("POPPLER_PATH chưa được thiết lập")
    # Tìm kiếm trong các đường dẫn phổ biến
    poppler_paths = [
        r"C:\Program Files\poppler\bin",
        r"C:\Program Files\poppler\Library\bin",
        r"C:\poppler\bin",
    ]
    for path in poppler_paths:
        if os.path.exists(path):
            print(f"Tìm thấy Poppler tại: {path}")
            os.environ["POPPLER_PATH"] = path
            poppler_path = path
            break

print(f"POPPLER_PATH = {poppler_path}")

# Chuyển đổi PDF sang ảnh
try:
    if poppler_path:
        images = convert_from_path(sample_pdf, poppler_path=poppler_path)
    else:
        images = convert_from_path(sample_pdf)
    print(f"Đã chuyển đổi PDF thành {len(images)} trang")
except Exception as e:
    print(f"Lỗi khi chuyển đổi PDF: {str(e)}")
    sys.exit(1)

# Thử tải các mô hình khác nhau
print("\n=== Thử tải Detectron2LayoutModel ===")
try:
    detectron_model = lp.Detectron2LayoutModel(
        "lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config",
        label_map={0: "Text", 1: "Title", 2: "List", 3: "Table", 4: "Figure"},
        extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.8],
    )
    print("✓ Tải thành công Detectron2LayoutModel")
    # Lưu mô hình thành công để sử dụng sau
    model = detectron_model
except Exception as e:
    print(f"✗ Không thể tải Detectron2LayoutModel: {str(e)}")
    model = None

if model is None:
    print("\n=== Thử tải EfficientDetLayoutModel ===")
    try:
        effdet_model = lp.EfficientDetLayoutModel(
            "lp://efficientdet/PubLayNet/tf_efficientdet_d0/config",
            label_map={0: "Text", 1: "Title", 2: "List", 3: "Table", 4: "Figure"},
        )
        print("✓ Tải thành công EfficientDetLayoutModel")
        model = effdet_model
    except Exception as e:
        print(f"✗ Không thể tải EfficientDetLayoutModel: {str(e)}")
        model = None

if model is None:
    print("\nKhông thể tải bất kỳ mô hình nào. Vui lòng kiểm tra cài đặt.")
    sys.exit(1)

# Phát hiện layout từ trang đầu tiên
print("\n=== Phát hiện layout từ trang đầu tiên ===")
try:
    # Lưu ảnh đầu tiên
    temp_image_path = "temp_page.jpg"
    images[0].save(temp_image_path)

    # Đọc ảnh với OpenCV
    image = cv2.imread(temp_image_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Phát hiện layout
    layout = model.detect(image)
    print(f"Đã phát hiện {len(layout)} vùng layout")

    # In chi tiết về 5 vùng đầu tiên
    for i, block in enumerate(layout[:5]):
        print(f"Vùng {i}: {block.type}, Score: {block.score:.2f}, Bbox: {block.block}")

    print("\n✓ Phát hiện layout thành công!")

    # Xóa file tạm
    if os.path.exists(temp_image_path):
        os.remove(temp_image_path)

except Exception as e:
    print(f"Lỗi khi phát hiện layout: {str(e)}")
    import traceback

    traceback.print_exc()

print("\n=== Kết thúc kiểm tra ===")
print("Nếu tất cả các bước trên thành công, layout detection đã sẵn sàng hoạt động.")
print("Hãy đặt ENABLE_LAYOUT_DETECTION=true trong file .env và khởi động lại API.")
