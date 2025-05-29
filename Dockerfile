FROM python:3.10-slim

WORKDIR /app

# Cài đặt LibreOffice (để chuyển đổi các định dạng tài liệu về PDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt các dependencies Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose port
EXPOSE 8000

# Khởi động ứng dụng
CMD ["python", "-m", "uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"] 