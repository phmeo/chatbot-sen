import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from pymilvus import connections, Collection
import numpy as np
from typing import List, Dict
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from facebook_messenger import FacebookMessenger

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv('OPEN_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)

# Milvus connection parameters
MILVUS_HOST = 'localhost'
MILVUS_PORT = '19530'
COLLECTION_NAME = "pdf_documents"

# Initialize Flask app
app = Flask(__name__, static_folder='frontend')
CORS(app)

# Conversation history management
class ConversationManager:
    def __init__(self, max_history: int = 5):
        self.history: List[Dict] = []
        self.max_history = max_history
    
    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-self.max_history * 2:]
    
    def get_history(self) -> List[Dict]:
        return self.history
    
    def clear(self):
        self.history = []

# Initialize conversation manager
conversation_manager = ConversationManager()

def get_embedding(text):
    """Get embedding from OpenAI API."""
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def search_similar_chunks(query, top_k=3):
    """Search for similar chunks in Milvus database."""
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
    
    # Search
    results = collection.search(
        data=[query_embedding],
        anns_field="embedding",
        param=search_params,
        limit=top_k,
        output_fields=["text", "source"]
    )
    
    # Process results
    similar_chunks = []
    for hits in results:
        for hit in hits:
            similar_chunks.append({
                "text": hit.entity.get('text'),
                "source": hit.entity.get('source'),
                "distance": hit.distance
            })
    
    return similar_chunks

def generate_response(query: str, context_chunks: List[Dict]):
    """Generate response using GPT-4o-mini with context and conversation history."""
    # Prepare context
    context = "\n\n".join([f"Source: {chunk['source']}\nContent: {chunk['text']}" for chunk in context_chunks])
    
    # Create system message
    system_message = """Bạn với vai trò là một người tư vấn tuyển sinh cho trường sentia.
    Nhiệm vụ của bạn là trả lời chi tiết đầy đủ chi tiết mọi thông tin, sử dụng giọng điệu thuyết phục, không được trả lời ngoài chủ đề tư vấn (chủ đề ngoài sentia).
    Nếu ngoài chủ đề tư vấn hãy trả lời là "Thông tin vượt ngoài khả năng".

    Khi trả lời về học bổng hoặc các chương trình của trường:
    1. Phân loại rõ ràng từng mục bằng số thứ tự
    2. Mỗi thông tin quan trọng nên được trình bày trên một dòng mới
    3. Sử dụng gạch đầu dòng (-) cho các chi tiết phụ)
    5. Kết thúc bằng lời mời gọi hoặc khuyến khích phù hợp

    Ví dụ cấu trúc câu trả lời:
    [Lời chào và giới thiệu ngắn gọn]

    [Nội dung chính được phân loại rõ ràng]:
    1. [Thông tin chính thứ nhất]
       - Chi tiết 1
       - Chi tiết 2

    2. [Thông tin chính thứ hai]
       - Chi tiết 1
       - Chi tiết 2

    [Kết luận và lời mời gọi]
    """
    
    # Prepare messages with history
    messages = [
        {"role": "system", "content": system_message},
        {"role": "system", "content": f"Context from documents:\n{context}"}
    ]
    
    # Add conversation history
    messages.extend(conversation_manager.get_history())
    
    # Add current query
    messages.append({"role": "user", "content": query})
    
    # Generate response
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=1000
    )
    
    return response.choices[0].message.content

# Initialize Facebook Messenger (sau khi các hàm đã được định nghĩa)
fb_messenger = FacebookMessenger(search_similar_chunks, generate_response)

@app.route('/')
def serve_frontend():
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('frontend', path)

@app.route('/chat', methods=['POST'])
def chat():
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
        
        # Get sources
        sources = list(set(chunk['source'] for chunk in similar_chunks))
        
        return jsonify({
            'response': response,
            'sources': sources
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """Facebook Messenger webhook endpoint"""
    if request.method == 'GET':
        # Xác thực webhook
        return fb_messenger.verify_webhook()
    
    elif request.method == 'POST':
        # Xử lý tin nhắn
        return fb_messenger.handle_webhook()

@app.route('/setup-messenger', methods=['POST'])
def setup_messenger():
    """Thiết lập các tính năng Messenger (chỉ chạy một lần)"""
    try:
        success = fb_messenger.set_get_started_button()
        if success:
            return jsonify({'message': 'Messenger setup successful'})
        else:
            return jsonify({'error': 'Failed to setup messenger'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
