"""
Module tích hợp Facebook Messenger với chatbot AI
Cung cấp các chức năng:
- Xác thực webhook (verify_webhook)
- Xử lý tin nhắn từ người dùng (handle_message)
- Gửi tin nhắn trả lời (send_message)
"""
import os
import json
import hmac
import hashlib
import requests
from typing import Dict, List, Callable, Optional, Any, Union, Tuple
from flask import Flask, request, jsonify, Response
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
PAGE_ACCESS_TOKEN = os.getenv('PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN', 'sentia_chatbot_verify_2025')
APP_SECRET = os.getenv('APP_SECRET')

class MessengerBot:
    """
    Lớp xử lý tích hợp Facebook Messenger
    Quản lý xác thực, nhận và gửi tin nhắn
    """
    def __init__(self, search_function: Callable, generate_response_function: Callable):
        """Initialize the Messenger bot with search and response generation functions"""
        self.search_similar_chunks = search_function
        self.generate_response = generate_response_function
        self.conversation_histories = {}  # Store history by user ID
        
    def verify_webhook(self, mode: Optional[str], token: Optional[str]) -> bool:
        """
        Xác thực webhook với token mà Facebook gửi
        Facebook sẽ gọi webhook với mode và token để xác minh
        """
        if mode and token:
            if mode == 'subscribe' and token == VERIFY_TOKEN:
                print("✅ Webhook verified!")
                return True
        return False
    
    def verify_signature(self, signature: Optional[str], body: bytes) -> bool:
        """
        Xác minh chữ ký của request từ Facebook
        Sử dụng APP_SECRET để xác thực rằng request thực sự từ Facebook
        """
        if not APP_SECRET or not signature:
            return False
            
        # The signature header format is "sha1=SIGNATURE"
        elements = signature.split('=')
        if len(elements) != 2:
            return False
            
        sig_hash = elements[1]
        
        # Calculate expected hash
        expected_hash = hmac.new(
            bytes(APP_SECRET, 'utf-8'),
            body,
            hashlib.sha1
        ).hexdigest()
        
        return hmac.compare_digest(sig_hash, expected_hash)
    
    def send_message(self, recipient_id: str, message_text: str) -> None:
        """
        Gửi tin nhắn đến người dùng qua Facebook Messenger API
        Tự động chia nhỏ tin nhắn dài để tuân thủ giới hạn của Facebook
        """
        if not PAGE_ACCESS_TOKEN:
            print("❌ Missing PAGE_ACCESS_TOKEN")
            return
        
        # Create payload
        payload = {
            'recipient': {'id': recipient_id},
            'message': {'text': message_text},
            'messaging_type': 'RESPONSE'
        }
        
        # Split long messages if needed (Facebook limit is 2000 characters)
        max_length = 1900  # Keeping some margin
        if len(message_text) > max_length:
            chunks = [message_text[i:i+max_length] for i in range(0, len(message_text), max_length)]
            for chunk in chunks:
                self._send_single_message(recipient_id, chunk)
        else:
            self._send_single_message(recipient_id, message_text)
    
    def _send_single_message(self, recipient_id: str, message_text: str) -> None:
        """
        Gửi một tin nhắn đơn đến người dùng
        Thực hiện HTTP request đến Facebook Graph API
        """
        url = f"https://graph.facebook.com/v18.0/me/messages"
        params = {'access_token': PAGE_ACCESS_TOKEN}
        
        payload = {
            'recipient': {'id': recipient_id},
            'message': {'text': message_text},
            'messaging_type': 'RESPONSE'
        }
        
        try:
            response = requests.post(
                url,
                params=params,
                json=payload
            )
            
            if response.status_code != 200:
                print(f"❌ Error sending message: {response.text}")
            else:
                print(f"✅ Message sent to {recipient_id}")
                
        except Exception as e:
            print(f"❌ Failed to send message: {e}")
    
    def handle_message(self, sender_id: str, message_text: str) -> None:
        """
        Xử lý tin nhắn đến và tạo phản hồi
        Tìm kiếm thông tin liên quan và tạo câu trả lời dựa trên context
        """
        print(f"💬 Received message from {sender_id}: {message_text}")
        
        # Handle special commands
        if message_text.lower() == '/start' or message_text.lower() == 'get_started':
            welcome_text = (
                "🎓 Xin chào!\n\n"
                "Tôi là AI Assistant tư vấn tuyển sinh của Sentia School - "
                "được tích hợp công nghệ AI hiện đại với dữ liệu từ website chính thức.\n\n"
                "🔥 Tôi có thể hỗ trợ bạn:\n\n"
                "📚 Chương trình đào tạo - Thông tin chi tiết về các khóa học\n"
                "💰 Học bổng và Chi phí - Các gói hỗ trợ tài chính\n"
                "📅 Tuyển sinh 2025 - Lịch thi, thủ tục đăng ký\n"
                "📍 Thông tin trường - Cơ sở vật chất, địa chỉ\n"
                "🎯 Định hướng nghề nghiệp - Tư vấn chọn ngành phù hợp\n\n"
                "💡 Hãy đặt câu hỏi cụ thể để nhận thông tin chính xác nhất!\n\n"
                "Ví dụ: \"Học phí ngành CNTT bao nhiêu?\" hoặc \"Điều kiện xét học bổng?\""
            )
            
            self.send_message(sender_id, welcome_text)
            return
        
        # Process normal message
        try:
            # Search for relevant chunks
            similar_chunks = self.search_similar_chunks(message_text)
            
            if not similar_chunks:
                response_text = "❌ Xin lỗi, tôi không tìm thấy thông tin liên quan trong cơ sở dữ liệu về câu hỏi của bạn.\n\nVui lòng thử đặt câu hỏi khác hoặc liên hệ trực tiếp với trường."
            else:
                # Generate response
                response_text = self.generate_response(message_text, similar_chunks)
                
                # Add source information
                sources = []
                for chunk in similar_chunks:
                    source_title = chunk['source']
                    url = chunk.get('url', '')
                    if url and url not in [s.get('url', '') for s in sources]:
                        sources.append({
                            'title': source_title,
                            'url': url
                        })
                
                if sources:
                    source_text = "\n\n📚 Nguồn tham khảo:\n"
                    for i, source in enumerate(sources[:3]):  # Show only top 3 sources
                        source_text += f"• {source['title']}"
                        if source.get('url'):
                            source_text += f" ({source['url']})"
                        source_text += "\n"
                    
                    response_text += source_text
            
            # Send the response
            self.send_message(sender_id, response_text)
            
        except Exception as e:
            print(f"❌ Error processing message: {e}")
            error_text = "❌ Xin lỗi, có lỗi xảy ra khi xử lý câu hỏi của bạn. Vui lòng thử lại sau."
            self.send_message(sender_id, error_text)

def create_webhook_endpoints(app: Flask, messenger_bot: MessengerBot):
    """
    Tạo các endpoint webhook cho tích hợp Facebook Messenger
    Đăng ký route /webhook cho cả GET (xác thực) và POST (nhận tin nhắn)
    """
    
    @app.route('/webhook', methods=['GET'])
    def webhook_verification() -> Union[Response, Tuple[str, int]]:
        """
        Xử lý xác thực webhook ban đầu từ Facebook
        Facebook gọi endpoint này để xác minh webhook khi cấu hình
        """
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.challenge')
        verify_token = request.args.get('hub.verify_token')
        
        if messenger_bot.verify_webhook(mode, verify_token):
            # Nếu token là None, trả về chuỗi rỗng thay vì None
            return str(token) if token is not None else "", 200
        else:
            return 'Verification failed', 403
    
    @app.route('/webhook', methods=['POST'])
    def webhook_handler() -> Tuple[str, int]:
        """
        Xử lý tin nhắn đến từ Facebook
        Facebook gọi webhook này mỗi khi có tin nhắn mới
        """
        # Verify signature
        signature = request.headers.get('X-Hub-Signature')
        if APP_SECRET and not messenger_bot.verify_signature(signature, request.data):
            return 'Invalid signature', 403
        
        data = request.json
        
        # Facebook sends a confirmation ping
        if data and data.get('object') == 'page':
            for entry in data.get('entry', []):
                for messaging_event in entry.get('messaging', []):
                    if messaging_event and messaging_event.get('message'):
                        sender_id = messaging_event.get('sender', {}).get('id')
                        message_text = messaging_event.get('message', {}).get('text')
                        
                        if sender_id and message_text:
                            # Process in a separate thread to avoid timeout
                            import threading
                            thread = threading.Thread(
                                target=messenger_bot.handle_message,
                                args=(sender_id, message_text)
                            )
                            thread.start()
                            
            return 'EVENT_RECEIVED', 200
        
        return 'Not a page object', 404

def setup_facebook_messenger(app: Flask, search_function: Callable, generate_response_function: Callable) -> MessengerBot:
    """
    Thiết lập webhook và handlers cho Facebook Messenger
    Điểm khởi tạo chính cho tích hợp Facebook với ứng dụng Flask
    """
    # Initialize the bot
    messenger_bot = MessengerBot(search_function, generate_response_function)
    
    # Create webhook endpoints
    create_webhook_endpoints(app, messenger_bot)
    
    print("🤖 Facebook Messenger Bot initialized")
    
    # Lấy URL từ môi trường nếu có
    webhook_url = os.getenv('WEBHOOK_URL', 'https://your-domain.com/webhook')
    print(f"💬 Webhook URL: {webhook_url}")
    print(f"🔑 Using verify token: {VERIFY_TOKEN}")
    
    return messenger_bot

def main():
    """
    Chức năng độc lập để test (sử dụng hàm giả)
    Khởi tạo Flask app và messenger bot với các hàm mock để test
    """
    from flask import Flask
    
    # Mock functions for testing
    def mock_search(query):
        return [{"text": "Sample content", "source": "Test Source", "url": "https://example.com"}]
    
    def mock_generate(query, chunks):
        return f"Response to: {query}"
    
    app = Flask(__name__)
    messenger_bot = setup_facebook_messenger(app, mock_search, mock_generate)
    
    print("🚀 Starting test server...")
    app.run(debug=True, port=5001)

if __name__ == "__main__":
    main()