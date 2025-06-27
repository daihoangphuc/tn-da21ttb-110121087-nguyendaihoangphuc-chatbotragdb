from sentence_transformers import SentenceTransformer
import logging
import asyncio

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
    """Lớp quản lý các mô hình embedding với hỗ trợ async"""

    def __init__(self, model_name=None):
        """Khởi tạo mô hình embedding"""
        self.model = SentenceTransformer(
            model_name
            or os.getenv("EMBEDDING_MODEL_NAME", "intfloat/multilingual-e5-base")
        )
        self.dimension = self.model.get_sentence_embedding_dimension()

    async def encode(self, texts, batch_size=32, show_progress=True):
        """Tạo vector embedding cho văn bản bất đồng bộ"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            lambda: self.model.encode(
                texts, batch_size=batch_size, show_progress_bar=show_progress
            )
        )

    async def encode_batch(self, texts, batch_size=32, show_progress=True):
        """Tạo vector embedding cho nhiều văn bản với batch processing bất đồng bộ"""
        return await self.encode(texts, batch_size=batch_size, show_progress=show_progress)

    def encode_sync(self, texts, batch_size=32, show_progress=True):
        """Tạo vector embedding cho văn bản đồng bộ (để tương thích ngược)"""
        return self.model.encode(
            texts, batch_size=batch_size, show_progress_bar=show_progress
        )

    def encode_batch_sync(self, texts, batch_size=32, show_progress=True):
        """Tạo vector embedding cho nhiều văn bản với batch processing đồng bộ"""
        return self.encode_sync(texts, batch_size=batch_size, show_progress=show_progress)

    def get_dimension(self):
        """Trả về kích thước vector của mô hình"""
        return self.dimension
