from fastapi.testclient import TestClient
from backend.api import app # Hoặc nơi bạn định nghĩa app FastAPI
import os

client = TestClient(app)

# Biến toàn cục để lưu token
access_token = None
test_user_email = "testuser_automated@example.com"
test_user_password = "Str0ngPassword!"
test_file_id = None
test_conversation_id = None

def test_signup():
    global access_token
    response = client.post(
        f"{os.getenv('API_PREFIX', '/api')}/auth/signup",
        json={"email": test_user_email, "password": test_user_password},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    access_token = data["access_token"]
    assert access_token is not None

def test_login():
    global access_token
    # Đảm bảo signup đã chạy hoặc user đã tồn tại
    if not access_token: # Có thể login trực tiếp nếu user đã tồn tại
        response_login = client.post(
            f"{os.getenv('API_PREFIX', '/api')}/auth/login",
            json={"email": test_user_email, "password": test_user_password},
        )
        assert response_login.status_code == 200
        data = response_login.json()
        assert "access_token" in data
        access_token = data["access_token"]
        assert access_token is not None

def test_get_user_unauthenticated():
    response = client.get(f"{os.getenv('API_PREFIX', '/api')}/auth/user")
    assert response.status_code == 401 # Hoặc 403 tùy cấu hình auto_error của HTTPBearer

def test_get_user_authenticated():
    global access_token
    if not access_token:
        test_login() # Đảm bảo đã login
    
    response = client.get(
        f"{os.getenv('API_PREFIX', '/api')}/auth/user",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user_email

def test_upload_file():
    global access_token, test_file_id
    if not access_token:
        test_login()

    # Tạo một file tạm để upload
    with open("temp_test_file.txt", "w") as f:
        f.write("This is content for testing upload.")
    
    with open("temp_test_file.txt", "rb") as f_upload:
        response = client.post(
            f"{os.getenv('API_PREFIX', '/api')}/upload",
            headers={"Authorization": f"Bearer {access_token}"},
            files={"file": ("temp_test_file.txt", f_upload, "text/plain")},
            data={"category": "test_category"}
        )
    os.remove("temp_test_file.txt") # Xóa file tạm

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "file_id" in data
    test_file_id = data["file_id"]
    assert test_file_id is not None

def test_ask_stream():
    global access_token, test_file_id, test_conversation_id
    if not access_token:
        test_login()
    if not test_file_id:
        test_upload_file() # Đảm bảo đã upload file
    if not test_conversation_id: # Tạo conversation nếu chưa có
        create_conv_response = client.post(
            f"{os.getenv('API_PREFIX', '/api')}/conversations/create",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert create_conv_response.status_code == 200
        test_conversation_id = create_conv_response.json()["conversation_id"]


    response = client.post(
        f"{os.getenv('API_PREFIX', '/api')}/ask/stream",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "question": "What is in the test file?",
            "file_id": [test_file_id],
            "conversation_id": test_conversation_id
        }
    )
    assert response.status_code == 200
    # Kiểm tra nội dung stream phức tạp hơn, có thể cần đọc từng event
    # Ví dụ đơn giản: kiểm tra content_type
    assert "text/event-stream" in response.headers["content-type"]
      # Đọc và kiểm tra stream (ví dụ cơ bản)
    full_response_content = ""
    for line in response.iter_lines():
        # Handle both bytes and string types
        if isinstance(line, bytes):
            full_response_content += line.decode('utf-8') + "\n"
        else:
            full_response_content += str(line) + "\n"
    
    print(f"Stream response: {full_response_content[:500]}...") # In ra một phần để debug
    assert "event: start" in full_response_content
    assert "event: content" in full_response_content # Hoặc sources tùy logic
    assert "event: end" in full_response_content


# Thêm các test case khác cho tất cả các endpoint...

# Ví dụ test cho GET /api/files
def test_get_files():
    global access_token
    if not access_token:
        test_login()
    
    response = client.get(
        f"{os.getenv('API_PREFIX', '/api')}/files",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_files" in data
    assert "files" in data

# Ví dụ test cho DELETE /api/files/{filename}
# Cần upload file trước để có file để xóa
def test_delete_file():
    global access_token, test_file_id
    if not access_token:
        test_login()
    
    # Upload một file tạm để xóa
    temp_filename_to_delete = "file_to_delete.txt"
    with open(temp_filename_to_delete, "w") as f:
        f.write("Content of file to delete.")
    
    with open(temp_filename_to_delete, "rb") as f_upload:
        upload_resp = client.post(
            f"{os.getenv('API_PREFIX', '/api')}/upload",
            headers={"Authorization": f"Bearer {access_token}"},
            files={"file": (temp_filename_to_delete, f_upload, "text/plain")}
        )
    os.remove(temp_filename_to_delete)
    assert upload_resp.status_code == 200
    # uploaded_file_id = upload_resp.json()["file_id"] # Không cần file_id để xóa theo filename

    delete_response = client.delete(
        f"{os.getenv('API_PREFIX', '/api')}/files/{temp_filename_to_delete}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert delete_response.status_code == 200
    data = delete_response.json()
    assert data["status"] == "success"
    assert data["filename"] == temp_filename_to_delete

# ... (tiếp tục với các hàm test khác)