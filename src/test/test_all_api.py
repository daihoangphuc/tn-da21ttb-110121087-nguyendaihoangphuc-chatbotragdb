import io
import os
import pytest
from fastapi.testclient import TestClient
from src.api import app

# Initialize the TestClient with the FastAPI app
testing_client = TestClient(app)

@pytest.fixture(scope="session")
def auth_token():
    """
    Fixture to sign up (if needed) and log in a test user, returning a valid JWT.
    Ensure TEST_USER_EMAIL and TEST_USER_PASSWORD are set in env or defaults will be used.
    """
    email = os.getenv("TEST_USER_EMAIL", "testuser@example.com")
    password = os.getenv("TEST_USER_PASSWORD", "TestPass123")
    # Attempt signup (ignore error if user already exists)
    testing_client.post("/api/auth/signup", json={"email": email, "password": password})
    # Log in
    resp = testing_client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    data = resp.json()
    return data["access_token"]


def auth_headers(token: str) -> dict:
    """
    Helper to build Authorization header from a token.
    """
    return {"Authorization": f"Bearer {token}"}


def test_root_endpoint():
    """
    Test the root endpoint returns a welcome message.
    """
    resp = testing_client.get("/api/")
    assert resp.status_code == 200
    payload = resp.json()
    assert "message" in payload and payload["message"].startswith("Chào mừng")


def test_protected_requires_auth():
    """
    Ensure protected GET endpoints return 401 when no token is provided.
    """
    protected_urls = [
        "/api/auth/user",
        "/api/auth/session",
        "/api/conversations",
        "/api/files",
    ]
    for url in protected_urls:
        resp = testing_client.get(url)
        assert resp.status_code == 401, f"Expected 401 for {url}, got {resp.status_code}"


def test_upload_requires_auth():
    """
    Ensure upload endpoint requires authentication (should return 401 without token).
    """
    response = testing_client.post("/api/upload", files={})
    assert response.status_code == 401, f"Expected 401 for upload without auth, got {response.status_code}"


def test_auth_user_and_session(auth_token):
    """
    Test retrieving user info and session info with a valid token.
    """
    headers = auth_headers(auth_token)
    # /auth/user
    resp = testing_client.get("/api/auth/user", headers=headers)
    assert resp.status_code == 200
    user_data = resp.json()
    assert "id" in user_data and "email" in user_data
    # /auth/session
    resp = testing_client.get("/api/auth/session", headers=headers)
    assert resp.status_code == 200
    session_data = resp.json()
    assert session_data.get("is_authenticated") is True


def test_conversation_crud(auth_token):
    """
    Test creating, listing, and retrieving conversation details.
    """
    headers = auth_headers(auth_token)
    # Create conversation
    resp = testing_client.post("/api/conversations/create", headers=headers)
    assert resp.status_code == 200
    conv_id = resp.json().get("conversation_id")
    assert conv_id
    # List conversations
    resp = testing_client.get("/api/conversations", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data.get("data"), list)
    # Retrieve conversation detail
    resp = testing_client.get(f"/api/conversations/{conv_id}", headers=headers)
    assert resp.status_code == 200
    detail = resp.json()
    # The API may return conversation_id at top-level if no messages, or within 'data' otherwise
    if "data" in detail:
        assert detail["data"].get("conversation_id") == conv_id
    else:
        assert detail.get("conversation_id") == conv_id


def test_file_upload_list_delete(auth_token):
    """
    Test uploading a file, listing it, and deleting it.
    """
    headers = auth_headers(auth_token)
    # Upload a simple text file
    file_obj = io.BytesIO(b"Hello FastAPI Test")
    response = testing_client.post(
        "/api/upload",
        headers=headers,
        files={"file": ("hello.txt", file_obj, "text/plain")},
    )
    assert response.status_code == 200
    result = response.json()
    assert result.get("status") == "success"
    file_id = result.get("file_id")
    # List uploaded files
    response = testing_client.get("/api/files", headers=headers)
    assert response.status_code == 200
    files_list = response.json().get("files", [])
    assert any(f.get("id") == file_id for f in files_list)
    # Delete the uploaded file
    response = testing_client.delete("/api/files/hello.txt", headers=headers)
    # Depending on file type handling, deletion may succeed or return 404 if not found
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        delete_result = response.json()
        assert delete_result.get("status") == "success"


def test_reset_collection_and_delete_by_filter(auth_token):
    """
    Test resetting the vector collection and deleting points by filter.
    """
    headers = auth_headers(auth_token)
    # Reset collection
    resp = testing_client.delete("/api/collection/reset", headers=headers)
    assert resp.status_code == 200
    reset_data = resp.json()
    assert reset_data.get("status") in ("success", "warning")
    # Delete by filter (using a dummy filter)
    filter_payload = {"filter": {"must": [{"key": "user_id", "match": {"value": auth_token}}]}}
    resp = testing_client.post(
        "/api/collections/delete-by-filter",
        headers=headers,
        json=filter_payload,
    )
    # Can succeed or return error if no points match
    assert resp.status_code in (200, 400)


def test_ask_stream_error(auth_token):
    """
    Test that /ask/stream returns 400 if no file_id is provided.
    """
    headers = auth_headers(auth_token)
    resp = testing_client.post(
        "/api/ask/stream",
        headers=headers,
        json={"question": "What is FastAPI?"},
    )
    assert resp.status_code == 400


def test_suggestions_and_latest(auth_token):
    """
    Test retrieving question suggestions and latest conversation.
    """
    headers = auth_headers(auth_token)
    # Suggestions
    resp = testing_client.get("/api/suggestions", headers=headers)
    assert resp.status_code == 200
    assert "suggestions" in resp.json()
    # Latest conversation
    resp = testing_client.get("/api/latest-conversation", headers=headers)
    assert resp.status_code == 200
    assert "found" in resp.json()
