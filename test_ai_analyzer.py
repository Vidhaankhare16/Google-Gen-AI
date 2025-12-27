#!/usr/bin/env python3
"""
Test the AI analyzer with real Gemini API
"""

import sys
import os
sys.path.append('backend')

from services.ai_analyzer import AIAnalyzer
from dotenv import load_dotenv

# Load environment variables
load_dotenv('backend/.env')

def test_ai_analyzer():
    """Test the AI analyzer"""
    print("🧪 Testing AI Analyzer...")
    print("=" * 50)
    
    try:
        # Initialize the analyzer
        analyzer = AIAnalyzer()
        
        # Test document analysis
        sample_text = """
        RENTAL AGREEMENT
        
        This rental agreement is entered into between John Smith (Landlord) and Jane Doe (Tenant).
        
        TERMS:
        1. Monthly rent: $1,200 due on the 1st of each month
        2. Security deposit: $2,400 (two months rent)
        3. Late fee: $50 if rent is paid after the 5th
        4. Lease term: 12 months starting January 1, 2024
        5. No pets allowed without written permission
        6. Tenant is responsible for utilities except water and trash
        7. 30-day notice required for termination
        
        RESTRICTIONS:
        - No smoking inside the property
        - No subletting without landlord approval
        - Maximum occupancy: 2 people
        
        By signing below, both parties agree to these terms.
        """
        
        print("📄 Analyzing sample rental agreement...")
        result = analyzer.analyze_document(sample_text, "sample_rental_agreement.pdf")
        
        print(f"\n📋 Analysis Result:")
        print(f"Summary: {result.get('summary', 'N/A')}")
        print(f"\nKey Points ({len(result.get('key_points', []))}):")
        for i, point in enumerate(result.get('key_points', []), 1):
            print(f"  {i}. {point}")
        
        print(f"\nWarnings ({len(result.get('warnings', []))}):")
        for i, warning in enumerate(result.get('warnings', []), 1):
            print(f"  {i}. {warning}")
        
        # Test Q&A
        print(f"\n❓ Testing Q&A...")
        question = "What is the monthly rent amount?"
        qa_result = analyzer.answer_question(sample_text, question)
        
        print(f"Question: {question}")
        print(f"Answer: {qa_result.get('answer', 'N/A')}")
        print(f"Source: {qa_result.get('source_section', 'N/A')}")
        print(f"Confidence: {qa_result.get('confidence', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_ai_analyzer()
    
    if success:
        print("\n🎉 AI Analyzer is working with real Gemini API!")
    else:
        print("\n⚠️ AI Analyzer test failed.")