import re
import hashlib
import secrets
import time
from typing import Dict, Optional, Set
from functools import wraps
from flask import request, jsonify, g
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests: Dict[str, list] = {}
        self.blocked_ips: Set[str] = set()
    
    def is_allowed(self, identifier: str, max_requests: int = 10, window_seconds: int = 60) -> bool:
        """Check if request is allowed based on rate limits"""
        
        if identifier in self.blocked_ips:
            return False
        
        current_time = time.time()
        
        # Clean old requests
        if identifier in self.requests:
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if current_time - req_time < window_seconds
            ]
        else:
            self.requests[identifier] = []
        
        # Check rate limit
        if len(self.requests[identifier]) >= max_requests:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return False
        
        # Add current request
        self.requests[identifier].append(current_time)
        return True
    
    def block_ip(self, ip: str, duration: int = 3600):
        """Block an IP address for a duration"""
        self.blocked_ips.add(ip)
        logger.warning(f"Blocked IP {ip} for {duration} seconds")
        
        # TODO: In production, use a proper scheduler to unblock
        # For now, this is a simple in-memory implementation

# Global rate limiter instance
rate_limiter = RateLimiter()

def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """Rate limiting decorator"""
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Use IP address as identifier
            identifier = request.remote_addr or 'unknown'
            
            if not rate_limiter.is_allowed(identifier, max_requests, window_seconds):
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'message': 'Too many requests',
                        'details': f'Maximum {max_requests} requests per {window_seconds} seconds allowed'
                    }
                }), 429
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent XSS and injection attacks"""
    
    if not text:
        return ""
    
    # Remove potentially dangerous characters and patterns
    text = re.sub(r'<[^>]*>', '', text)  # Remove HTML tags
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)  # Remove javascript:
    text = re.sub(r'data:', '', text, flags=re.IGNORECASE)  # Remove data:
    text = re.sub(r'vbscript:', '', text, flags=re.IGNORECASE)  # Remove vbscript:
    
    # Limit length
    if len(text) > 10000:
        text = text[:10000]
    
    return text.strip()

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    
    if not filename:
        return "document.pdf"
    
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # Remove control characters
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
    
    return filename

def mask_pii(text: str) -> str:
    """Basic PII masking for document text"""
    
    if not text:
        return text
    
    # Email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    
    # Phone numbers (basic patterns)
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    text = re.sub(r'\(\d{3}\)\s*\d{3}[-.]?\d{4}', '[PHONE]', text)
    
    # Social Security Numbers
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
    
    # Credit card numbers (basic pattern)
    text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CREDIT_CARD]', text)
    
    return text

def generate_secure_token() -> str:
    """Generate a secure random token"""
    return secrets.token_urlsafe(32)

def hash_document_id(document_id: str) -> str:
    """Hash document ID for logging without exposing actual ID"""
    return hashlib.sha256(document_id.encode()).hexdigest()[:16]

def validate_request_size(max_size: int = 10485760):  # 10MB default
    """Validate request content length"""
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            content_length = request.content_length
            
            if content_length and content_length > max_size:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'REQUEST_TOO_LARGE',
                        'message': 'Request too large',
                        'details': f'Maximum request size is {max_size // (1024*1024)}MB'
                    }
                }), 413
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def require_https():
    """Decorator to require HTTPS in production"""
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip HTTPS check in development
            import os
            if os.environ.get('FLASK_ENV') == 'development':
                return f(*args, **kwargs)
            
            if not request.is_secure and request.headers.get('X-Forwarded-Proto') != 'https':
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'HTTPS_REQUIRED',
                        'message': 'HTTPS required',
                        'details': 'This endpoint requires a secure connection'
                    }
                }), 400
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def add_security_headers(response):
    """Add security headers to response"""
    
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Content Security Policy. Google Fonts is allowed explicitly: the UI's three
    # typefaces are served from fonts.googleapis.com (stylesheet) and fonts.gstatic.com
    # (the font files), and a bare 'self' policy silently drops both in production.
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "img-src 'self' data:; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "connect-src 'self'"
    )
    
    # HSTS (only in production with HTTPS)
    if request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    return response

class SecurityMonitor:
    """Monitor security events"""
    
    def __init__(self):
        self.suspicious_activities: Dict[str, int] = {}
        self.blocked_attempts: int = 0
    
    def log_suspicious_activity(self, ip: str, activity: str):
        """Log suspicious activity"""
        
        key = f"{ip}:{activity}"
        self.suspicious_activities[key] = self.suspicious_activities.get(key, 0) + 1
        
        logger.warning(f"Suspicious activity from {ip}: {activity}")
        
        # Auto-block after multiple suspicious activities
        if self.suspicious_activities[key] > 5:
            rate_limiter.block_ip(ip)
            self.blocked_attempts += 1
    
    def get_security_stats(self) -> Dict:
        """Get security statistics"""
        
        return {
            'suspicious_activities': len(self.suspicious_activities),
            'blocked_attempts': self.blocked_attempts,
            'blocked_ips': len(rate_limiter.blocked_ips)
        }

# Global security monitor
security_monitor = SecurityMonitor()

def detect_malicious_content(text: str) -> bool:
    """Detect potentially malicious content in text"""
    
    if not text:
        return False
    
    text_lower = text.lower()
    
    # Check for script injection attempts
    malicious_patterns = [
        '<script',
        'javascript:',
        'data:text/html',
        'vbscript:',
        'onload=',
        'onerror=',
        'eval(',
        'document.cookie',
        'window.location',
        'alert(',
    ]
    
    for pattern in malicious_patterns:
        if pattern in text_lower:
            return True
    
    return False

def log_security_event(event_type: str, details: str, ip: str = None):
    """Log security events for monitoring"""
    
    ip = ip or request.remote_addr or 'unknown'
    
    logger.warning(f"Security Event [{event_type}] from {ip}: {details}")
    
    # Track in security monitor
    security_monitor.log_suspicious_activity(ip, event_type)