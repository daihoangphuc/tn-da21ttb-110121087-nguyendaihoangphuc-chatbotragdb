@echo off
echo === Kích hoạt môi trường ảo ===
call venv\Scripts\activate

echo === Chạy ứng dụng RAG ===
python main.py

pause 