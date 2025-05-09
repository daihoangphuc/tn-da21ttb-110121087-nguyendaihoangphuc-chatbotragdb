"""
Script kiểm tra các API xác thực với Supabase
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv
import getpass

# Load biến môi trường từ .env
load_dotenv()

# URL cơ sở của API
API_BASE_URL = "http://localhost:8000/api"

# Lưu token giữa các yêu cầu
ACCESS_TOKEN = None


def test_signup():
    """Kiểm tra API đăng ký tài khoản"""
    email = input("Nhập email để đăng ký: ")
    password = getpass.getpass("Nhập mật khẩu: ")

    # Gửi yêu cầu đăng ký
    response = requests.post(
        f"{API_BASE_URL}/auth/signup", json={"email": email, "password": password}
    )

    # Hiển thị kết quả
    if response.status_code == 200:
        result = response.json()
        print("✅ Đăng ký thành công!")
        print(f"📧 Email: {result['user']['email']}")
        print(f"🔑 User ID: {result['user']['id']}")
        return result
    else:
        print(f"❌ Lỗi khi đăng ký [{response.status_code}]: {response.text}")
        return None


def test_login():
    """Kiểm tra API đăng nhập"""
    global ACCESS_TOKEN

    email = input("Nhập email để đăng nhập: ")
    password = getpass.getpass("Nhập mật khẩu: ")

    # Gửi yêu cầu đăng nhập
    response = requests.post(
        f"{API_BASE_URL}/auth/login", json={"email": email, "password": password}
    )

    # Hiển thị kết quả
    if response.status_code == 200:
        result = response.json()
        print("✅ Đăng nhập thành công!")
        print(f"📧 Email: {result['user']['email']}")
        print(f"🔑 User ID: {result['user']['id']}")
        print(f"🧾 Access Token: {result['access_token'][:20]}...")

        # Lưu token để sử dụng cho các yêu cầu tiếp theo
        ACCESS_TOKEN = result["access_token"]
        return result
    else:
        print(f"❌ Lỗi khi đăng nhập [{response.status_code}]: {response.text}")
        return None


def test_get_user():
    """Kiểm tra API lấy thông tin người dùng hiện tại"""
    global ACCESS_TOKEN

    if not ACCESS_TOKEN:
        print("❌ Chưa đăng nhập. Vui lòng đăng nhập trước.")
        return None

    # Gửi yêu cầu lấy thông tin người dùng
    response = requests.get(
        f"{API_BASE_URL}/auth/user", headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
    )

    # Hiển thị kết quả
    if response.status_code == 200:
        result = response.json()
        print("✅ Lấy thông tin người dùng thành công!")
        print(f"📧 Email: {result['email']}")
        print(f"🔑 User ID: {result['id']}")
        print(f"⏰ Tạo vào: {result['created_at']}")
        return result
    else:
        print(
            f"❌ Lỗi khi lấy thông tin người dùng [{response.status_code}]: {response.text}"
        )
        return None


def test_session_info():
    """Kiểm tra API thông tin phiên đăng nhập"""
    global ACCESS_TOKEN

    if not ACCESS_TOKEN:
        print("❌ Chưa đăng nhập. Vui lòng đăng nhập trước.")
        return None

    # Gửi yêu cầu kiểm tra phiên
    response = requests.get(
        f"{API_BASE_URL}/auth/session",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
    )

    # Hiển thị kết quả
    if response.status_code == 200:
        result = response.json()
        print("✅ Lấy thông tin phiên thành công!")
        print(f"🔐 Đã xác thực: {result['is_authenticated']}")
        print(f"📧 Email: {result['email']}")
        print(f"🔑 User ID: {result['user_id']}")
        return result
    else:
        print(
            f"❌ Lỗi khi lấy thông tin phiên [{response.status_code}]: {response.text}"
        )
        return None


def test_logout():
    """Kiểm tra API đăng xuất"""
    global ACCESS_TOKEN

    if not ACCESS_TOKEN:
        print("❌ Chưa đăng nhập. Vui lòng đăng nhập trước.")
        return False

    # Gửi yêu cầu đăng xuất
    response = requests.post(
        f"{API_BASE_URL}/auth/logout",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
    )

    # Hiển thị kết quả
    if response.status_code == 200:
        result = response.json()
        print("✅ Đăng xuất thành công!")
        print(f"📝 Thông báo: {result['message']}")

        # Xóa token
        ACCESS_TOKEN = None
        return True
    else:
        print(f"❌ Lỗi khi đăng xuất [{response.status_code}]: {response.text}")
        return False


def main():
    """Hàm chính để chạy kiểm tra API xác thực"""

    # Kiểm tra kết nối đến API
    try:
        response = requests.get(f"{API_BASE_URL}/")
        if response.status_code != 200:
            print(f"❌ Không thể kết nối đến API. Trạng thái: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Lỗi kết nối đến API: {str(e)}")
        print("⚠️ Đảm bảo rằng server API đang chạy tại http://localhost:8000")
        return

    print("🔌 Đã kết nối thành công đến API")

    # Menu chức năng
    while True:
        print("\n===== KIỂM TRA API XÁC THỰC =====")
        print("1. Đăng ký tài khoản mới")
        print("2. Đăng nhập")
        print("3. Lấy thông tin người dùng hiện tại")
        print("4. Kiểm tra thông tin phiên")
        print("5. Đăng xuất")
        print("6. Thoát")

        choice = input("\nNhập lựa chọn của bạn (1-6): ")

        if choice == "1":
            test_signup()
        elif choice == "2":
            test_login()
        elif choice == "3":
            test_get_user()
        elif choice == "4":
            test_session_info()
        elif choice == "5":
            test_logout()
        elif choice == "6":
            print("👋 Tạm biệt!")
            break
        else:
            print("❌ Lựa chọn không hợp lệ. Vui lòng thử lại.")


if __name__ == "__main__":
    main()
