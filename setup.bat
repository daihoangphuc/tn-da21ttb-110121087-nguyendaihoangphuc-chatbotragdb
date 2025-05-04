@echo off
echo === Tạo môi trường ảo Python ===
python -m venv venv

echo === Kích hoạt môi trường ảo ===
call venv\Scripts\activate

echo === Nâng cấp pip lên phiên bản mới nhất ===
python -m pip install --upgrade pip

echo === Cài đặt các thư viện cần thiết ===
pip install -r requirements.txt

echo.
echo === Cài đặt hoàn tất ===
echo Sử dụng 'call venv\Scripts\activate' để kích hoạt môi trường trước khi chạy
echo Sử dụng 'python main.py' để chạy ứng dụng
echo.

pause 

