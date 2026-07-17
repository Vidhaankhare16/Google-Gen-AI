import logging
import json
import re
from typing import Dict, List, Optional, Tuple
import os
import requests
import json

from config import Config

logger = logging.getLogger(__name__)

class AIAnalyzer:
    """
    Service for analyzing legal documents using Google Cloud AI
    Supports both Vertex AI and Gemini API
    """
    
    def __init__(self):
        self.project_id = Config.GOOGLE_CLOUD_PROJECT
        self.location = Config.VERTEX_AI_LOCATION
        self.gemini_api_key = Config.GEMINI_API_KEY
        
        # Initialize AI clients
        self._init_ai_clients()
        
        # Analysis prompts
        self.analysis_prompt = self._get_analysis_prompt()
        self.qa_prompt = self._get_qa_prompt()
    
    def _init_ai_clients(self):
        """Initialize Google Cloud AI clients"""
        try:
            if self.gemini_api_key:
                # Use direct REST API calls to Gemini 2.0 Flash
                self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent"
                self.use_gemini_api = True
                logger.info("✅ Initialized Gemini 2.0 Flash API client - Real AI analysis enabled!")
            else:
                self.use_gemini_api = False
                logger.info("No API key provided, using mock responses")
                
        except Exception as e:
            logger.error(f"Failed to initialize AI clients: {str(e)}")
            self.use_gemini_api = False
            logger.info("Falling back to mock responses")
    
    def analyze_document(self, text: str, filename: str = None) -> Dict:
        """
        Analyze legal document and extract key information
        
        Args:
            text: Document text content
            filename: Original filename (optional)
        
        Returns:
            Dictionary with analysis results
        """
        
        try:
            # Prepare the prompt with document text
            prompt = self.analysis_prompt.format(
                document_text=text[:8000],  # Limit text length for API
                filename=filename or "document"
            )
            
            # Generate analysis
            if self.use_gemini_api:
                analysis_text = self._call_gemini_api(prompt)
            else:
                # Realistic mock response based on document content
                analysis_text = f'''
                {{
                    "summary": "This legal document contains {len(text)} characters of text with various contractual provisions. The document appears to establish terms and conditions between parties, including rights, obligations, and procedures for compliance.",
                    "key_points": [
                        "Document contains specific terms and conditions for the agreement",
                        "Payment obligations and financial responsibilities are outlined",
                        "Liability limitations and risk allocation clauses are present",
                        "Termination procedures and conditions are specified",
                        "Dispute resolution mechanisms are established"
                    ],
                    "warnings": [
                        "Review all financial obligations and payment terms carefully",
                        "Pay attention to liability limitations that may affect your rights",
                        "Note any automatic renewal or termination clauses",
                        "Consider consulting with a legal professional for complex matters",
                        "This is a demo analysis - full AI analysis coming soon"
                    ]
                }}
                '''
            
            # Parse the structured response
            analysis_result = self._parse_analysis_response(analysis_text)
            
            logger.info(f"Successfully analyzed document: {filename}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Document analysis error: {str(e)}")
            return {
                'summary': 'Analysis failed due to technical error',
                'key_points': ['Unable to analyze document at this time'],
                'warnings': ['Please try again later or contact support'],
                'error': str(e)
            }
    
    def answer_question(self, document_text: str, question: str) -> Dict:
        """
        Answer specific questions about the document
        
        Args:
            document_text: Full document text
            question: User's question
        
        Returns:
            Dictionary with answer and source information
        """
        
        try:
            # Prepare the Q&A prompt
            prompt = self.qa_prompt.format(
                document_text=document_text[:8000],  # Limit text length
                question=question
            )
            
            # Generate answer
            if self.use_gemini_api:
                answer_text = self._call_gemini_api(prompt)
            else:
                # Mock response for Q&A
                answer_text = f'''
                {{
                    "answer": "Based on the document content, I can see this is a legal document with {len(document_text)} characters. Your question '{question}' relates to the document content. This is a demo response - the full AI analysis system will provide detailed answers to your specific questions about clauses, terms, and conditions.",
                    "source_section": "Document Analysis (Demo Mode)",
                    "confidence": "medium"
                }}
                '''
            
            # Parse the response
            answer_result = self._parse_qa_response(answer_text)
            
            logger.info(f"Successfully answered question: {question[:50]}...")
            return answer_result
            
        except Exception as e:
            logger.error(f"Question answering error: {str(e)}")
            return {
                'answer': 'Unable to answer question due to technical error',
                'source_section': None,
                'confidence': 'low',
                'error': str(e)
            }
    
    def _get_analysis_prompt(self) -> str:
        """Get the prompt template for document analysis"""
        return """
You are a legal document analysis AI. Analyze the following legal document and provide a structured response.

Document: {filename}
Content: {document_text}

Please provide your analysis in the following JSON format:
{{
    "document_type": "The specific type of legal document (e.g., NDA, Employment Contract, Lease Agreement, Service Agreement, Terms of Service, Loan Agreement, Partnership Agreement, etc.)",
    "risk_score": <integer from 1 to 10, where 1=very favorable/safe, 5=neutral/balanced, 10=very risky/unfavorable>,
    "summary": "A clear, plain English summary of the document's main purpose and key terms (2-3 sentences)",
    "key_points": [
        "First important clause or term explained in simple language",
        "Second important clause or term explained in simple language",
        "Third important clause or term explained in simple language",
        "Fourth important clause or term explained in simple language",
        "Fifth important clause or term explained in simple language"
    ],
    "warnings": [
        "[HIGH] Any critical or very concerning clauses that could seriously disadvantage the user",
        "[MEDIUM] Moderately concerning terms or unusual clauses to be aware of",
        "[LOW] Minor things to note or understand"
    ]
}}

Focus on:
1. Making complex legal language understandable
2. Identifying the most important terms and obligations
3. Highlighting potential risks - prefix each warning with [HIGH], [MEDIUM], or [LOW]
4. Explaining what the user is agreeing to in plain English
5. Assigning an accurate risk_score based on overall favorability of the terms

Respond only with the JSON format above, no extra text.
"""
    
    def _get_qa_prompt(self) -> str:
        """Get the prompt template for question answering"""
        return """
You are a legal document Q&A assistant. Answer the user's question based on the provided document.

Document Content: {document_text}

User Question: {question}

Please provide your response in the following JSON format:
{{
    "answer": "Clear, direct answer to the user's question based on the document",
    "source_section": "The specific section or clause that contains this information (if identifiable)",
    "confidence": "high/medium/low based on how clearly the document addresses this question"
}}

Guidelines:
1. Only answer based on information actually present in the document
2. If the information is not in the document, clearly state that
3. Explain legal terms in plain English
4. Be specific and cite relevant sections when possible
5. If the answer is unclear or ambiguous, indicate that

Respond only with the JSON format above.
"""
    
    def _parse_analysis_response(self, response_text: str) -> Dict:
        """Parse AI response for document analysis"""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                
                # Validate required fields
                required_fields = ['summary', 'key_points', 'warnings']
                for field in required_fields:
                    if field not in result:
                        result[field] = []
                
                return result
            else:
                # Fallback parsing if JSON extraction fails
                return self._fallback_parse_analysis(response_text)
                
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response, using fallback")
            return self._fallback_parse_analysis(response_text)
    
    def _parse_qa_response(self, response_text: str) -> Dict:
        """Parse AI response for question answering"""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                
                # Validate required fields
                if 'answer' not in result:
                    result['answer'] = response_text
                if 'source_section' not in result:
                    result['source_section'] = None
                if 'confidence' not in result:
                    result['confidence'] = 'medium'
                
                return result
            else:
                # Fallback if JSON extraction fails
                return {
                    'answer': response_text,
                    'source_section': None,
                    'confidence': 'medium'
                }
                
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response for Q&A")
            return {
                'answer': response_text,
                'source_section': None,
                'confidence': 'low'
            }
    
    def _call_gemini_api(self, prompt: str) -> str:
        """Call Gemini API using REST API"""
        try:
            headers = {
                'Content-Type': 'application/json',
            }
            
            data = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }]
            }
            
            # Make the API call
            url = f"{self.api_url}?key={self.gemini_api_key}"
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    if 'content' in result['candidates'][0] and 'parts' in result['candidates'][0]['content']:
                        return result['candidates'][0]['content']['parts'][0]['text']
                    else:
                        logger.error("Unexpected API response structure")
                        return "Error: Unexpected response format"
                else:
                    logger.error("No candidates in API response")
                    return "Error: No response generated"
            else:
                logger.error(f"API call failed with status {response.status_code}: {response.text[:500]}")
                if response.status_code == 404:
                    logger.error("404 likely means the model name is incorrect or not available in your region")
                return f"Error: API call failed ({response.status_code})"
                
        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            return f"Error: {str(e)}"
    
    def _fallback_parse_analysis(self, response_text: str) -> Dict:
        """Fallback parsing when JSON parsing fails"""
        return {
            'summary': response_text[:500] + "..." if len(response_text) > 500 else response_text,
            'key_points': [
                'Document analysis completed',
                'Please review the full response above',
                'Contact support if you need clarification'
            ],
            'warnings': [
                'Analysis format may not be optimal',
                'Please verify important details independently'
            ]
        }

# Global AI analyzer instance
ai_analyzer = AIAnalyzer()