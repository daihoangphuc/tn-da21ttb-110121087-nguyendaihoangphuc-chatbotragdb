from sentence_transformers import SentenceTransformer
import logging

# Cấu hình logging
logging.basicConfig(
    format='[Embedding] %(message)s',
    level=logging.INFO
)
# Ghi đè hàm print để thêm prefix
original_print = print
def print(*args, **kwargs):
    prefix = "[Embedding] "
    original_print(prefix + " ".join(map(str, args)), **kwargs)
logger = logging.getLogger(__name__)
import os
from dotenv import load_dotenv

# Load biến môi trường từ .env
load_dotenv()


class EmbeddingModel:
    """Lớp quản lý các mô hình embedding"""

    def __init__(self, model_name=None):
        """Khởi tạo mô hình embedding"""
        self.model = SentenceTransformer(
            model_name
            or os.getenv("EMBEDDING_MODEL_NAME", "intfloat/multilingual-e5-base")
        )
        self.dimension = self.model.get_sentence_embedding_dimension()

    def encode(self, texts, batch_size=32, show_progress=True):
        """Tạo vector embedding cho văn bản"""
        return self.model.encode(
            texts, batch_size=batch_size, show_progress_bar=show_progress
        )

    def get_dimension(self):
        """Trả về kích thước vector của mô hình"""
        return self.dimension
