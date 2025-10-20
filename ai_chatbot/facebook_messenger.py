import os
import requests
from flask import request, jsonify
from dotenv import load_dotenv
import hmac
import hashlib

# Load environment variables
load_dotenv()

# Facebook Messenger configuration
PAGE_ACCESS_TOKEN = os.getenv('PAGE_ACCESS_TOKEN', 'EAAQ757pOgKoBOz3pMRzcU3i21o8QGYZCrU3dAaZCV8S0QST8sBRTzaZCy7DsZAfivTu6VRtzRg6N2uUgwvbgeOatn07zbf84Wd9Sgu8puF67R8J1sUiMNa8ZC4CZCmq6Rb5mxv4QG3k8UVgnQx2u5LycLCMXlYl1ZC0urYPShtpiLM7AfbvZCayTs2KV1D0qK8sDnO4PbgZDZD')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN', 'sentia_chatbot_verify_2025')
APP_SECRET = os.getenv('8f6acb19298af6b13e479c99d866e7c0')

class FacebookMessenger:
    def __init__(self, search_function, generate_response_function):
        self.search_similar_chunks = search_function
        self.generate_response = generate_response_function
        self.conversation_histories = {}  # Lưu lịch sử theo user_id
    
    def verify_webhook(self):
        """Xác thực webhook với Facebook"""
        if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
            # Trong lúc verification, không cần kiểm tra signature
            if request.args.get("hub.verify_token") == VERIFY_TOKEN:
                print(f"✅ Webhook verification successful! Token: {VERIFY_TOKEN}")
                return request.args["hub.challenge"]
            else:
                print(f"❌ Invalid verification token. Expected: {VERIFY_TOKEN}, Got: {request.args.get('hub.verify_token')}")
                return "Invalid verification token", 403
        return "Hello world", 200
    
    def verify_request_signature(self, payload):
        """Xác thực chữ ký từ Facebook"""
        if not APP_SECRET:
            return True  # Skip verification nếu không có APP_SECRET
        
        signature = request.headers.get('X-Hub-Signature-256')
        if not signature:
            return False
        
        expected_signature = 'sha256=' + hmac.new(
            APP_SECRET.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def handle_webhook(self):
        """Xử lý webhook từ Facebook"""
        if not self.verify_request_signature(request.data):
            return "Forbidden", 403
        
        data = request.get_json()
        
        if data.get("object") == "page":
            for entry in data.get("entries", []):
                for messaging_event in entry.get("messaging", []):
                    if messaging_event.get("message"):
                        self.handle_message(messaging_event)
                    elif messaging_event.get("postback"):
                        self.handle_postback(messaging_event)
        
        return "EVENT_RECEIVED", 200
    
    def handle_message(self, messaging_event):
        """Xử lý tin nhắn từ người dùng"""
        sender_id = messaging_event["sender"]["id"]
        message_text = messaging_event["message"].get("text", "")
        
        if not message_text:
            return
        
        # Tìm kiếm thông tin liên quan
        try:
            similar_chunks = self.search_similar_chunks(message_text)
            
            if not similar_chunks:
                response_text = "Xin lỗi, tôi không tìm thấy thông tin liên quan trong cơ sở dữ liệu về câu hỏi của bạn."
            else:
                # Sinh phản hồi
                response_text = self.generate_response(message_text, similar_chunks)
            
            # Gửi phản hồi
            self.send_message(sender_id, response_text)
            
        except Exception as e:
            print(f"Error handling message: {e}")
            self.send_message(sender_id, "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại sau.")
    
    def handle_postback(self, messaging_event):
        """Xử lý postback (nút bấm)"""
        sender_id = messaging_event["sender"]["id"]
        postback_payload = messaging_event["postback"]["payload"]
        
        if postback_payload == "GET_STARTED":
            welcome_text = """Xin chào! 👋
            
Tôi là chatbot tư vấn tuyển sinh của trường Sentia. Tôi có thể giúp bạn:

🎓 Thông tin về các chương trình đào tạo
📚 Học bổng và hỗ trợ tài chính  
📅 Lịch tuyển sinh và đăng ký
📍 Thông tin liên hệ và địa chỉ
❓ Các câu hỏi khác về trường

Hãy nhắn tin cho tôi bất kỳ câu hỏi nào bạn muốn biết!"""
            
            self.send_message(sender_id, welcome_text)
    
    def send_message(self, recipient_id, message_text):
        """Gửi tin nhắn đến người dùng"""
        # Chia nhỏ tin nhắn nếu quá dài (Facebook giới hạn 2000 ký tự)
        max_length = 2000
        if len(message_text) > max_length:
            messages = [message_text[i:i+max_length] for i in range(0, len(message_text), max_length)]
            for msg in messages:
                self._send_single_message(recipient_id, msg)
        else:
            self._send_single_message(recipient_id, message_text)
    
    def _send_single_message(self, recipient_id, message_text):
        """Gửi một tin nhắn đơn"""
        url = f"https://graph.facebook.com/v18.0/me/messages"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        params = {
            "access_token": PAGE_ACCESS_TOKEN
        }
        
        data = {
            "recipient": {"id": recipient_id},
            "message": {"text": message_text},
            "messaging_type": "RESPONSE"
        }
        
        response = requests.post(url, headers=headers, params=params, json=data)
        
        if response.status_code != 200:
            print(f"Error sending message: {response.text}")
    
    def set_get_started_button(self):
        """Thiết lập nút Get Started"""
        url = f"https://graph.facebook.com/v18.0/me/messenger_profile"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        params = {
            "access_token": PAGE_ACCESS_TOKEN
        }
        
        data = {
            "get_started": {"payload": "GET_STARTED"},
            "greeting": [
                {
                    "locale": "default",
                    "text": "Xin chào! Tôi là chatbot tư vấn tuyển sinh của trường Sentia. Hãy nhấn 'Bắt đầu' để bắt đầu cuộc trò chuyện!"
                }
            ]
        }
        
        response = requests.post(url, headers=headers, params=params, json=data)
        return response.status_code == 200 