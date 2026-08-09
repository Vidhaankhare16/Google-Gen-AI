import io
import os
import base64
import logging
import requests
from typing import Tuple, Optional
import PyPDF2
import pdfplumber
from werkzeug.datastructures import FileStorage

from config import Config
from services import genai_backend

logger = logging.getLogger(__name__)

class PDFProcessor:
    """
    Service for extracting text from PDF documents
    Uses multiple libraries for better extraction reliability
    """
    
    def __init__(self):
        self.max_pages = 50  # Limit for prototype
        self.min_text_length = 10  # Minimum text length to consider valid
    
    def extract_text(self, file: FileStorage) -> Tuple[bool, str, Optional[str]]:
        """
        Extract text from PDF file
        
        Args:
            file: Uploaded PDF file
        
        Returns:
            Tuple of (success, extracted_text, error_message)
        """
        
        try:
            # Reset file pointer to beginning
            file.seek(0)
            
            # Try pdfplumber first (better for complex layouts)
            success, text, error = self._extract_with_pdfplumber(file)
            
            if success and len(text.strip()) >= self.min_text_length:
                logger.info(f"Successfully extracted {len(text)} characters using pdfplumber")
                return True, text, None
            
            # Fallback to PyPDF2
            file.seek(0)
            success, text, error = self._extract_with_pypdf2(file)
            
            if success and len(text.strip()) >= self.min_text_length:
                logger.info(f"Successfully extracted {len(text)} characters using PyPDF2")
                return True, text, None
            
            # Fallback: use Gemini Vision OCR for scanned/image-based PDFs
            if genai_backend.is_vertex() or Config.GEMINI_API_KEY:
                file.seek(0)
                success, text, error = self._extract_with_gemini_vision(file)
                if success and len(text.strip()) >= self.min_text_length:
                    logger.info(f"Successfully extracted {len(text)} characters using Gemini Vision OCR")
                    return True, text, None

            return False, "", "Document appears to be a scanned PDF with no extractable text"

        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            return False, "", f"Error processing PDF: {str(e)}"
    
    def _extract_with_pdfplumber(self, file: FileStorage) -> Tuple[bool, str, Optional[str]]:
        """
        Extract text using pdfplumber (better for tables and complex layouts)
        
        Args:
            file: PDF file object
        
        Returns:
            Tuple of (success, text, error_message)
        """
        
        try:
            file_bytes = io.BytesIO(file.read())
            extracted_text = []
            
            with pdfplumber.open(file_bytes) as pdf:
                total_pages = len(pdf.pages)
                
                if total_pages > self.max_pages:
                    logger.warning(f"PDF has {total_pages} pages, limiting to {self.max_pages}")
                
                pages_to_process = min(total_pages, self.max_pages)
                
                for page_num in range(pages_to_process):
                    try:
                        page = pdf.pages[page_num]
                        text = page.extract_text()
                        
                        if text:
                            extracted_text.append(f"--- Page {page_num + 1} ---\n{text}\n")
                        else:
                            logger.warning(f"No text found on page {page_num + 1}")
                            
                    except Exception as e:
                        logger.warning(f"Error extracting page {page_num + 1}: {str(e)}")
                        continue
                
                full_text = "\n".join(extracted_text)
                
                if len(full_text.strip()) < self.min_text_length:
                    return False, "", "No readable text found in PDF"
                
                return True, full_text, None
                
        except Exception as e:
            logger.error(f"pdfplumber extraction error: {str(e)}")
            return False, "", f"pdfplumber error: {str(e)}"
    
    def _extract_with_pypdf2(self, file: FileStorage) -> Tuple[bool, str, Optional[str]]:
        """
        Extract text using PyPDF2 (fallback method)
        
        Args:
            file: PDF file object
        
        Returns:
            Tuple of (success, text, error_message)
        """
        
        try:
            file_bytes = io.BytesIO(file.read())
            extracted_text = []
            
            pdf_reader = PyPDF2.PdfReader(file_bytes)
            total_pages = len(pdf_reader.pages)
            
            if total_pages > self.max_pages:
                logger.warning(f"PDF has {total_pages} pages, limiting to {self.max_pages}")
            
            pages_to_process = min(total_pages, self.max_pages)
            
            for page_num in range(pages_to_process):
                try:
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    
                    if text:
                        extracted_text.append(f"--- Page {page_num + 1} ---\n{text}\n")
                    else:
                        logger.warning(f"No text found on page {page_num + 1}")
                        
                except Exception as e:
                    logger.warning(f"Error extracting page {page_num + 1}: {str(e)}")
                    continue
            
            full_text = "\n".join(extracted_text)
            
            if len(full_text.strip()) < self.min_text_length:
                return False, "", "No readable text found in PDF"
            
            return True, full_text, None
            
        except Exception as e:
            logger.error(f"PyPDF2 extraction error: {str(e)}")
            return False, "", f"PyPDF2 error: {str(e)}"
    
    def _extract_with_gemini_vision(self, file: FileStorage) -> Tuple[bool, str, Optional[str]]:
        """Extract text from scanned PDFs using Gemini Vision API (OCR fallback)"""
        try:
            import fitz  # PyMuPDF

            # Same backend selection as the analyzer (Vertex AI or the AI Studio API).
            model = os.getenv('GEMINI_VISION_MODEL') or os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
            file_bytes = io.BytesIO(file.read())
            doc = fitz.open(stream=file_bytes, filetype="pdf")

            total_pages = len(doc)
            pages_to_process = min(total_pages, self.max_pages)
            extracted_text = []

            for page_num in range(pages_to_process):
                try:
                    page = doc[page_num]
                    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
                    img_base64 = base64.b64encode(pix.tobytes("png")).decode("utf-8")

                    payload = {
                        "contents": [{
                            "role": "user",   # required by Vertex AI, ignored by AI Studio
                            "parts": [
                                {"text": "Extract all text from this document page. Return only the extracted text, preserving the original layout."},
                                {"inline_data": {"mime_type": "image/png", "data": img_base64}}
                            ]
                        }]
                    }

                    api_url, headers = genai_backend.request_args(model)
                    response = requests.post(api_url, headers=headers, json=payload, timeout=60)

                    if response.status_code == 200:
                        result = response.json()
                        candidates = result.get("candidates", [])
                        if candidates:
                            text = candidates[0]["content"]["parts"][0]["text"]
                            extracted_text.append(f"--- Page {page_num + 1} ---\n{text}\n")
                            logger.info(f"Gemini Vision OCR: extracted page {page_num + 1}")
                    else:
                        logger.error(f"Gemini Vision API error {response.status_code}: {response.text}")

                except Exception as e:
                    logger.warning(f"Vision OCR failed for page {page_num + 1}: {str(e)}")
                    continue

            doc.close()
            full_text = "\n".join(extracted_text)

            if len(full_text.strip()) < self.min_text_length:
                return False, "", "Gemini Vision could not extract text from this document"

            return True, full_text, None

        except ImportError:
            return False, "", "PyMuPDF not available for vision-based extraction"
        except Exception as e:
            logger.error(f"Gemini Vision extraction error: {str(e)}")
            return False, "", f"Vision extraction error: {str(e)}"

    def extract_text_from_bytes(self, pdf_bytes: bytes) -> str:
        """
        Extract text from PDF bytes (for WhatsApp integration)
        
        Args:
            pdf_bytes: PDF file content as bytes
        
        Returns:
            Extracted text content
        
        Raises:
            Exception: If text extraction fails
        """
        try:
            # Try pdfplumber first
            try:
                file_obj = io.BytesIO(pdf_bytes)
                extracted_text = []
                
                with pdfplumber.open(file_obj) as pdf:
                    total_pages = len(pdf.pages)
                    pages_to_process = min(total_pages, self.max_pages)
                    
                    for page_num in range(pages_to_process):
                        try:
                            page = pdf.pages[page_num]
                            text = page.extract_text()
                            if text:
                                extracted_text.append(f"--- Page {page_num + 1} ---\n{text}\n")
                        except Exception as e:
                            logger.warning(f"Error extracting page {page_num + 1}: {str(e)}")
                            continue
                    
                    full_text = "\n".join(extracted_text)
                    if len(full_text.strip()) >= self.min_text_length:
                        logger.info(f"Successfully extracted {len(full_text)} characters from bytes using pdfplumber")
                        return full_text
                        
            except Exception as e:
                logger.warning(f"pdfplumber failed on bytes: {str(e)}")
            
            # Fallback to PyPDF2
            try:
                file_obj = io.BytesIO(pdf_bytes)
                extracted_text = []
                
                pdf_reader = PyPDF2.PdfReader(file_obj)
                total_pages = len(pdf_reader.pages)
                pages_to_process = min(total_pages, self.max_pages)
                
                for page_num in range(pages_to_process):
                    try:
                        page = pdf_reader.pages[page_num]
                        text = page.extract_text()
                        if text:
                            extracted_text.append(f"--- Page {page_num + 1} ---\n{text}\n")
                    except Exception as e:
                        logger.warning(f"Error extracting page {page_num + 1}: {str(e)}")
                        continue
                
                full_text = "\n".join(extracted_text)
                if len(full_text.strip()) >= self.min_text_length:
                    logger.info(f"Successfully extracted {len(full_text)} characters from bytes using PyPDF2")
                    return full_text
                    
            except Exception as e:
                logger.warning(f"PyPDF2 failed on bytes: {str(e)}")
            
            # If both methods fail
            raise Exception("Document appears to be empty or contains only images")
            
        except Exception as e:
            logger.error(f"PDF bytes extraction failed: {str(e)}")
            raise Exception(f"Failed to extract text from PDF: {str(e)}")

    def get_document_info(self, file: FileStorage) -> dict:
        """
        Get basic information about the PDF document
        
        Args:
            file: PDF file object
        
        Returns:
            Dictionary with document information
        """
        
        try:
            file.seek(0)
            file_bytes = io.BytesIO(file.read())
            
            with pdfplumber.open(file_bytes) as pdf:
                return {
                    'total_pages': len(pdf.pages),
                    'metadata': pdf.metadata or {},
                    'file_size': len(file_bytes.getvalue())
                }
                
        except Exception as e:
            logger.error(f"Error getting document info: {str(e)}")
            return {
                'total_pages': 0,
                'metadata': {},
                'file_size': 0,
                'error': str(e)
            }

# Global PDF processor instance
pdf_processor = PDFProcessor()