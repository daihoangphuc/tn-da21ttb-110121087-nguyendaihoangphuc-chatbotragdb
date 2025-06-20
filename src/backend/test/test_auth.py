"""
Script kiểm tra chức năng đăng ký và đăng nhập với Supabase
"""

import os
import sys
import time
from dotenv import load_dotenv
import getpass

# Xóa đường dẫn hiện tại khỏi sys.path để tránh xung đột với module cục bộ
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir in sys.path:
    sys.path.remove(current_dir)

# Import thư viện supabase
import supabase

# Load biến môi trường
load_dotenv()


def test_auth():
    """Kiểm tra chức năng đăng ký và đăng nhập với Supabase"""
    # Lấy thông tin xác thực
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL và SUPABASE_KEY chưa được cấu hình trong file .env")
        return False

    try:
        # Kết nối đến Supabase
        print(f"🔌 Đang kết nối đến Supabase URL: {supabase_url}...")
        client = supabase.create_client(supabase_url, supabase_key)

        # Use environment variables for testing instead of interactive menu
        test_email = os.getenv("TEST_EMAIL", "test@example.com")
        test_password = os.getenv("TEST_PASSWORD", "testpassword123")
        
        print(f"Testing with email: {test_email}")
        
        # Test signup
        try:
            print(f"📝 Đang đăng ký tài khoản với email: {test_email}...")
            result = client.auth.sign_up({"email": test_email, "password": test_password})
            print("✅ Đăng ký thành công!")
            print(f"🔑 User ID: {result.user.id}")
        except Exception as e:
            print(f"❌ Lỗi khi đăng ký: {str(e)}")

        # Test login
        try:
            print(f"🔐 Đang đăng nhập với email: {test_email}...")
            result = client.auth.sign_in_with_password(
                {"email": test_email, "password": test_password}
            )
            print("✅ Đăng nhập thành công!")
            print(f"🔑 User ID: {result.user.id}")
            print(f"🧾 Access Token: {result.session.access_token[:20]}...")
        except Exception as e:
            print(f"❌ Lỗi khi đăng nhập: {str(e)}")

        # Test logout
        try:
            print("🚪 Đang đăng xuất...")
            client.auth.sign_out()
            print("✅ Đăng xuất thành công!")
        except Exception as e:
            print(f"❌ Lỗi khi đăng xuất: {str(e)}")

        return True

    except Exception as e:
        print(f"❌ Lỗi khi kết nối đến Supabase: {str(e)}")
        return False


if __name__ == "__main__":
    test_auth()
