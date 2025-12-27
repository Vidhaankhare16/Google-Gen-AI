import logging
import traceback
from functools import wraps
from flask import jsonify, request
from typing import Dict, Any, Optional, Callable
import time

logger = logging.getLogger(__name__)

class APIError(Exception):
    """Custom API error class"""
    
    def __init__(self, message: str, code: str = 'API_ERROR', status_code: int = 500, details: str = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or message
        super().__init__(self.message)

class ValidationError(APIError):
    """Validation error"""
    
    def __init__(self, message: str, details: str = None):
        super().__init__(message, 'VALIDATION_ERROR', 400, details)

class ProcessingError(APIError):
    """Processing error"""
    
    def __init__(self, message: str, details: str = None):
        super().__init__(message, 'PROCESSING_ERROR', 500, details)

class RateLimitError(APIError):
    """Rate limit error"""
    
    def __init__(self, message: str = 'Rate limit exceeded', details: str = None):
        super().__init__(message, 'RATE_LIMIT_ERROR', 429, details)

def handle_api_error(error: APIError) -> tuple:
    """Handle API errors and return formatted response"""
    
    logger.error(f"API Error: {error.code} - {error.message}")
    
    return jsonify({
        'success': False,
        'error': {
            'code': error.code,
            'message': error.message,
            'details': error.details
        }
    }), error.status_code

def handle_unexpected_error(error: Exception) -> tuple:
    """Handle unexpected errors"""
    
    logger.error(f"Unexpected error: {str(error)}")
    logger.error(traceback.format_exc())
    
    # Don't expose internal error details in production
    if logger.level == logging.DEBUG:
        details = str(error)
    else:
        details = 'An unexpected error occurred. Please try again later.'
    
    return jsonify({
        'success': False,
        'error': {
            'code': 'INTERNAL_ERROR',
            'message': 'Internal server error',
            'details': details
        }
    }), 500

def with_error_handling(f: Callable) -> Callable:
    """Decorator to add error handling to route functions"""
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except APIError as e:
            return handle_api_error(e)
        except Exception as e:
            return handle_unexpected_error(e)
    
    return decorated_function

def with_request_logging(f: Callable) -> Callable:
    """Decorator to add request logging"""
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")
        
        try:
            result = f(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"Request completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Request failed after {duration:.3f}s: {str(e)}")
            raise
    
    return decorated_function

def with_retry(max_attempts: int = 3, delay: float = 1.0):
    """Decorator to add retry logic to functions"""
    
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_attempts} attempts failed")
            
            raise last_exception
        
        return decorated_function
    return decorator

class ErrorTracker:
    """Simple error tracking for monitoring"""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.last_errors: Dict[str, float] = {}
    
    def track_error(self, error_code: str, error_message: str):
        """Track an error occurrence"""
        
        self.error_counts[error_code] = self.error_counts.get(error_code, 0) + 1
        self.last_errors[error_code] = time.time()
        
        # Log high-frequency errors
        if self.error_counts[error_code] > 10:
            logger.warning(f"High frequency error: {error_code} occurred {self.error_counts[error_code]} times")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        
        return {
            'error_counts': self.error_counts.copy(),
            'total_errors': sum(self.error_counts.values()),
            'unique_errors': len(self.error_counts)
        }
    
    def reset_stats(self):
        """Reset error statistics"""
        
        self.error_counts.clear()
        self.last_errors.clear()

# Global error tracker instance
error_tracker = ErrorTracker()

def validate_file_upload(file) -> None:
    """Validate file upload with detailed error messages"""
    
    if not file:
        raise ValidationError('No file provided', 'Please select a file to upload')
    
    if file.filename == '':
        raise ValidationError('Empty filename', 'Please select a valid file')
    
    if not file.filename.lower().endswith('.pdf'):
        raise ValidationError(
            'Invalid file type', 
            'Only PDF files are supported. Please upload a PDF document.'
        )
    
    # Check file size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    max_size = 10 * 1024 * 1024  # 10MB
    if file_size > max_size:
        raise ValidationError(
            'File too large',
            f'File size ({file_size // (1024*1024)}MB) exceeds the maximum limit of 10MB'
        )
    
    if file_size == 0:
        raise ValidationError('Empty file', 'The uploaded file is empty')

def validate_question(question: str) -> None:
    """Validate question input"""
    
    if not question or not question.strip():
        raise ValidationError('Empty question', 'Please provide a question about the document')
    
    question = question.strip()
    
    if len(question) > 1000:
        raise ValidationError(
            'Question too long',
            'Questions must be less than 1000 characters'
        )
    
    if len(question) < 3:
        raise ValidationError(
            'Question too short',
            'Please provide a more detailed question'
        )
    
    # Check for potentially malicious content
    suspicious_patterns = ['<script', 'javascript:', 'data:', 'vbscript:']
    question_lower = question.lower()
    
    for pattern in suspicious_patterns:
        if pattern in question_lower:
            raise ValidationError(
                'Invalid question content',
                'Question contains invalid characters or content'
            )