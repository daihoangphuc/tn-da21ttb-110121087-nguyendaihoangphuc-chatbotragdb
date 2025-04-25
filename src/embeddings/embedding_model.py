import os
from langchain_huggingface import HuggingFaceEmbeddings
from huggingface_hub import login, snapshot_download
import time

from src.config import HF_TOKEN, EMBEDDING_MODEL, EMBEDDING_DEVICE

# Biến toàn cục để lưu trữ instance của embeddings đã tải
_GLOBAL_EMBEDDINGS = None


def initialize_embeddings():
    """Khởi tạo embedding model

    Nếu model đã được tải trước đó, sẽ sử dụng lại để tiết kiệm thời gian.
    Nếu chưa, sẽ tải model từ Hugging Face và cache lại.

    Returns:
        HuggingFaceEmbeddings: Instance của model embedding đã được khởi tạo
    """
    global _GLOBAL_EMBEDDINGS

    # Nếu đã tải trước đó, trả về instance đã cache
    if _GLOBAL_EMBEDDINGS is not None:
        print(f"ℹ️ Sử dụng model embedding đã tải trước đó: {EMBEDDING_MODEL}")
        return _GLOBAL_EMBEDDINGS

    # Đăng nhập Hugging Face
    print(f"🔑 Đăng nhập Hugging Face Hub...")
    login(token=HF_TOKEN)

    # Kiểm tra xem model đã được tải về máy chưa
    cache_folder = os.path.expanduser("~/.cache/huggingface/hub")
    model_folder = os.path.join(
        cache_folder, "models--" + EMBEDDING_MODEL.replace("/", "--")
    )

    # Nếu chưa tải, download trước để đảm bảo có model sẵn sàng
    if not os.path.exists(model_folder):
        print(f"📥 Tải model từ Hugging Face Hub: {EMBEDDING_MODEL}")
        start_time = time.time()
        snapshot_download(repo_id=EMBEDDING_MODEL)
        print(f"✅ Đã tải model trong {time.time() - start_time:.2f}s")
    else:
        print(f"✅ Model đã tồn tại trong cache: {model_folder}")

    # Khởi tạo embedding model
    print(f"⚙️ Khởi tạo embedding model với device: {EMBEDDING_DEVICE}")
    start_time = time.time()

    # Khởi tạo với retry mechanism trong trường hợp lỗi mạng
    max_retries = 3
    retry_count = 0
    while retry_count < max_retries:
        try:
            embeddings = HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL, model_kwargs={"device": EMBEDDING_DEVICE}
            )

            # Thử embedding một câu test để đảm bảo model hoạt động tốt
            _ = embeddings.embed_query("Kiểm tra model embedding")

            # Cache lại instance để sử dụng lần sau
            _GLOBAL_EMBEDDINGS = embeddings

            print(f"✅ Khởi tạo model thành công trong {time.time() - start_time:.2f}s")
            return embeddings
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                print(
                    f"⚠️ Lỗi khi khởi tạo model, thử lại lần {retry_count}/{max_retries}: {str(e)}"
                )
                time.sleep(2)  # Đợi 2 giây trước khi thử lại
            else:
                print(
                    f"❌ Không thể khởi tạo model sau {max_retries} lần thử: {str(e)}"
                )
                raise e
