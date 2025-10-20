"""
Module tích hợp Telegram Bot với chatbot AI
Cung cấp các chức năng:
- Nhận tin nhắn từ người dùng Telegram
- Xử lý tin nhắn và tìm kiếm thông tin liên quan
- Tạo câu trả lời và gửi lại cho người dùng
"""
import os
import requests
from typing import Dict, List
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class TelegramBot:
    """
    Lớp quản lý Telegram Bot
    Xử lý kết nối API Telegram và tích hợp với hệ thống AI
    """
    def __init__(self, token: str, search_function, generate_response_function):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.search_similar_chunks = search_function
        self.generate_response = generate_response_function
        self.conversation_histories = {}  # Lưu lịch sử theo chat_id
        
    def get_updates(self, offset=None, timeout=30):
        """
        Lấy tin nhắn mới từ Telegram
        Sử dụng long polling để nhận tin nhắn từ API Telegram
        
        Args:
            offset: ID của update cuối cùng đã xử lý + 1
            timeout: Thời gian chờ tối đa cho mỗi request
        """
        url = f"{self.base_url}/getUpdates"
        params = {
            'timeout': timeout,
            'offset': offset
        }
        
        try:
            response = requests.get(url, params=params)
            return response.json()
        except Exception as e:
            print(f"❌ Lỗi khi lấy updates: {e}")
            return None
    
    def send_message(self, chat_id: int, text: str, parse_mode='HTML'):
        """
        Gửi tin nhắn đến người dùng
        Hỗ trợ chia nhỏ tin nhắn dài để tránh vượt quá giới hạn Telegram
        
        Args:
            chat_id: ID của cuộc trò chuyện
            text: Nội dung tin nhắn
            parse_mode: Chế độ parse (HTML, Markdown)
        """
        url = f"{self.base_url}/sendMessage"
        
        # Chia nhỏ tin nhắn nếu quá dài (Telegram giới hạn 4096 ký tự)
        max_length = 4000
        if len(text) > max_length:
            messages = [text[i:i+max_length] for i in range(0, len(text), max_length)]
            for msg in messages:
                self._send_single_message(chat_id, msg, parse_mode)
        else:
            self._send_single_message(chat_id, text, parse_mode)
    
    def _send_single_message(self, chat_id: int, text: str, parse_mode='HTML'):
        """
        Gửi một tin nhắn đơn
        Thực hiện HTTP request đến Telegram API
        """
        url = f"{self.base_url}/sendMessage"
        
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        
        try:
            response = requests.post(url, data=data)
            if response.status_code == 200:
                print(f"✅ Đã gửi tin nhắn tới {chat_id}")
            else:
                print(f"❌ Lỗi gửi tin nhắn: {response.text}")
        except Exception as e:
            print(f"❌ Lỗi khi gửi tin nhắn: {e}")
    
    def handle_message(self, message):
        """
        Xử lý tin nhắn từ người dùng
        Phân tích tin nhắn, tìm kiếm thông tin liên quan và tạo phản hồi
        
        Args:
            message: Object tin nhắn từ Telegram API
        """
        chat_id = message['chat']['id']
        user_name = message['from'].get('first_name', 'Bạn')
        
        # Xử lý các loại tin nhắn khác nhau
        if 'text' in message:
            text = message['text']
            print(f"💬 Nhận tin nhắn từ {user_name} (ID: {chat_id}): {text}")
            
            # Xử lý lệnh /start
            if text == '/start':
                welcome_text = (
                    f"🎓 <b>Xin chào {user_name}!</b>\n\n"
                    "Tôi là AI Assistant tư vấn tuyển sinh của <b>Sentia School</b> - "
                    "được tích hợp công nghệ AI hiện đại với dữ liệu từ website chính thức.\n\n"
                    "🔥 <b>Tôi có thể hỗ trợ bạn:</b>\n\n"
                    "📚 <b>Chương trình đào tạo</b> - Thông tin chi tiết về các khóa học\n"
                    "💰 <b>Học bổng và Chi phí</b> - Các gói hỗ trợ tài chính\n"
                    "📅 <b>Tuyển sinh 2025</b> - Lịch thi, thủ tục đăng ký\n"
                    "📍 <b>Thông tin trường</b> - Cơ sở vật chất, địa chỉ\n"
                    "🎯 <b>Định hướng nghề nghiệp</b> - Tư vấn chọn ngành phù hợp\n\n"
                    "💡 <i>Hãy đặt câu hỏi cụ thể để nhận thông tin chính xác nhất!</i>\n\n"
                    "<b>Ví dụ:</b> \"Học phí ngành CNTT bao nhiêu?\" hoặc \"Điều kiện xét học bổng?\""
                )
                
                self.send_message(chat_id, welcome_text)
                return
            
            # Xử lý tin nhắn bình thường
            try:
                # Tìm kiếm thông tin liên quan
                similar_chunks = self.search_similar_chunks(text)
                
                if not similar_chunks:
                    response_text = "❌ Xin lỗi, tôi không tìm thấy thông tin liên quan trong cơ sở dữ liệu về câu hỏi của bạn.\n\nVui lòng thử đặt câu hỏi khác hoặc liên hệ trực tiếp với trường."
                else:
                    # Sinh phản hồi
                    response_text = self.generate_response(text, similar_chunks)
                    
                    # Thêm thông tin nguồn với URL
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
                        source_links = []
                        for source in sources[:3]:  # Chỉ hiển thị 3 nguồn chính
                            if source.get('url'):
                                source_links.append(f"• <a href='{source['url']}'>{source['title']}</a>")
                            else:
                                source_links.append(f"• {source['title']}")
                        
                        if source_links:
                            response_text += f"\n\n📚 <b>Nguồn tham khảo:</b>\n" + "\n".join(source_links)
                
                # Gửi phản hồi
                self.send_message(chat_id, response_text)
                
            except Exception as e:
                print(f"❌ Lỗi xử lý tin nhắn: {e}")
                error_text = "❌ Xin lỗi, có lỗi xảy ra khi xử lý câu hỏi của bạn. Vui lòng thử lại sau."
                self.send_message(chat_id, error_text)
        
        else:
            # Xử lý các loại tin nhắn khác (hình ảnh, file, v.v.)
            unsupported_text = "📝 Hiện tại tôi chỉ hỗ trợ tin nhắn văn bản. Vui lòng gửi câu hỏi bằng chữ."
            self.send_message(chat_id, unsupported_text)
    
    def clear_pending_updates(self):
        """
        Xóa các updates cũ để tránh conflict
        Hữu ích khi bot khởi động lại sau thời gian dài ngừng hoạt động
        """
        try:
            url = f"{self.base_url}/getUpdates"
            params = {'offset': -1}  # Lấy update cuối cùng và đánh dấu đã đọc
            response = requests.get(url, params=params)
            print("🧹 Đã clear pending updates")
        except Exception as e:
            print(f"⚠️  Không thể clear updates: {e}")
    
    def run_polling(self):
        """
        Chạy bot với polling mode
        Liên tục kiểm tra tin nhắn mới từ Telegram API
        """
        print("🚀 Bắt đầu chạy Telegram bot...")
        
        # Clear pending updates trước khi bắt đầu
        self.clear_pending_updates()
        
        print("📱 Bot đang lắng nghe tin nhắn...")
        
        offset = None
        
        while True:
            try:
                updates = self.get_updates(offset)
                
                if updates and updates.get('ok'):
                    for update in updates.get('result', []):
                        offset = update['update_id'] + 1
                        
                        if 'message' in update:
                            self.handle_message(update['message'])
                            
                elif updates and not updates.get('ok'):
                    error_code = updates.get('error_code')
                    
                    if error_code == 409:  # Conflict error
                        print("⚠️  Phát hiện conflict - đang clear updates...")
                        self.clear_pending_updates()
                        import time
                        time.sleep(2)  # Đợi 2 giây trước khi thử lại
                    else:
                        print(f"❌ Lỗi API: {updates}")
                    
            except KeyboardInterrupt:
                print("\n⏹️  Dừng bot...")
                break
            except Exception as e:
                print(f"❌ Lỗi không mong đợi: {e}")
                continue 