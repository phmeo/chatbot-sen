import os
from pathlib import Path
import re
import time
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

def parse_website_crawl_file(file_path):
    """Parse file crawl website và trích xuất thông tin từng trang."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Tách các trang bằng dấu phân cách
    pages = content.split('=' * 80)
    
    parsed_pages = []
    
    for page in pages[1:]:  # Bỏ qua phần header đầu tiên
        if not page.strip():
            continue
            
        lines = page.strip().split('\n')
        if len(lines) < 3:
            continue
            
        # Parse thông tin trang
        page_info = {}
        
        # Dòng đầu tiên chứa [TRANG X/Y] TÊN_TRANG
        title_line = lines[0].strip()
        title_match = re.match(r'\[TRANG (\d+)/(\d+)\] (.+)', title_line)
        if title_match:
            page_info['page_number'] = int(title_match.group(1))
            page_info['total_pages'] = int(title_match.group(2))
            page_info['page_title'] = title_match.group(3)
        
        # Tìm URL
        url_line = None
        length_line = None
        content_start = 3  # Mặc định nội dung bắt đầu từ dòng thứ 4
        
        for i, line in enumerate(lines[1:], 1):
            if line.startswith('URL:'):
                url_line = line
                page_info['url'] = line.replace('URL:', '').strip()
            elif line.startswith('Độ dài:'):
                length_line = line
                page_info['length'] = line.replace('Độ dài:', '').strip()
            elif line.startswith('--'):
                content_start = i + 1
                break
        
        # Lấy nội dung trang
        if content_start < len(lines):
            page_content = '\n'.join(lines[content_start:]).strip()
            page_info['content'] = page_content
        else:
            page_info['content'] = ''
        
        if page_info.get('content') and len(page_info.get('content', '').strip()) > 50:
            parsed_pages.append(page_info)
    
    return parsed_pages

def count_tokens(text):
    """Đếm số tokens trong text."""
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def chunk_large_text(text, max_tokens=6000):
    """Chia text lớn thành các chunks nhỏ đơn giản."""
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    
    if len(tokens) <= max_tokens:
        return [text]  # Không cần chunk
    
    chunks = []
    start = 0
    
    while start < len(tokens):
        # Lấy chunk với max_tokens
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)
        
        # Di chuyển start không overlap
        start = end
    
    return chunks

def get_embedding_single(text):
    """Get embedding cho 1 text từ OpenAI API."""
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-large"
    )
    return response.data[0].embedding

def get_embedding_batch(texts):
    """Get embedding for a batch of texts from OpenAI API."""
    # Kiểm tra tổng tokens trong batch
    total_tokens = sum(count_tokens(text) for text in texts)
    if total_tokens > 8000:  # An toàn với giới hạn 8192
        print(f"    ⚠️  Cảnh báo: Batch có {total_tokens:,} tokens")
    
    response = client.embeddings.create(
        input=texts,
        model="text-embedding-3-large"
    )
    return [item.embedding for item in response.data]

def calculate_embedding_cost(total_tokens):
    """Tính toán chi phí embedding.
    text-embedding-3-large: $0.00013 / 1K tokens
    """
    cost_per_1k_tokens = 0.00013  # USD cho text-embedding-3-large
    total_cost = (total_tokens / 1000) * cost_per_1k_tokens
    return total_cost

def main():
    """Main function - làm mọi thứ tự động."""
    print("="*70)
    print("🚀 SENTIA AI RAG - MILVUS UPDATE TOOL")
    print("="*70)
    print("🔄 Tự động: Drop collection cũ → Tạo mới → Update data → Tạo index")
    print("="*70)
    
    # Connect to Milvus
    connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)
    
    collection_name = "sentia_website"
    
    # 🗑️ BƯỚC 1: Xóa collection cũ nếu có
    if utility.has_collection(collection_name):
        print(f"🗑️  Tìm thấy collection cũ: {collection_name}")
        utility.drop_collection(collection_name)
        print(f"✅ Đã xóa collection cũ")
    else:
        print(f"ℹ️  Chưa có collection: {collection_name}")
    
    # 🆕 BƯỚC 2: Tạo collection mới với schema đầy đủ
    print(f"🆕 Đang tạo collection mới với schema đầy đủ...")
    from pymilvus import CollectionSchema, FieldSchema, DataType
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=3072),
        FieldSchema(name="page_title", dtype=DataType.VARCHAR, max_length=500),
        FieldSchema(name="url", dtype=DataType.VARCHAR, max_length=500),
        FieldSchema(name="page_number", dtype=DataType.INT64),
        FieldSchema(name="page_length", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="chunk_index", dtype=DataType.INT64),
        FieldSchema(name="is_chunked", dtype=DataType.BOOL)
    ]
    schema = CollectionSchema(fields=fields)
    collection = Collection(name=collection_name, schema=schema)
    print(f"✅ Đã tạo collection: {collection_name} (8 fields, dimension: 3072)")
    
    # 📂 BƯỚC 3: Đọc file dữ liệu
    crawl_file = Path("sentia_full_website.txt")
    if not crawl_file.exists():
        print(f"❌ Không tìm thấy file: {crawl_file}")
        return
    
    print(f"📂 Đang đọc file: {crawl_file}")
    pages = parse_website_crawl_file(crawl_file)
    print(f"📄 Đã parse {len(pages)} trang từ file crawl")
    
    # 📊 BƯỚC 4: Xử lý dữ liệu
    total_tokens_used = 0
    successful_pages = 0
    failed_pages = 0
    
    # Xử lý theo batches 3 trang/lần để tránh token limit
    batch_size = 3
    total_batches = (len(pages) + batch_size - 1) // batch_size
    
    print(f"🔄 Sẽ xử lý {total_batches} batches, mỗi batch tối đa {batch_size} trang")
    
    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(pages))
        batch_pages = pages[start_idx:end_idx]
        
        print(f"\n--- Batch {batch_idx + 1}/{total_batches} ---")
        print(f"Xử lý trang {start_idx + 1} đến {end_idx} ({len(batch_pages)} trang)")
        
        # Prepare data for this batch
        batch_contents = []
        batch_page_titles = []
        batch_urls = []
        batch_page_numbers = []
        batch_page_lengths = []
        batch_chunk_indices = []
        batch_is_chunked = []
        
        for page in batch_pages:
            content = page.get('content', '')
            if content and len(content.strip()) > 50:
                page_tokens = count_tokens(content)
                
                # Kiểm tra nếu trang quá lớn cần chunk
                if page_tokens > 6500:  # Ngưỡng đơn giản
                    print(f"    📄 Trang {page.get('page_number', 'N/A')} ({page_tokens:,} tokens) - chia chunks")
                    chunks = chunk_large_text(content, max_tokens=6000)
                    print(f"      └─ Chia thành {len(chunks)} chunks")
                    
                    for chunk_idx, chunk in enumerate(chunks):
                        batch_contents.append(chunk)
                        batch_page_titles.append(page.get('page_title', 'Unknown'))
                        batch_urls.append(page.get('url', ''))
                        batch_page_numbers.append(page.get('page_number', 0))
                        batch_page_lengths.append(page.get('length', ''))
                        batch_chunk_indices.append(chunk_idx)
                        batch_is_chunked.append(True)  # Đánh dấu đã chia chunk
                else:
                    batch_contents.append(content)
                    batch_page_titles.append(page.get('page_title', 'Unknown'))
                    batch_urls.append(page.get('url', ''))
                    batch_page_numbers.append(page.get('page_number', 0))
                    batch_page_lengths.append(page.get('length', ''))
                    batch_chunk_indices.append(0)  # Chunk đầu tiên cho trang không chia
                    batch_is_chunked.append(False)  # Không chia chunk
        
        if not batch_contents:
            print("  - Không có nội dung hợp lệ trong batch này")
            continue
        
        # Tính tổng tokens trong batch này
        batch_tokens = sum(count_tokens(content) for content in batch_contents)
        total_tokens_used += batch_tokens
        
        print(f"  - Đang tạo embedding cho {len(batch_contents)} items ({batch_tokens:,} tokens)...")
        
        try:
            # Tạo embeddings cho cả batch
            embeddings = get_embedding_batch(batch_contents)
            print(f"  - ✅ Batch thành công: {len(embeddings)} embeddings")
            
            # Insert into Milvus
            entities = [
                batch_contents,
                embeddings,
                batch_page_titles,
                batch_urls,
                batch_page_numbers,
                batch_page_lengths,
                batch_chunk_indices,
                batch_is_chunked
            ]
            
            insert_result = collection.insert(entities)
            print(f"  - ✅ Đã chèn {len(batch_contents)} items vào Milvus")
            
            successful_pages += len(batch_contents)
            
            # Flush để đảm bảo dữ liệu được ghi
            collection.flush()
            
        except Exception as e:
            print(f"  - ❌ Batch {batch_idx + 1} lỗi: {e}")
            print(f"  - 🔄 Fallback: Xử lý từng item một...")
            
            # Fallback: Xử lý từng item một cách đơn giản
            for i, (content, title, url, page_num, length, chunk_idx, is_chunked) in enumerate(zip(
                batch_contents, batch_page_titles, batch_urls, batch_page_numbers, batch_page_lengths, batch_chunk_indices, batch_is_chunked
            )):
                try:
                    content_tokens = count_tokens(content)
                    
                    # Nếu vẫn quá lớn, chia đơn giản
                    if content_tokens > 6500:
                        print(f"    📄 Item quá lớn ({content_tokens:,} tokens) - chia nhỏ...")
                        mini_chunks = chunk_large_text(content, max_tokens=5500)
                        
                        for mini_idx, mini_chunk in enumerate(mini_chunks):
                            try:
                                embedding = get_embedding_single(mini_chunk)
                                
                                # Insert mini chunk
                                entities = [
                                    [mini_chunk],
                                    [embedding], 
                                    [title],
                                    [url],
                                    [page_num],
                                    [length],
                                    [mini_idx],
                                    [True]  # Luôn True vì đã chia
                                ]
                                
                                insert_result = collection.insert(entities)
                                collection.flush()
                                successful_pages += 1
                                print(f"      ✅ Mini-chunk {mini_idx + 1}/{len(mini_chunks)}")
                                
                            except Exception as mini_error:
                                print(f"      ❌ Lỗi: {mini_error}")
                                failed_pages += 1
                                continue
                    else:
                        print(f"    📄 Item {page_num}: {title[:30]}... ({content_tokens:,} tokens)")
                        embedding = get_embedding_single(content)
                        
                        # Insert item
                        entities = [
                            [content],
                            [embedding], 
                            [title],
                            [url],
                            [page_num],
                            [length],
                            [chunk_idx],
                            [is_chunked]
                        ]
                        
                        insert_result = collection.insert(entities)
                        collection.flush()
                        
                        successful_pages += 1
                        print(f"    ✅ Thành công")
                    
                except Exception as page_error:
                    print(f"    ❌ Lỗi: {page_error}")
                    failed_pages += 1
                    continue
        
        # Delay 1s giữa các batch
        if batch_idx < total_batches - 1:
            print("  - 💤 Delay 1s...")
            time.sleep(1)
    
    # 🔧 BƯỚC 5: Tạo index tự động
    print(f"\n🔧 Đang tạo index cho vector search...")
    index_params = {
        "metric_type": "L2",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 1024}
    }
    collection.create_index(field_name="embedding", index_params=index_params)
    print(f"✅ Đã tạo index thành công")
    
    # 🚀 BƯỚC 6: Load collection để sử dụng
    collection.load()
    print(f"🚀 Collection đã được load và sẵn sàng sử dụng")
    
    # 💰 BƯỚC 7: Tính toán chi phí và báo cáo
    total_cost_usd = calculate_embedding_cost(total_tokens_used)
    total_cost_vnd = total_cost_usd * 24000  # Tỷ giá gần đúng
    
    # Báo cáo kết quả
    print(f"\n" + "="*70)
    print(f"🎉 HOÀN THÀNH! SENTIA AI RAG ĐÃ SẴN SÀNG!")
    print(f"="*70)
    print(f"📊 Thống kê xử lý:")
    print(f"   • Tổng số trang gốc: {len(pages)}")
    print(f"   • Items đã xử lý: {successful_pages}")
    print(f"   • Thất bại: {failed_pages}")
    print(f"   • Tỷ lệ thành công: {successful_pages/(successful_pages+failed_pages)*100:.1f}%")
    print(f"   • Documents trong DB: {collection.num_entities}")
    print(f"\n💰 Chi phí embedding:")
    print(f"   • Tổng tokens: {total_tokens_used:,}")
    print(f"   • Model: text-embedding-3-large")
    print(f"   • Tổng chi phí: ${total_cost_usd:.4f} USD")
    print(f"   • Quy đổi VND: {total_cost_vnd:,.0f} ₫")
    if successful_pages > 0:
        print(f"   • Chi phí/item: ${total_cost_usd/successful_pages:.6f} USD")
    print(f"\n🎯 Database ready for AI RAG!")
    print(f"   • Collection: {collection_name}")
    print(f"   • Status: Loaded & Indexed")
    print(f"   • Ready for vector search")
    print(f"="*70)

if __name__ == "__main__":
    main()
