import os
from pathlib import Path
import pdfplumber
from dotenv import load_dotenv
from openai import OpenAI
from pymilvus import connections, Collection, utility
import tiktoken
import numpy as np

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv('OPEN_API_KEY')

# Khởi tạo OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Milvus connection parameters
MILVUS_HOST = 'localhost'
MILVUS_PORT = '19530'

def get_pdf_text(pdf_path):
    """Extract text from PDF file using pdfplumber."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:  # Kiểm tra page có text không
                text += page_text + "\n"  # Thêm xuống dòng giữa các trang
    return text

def chunk_text(text, chunk_size=512, overlap=150):
    """Split text into chunks with specified size and overlap."""
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    
    chunks = []
    for i in range(0, len(tokens), chunk_size - overlap):
        chunk = tokens[i:i + chunk_size]
        chunks.append(encoding.decode(chunk))
    
    return chunks

def get_embedding(text):
    """Get embedding from OpenAI API."""
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def update_milvus():
    """Update Milvus database with PDF content."""
    # Connect to Milvus
    connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)
    
    # Get or create collection
    collection_name = "pdf_documents"
    if not utility.has_collection(collection_name):
        from pymilvus import CollectionSchema, FieldSchema, DataType
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=255)
        ]
        schema = CollectionSchema(fields=fields)
        collection = Collection(name=collection_name, schema=schema)
    else:
        collection = Collection(collection_name)
    
    # Process PDF files
    current_dir = Path(".")  # Thư mục hiện tại thay vì thư mục "save"
    pdf_files = list(current_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("Không tìm thấy file PDF nào trong thư mục hiện tại")
        return
    
    for pdf_file in pdf_files:
        print(f"Processing {pdf_file.name}...")
        
        # Extract text from PDF
        text = get_pdf_text(pdf_file)
        print(f"Đã trích xuất {len(text)} ký tự từ {pdf_file.name}")
        
        # Split into chunks
        chunks = chunk_text(text)
        print(f"Đã chia thành {len(chunks)} chunks")
        
        # Prepare data for insertion
        texts = []
        embeddings = []
        sources = []
        
        for i, chunk in enumerate(chunks):
            print(f"Đang tạo embedding cho chunk {i+1}/{len(chunks)}")
            embedding = get_embedding(chunk)
            texts.append(chunk)
            embeddings.append(embedding)
            sources.append(pdf_file.name)
        
        # Insert into Milvus
        entities = [
            texts,
            embeddings,
            sources
        ]
        insert_result = collection.insert(entities)
        print(f"Đã chèn {len(chunks)} chunks từ {pdf_file.name} vào Milvus. Insert IDs: {insert_result.primary_keys[:5]}...")  # Hiển thị 5 ID đầu tiên
    
    # Create index if not exists
    if not collection.has_index():
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
        collection.create_index(field_name="embedding", index_params=index_params)
    
    # Load collection
    collection.load()
    
    # Flush để đảm bảo dữ liệu được ghi vào disk
    collection.flush()
    
    # Kiểm tra số lượng document trong collection
    print(f"Tổng số document trong collection: {collection.num_entities}")
    
    print("Milvus update completed successfully")

if __name__ == "__main__":
    update_milvus()
