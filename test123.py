import requests
import time

url_base = "https://4588-34-125-213-42.ngrok-free.app"

response = requests.post(f"{url_base}/generate", json={
    "topic": "Truyện ma đêm khuya kinh dị Nam Bộ"
})

resp_data = response.json()
print("Generation response:", resp_data)

# Kiểm tra lỗi trước khi lấy video_id
if "video_id" not in resp_data:
    print("Error generating video:", resp_data.get("detail", "Unknown error"))
else:
    video_id = resp_data["video_id"]
    
    # Chờ xử lý
    print("Waiting for processing...")
    time.sleep(120)  # Đợi ít nhất 2 phút
    
    # Thử download
    try:
        download_url = f"{url_base}/download/{video_id}"
        # Bằng code mới:
        print(f"Download video tại: {download_url}")
        # Hoặc mở trình duyệt tự động
        import webbrowser
        webbrowser.open(download_url)
    except Exception as e:
        print("Download error:", str(e))