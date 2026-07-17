import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Google Cloud Configuration
    GOOGLE_CLOUD_PROJECT = os.getenv('GOOGLE_CLOUD_PROJECT')
    VERTEX_AI_LOCATION = os.getenv('VERTEX_AI_LOCATION', 'us-central1')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # Application Configuration
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 10485760))  # 10MB default
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', 3600))  # 1 hour default
    
    # Server Configuration
    PORT = int(os.getenv('PORT', 5000))
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    @staticmethod
    def validate_config():
        """Validate that required configuration is present"""
        if not Config.GEMINI_API_KEY:
            raise ValueError("Missing required environment variable: GEMINI_API_KEY")
        return True