from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time
import logging

# Import router từ routes.py
from src.api.routes import router

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Tạo FastAPI app
app = FastAPI(
    title="RAG API",
    description="API cho hệ thống RAG với chunking và clustering",
    version="2.0.0",
    docs_url="/docs",
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thêm router vào app
app.include_router(router)

# Ghi log khi khởi tạo
logger.info("RAG API đã được khởi tạo thành công")
logger.info(f"Thời gian khởi tạo: {time.strftime('%Y-%m-%d %H:%M:%S')}")
logger.info("Tất cả các routes đã được đăng ký")
