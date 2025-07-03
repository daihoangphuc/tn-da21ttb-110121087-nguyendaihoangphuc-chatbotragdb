#!/usr/bin/env python3
"""
Test script để kiểm tra Smart Fallback logic sau khi fix
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from backend.rag import AdvancedDatabaseRAG, initialize_global_resources


async def test_smart_fallback_fixed():
    """Test các trường hợp Smart Fallback sau khi fix logic"""
    
    print("=" * 60)
    print("TEST SMART FALLBACK LOGIC - AFTER FIX")
    print("=" * 60)
    
    # Initialize global resources
    print("\n1. Initializing RAG system...")
    global_resources = initialize_global_resources()
    
    # Create RAG instance with user_id
    test_user_id = "global_documents"
    rag = AdvancedDatabaseRAG(
        user_id=test_user_id,
        **global_resources
    )
    
    # Test cases với different context quality scenarios
    test_cases = [
        {
            "name": "Oracle database question (insufficient context)",
            "query": "Oracle là CSDL như thế nào?",
            "expected_trigger": True,
            "reason": "Should trigger fallback due to is_sufficient=False"
        },
        {
            "name": "PostgreSQL features question", 
            "query": "PostgreSQL có những tính năng gì?",
            "expected_trigger": True,
            "reason": "Should trigger fallback due to insufficient specific info"
        },
        {
            "name": "Basic SQL question",
            "query": "Câu lệnh SELECT trong SQL hoạt động như thế nào?",
            "expected_trigger": False,
            "reason": "Should have sufficient context in documents"
        }
    ]
    
    print(f"\n2. Testing {len(test_cases)} scenarios...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i}: {test_case['name']} ---")
        print(f"Query: {test_case['query']}")
        print(f"Expected to trigger fallback: {test_case['expected_trigger']}")
        print(f"Reason: {test_case['reason']}")
        
        try:
            # Track if fallback was actually triggered
            fallback_triggered = False
            response_parts = []
            
            # Process the query and collect results
            async for result in rag.query_with_sources_streaming(
                query=test_case['query'],
                conversation_history=""
            ):
                if result["type"] == "start":
                    data = result.get("data", {})
                    search_type = data.get("search_type", "")
                    query_type = data.get("query_type", "")
                    
                    # Check for fallback indicators
                    if "smart_fallback" in search_type or "smart_fallback" in query_type:
                        fallback_triggered = True
                        print(f"✅ FALLBACK TRIGGERED: {search_type or query_type}")
                        
                elif result["type"] == "content":
                    content = result.get("data", {}).get("content", "")
                    response_parts.append(content)
                    
                elif result["type"] == "end":
                    break
            
            # Verify result
            full_response = "".join(response_parts)
            
            if fallback_triggered == test_case["expected_trigger"]:
                print(f"✅ TEST PASSED: Fallback behavior matched expectation")
            else:
                print(f"❌ TEST FAILED: Expected fallback={test_case['expected_trigger']}, got fallback={fallback_triggered}")
            
            # Show response preview
            preview = full_response[:200] + "..." if len(full_response) > 200 else full_response
            print(f"Response preview: {preview}")
            
        except Exception as e:
            print(f"❌ ERROR during test: {str(e)}")
        
        print("-" * 50)
    
    print(f"\n3. Test completed!")
    print("\nNOTE: Trường hợp trước đây bị lỗi:")
    print("- Query về Oracle có context insufficient (is_sufficient=False)")
    print("- Nhưng confidence=0.30 >= threshold=0.20")
    print("- Logic cũ chỉ xét confidence → Không fallback")
    print("- Logic mới xét cả is_sufficient → Sẽ fallback ✅")


if __name__ == "__main__":
    asyncio.run(test_smart_fallback_fixed()) 