"""
Test Smart Fallback feature correctly
"""

import asyncio
from backend.rag import AdvancedDatabaseRAG

async def test_smart_fallback_proper():
    """Test Smart Fallback với câu hỏi về database nhưng không có trong tài liệu"""
    print("🚀 Testing Smart Fallback (Context Quality Check)...")
    
    rag = AdvancedDatabaseRAG()
    
    # Câu hỏi về database nhưng specific tech không có trong documents
    # Sẽ được classify là question_from_document nhưng context không đủ
    test_queries = [
        "CockroachDB có ưu điểm gì so với PostgreSQL?",  # Specific database comparison
        "Cách optimize MongoDB performance với sharding?",  # Specific tech không có trong docs
        "Redis Cluster setup và configuration như thế nào?",  # Specific setup
        "Khóa chính trong SQL là gì?",  # Basic question (should NOT trigger fallback)
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"🧪 TEST {i}: {query}")
        print(f"{'='*80}")
        
        fallback_triggered = False
        query_type = "unknown"
        sources_count = 0
        web_sources = 0
        doc_sources = 0
        
        async for item in rag.query_with_sources_streaming(
            query=query,
            conversation_history=""
        ):
            if item["type"] == "start":
                query_type = item["data"].get("query_type", "unknown")
                fallback_reason = item["data"].get("fallback_reason", "")
                
                print(f"🏷️  Query Type: {query_type}")
                
                if fallback_reason:
                    fallback_triggered = True
                    print(f"🔄 Smart Fallback Triggered: {fallback_reason}")
                elif "_fallback" in query_type:
                    fallback_triggered = True
                    print(f"🔄 Smart Fallback Detected in query_type")
            
            elif item["type"] == "sources":
                sources = item["data"].get("sources", [])
                sources_count = len(sources)
                web_sources = len([s for s in sources if s.get("is_web_search", False)])
                doc_sources = len([s for s in sources if not s.get("is_web_search", False)])
                
                print(f"📊 Sources: {sources_count} total ({doc_sources} docs, {web_sources} web)")
            
            elif item["type"] == "content":
                content = item["data"].get("content", "")
                print(content, end="", flush=True)
            
            elif item["type"] == "end":
                processing_time = item["data"].get("processing_time", 0)
                print(f"\n\n⏱️  Processing time: {processing_time:.2f}s")
        
        # Analysis
        print(f"\n📈 ANALYSIS:")
        print(f"   Smart Fallback: {'✅ YES' if fallback_triggered else '❌ NO'}")
        print(f"   Expected for this query: {'✅ YES' if i <= 3 else '❌ NO'}")
        print(f"   Result: {'✅ CORRECT' if (fallback_triggered and i <= 3) or (not fallback_triggered and i == 4) else '❌ UNEXPECTED'}")

async def test_threshold_sensitivity():
    """Test với threshold khác nhau"""
    print(f"\n🔧 Testing threshold sensitivity...")
    
    rag = AdvancedDatabaseRAG()
    query = "Apache Cassandra cluster setup best practices?"
    
    thresholds = [0.5, 0.7, 0.9]
    
    for threshold in thresholds:
        print(f"\n🎚️  Testing threshold: {threshold}")
        rag.context_quality_threshold = threshold
        
        fallback_count = 0
        async for item in rag.query_with_sources_streaming(query=query, conversation_history=""):
            if item["type"] == "start":
                if "_fallback" in item["data"].get("query_type", ""):
                    fallback_count += 1
                    break
        
        print(f"   Result: {'Fallback' if fallback_count > 0 else 'No fallback'}")

async def main():
    print("🧪 SMART FALLBACK PROPER TEST")
    print("="*80)
    
    await test_smart_fallback_proper()
    await test_threshold_sensitivity()
    
    print(f"\n🎉 Test completed!")
    print(f"\n💡 Expected behavior:")
    print(f"   - Tests 1-3: Should trigger Smart Fallback (specific tech not in docs)")
    print(f"   - Test 4: Should NOT trigger (basic SQL concept in docs)")

if __name__ == "__main__":
    asyncio.run(main())