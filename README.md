# Sentia School AI RAG Chatbot

## Tổng quan

Hệ thống chatbot tư vấn tuyển sinh cho Sentia School sử dụng công nghệ AI kết hợp với Retrieval-Augmented Generation (RAG). Hệ thống hỗ trợ nhiều nền tảng:
- Web interface
- Telegram Bot
- Facebook Messenger Bot

## Thành phần hệ thống

1. **RAG Engine**
   - Sử dụng Milvus làm vector database
   - OpenAI để tạo embeddings và sinh responses
   - Hỗ trợ tìm kiếm thông tin từ website và tài liệu của trường

2. **Các nền tảng**
   - Website chat interface
   - Telegram Bot (@sentia2015_bot)
   - Facebook Messenger Bot (mới)

## Cài đặt

### Yêu cầu hệ thống
- Python 3.7+
- Docker và Docker Compose (để chạy Milvus)
- Các API keys:
  - OpenAI API Key
  - Telegram Bot Token
  - Facebook Messenger Token (nếu sử dụng)

### Bước 1: Cài đặt môi trường
```bash
# Clone repository
git clone <repository_url>
cd ai_chatbot

# Tạo môi trường ảo
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Cài đặt các packages
pip install -r requirements.txt
```

### Bước 2: Khởi tạo Milvus Database
```bash
# Chạy Milvus sử dụng Docker
docker-compose up -d
```

### Bước 3: Cấu hình
Tạo file `.env` với nội dung:
```
# OpenAI API Configuration
OPEN_API_KEY=your_openai_api_key_here

# Milvus Configuration  
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Facebook Messenger Configuration
PAGE_ACCESS_TOKEN=your_page_access_token_here
VERIFY_TOKEN=sentia_chatbot_verify_2025
APP_SECRET=your_app_secret_here
```

## Chạy hệ thống

### Khởi động hệ thống
```bash
python start_server.py
```

### Kiểm tra hệ thống
Để kiểm tra các thành phần của hệ thống:
```bash
python test_system.py
```

## Cấu hình Telegram Bot
1. Tạo bot qua BotFather
2. Thêm token vào biến `TELEGRAM_TOKEN` trong `main.py`

## Cấu hình Facebook Messenger Bot
1. Tạo một Facebook App tại [Facebook Developers](https://developers.facebook.com/)
2. Cấu hình Messenger product
3. Tạo Page Access Token và thêm vào file `.env`
4. Setup webhook với verify token (mặc định: `sentia_chatbot_verify_2025`)
5. Đăng ký webhook URL của bạn: `https://your-domain.com/webhook`

## Cấu trúc thư mục
- `main.py` - Core application và Flask server
- `telegram_bot.py` - Telegram bot implementation
- `messanger_facebook.py` - Facebook Messenger bot implementation
- `start_server.py` - Server launcher với các kiểm tra cơ bản
- `test_system.py` - Kiểm tra và chẩn đoán hệ thống
- `frontend/` - Web interface
- `database/` - Data và các file liên quan đến database

## Xử lý lỗi
- **Lỗi kết nối Milvus**: Kiểm tra Docker service và port 19530
- **Lỗi OpenAI API**: Kiểm tra API key và network connection
- **Lỗi webhook Messenger**: Kiểm tra cấu hình và verify token

## Ghi chú phát triển
Hệ thống sử dụng mô hình:
- Embedding: text-embedding-3-large (3072 chiều)
- Completion: gpt-4o-mini 