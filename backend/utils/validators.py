import os
from werkzeug.datastructures import FileStorage
from typing import Tuple, Optional

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

def validate_pdf_file(file: FileStorage, max_size: int = 10485760) -> Tuple[bool, Optional[str]]:
    """
    Validate uploaded PDF file
    
    Args:
        file: Uploaded file object
        max_size: Maximum file size in bytes (default 10MB)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    
    # Check if file exists
    if not file or not file.filename:
        return False, "No file provided"
    
    # Check file extension
    if not file.filename.lower().endswith('.pdf'):
        return False, "Only PDF files are supported"
    
    # Check file size by seeking to end
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    if file_size > max_size:
        max_mb = max_size // (1024 * 1024)
        return False, f"File size exceeds {max_mb}MB limit"
    
    if file_size == 0:
        return False, "File is empty"
    
    # Try to detect file type using python-magic if available
    if HAS_MAGIC:
        try:
            file_content = file.read(1024)  # Read first 1KB
            file.seek(0)  # Reset to beginning
            
            mime_type = magic.from_buffer(file_content, mime=True)
            if mime_type != 'application/pdf':
                return False, "File is not a valid PDF"
        except Exception:
            # If magic fails, continue without MIME check
            pass
    
    return True, None

def validate_question(question: str, max_length: int = 1000) -> Tuple[bool, Optional[str]]:
    """
    Validate user question
    
    Args:
        question: User's question string
        max_length: Maximum question length
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    
    if not question or not question.strip():
        return False, "Question cannot be empty"
    
    question = question.strip()
    
    if len(question) > max_length:
        return False, f"Question exceeds {max_length} character limit"
    
    # Check for potentially malicious content
    suspicious_patterns = ['<script', 'javascript:', 'data:', 'vbscript:']
    question_lower = question.lower()
    
    for pattern in suspicious_patterns:
        if pattern in question_lower:
            return False, "Question contains invalid content"
    
    return True, None

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    
    if not filename:
        return "document.pdf"
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext
    
    return filename