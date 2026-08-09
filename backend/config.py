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
    
    # Which Gemini backend to use: 'vertex' (OAuth via the service account) or 'studio'
    # (an API key). Left unset, services.genai_backend infers it from what's configured.
    AI_BACKEND = os.getenv('AI_BACKEND', '')

    @staticmethod
    def validate_config():
        """
        Validate that a usable Gemini backend is configured.

        Either an AI Studio API key, or a GCP project to call Vertex AI in — on Cloud Run
        the latter needs no key at all, since the attached service account authenticates.
        """
        using_vertex = Config.AI_BACKEND.lower() == 'vertex' or (
            not Config.GEMINI_API_KEY and bool(Config.GOOGLE_CLOUD_PROJECT)
        )
        if using_vertex:
            if not Config.GOOGLE_CLOUD_PROJECT:
                raise ValueError("AI_BACKEND=vertex requires GOOGLE_CLOUD_PROJECT to be set")
            return True

        if not Config.GEMINI_API_KEY:
            raise ValueError(
                "No Gemini backend configured: set GEMINI_API_KEY, or set AI_BACKEND=vertex "
                "with GOOGLE_CLOUD_PROJECT to call Vertex AI."
            )
        return True