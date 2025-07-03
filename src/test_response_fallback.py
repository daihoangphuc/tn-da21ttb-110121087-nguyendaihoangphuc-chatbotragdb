#!/usr/bin/env python3
"""
Test script để kiểm tra tính năng Response-based Fallback
"""

import asyncio
import sys
import os

# Thêm đường dẫn để import backend modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.rag import AdvancedDatabaseRAG


async def test_insufficient_response_detection():
    """Test hàm _detect_insufficient_response"""
    
    # Khởi tạo RAG instance
    rag = AdvancedDatabaseRAG()
    
    print("🧪 Testing Response-based Fallback Detection...")
    print("=" * 60)
    
    # Test cases
    test_cases = [
        {
            "name": "Strong insufficient pattern - exact match",
            "response": "Tôi không thể trả lời đầy đủ câu hỏi này dựa trên tài liệu hiện có. Thông tin về PostgreSQL không được tìm thấy trong tài liệu được cung cấp.",
            "expected": True
        },
        {
            "name": "Strong insufficient pattern - variant",
            "response": "Dựa trên tài liệu được cung cấp, tôi không thể trả lời đầy đủ câu hỏi này dựa trên tài liệu hiện có vì thiếu thông tin chi tiết.",
            "expected": True
        },
        {
            "name": "Short response with weak patterns",
            "response": "Không đủ thông tin để trả lời. Tài liệu không đề cập.",
            "expected": True
        },
        {
            "name": "Multiple refusal indicators in short response",
            "response": "Xin lỗi, tôi không thể cung cấp thông tin này vì không có thông tin trong tài liệu.",
            "expected": True
        },
        {
            "name": "Long detailed response",
            "response": "SQL Server là một hệ quản trị cơ sở dữ liệu quan hệ được phát triển bởi Microsoft. Nó hỗ trợ nhiều tính năng như stored procedures, triggers, views, và indexes. SQL Server có thể được sử dụng để quản lý dữ liệu của các ứng dụng web và desktop. Nó cung cấp các công cụ quản lý như SQL Server Management Studio (SSMS) để người dùng có thể dễ dàng tương tác với database.",
            "expected": False
        },
        {
            "name": "Normal informative response",
            "response": "Khóa chính (Primary Key) là một ràng buộc quan trọng trong cơ sở dữ liệu quan hệ (trang 15, database_fundamentals.pdf). Nó được sử dụng để xác định duy nhất mỗi bản ghi trong bảng.",
            "expected": False
        },
        {
            "name": "Empty response",
            "response": "",
            "expected": False
        },
        {
            "name": "Very short response",
            "response": "Không có.",
            "expected": False
        }
    ]
    
    # Chạy test cases
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        print(f"Response: '{test_case['response'][:100]}{'...' if len(test_case['response']) > 100 else ''}'")
        
        result = await rag._detect_insufficient_response(test_case['response'])
        expected = test_case['expected']
        
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"Expected: {expected}, Got: {result} - {status}")
        
        if result != expected:
            print(f"❌ Test failed! Expected {expected} but got {result}")
    
    print("\n" + "=" * 60)
    print("🏁 Test completed!")


async def test_config_values():
    """Test các giá trị cấu hình"""
    
    print("\n🔧 Testing Configuration Values...")
    print("=" * 40)
    
    # Test với giá trị mặc định
    rag = AdvancedDatabaseRAG()
    print(f"✅ Smart Fallback: {rag.enable_smart_fallback}")
    print(f"✅ Response Fallback: {rag.enable_response_fallback}")
    print(f"✅ Context Quality Threshold: {rag.context_quality_threshold}")


if __name__ == "__main__":
    print("🚀 Starting Response-based Fallback Tests...")
    
    # Chạy tests
    asyncio.run(test_insufficient_response_detection())
    asyncio.run(test_config_values())
    
    print("\n✨ All tests completed!") 