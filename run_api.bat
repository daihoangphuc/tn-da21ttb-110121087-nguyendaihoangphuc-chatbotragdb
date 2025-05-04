@echo off
echo === Khởi động API Hệ thống RAG cho Cơ sở dữ liệu ===

REM Kích hoạt môi trường ảo
call venv\Scripts\activate

REM Chạy API bằng uvicorn
python -m uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload

REM Dừng và chờ
pause 