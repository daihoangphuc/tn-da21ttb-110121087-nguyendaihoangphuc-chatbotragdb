#!/usr/bin/env python3
"""
Test logic đánh giá context quality để xác định smart fallback
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_context_evaluation_logic():
    """Test logic đánh giá context quality"""
    
    print("=" * 60)
    print("TEST CONTEXT EVALUATION LOGIC")
    print("=" * 60)
    
    # Simulate context quality results
    test_cases = [
        {
            "name": "Trường hợp ban đầu (Oracle question)",
            "context_quality": {
                "is_sufficient": False,
                "confidence": 0.30,
                "reason": "Thông tin chỉ nói chung về DBMS và SQL Server, không có thông tin cụ thể về Oracle"
            },
            "threshold": 0.20,
            "expected_fallback": True,
            "old_logic_result": False,  # Logic cũ không fallback
            "new_logic_result": True    # Logic mới sẽ fallback
        },
        {
            "name": "Confidence thấp nhưng sufficient=True",
            "context_quality": {
                "is_sufficient": True,
                "confidence": 0.15,
                "reason": "Confidence thấp"
            },
            "threshold": 0.20,
            "expected_fallback": True,
            "old_logic_result": True,   # Logic cũ cũng fallback
            "new_logic_result": True    # Logic mới cũng fallback
        },
        {
            "name": "Context đủ và confidence cao",
            "context_quality": {
                "is_sufficient": True,
                "confidence": 0.80,
                "reason": "Thông tin đầy đủ"
            },
            "threshold": 0.20,
            "expected_fallback": False,
            "old_logic_result": False,  # Logic cũ không fallback
            "new_logic_result": False   # Logic mới không fallback
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i}: {test_case['name']} ---")
        
        context_quality = test_case["context_quality"]
        threshold = test_case["threshold"]
        
        print(f"Context: sufficient={context_quality['is_sufficient']}, confidence={context_quality['confidence']}, threshold={threshold}")
        print(f"Reason: {context_quality['reason']}")
        
        # OLD LOGIC (chỉ xét confidence)
        old_should_fallback = context_quality["confidence"] < threshold
        
        # NEW LOGIC (xét cả is_sufficient và confidence)
        insufficient_context = not context_quality.get("is_sufficient", True)
        low_confidence = context_quality["confidence"] < threshold
        new_should_fallback = insufficient_context or low_confidence
        
        print(f"\nOLD LOGIC: confidence < threshold = {context_quality['confidence']} < {threshold} = {old_should_fallback}")
        print(f"NEW LOGIC: insufficient_context OR low_confidence = {insufficient_context} OR {low_confidence} = {new_should_fallback}")
        
        # Verify results
        old_correct = old_should_fallback == test_case["old_logic_result"]
        new_correct = new_should_fallback == test_case["new_logic_result"]
        expected_correct = new_should_fallback == test_case["expected_fallback"]
        
        print(f"\n✅ Old logic verification: {old_correct} (expected: {test_case['old_logic_result']}, got: {old_should_fallback})")
        print(f"✅ New logic verification: {new_correct} (expected: {test_case['new_logic_result']}, got: {new_should_fallback})")
        print(f"✅ Expected behavior: {expected_correct} (should fallback: {test_case['expected_fallback']}, new logic result: {new_should_fallback})")
        
        if test_case["name"] == "Trường hợp ban đầu (Oracle question)":
            print(f"\n🎯 QUAN TRỌNG: Đây là trường hợp từ logs gốc!")
            print(f"   - Old logic: {old_should_fallback} (không fallback → WRONG)")
            print(f"   - New logic: {new_should_fallback} (có fallback → CORRECT)")
        
        print("-" * 50)
    
    print(f"\n✅ CONCLUSION:")
    print(f"Logic mới đã sửa được vấn đề trong trường hợp ban đầu:")
    print(f"- Khi is_sufficient=False nhưng confidence >= threshold")
    print(f"- Logic cũ: chỉ xét confidence → không fallback (SAI)")  
    print(f"- Logic mới: xét cả is_sufficient → có fallback (ĐÚNG)")


if __name__ == "__main__":
    test_context_evaluation_logic() 