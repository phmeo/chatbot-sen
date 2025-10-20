#!/usr/bin/env python3
"""
Script khởi động server Flask với cấu hình phù hợp cho VPS
"""

import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    """
    Kiểm tra các yêu cầu cần thiết trước khi khởi động
    Đảm bảo Python version, các file chính và file .env đều tồn tại
    """
    print("🔍 Kiểm tra yêu cầu hệ thống...")
    
    # Kiểm tra Python version
    if sys.version_info < (3, 7):
        print("❌ Cần Python 3.7 trở lên")
        return False
    
    # Kiểm tra file main.py
    if not Path("main.py").exists():
        print("❌ Không tìm thấy file main.py")
        return False
    
    # Kiểm tra file messenger_facebook.py
    if not Path("messanger_facebook.py").exists():
        print("❌ Không tìm thấy file messanger_facebook.py")
        return False
    
    # Kiểm tra .env file
    if not Path(".env").exists():
        print("⚠️  Không tìm thấy file .env - tạo file mẫu")
        create_sample_env()
    
    print("✅ Các yêu cầu cơ bản đã được đáp ứng")
    return True

def create_sample_env():
    """
    Tạo file .env mẫu khi không tìm thấy
    File này chứa các biến môi trường cần thiết cho hệ thống
    """
    sample_env = """# OpenAI API Configuration
OPEN_API_KEY=your_openai_api_key_here

# Milvus Configuration  
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Facebook Messenger Configuration
PAGE_ACCESS_TOKEN=your_page_access_token_here
VERIFY_TOKEN=sentia_chatbot_verify_2025
APP_SECRET=your_app_secret_here
"""
    
    with open(".env", "w", encoding="utf-8") as f:
        f.write(sample_env)
    
    print("📝 Đã tạo file .env mẫu - vui lòng cập nhật các giá trị thực")

def check_port_availability(port=5000):
    """
    Kiểm tra port có khả dụng không
    Đảm bảo không có process nào khác đang sử dụng port
    """
    import socket
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('0.0.0.0', port))
            print(f"✅ Port {port} khả dụng")
            return True
    except OSError:
        print(f"❌ Port {port} đã được sử dụng")
        return False

def get_server_info():
    """
    Lấy thông tin server
    Hiển thị hostname, IP local, IP public để thuận tiện cho việc kết nối
    """
    import socket
    
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print(f"🖥️  Server Info:")
    print(f"   Hostname: {hostname}")
    print(f"   Local IP: {local_ip}")
    
    # Cố gắng lấy public IP
    try:
        import requests
        public_ip = requests.get('https://api.ipify.org', timeout=5).text
        print(f"   Public IP: {public_ip}")
        print(f"   🌐 Truy cập qua: http://{public_ip}:5000")
        print(f"   🌐 Facebook webhook: https://{public_ip}/webhook")
    except:
        print("   ⚠️  Không thể lấy Public IP")

def start_server():
    """
    Khởi động server Flask
    Chạy main.py để khởi động Flask, Telegram bot và Facebook Messenger
    """
    print("\n🚀 Khởi động server...")
    print("📍 Server sẽ chạy trên: http://0.0.0.0:5000")
    print("🔧 Chế độ debug: ON")
    print("🛑 Nhấn Ctrl+C để dừng server")
    print("-" * 50)
    
    try:
        # Chạy main.py
        subprocess.run([sys.executable, "main.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Server đã dừng")
    except subprocess.CalledProcessError as e:
        print(f"❌ Lỗi khi khởi động server: {e}")

def main():
    """
    Hàm chính điều phối quy trình khởi động
    Thực hiện kiểm tra, hiển thị thông tin và khởi động server
    """
    print("🤖 Sentia AI RAG Chatbot Server Launcher") 
    print("🎓 Hệ thống AI tư vấn tuyển sinh với Milvus Vector Database")
    print("=" * 60)
    
    # Kiểm tra yêu cầu
    if not check_requirements():
        return
    
    # Kiểm tra port
    if not check_port_availability():
        print("💡 Có thể cần dừng process đang sử dụng port 5000:")
        print("   sudo lsof -ti:5000 | xargs kill -9")
        return
    
    # Hiển thị thông tin server
    get_server_info()
    
    # Thông báo database
    print("\n📊 Database Info:")
    print("   Collection: sentia_website")
    print("   Embedding Model: text-embedding-3-large (3072 dimensions)")
    print("   Telegram Bot: @sentia2015_bot")
    
    # Thông tin về Facebook Messenger
    print("\n📱 Facebook Messenger Info:")
    print("   Webhook URL: /webhook")
    print("   Verify Token: sentia_chatbot_verify_2025 (mặc định)")
    print("   Cấu hình: Xem trong file .env")
    
    # Hỏi xác nhận
    print("\n❓ Bạn có muốn khởi động server không? (y/n): ", end="")
    if input().lower().startswith('y'):
        start_server()
    else:
        print("👋 Tạm biệt!")

if __name__ == "__main__":
    main() 