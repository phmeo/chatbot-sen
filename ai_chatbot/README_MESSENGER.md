# Hướng dẫn kết nối Facebook Messenger với Chatbot

## Cài đặt

1. Cài đặt ngrok:
```bash
npm install -g ngrok
```

2. Cài đặt các thư viện Python cần thiết:
```bash
pip install flask requests python-dotenv
```

## Cấu hình

1. Khởi động server Flask chính (main.py):
```bash
python main.py
```

2. Khởi động server Facebook Messenger (facebook_messenger.py):
```bash
python facebook_messenger.py
```

3. Khởi động ngrok để tạo tunnel:
```bash
ngrok http 5001
```

4. Cấu hình Facebook Webhook:
   - Truy cập Meta Developer Console
   - Vào phần Webhooks
   - Thêm URL mới: `https://[your-ngrok-url]/webhook`
   - Verify Token: `f948b6f6e1a08a02c2789a1447f17493`
   - Chọn các events cần thiết (messages, messaging_postbacks)

## Cấu trúc hệ thống

- `main.py`: Server chính xử lý chat (port 5000)
- `facebook_messenger.py`: Server xử lý Facebook Messenger (port 5001)
- Ngrok tạo tunnel cho port 5001 để Facebook có thể gửi webhook

## Lưu ý

- Đảm bảo cả hai server (main.py và facebook_messenger.py) đều đang chạy
- URL ngrok sẽ thay đổi mỗi lần khởi động lại, cần cập nhật lại trong Facebook Developer Console
- Kiểm tra logs của cả hai server để debug nếu cần 