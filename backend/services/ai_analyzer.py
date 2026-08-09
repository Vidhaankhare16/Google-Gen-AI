import logging
import json
import re
from typing import Dict, List, Optional, Tuple
import os
import requests
import json

from config import Config
from services import rag_service, genai_backend

logger = logging.getLogger(__name__)

# With RAG grounding + Gemini's large context window we no longer truncate to 8000 chars.
# Analysis still caps very long documents generously; Q&A uses retrieved chunks instead.
ANALYSIS_DOC_CHARS = int(os.getenv("ANALYSIS_DOC_CHARS", "40000"))
QA_FALLBACK_DOC_CHARS = int(os.getenv("QA_FALLBACK_DOC_CHARS", "12000"))

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
        """
        Pick the Gemini backend (Vertex AI or the AI Studio API) and record the model.

        The URL is resolved per call rather than cached here: on Vertex the request also
        needs a bearer token that expires, so `genai_backend` builds both together.
        """
        try:
            self.model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
            self.use_gemini_api = genai_backend.is_vertex() or bool(self.gemini_api_key)
            if self.use_gemini_api:
                logger.info(f"✅ Gemini ready — model {self.model} via {genai_backend.describe()}")
            else:
                logger.info("No Gemini backend configured, using mock responses")

        except Exception as e:
            logger.error(f"Failed to initialize AI clients: {str(e)}")
            self.use_gemini_api = False
            logger.info("Falling back to mock responses")
    
    def analyze_document(self, text: str, filename: str = None, document_id: str = None) -> Dict:
        """
        Analyze legal document and extract key information, grounded in the Indian legal KB.

        Args:
            text: Document text content
            filename: Original filename (optional)
            document_id: Storage id (unused for analysis grounding; kept for symmetry)

        Returns:
            Dictionary with analysis results (plus a 'sources' list of legal citations)
        """

        try:
            # Retrieve relevant Indian law (red-flags, statutes, precedents) to ground the
            # analysis, probing across the whole document rather than just its preamble.
            grounding = rag_service.retrieve_for_document(text)
            legal_context = grounding.format_context() if grounding else ""
            sources = grounding.citations() if grounding else []

            # Prepare the prompt with the (untruncated-ish) document text + retrieved legal context.
            prompt = self.analysis_prompt.format(
                document_text=text[:ANALYSIS_DOC_CHARS],
                filename=filename or "document",
                legal_context=legal_context or "(no external legal context retrieved)",
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
            analysis_result['sources'] = sources

            logger.info(f"Successfully analyzed document: {filename} "
                        f"(grounded on {len(sources)} legal sources)")
            return analysis_result

        except Exception as e:
            logger.error(f"Document analysis error: {str(e)}")
            return {
                'summary': 'Analysis failed due to technical error',
                'key_points': ['Unable to analyze document at this time'],
                'warnings': ['Please try again later or contact support'],
                'sources': [],
                'error': str(e)
            }
    
    def answer_question(self, document_text: str, question: str, document_id: str = None) -> Dict:
        """
        Answer a question about the document using hybrid RAG: the question is used to retrieve the
        most relevant chunks of the uploaded document AND relevant Indian law/precedent, which are
        fed to the model instead of the whole (truncated) document.

        Args:
            document_text: Full document text (fallback if retrieval is unavailable)
            question: User's question
            document_id: Storage id, used to retrieve this document's chunks

        Returns:
            Dictionary with answer, source_section, confidence, and a 'sources' citation list
        """

        try:
            retr = rag_service.retrieve(question, document_id=document_id,
                                        include_doc=True, include_kb=True)

            # Document context: retrieved chunks if available, else fall back to (capped) full text.
            if retr and retr.doc_hits:
                document_context = "\n\n".join(f"[D{i}] {h.text.strip()}"
                                               for i, h in enumerate(retr.doc_hits, 1))
            else:
                document_context = document_text[:QA_FALLBACK_DOC_CHARS]

            legal_context = ""
            sources = []
            if retr:
                legal_context = retr.format_kb()
                sources = retr.citations()

            prompt = self.qa_prompt.format(
                document_context=document_context,
                legal_context=legal_context or "(no external legal context retrieved)",
                question=question,
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
            answer_result['sources'] = sources

            logger.info(f"Successfully answered question: {question[:50]}... "
                        f"(doc_hits={len(retr.doc_hits) if retr else 0}, "
                        f"legal_sources={len(sources)})")
            return answer_result

        except Exception as e:
            logger.error(f"Question answering error: {str(e)}")
            return {
                'answer': 'Unable to answer question due to technical error',
                'source_section': None,
                'confidence': 'low',
                'sources': [],
                'error': str(e)
            }
    
    def _get_analysis_prompt(self) -> str:
        """Get the prompt template for document analysis"""
        return """
You are a legal document analysis AI specializing in Indian law. Analyze the following legal
document and provide a structured response. Use the RETRIEVED INDIAN LAW & PRECEDENT below to
ground your risk assessment and warnings in actual statutes and case law wherever relevant — when
a clause relates to a provided law, reference it briefly in plain English (e.g. "penalty clauses
are only enforceable as reasonable compensation under Section 74 of the Indian Contract Act").

Document: {filename}
Content: {document_text}

RETRIEVED INDIAN LAW & PRECEDENT (grounding — cite where relevant, do not invent laws):
{legal_context}

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
You are a legal document Q&A assistant specializing in Indian law. Answer the user's question
using the retrieved excerpts from THEIR document below. For questions about legality, fairness, or
rights, also use the retrieved Indian law & precedent to ground your answer and cite it plainly.

RETRIEVED EXCERPTS FROM THE USER'S DOCUMENT:
{document_context}

RELEVANT INDIAN LAW & PRECEDENT (use for legal grounding; do not invent laws):
{legal_context}

User Question: {question}

Please provide your response in the following JSON format:
{{
    "answer": "Clear, direct answer. Base facts about the contract strictly on the document excerpts. For legal points, reference the relevant Indian law/precedent by name.",
    "source_section": "The specific clause in the user's document (or law) that supports this, if identifiable",
    "confidence": "high/medium/low based on how clearly the excerpts address this question"
}}

Guidelines:
1. Base statements about the contract only on the provided document excerpts.
2. If the document excerpts do not contain the answer, clearly say so (don't guess the contract's contents).
3. Explain legal terms in plain English; cite Indian statutes/precedent only from the provided legal context.
4. If the answer is unclear or ambiguous, indicate that.

Respond only with the JSON format above.
"""
    
    @staticmethod
    def _strip_fence(text: str) -> str:
        """Drop a surrounding ```json … ``` fence if the model added one anyway."""
        stripped = (text or "").strip()
        if stripped.startswith("```"):
            stripped = re.sub(r'^```[a-zA-Z]*\s*', '', stripped)
            stripped = re.sub(r'\s*```$', '', stripped)
        return stripped.strip()

    def _load_json(self, response_text: str):
        """Best-effort JSON parse of a model reply; None if it isn't recoverable."""
        cleaned = self._strip_fence(response_text)
        candidates = [cleaned]
        braces = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if braces:
            candidates.append(braces.group())

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        return None

    def _parse_analysis_response(self, response_text: str) -> Dict:
        """Parse AI response for document analysis"""
        result = self._load_json(response_text)
        if result is None:
            logger.warning("Failed to parse analysis JSON, using fallback")
            return self._fallback_parse_analysis(self._strip_fence(response_text))

        for field in ('summary', 'key_points', 'warnings'):
            if field not in result:
                result[field] = [] if field != 'summary' else ''
        return result

    def _parse_qa_response(self, response_text: str) -> Dict:
        """Parse AI response for question answering"""
        result = self._load_json(response_text)

        if result is None:
            # Salvage the answer text rather than showing the user a raw JSON blob.
            cleaned = self._strip_fence(response_text)
            salvaged = re.search(r'"answer"\s*:\s*"(.*?)"\s*(?:,\s*"(?:source_section|confidence)"|\}\s*$)',
                                 cleaned, re.DOTALL)
            answer = salvaged.group(1).replace('\\n', '\n').replace('\\"', '"') if salvaged else cleaned
            logger.warning("Failed to parse Q&A JSON; returning salvaged answer text")
            return {'answer': answer, 'source_section': None, 'confidence': 'low'}

        result.setdefault('answer', self._strip_fence(response_text))
        result.setdefault('source_section', None)
        if result.get('confidence') not in ('high', 'medium', 'low'):
            result['confidence'] = 'medium'
        return result
    
    def _call_gemini_api(self, prompt: str, max_retries: int = 3, as_json: bool = True) -> str:
        """
        Call the Gemini REST API, retrying transient 429/500/503 errors with backoff.

        Both prompts ask for JSON, so we request `application/json` explicitly. Without it
        the model wraps its reply in a ```json fence and is free to leave unescaped quotes
        inside string values, which breaks parsing and leaks the raw fence into the answer
        the user reads.
        """
        import time
        # `role` is optional on the AI Studio API but required by Vertex AI, which rejects
        # a role-less turn with 400 "Please use a valid role". Sending it always is valid
        # for both backends.
        data = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
        if as_json:
            data["generationConfig"] = {"responseMimeType": "application/json"}

        last_status = None
        for attempt in range(max_retries):
            # Rebuilt each attempt so an expired Vertex bearer token is refreshed on retry.
            url, headers = genai_backend.request_args(self.model)
            try:
                response = requests.post(url, headers=headers, json=data, timeout=60)
            except Exception as e:
                logger.warning(f"Gemini request error (attempt {attempt+1}): {e}")
                time.sleep(2 * (attempt + 1))
                continue

            if response.status_code == 200:
                result = response.json()
                candidates = result.get('candidates') or []
                if candidates and 'content' in candidates[0] and 'parts' in candidates[0]['content']:
                    return candidates[0]['content']['parts'][0]['text']
                logger.error("Unexpected API response structure / no candidates")
                return "Error: No response generated"

            last_status = response.status_code
            # Retry transient overload/rate-limit/server errors; fail fast on the rest.
            if response.status_code in (429, 500, 503) and attempt < max_retries - 1:
                wait = 2 * (attempt + 1)
                logger.warning(f"Gemini {response.status_code} (attempt {attempt+1}); retrying in {wait}s")
                time.sleep(wait)
                continue

            logger.error(f"API call failed with status {response.status_code}: {response.text[:500]}")
            if response.status_code == 404:
                logger.error("404 likely means the model name is incorrect or not available in your region")
            break

        return f"Error: API call failed ({last_status})"
    
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