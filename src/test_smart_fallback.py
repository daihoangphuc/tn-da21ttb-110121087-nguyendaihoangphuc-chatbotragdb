"""
Simple Smart Fallback Test Script
"""

import asyncio
from backend.rag import AdvancedDatabaseRAG

async def test_smart_fallback():
    """Test Smart Fallback với câu hỏi mẫu"""
    print("🚀 Testing Smart Fallback...")
    
    rag = AdvancedDatabaseRAG()
    
    # Câu hỏi sẽ trigger fallback (không có trong document)
    test_query = "PostgreSQL 16 có tính năng mới gì trong năm 2024?"
    
    print(f"📝 Testing query: {test_query}")
    print("=" * 60)
    
    async for item in rag.query_with_sources_streaming(
        query=test_query,
        conversation_history=""
    ):
        if item["type"] == "start":
            query_type = item["data"].get("query_type", "unknown")
            fallback_reason = item["data"].get("fallback_reason", "")
            print(f"🏷️ Query Type: {query_type}")
            if fallback_reason:
                print(f"🔄 Fallback Reason: {fallback_reason}")
        
        elif item["type"] == "sources":
            sources = item["data"].get("sources", [])
            web_sources = [s for s in sources if s.get("is_web_search", False)]
            doc_sources = [s for s in sources if not s.get("is_web_search", False)]
            print(f"📊 Sources: {len(sources)} total ({len(doc_sources)} docs, {len(web_sources)} web)")
        
        elif item["type"] == "content":
            content = item["data"].get("content", "")
            print(content, end="", flush=True)
        
        elif item["type"] == "end":
            processing_time = item["data"].get("processing_time", 0)
            print(f"\n\n⏱️ Processing time: {processing_time:.2f}s")

if __name__ == "__main__":
    asyncio.run(test_smart_fallback())