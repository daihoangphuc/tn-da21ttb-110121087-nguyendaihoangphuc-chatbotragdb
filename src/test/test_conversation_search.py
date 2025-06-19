"""
Test file cho API tìm kiếm hội thoại
"""

import requests
import json
from datetime import datetime, timedelta

# Cấu hình
BASE_URL = "http://localhost:8000/api"

def get_auth_token():
    """Đăng nhập và lấy token xác thực"""
    login_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Lỗi đăng nhập: {response.status_code} - {response.text}")
        return None

def test_search_conversations():
    """Test API tìm kiếm hội thoại"""
    token = get_auth_token()
    if not token:
        print("Không thể lấy token xác thực")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("=== TEST API TÌM KIẾM HỘI THOẠI ===\n")
    
    # Test 1: Tìm kiếm theo từ khóa
    print("1. Test tìm kiếm theo từ khóa 'SQL':")
    params = {
        "query": "SQL",
        "page": 1,
        "page_size": 5
    }
    
    response = requests.get(f"{BASE_URL}/conversations/search", params=params, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Tìm thấy: {data['total_count']} hội thoại")
        print(f"Trang: {data['page']}/{data['total_pages']}")
        print(f"Query: {data['search_query']}")
        for conv in data['conversations'][:3]:  # Hiển thị 3 kết quả đầu
            print(f"  - ID: {conv['conversation_id']}")
            print(f"    Tin nhắn đầu: {conv['first_message'][:50]}...")
            print(f"    Số tin nhắn: {conv['message_count']}")
            if conv.get('matching_content'):
                print(f"    Nội dung khớp: {conv['matching_content'][:80]}...")
        print()
    else:
        print(f"Lỗi: {response.text}\n")
    
    # Test 2: Tìm kiếm theo khoảng thời gian
    print("2. Test tìm kiếm theo thời gian (7 ngày gần đây):")
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    
    params = {
        "date_from": week_ago.strftime("%Y-%m-%d"),
        "date_to": today.strftime("%Y-%m-%d"),
        "page": 1,
        "page_size": 5
    }
    
    response = requests.get(f"{BASE_URL}/conversations/search", params=params, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Tìm thấy: {data['total_count']} hội thoại trong 7 ngày gần đây")
        print(f"Metadata: {data['search_metadata']}")
        print()
    else:
        print(f"Lỗi: {response.text}\n")
    
    # Test 3: Tìm kiếm kết hợp từ khóa và thời gian
    print("3. Test tìm kiếm kết hợp (từ khóa + thời gian):")
    params = {
        "query": "database",
        "date_from": week_ago.strftime("%Y-%m-%d"),
        "date_to": today.strftime("%Y-%m-%d"),
        "page": 1,
        "page_size": 10
    }
    
    response = requests.get(f"{BASE_URL}/conversations/search", params=params, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Tìm thấy: {data['total_count']} hội thoại")
        print(f"Điều kiện: từ khóa '{data['search_query']}' trong 7 ngày gần đây")
        print()
    else:
        print(f"Lỗi: {response.text}\n")
    
    # Test 4: Tìm kiếm không có kết quả
    print("4. Test tìm kiếm không có kết quả:")
    params = {
        "query": "nonexistentkeyword12345",
        "page": 1,
        "page_size": 10
    }
    
    response = requests.get(f"{BASE_URL}/conversations/search", params=params, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Tìm thấy: {data['total_count']} hội thoại")
        print("Kết quả trống như mong đợi")
        print()
    else:
        print(f"Lỗi: {response.text}\n")
    
    # Test 5: Test phân trang
    print("5. Test phân trang:")
    params = {
        "query": "",  # Tìm kiếm rỗng để lấy tất cả
        "date_from": (today - timedelta(days=30)).strftime("%Y-%m-%d"),
        "page": 1,
        "page_size": 2  # Giới hạn 2 kết quả mỗi trang
    }
    
    response = requests.get(f"{BASE_URL}/conversations/search", params=params, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Tổng: {data['total_count']} hội thoại")
        print(f"Trang 1/{data['total_pages']} (mỗi trang {data['page_size']} kết quả)")
        print(f"Kết quả trang 1: {len(data['conversations'])} hội thoại")
        print()
    else:
        print(f"Lỗi: {response.text}\n")
    
    # Test 6: Test lỗi validation
    print("6. Test validation (date format sai):")
    params = {
        "query": "test",
        "date_from": "invalid-date",
        "page": 1,
        "page_size": 10
    }
    
    response = requests.get(f"{BASE_URL}/conversations/search", params=params, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 400:
        print("Validation lỗi như mong đợi")
        print(f"Chi tiết lỗi: {response.json().get('detail', 'N/A')}")
    else:
        print(f"Kết quả bất ngờ: {response.text}")
    print()

if __name__ == "__main__":
    test_search_conversations() 