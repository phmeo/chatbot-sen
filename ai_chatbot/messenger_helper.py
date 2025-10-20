#!/usr/bin/env python3
"""
Script helper để test và setup Facebook Messenger
Chạy: python messenger_helper.py
"""

import os
import subprocess
import requests
from dotenv import load_dotenv

load_dotenv()

def check_environment():
    """Kiểm tra environment variables"""
    required_vars = ['PAGE_ACCESS_TOKEN', 'VERIFY_TOKEN', 'APP_SECRET']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Thiếu environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Vui lòng cập nhật file .env")
        return False
    
    print("✅ Environment variables OK")
    return True

def start_ngrok():
    """Khởi động ngrok để tạo HTTPS tunnel"""
    try:
        from pyngrok import ngrok
        
        # Mở tunnel cho port 5000
        tunnel = ngrok.connect(5000)
        public_url = tunnel.public_url
        
        print(f"🌐 Ngrok tunnel: {public_url}")
        print(f"📝 Webhook URL cho Facebook: {public_url}/webhook")
        
        return public_url
    except ImportError:
        print("❌ Chưa cài đặt pyngrok. Chạy: pip install pyngrok")
        return None
    except Exception as e:
        print(f"❌ Lỗi khi khởi động ngrok: {e}")
        return None

def test_webhook(base_url):
    """Test webhook verification"""
    verify_token = os.getenv('VERIFY_TOKEN')
    test_url = f"{base_url}/webhook?hub.mode=subscribe&hub.challenge=test123&hub.verify_token={verify_token}"
    
    try:
        response = requests.get(test_url)
        if response.status_code == 200 and response.text == "test123":
            print("✅ Webhook verification test OK")
            return True
        else:
            print(f"❌ Webhook verification failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Lỗi khi test webhook: {e}")
        return False

def setup_messenger_profile():
    """Thiết lập profile cho Messenger"""
    try:
        response = requests.post('http://localhost:5000/setup-messenger')
        if response.status_code == 200:
            print("✅ Messenger profile setup thành công")
            return True
        else:
            print(f"❌ Lỗi setup messenger profile: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Lỗi khi setup messenger profile: {e}")
        return False

def test_send_message():
    """Test gửi tin nhắn trực tiếp"""
    page_token = os.getenv('PAGE_ACCESS_TOKEN')
    if not page_token:
        print("❌ Không có PAGE_ACCESS_TOKEN")
        return False
    
    # Note: Cần USER_ID thực để test
    print("💡 Để test gửi tin nhắn, bạn cần:")
    print("   1. Nhắn tin cho Page từ tài khoản Facebook")
    print("   2. Lấy User ID từ webhook logs")
    print("   3. Chạy lại script này với USER_ID")

def main():
    """Menu chính"""
    print("🤖 Facebook Messenger Setup Helper")
    print("=" * 40)
    
    # Kiểm tra environment
    if not check_environment():
        return
    
    while True:
        print("\nChọn một tùy chọn:")
        print("1. Khởi động ngrok tunnel")
        print("2. Test webhook verification")
        print("3. Setup Messenger profile")
        print("4. Kiểm tra tất cả")
        print("5. Hướng dẫn chi tiết")
        print("0. Thoát")
        
        choice = input("\nNhập lựa chọn (0-5): ").strip()
        
        if choice == "0":
            print("👋 Tạm biệt!")
            break
        
        elif choice == "1":
            url = start_ngrok()
            if url:
                print(f"\n📋 Copy URL này vào Facebook Webhook:")
                print(f"   {url}/webhook")
        
        elif choice == "2":
            base_url = input("Nhập base URL (ví dụ: https://abc123.ngrok.io): ").strip()
            if base_url:
                test_webhook(base_url)
        
        elif choice == "3":
            setup_messenger_profile()
        
        elif choice == "4":
            print("\n🔍 Kiểm tra tất cả...")
            url = start_ngrok()
            if url:
                test_webhook(url)
                setup_messenger_profile()
                print(f"\n✅ Hoàn tất! Webhook URL: {url}/webhook")
        
        elif choice == "5":
            print("\n📚 Các bước thiết lập:")
            print("1. Tạo Facebook App tại https://developers.facebook.com/")
            print("2. Thêm Messenger product")
            print("3. Tạo Page Access Token")
            print("4. Cập nhật file .env với các token")
            print("5. Chạy option 4 để setup tự động")
            print("6. Copy webhook URL vào Facebook App settings")
            print("7. Test bằng cách nhắn tin cho Page")
        
        else:
            print("❌ Lựa chọn không hợp lệ!")

if __name__ == "__main__":
    main() 