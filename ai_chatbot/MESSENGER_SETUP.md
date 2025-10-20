# Hướng dẫn thiết lập Facebook Messenger Chatbot

## 1. Chuẩn bị trên Facebook Developers

### Bước 1: Tạo Facebook App
1. Truy cập [Facebook Developers](https://developers.facebook.com/)
2. Đăng nhập và nhấn "My Apps" → "Create App"
3. Chọn "Business" → nhập tên app → "Create App"

### Bước 2: Thêm Messenger Platform
1. Trong dashboard app, nhấn "Add Product"
2. Tìm "Messenger" và nhấn "Set Up"

### Bước 3: Tạo/Chọn Facebook Page
1. Trong Messenger Settings, tìm "Access Tokens"
2. Chọn Page hiện có hoặc tạo Page mới
3. Nhấn "Generate Token" → sao chép **PAGE_ACCESS_TOKEN**

### Bước 4: Lấy App Secret
1. Trong Settings → Basic
2. Sao chép **App Secret**

## 2. Cấu hình Environment Variables

Cập nhật file `.env` với các thông tin sau:

```env
# OpenAI API Key (đã có)
OPEN_API_KEY=your_openai_api_key_here

# Facebook Messenger Configuration
PAGE_ACCESS_TOKEN=EAAxxxxxxxxxxxxx  # Token từ bước 3
VERIFY_TOKEN=sentia_chatbot_verify   # Tự đặt (nhớ để dùng ở bước 5)
APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx # App Secret từ bước 4
```

## 3. Cài đặt Dependencies

```bash
pip install requests
```

## 4. Deploy ứng dụng

Bạn cần deploy ứng dụng lên server có SSL (HTTPS) vì Facebook yêu cầu HTTPS:

### Option 1: Sử dụng ngrok (để test)
```bash
# Cài đặt ngrok
pip install pyngrok

# Chạy ứng dụng
python main.py

# Trong terminal khác
ngrok http 5000
```

### Option 2: Deploy lên cloud (Heroku, Railway, etc.)

## 5. Thiết lập Webhook

1. Trong Facebook App → Messenger → Settings
2. Tìm "Webhooks" → nhấn "Add Callback URL"
3. Nhập:
   - **Callback URL**: `https://your-domain.com/webhook`
   - **Verify Token**: giá trị `VERIFY_TOKEN` từ file .env
4. Chọn subscriptions:
   - `messages`
   - `messaging_postbacks`
5. Nhấn "Verify and Save"

## 6. Thiết lập Get Started Button

Sau khi webhook hoạt động, gọi API để thiết lập nút "Bắt đầu":

```bash
curl -X POST http://localhost:5000/setup-messenger
```

Hoặc từ frontend:
```javascript
fetch('/setup-messenger', { method: 'POST' })
```

## 7. Test Chatbot

1. Truy cập Facebook Page
2. Nhấn "Message" để mở Messenger
3. Nhấn nút "Bắt đầu" hoặc gửi tin nhắn
4. Bot sẽ phản hồi dựa trên database hiện tại

## 8. Đưa Bot lên Live (Production)

1. Trong Facebook App → App Review
2. Thêm quyền `pages_messaging`
3. Submit for review với video demo
4. Sau khi được approve, bot sẽ hoạt động với tất cả user

## Cấu trúc File Đã Thêm

```
ai_chatbot/
├── main.py                 # Đã cập nhật với webhook routes
├── facebook_messenger.py   # Class xử lý Messenger logic
├── .env                   # Thêm Facebook config
└── MESSENGER_SETUP.md     # File hướng dẫn này
```

## Troubleshooting

### Lỗi thường gặp:

1. **Webhook verification failed**
   - Kiểm tra VERIFY_TOKEN có khớp với Facebook không
   - Đảm bảo URL có HTTPS

2. **Bot không phản hồi**
   - Kiểm tra PAGE_ACCESS_TOKEN
   - Xem logs server để debug
   - Đảm bảo webhook subscriptions đã được chọn

3. **Lỗi SSL/HTTPS**
   - Facebook yêu cầu HTTPS cho webhook
   - Sử dụng ngrok để test local

### Debug Commands:
```bash
# Kiểm tra webhook status
curl -X GET "https://your-domain.com/webhook?hub.verify_token=your_verify_token&hub.challenge=test&hub.mode=subscribe"

# Test send message manually
curl -X POST \
  https://graph.facebook.com/v18.0/me/messages \
  -H 'Content-Type: application/json' \
  -d '{
    "recipient": {"id": "USER_ID"},
    "message": {"text": "Test message"}
  }' \
  -G -d access_token=YOUR_PAGE_ACCESS_TOKEN
``` 