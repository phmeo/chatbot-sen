#!/usr/bin/env python3
"""
Script test hệ thống AI RAG với database mới
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from pymilvus import connections, Collection, utility

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv('OPEN_API_KEY')

def test_database_connection():
    """Test kết nối database"""
    print("🔍 Kiểm tra kết nối Milvus...")
    
    try:
        # Connect to Milvus
        connections.connect(host='localhost', port='19530')
        print("✅ Kết nối Milvus thành công")
        
        # Check collection
        collection_name = "sentia_website"
        if utility.has_collection(collection_name):
            collection = Collection(collection_name)
            collection.load()
            
            # Get collection info
            num_entities = collection.num_entities
            print(f"✅ Collection '{collection_name}' có {num_entities:,} records")
            
            # Check schema
            schema = collection.schema
            fields = [field.name for field in schema.fields]
            print(f"📊 Schema: {', '.join(fields)}")
            
            return True
        else:
            print(f"❌ Không tìm thấy collection: {collection_name}")
            return False
            
    except Exception as e:
        print(f"❌ Lỗi kết nối database: {e}")
        return False

def test_openai_connection():
    """Test kết nối OpenAI"""
    print("\n🔍 Kiểm tra kết nối OpenAI...")
    
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Test embedding
        response = client.embeddings.create(
            input="test query",
            model="text-embedding-3-large"
        )
        
        embedding = response.data[0].embedding
        print(f"✅ OpenAI API hoạt động (dimension: {len(embedding)})")
        return True
        
    except Exception as e:
        print(f"❌ Lỗi kết nối OpenAI: {e}")
        return False

def test_search_function():
    """Test chức năng search"""
    print("\n🔍 Kiểm tra chức năng tìm kiếm...")
    
    try:
        # Import search function from main
        sys.path.append('.')
        from main import search_similar_chunks
        
        # Test search
        test_query = "học phí"
        results = search_similar_chunks(test_query, top_k=3)
        
        if results:
            print(f"✅ Tìm thấy {len(results)} kết quả cho query: '{test_query}'")
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result['source'][:60]}...")
            return True
        else:
            print(f"⚠️  Không tìm thấy kết quả cho query: '{test_query}'")
            return False
            
    except Exception as e:
        print(f"❌ Lỗi test search: {e}")
        return False

def test_generate_response():
    """Test chức năng generate response"""
    print("\n🔍 Kiểm tra chức năng generate response...")
    
    try:
        # Import functions from main
        sys.path.append('.')
        from main import search_similar_chunks, generate_response
        
        # Test end-to-end
        test_query = "thông tin về học phí"
        similar_chunks = search_similar_chunks(test_query, top_k=2)
        
        if similar_chunks:
            response = generate_response(test_query, similar_chunks)
            print(f"✅ Generated response ({len(response)} ký tự)")
            print(f"   Preview: {response[:100]}...")
            return True
        else:
            print("⚠️  Không có chunks để test response")
            return False
            
    except Exception as e:
        print(f"❌ Lỗi test response: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 SENTIA AI RAG - SYSTEM TEST")
    print("=" * 50)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("OpenAI Connection", test_openai_connection), 
        ("Search Function", test_search_function),
        ("Generate Response", test_generate_response)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Testing: {test_name}")
        if test_func():
            passed += 1
        print("-" * 30)
    
    print(f"\n📊 TEST RESULTS: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 Tất cả tests PASSED! Hệ thống sẵn sàng hoạt động.")
    else:
        print("⚠️  Một số tests FAILED! Kiểm tra lại cấu hình.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 