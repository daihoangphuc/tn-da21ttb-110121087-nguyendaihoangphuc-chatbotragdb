#!/usr/bin/env python3
"""
Test script để kiểm tra định dạng response cho other_question
"""

import asyncio
import sys
import os

# Thêm đường dẫn để import backend modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.query_handler import QueryHandler


async def test_other_question_format():
    """Test format của response cho other_question"""
    
    query_handler = QueryHandler()
    
    test_query = "thời tiết tra vinh hôm nay thế nào?"
    
    print(f"🧪 Testing response format for query: '{test_query}'")
    print("=" * 60)
    
    # Test phân loại câu hỏi
    expanded_query, query_type = query_handler.expand_and_classify_query_sync(test_query, "")
    print(f"📝 Query type: {query_type}")
    print(f"📝 Expanded query: {expanded_query}")
    
    if query_type == "other_question":
        # Test response format
        response = await query_handler.get_response_for_other_question(test_query)
        
        print("\n📄 Response content:")
        print("-" * 40)
        print(repr(response))  # Show with escape characters
        print("-" * 40)
        print("📄 Response display:")
        print(response)
        print("-" * 40)
        
        # Check for indentation issues
        lines = response.split('\n')
        for i, line in enumerate(lines[:5]):  # Check first 5 lines
            leading_spaces = len(line) - len(line.lstrip())
            print(f"Line {i+1}: {leading_spaces} leading spaces - '{line[:50]}{'...' if len(line) > 50 else ''}'")
    else:
        print(f"❌ Query was classified as '{query_type}' instead of 'other_question'")


if __name__ == "__main__":
    print("🚀 Testing other_question response format...")
    asyncio.run(test_other_question_format())
    print("✨ Test completed!") 