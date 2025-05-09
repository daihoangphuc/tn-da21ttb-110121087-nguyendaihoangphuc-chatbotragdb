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

        # Menu chức năng
        while True:
            print("\n===== KIỂM TRA ĐĂNG KÝ & ĐĂNG NHẬP =====")
            print("1. Đăng ký tài khoản mới")
            print("2. Đăng nhập")
            print("3. Đăng xuất")
            print("4. Lấy thông tin người dùng hiện tại")
            print("5. Thoát")

            choice = input("\nNhập lựa chọn của bạn (1-5): ")

            if choice == "1":
                # Đăng ký tài khoản mới
                email = input("Nhập email: ")
                password = getpass.getpass("Nhập mật khẩu: ")

                try:
                    print(f"📝 Đang đăng ký tài khoản với email: {email}...")
                    result = client.auth.sign_up({"email": email, "password": password})
                    print("✅ Đăng ký thành công!")
                    print(
                        f"📧 Vui lòng kiểm tra email để xác nhận tài khoản (nếu được yêu cầu)"
                    )
                    print(f"🔑 User ID: {result.user.id}")
                except Exception as e:
                    print(f"❌ Lỗi khi đăng ký: {str(e)}")

            elif choice == "2":
                # Đăng nhập
                email = input("Nhập email: ")
                password = getpass.getpass("Nhập mật khẩu: ")

                try:
                    print(f"🔐 Đang đăng nhập với email: {email}...")
                    result = client.auth.sign_in_with_password(
                        {"email": email, "password": password}
                    )
                    print("✅ Đăng nhập thành công!")
                    print(f"🔑 User ID: {result.user.id}")
                    print(f"🧾 Access Token: {result.session.access_token[:20]}...")
                except Exception as e:
                    print(f"❌ Lỗi khi đăng nhập: {str(e)}")

            elif choice == "3":
                # Đăng xuất
                try:
                    print("🚪 Đang đăng xuất...")
                    client.auth.sign_out()
                    print("✅ Đăng xuất thành công!")
                except Exception as e:
                    print(f"❌ Lỗi khi đăng xuất: {str(e)}")

            elif choice == "4":
                # Lấy thông tin người dùng hiện tại
                try:
                    print("👤 Đang lấy thông tin người dùng hiện tại...")
                    user = client.auth.get_user()
                    if user and user.user:
                        print("✅ Đã đăng nhập!")
                        print(f"🔑 User ID: {user.user.id}")
                        print(f"📧 Email: {user.user.email}")
                        print(f"⏰ Tạo vào: {user.user.created_at}")
                    else:
                        print("❌ Không có người dùng nào đang đăng nhập")
                except Exception as e:
                    print(f"❌ Lỗi khi lấy thông tin người dùng: {str(e)}")

            elif choice == "5":
                # Thoát
                print("👋 Tạm biệt!")
                break

            else:
                print("❌ Lựa chọn không hợp lệ. Vui lòng thử lại.")

            # Tạm dừng để người dùng có thể đọc kết quả
            time.sleep(1)

        return True

    except Exception as e:
        print(f"❌ Lỗi khi kết nối đến Supabase: {str(e)}")
        return False


if __name__ == "__main__":
    test_auth()
