"""
Chatbot tư vấn tuyển sinh cho trường Sentia School, tích hợp đa nền tảng:
- Web interface (Flask)
- Telegram bot
- Facebook Messenger bot

Chatbot sử dụng:
- OpenAI embeddings cho vector search
- Milvus làm vector database để lưu trữ các đoạn văn bản
- GPT-4o-mini để tạo câu trả lời dựa trên các đoạn văn bản liên quan
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from pymilvus import connections, Collection, utility
import numpy as np
from typing import List, Dict, Optional, Any, Union, cast
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from telegram_bot import TelegramBot
import threading
import json
# Import Facebook Messenger bot integration
from messanger_facebook import setup_facebook_messenger

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv('OPEN_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)

# Milvus connection parameters
MILVUS_HOST = 'localhost'
MILVUS_PORT = '19530'
COLLECTION_NAME = "sentia_website"

# Initialize Flask app
app = Flask(__name__, static_folder='frontend')
CORS(app)

# Conversation history management
class ConversationManager:
    """
    Lớp quản lý lịch sử hội thoại, lưu trữ các tin nhắn giữa người dùng và chatbot
    Giới hạn số lượng tin nhắn để tránh quá tải context window của OpenAI
    """
    def __init__(self, max_history: int = 5):
        self.history: List[Dict[str, str]] = []
        self.max_history = max_history
    
    def add_message(self, role: str, content: str):
        """Thêm tin nhắn vào lịch sử hội thoại"""
        if content is None:
            content = ""  # Đảm bảo content không bao giờ là None
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-self.max_history * 2:]
    
    def get_history(self) -> List[Dict[str, str]]:
        """Lấy toàn bộ lịch sử hội thoại"""
        return self.history
    
    def clear(self):
        """Xóa toàn bộ lịch sử hội thoại"""
        self.history = []

# Initialize conversation manager
conversation_manager = ConversationManager()

# Telegram Bot configuration
TELEGRAM_TOKEN = "7617019912:AAH1Ws5xaO54Gpktg3qdIHH4RLiHNsZyRvc"

def get_embedding(text):
    """
    Lấy vector embedding từ OpenAI API cho văn bản đầu vào
    Sử dụng model text-embedding-3-large để có độ chính xác cao
    """
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-large"
    )
    return response.data[0].embedding

def search_similar_chunks(query, top_k=5):
    """
    Tìm kiếm các đoạn văn bản tương tự trong cơ sở dữ liệu Milvus
    Sử dụng vector embedding để tìm kiếm ngữ nghĩa, không phải từ khóa
    
    Args:
        query: Câu hỏi của người dùng
        top_k: Số lượng kết quả trả về
        
    Returns:
        List[Dict]: Danh sách các đoạn văn bản tương tự kèm thông tin
    """
    similar_chunks = []
    
    try:
        # Connect to Milvus
        connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)
        
        # Get collection
        collection = Collection(COLLECTION_NAME)
        collection.load()
        
        # Get query embedding
        query_embedding = get_embedding(query)
        
        # Search parameters
        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 10}
        }
        
        # Thực hiện tìm kiếm
        future = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["content", "page_title", "url", "page_number", "chunk_index", "is_chunked"]
        )
        
        # Cấu trúc kết quả từ pymilvus thường gồm danh sách các hits cho mỗi vector query
        if hasattr(future, '__getitem__'):
            result_list = future[0]  # Lấy kết quả cho vector đầu tiên
            for hit in result_list:
                # Tạo source info từ page info
                entity = hit.entity
                page_title = getattr(entity, 'page_title', 'Unknown')
                url = getattr(entity, 'url', '')
                page_num = getattr(entity, 'page_number', '')
                chunk_idx = getattr(entity, 'chunk_index', 0)
                is_chunked = getattr(entity, 'is_chunked', False)
                content = getattr(entity, 'content', '')
                
                # Tạo source string
                source = f"{page_title}"
                if page_num:
                    source += f" (Trang {page_num})"
                if is_chunked and chunk_idx > 0:
                    source += f" - Phần {chunk_idx + 1}"
                
                similar_chunks.append({
                    "text": content,
                    "source": source,
                    "url": url,
                    "distance": hit.distance,
                    "page_title": page_title,
                    "page_number": page_num,
                    "is_chunked": is_chunked
                })
        else:
            print("Định dạng kết quả không đúng như mong đợi")
            
    except Exception as e:
        print(f"Lỗi trong search_similar_chunks: {e}")
    
    return similar_chunks

def generate_response(query: str, context_chunks: List[Dict]) -> str:
    """
    Tạo câu trả lời sử dụng GPT-4o-mini với context và lịch sử hội thoại
    
    Args:
        query: Câu hỏi của người dùng
        context_chunks: Danh sách các đoạn văn bản liên quan từ cơ sở dữ liệu
        
    Returns:
        str: Câu trả lời từ AI
    """
    # Prepare context
    context = "\n\n".join([f"Source: {chunk['source']}\nContent: {chunk['text']}" for chunk in context_chunks])
    
    # Create system message
    system_message = """Bạn là AI Assistant tư vấn tuyển sinh chuyên nghiệp của trường Sentia School.

NHIỆM VỤ CHÍNH:
- Trả lời chi tiết, chính xác về mọi thông tin liên quan đến Sentia School
- Sử dụng giọng điệu thân thiện, chuyên nghiệp và thuyết phục
- Các câu hỏi chào, hello,... bạn phải trả lời từ tốn hỏi xem người dùng có cần giúp đỡ gì không 
- Chỉ trả lời các câu hỏi liên quan đến trường, giáo dục
- Nếu câu hỏi ngoài phạm vi kiến thức thì trả lời, ngoài trừ Hello, xin chào,....: "Xin lỗi, tôi chỉ có thể tư vấn về Sentia School"

CÁCH TRÌNH BÀY:
✨ Sử dụng emoji phù hợp để tạo điểm nhấn
📋 Chia thành các mục rõ ràng với emoji đầu dòng
📞 Luôn cung cấp thông tin liên hệ khi có thể
🎯 Khuyến khích hành động cụ thể

FORMAT RESPONSE:
- Dùng ít ** (chỉ cho tiêu đề quan trọng)
- Sử dụng emoji thay vì ** cho điểm nhấn
- Xuống dòng rõ ràng giữa các ý
- Dùng • hoặc ✓ cho danh sách thay vì -

VÍ DỤ FORMAT TỐT:
🏫 **Về Sentia School**
✨ Trường được thành lập năm...
📚 Chương trình đào tạo bao gồm:
• Môn A
• Môn B
📞 Liên hệ: 024 3789 4666, 0906 288 849, 0896 675 889 """
    
    # Chuẩn bị tin nhắn theo định dạng OpenAI cần
    from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam
    
    # Tạo messages với kiểu dữ liệu cụ thể
    system_messages = [
        ChatCompletionSystemMessageParam(role="system", content=system_message),
        ChatCompletionSystemMessageParam(role="system", content=f"Context from documents:\n{context}")
    ]
    
    # Chuyển đổi conversation history
    history_messages = []
    for msg in conversation_manager.get_history():
        if msg["role"] == "user":
            history_messages.append(ChatCompletionUserMessageParam(role="user", content=msg["content"]))
        elif msg["role"] == "assistant":
            history_messages.append(ChatCompletionAssistantMessageParam(role="assistant", content=msg["content"]))
        elif msg["role"] == "system":
            history_messages.append(ChatCompletionSystemMessageParam(role="system", content=msg["content"]))
    
    # Thêm câu hỏi hiện tại
    current_message = ChatCompletionUserMessageParam(role="user", content=query)
    
    # Kết hợp tất cả messages
    all_messages = system_messages + history_messages + [current_message]
    
    try:
        # Generate response
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=all_messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        # Đảm bảo response có nội dung
        if response and response.choices and len(response.choices) > 0:
            return response.choices[0].message.content or ""
        return "Xin lỗi, tôi không thể tạo câu trả lời lúc này."
    except Exception as e:
        print(f"Lỗi khi tạo response: {e}")
        return "Xin lỗi, có lỗi xảy ra khi xử lý câu hỏi của bạn."

# Initialize Telegram Bot
telegram_bot = TelegramBot(TELEGRAM_TOKEN, search_similar_chunks, generate_response)

@app.route('/')
def serve_frontend():
    """Phục vụ trang chủ của ứng dụng web"""
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Phục vụ các file tĩnh (CSS, JS, images,...)"""
    return send_from_directory('frontend', path)

@app.route('/chat', methods=['POST'])
def chat():
    """
    API endpoint xử lý tin nhắn từ giao diện web
    Nhận câu hỏi, tìm kiếm nội dung liên quan, tạo câu trả lời và trả về kết quả
    """
    data = request.get_json()
    query = data.get('message', '')
    
    if not query:
        return jsonify({'error': 'No message provided'}), 400
    
    try:
        # Add user query to history
        conversation_manager.add_message("user", query)
        
        # Search for relevant chunks
        similar_chunks = search_similar_chunks(query)
        
        if not similar_chunks:
            return jsonify({
                'response': 'Không tìm thấy thông tin liên quan trong cơ sở dữ liệu.',
                'sources': []
            })
        
        # Generate response
        response = generate_response(query, similar_chunks)
        
        # Add assistant response to history
        conversation_manager.add_message("assistant", response)
        
        # Get sources with URLs
        sources = []
        for chunk in similar_chunks:
            source_info = {
                'title': chunk['source'],
                'url': chunk.get('url', ''),
                'page_title': chunk.get('page_title', ''),
                'is_chunked': chunk.get('is_chunked', False)
            }
            if source_info not in sources:
                sources.append(source_info)
        
        return jsonify({
            'response': response,
            'sources': sources[:3],  # Chỉ lấy 3 source chính
            'total_chunks': len(similar_chunks)
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


# Initialize Facebook Messenger Bot
messenger_bot = None

def run_telegram_bot():
    """Chạy Telegram bot trong thread riêng"""
    telegram_bot.run_polling()

def run_facebook_bot():
    """Set up Facebook Messenger integration trong thread riêng"""
    global messenger_bot
    messenger_bot = setup_facebook_messenger(app, search_similar_chunks, generate_response)
    print("🤖 Facebook Messenger Bot đã khởi động!")

if __name__ == "__main__":
    # Chạy Telegram bot trong background thread
    telegram_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    telegram_thread.start()
    
    # Chạy Facebook Messenger bot
    facebook_thread = threading.Thread(target=run_facebook_bot, daemon=True)
    facebook_thread.start()
    
    print("🤖 Telegram bot đã khởi động!")
    print(f"📱 Truy cập bot tại: t.me/sentia2015_bot")
    print("🤖 Facebook Messenger đã khởi động!")
    print("🌐 Flask server đang chạy...")
    
    # Chạy Flask server
    app.run(debug=False, host='0.0.0.0', port=5000)
