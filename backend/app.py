from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge
import os
import logging
from datetime import datetime
import traceback

from config import Config
from services.pdf_processor import pdf_processor
from services.ai_analyzer import ai_analyzer
from services.document_storage import document_storage
from utils.error_handler import (
    APIError, ValidationError, ProcessingError,
    handle_api_error, handle_unexpected_error,
    with_error_handling, with_request_logging,
    error_tracker, validate_file_upload, validate_question
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='')
    
    # Load configuration
    app.config.from_object(Config)
    
    # Validate configuration
    try:
        Config.validate_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise

    # Wire vector-store eviction: when a stored document is deleted or expires, drop its chunks too.
    from services import rag_service
    document_storage.on_evict = rag_service.delete_document

    # Warm the retriever in the background. Loading InLegalBERT and opening the Chroma
    # index takes tens of seconds; doing it in a daemon thread means the port starts
    # listening immediately (so Cloud Run's startup probe passes) while the model loads
    # in parallel, instead of the first user's upload paying the whole cost.
    if os.getenv('RAG_WARMUP', '1') != '0':
        import threading

        def _warm():
            try:
                logger.info("Warming RAG retriever...")
                if rag_service.available():
                    logger.info("✅ RAG retriever warm")
                else:
                    logger.warning("⚠️ RAG retriever unavailable after warm-up")
            except Exception as e:
                logger.warning(f"RAG warm-up failed (will retry on first request): {e}")

        threading.Thread(target=_warm, name='rag-warmup', daemon=True).start()
    
    # In production the frontend is served by Flask (same origin), so CORS only
    # matters for external API callers. In development we proxy from port 3000.
    if Config.FLASK_ENV == 'production':
        CORS(app)
    else:
        CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])
    
    # Register document routes (delete / info / stats). The frontend's "Erase now"
    # button calls DELETE /api/document/delete/<id>, so the prefix must match.
    from api.document_routes import document_bp
    app.register_blueprint(document_bp, url_prefix='/api/document')
    logger.info("✅ Document routes registered")

    # Register WhatsApp blueprint
    try:
        from api.whatsapp_routes import whatsapp_bp
        app.register_blueprint(whatsapp_bp, url_prefix='/whatsapp')
        logger.info("✅ WhatsApp routes registered")
    except ImportError as e:
        logger.warning(f"⚠️ WhatsApp routes not available: {e}")
    
    # Import security utilities
    from utils.security import add_security_headers, rate_limit, require_https
    
    # Add security headers to all responses
    @app.after_request
    def after_request(response):
        return add_security_headers(response)
    
    # Set maximum file size
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_FILE_SIZE
    
    # Error handlers
    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(e):
        return jsonify({
            'success': False,
            'error': {
                'code': 'FILE_TOO_LARGE',
                'message': f'File size exceeds maximum limit of {Config.MAX_FILE_SIZE // (1024*1024)}MB',
                'details': 'Please upload a smaller file'
            }
        }), 413
    
    @app.errorhandler(400)
    def handle_bad_request(e):
        return jsonify({
            'success': False,
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'Invalid request format',
                'details': str(e.description) if hasattr(e, 'description') else 'Please check your request'
            }
        }), 400
    
    @app.errorhandler(500)
    def handle_internal_error(e):
        logger.error(f"Internal server error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An internal server error occurred',
                'details': 'Please try again later'
            }
        }), 500
    
    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint for monitoring and load balancers"""
        try:
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'version': '1.0.0',
                'service': 'legal-ease-backend'
            }), 200
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                'status': 'unhealthy',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'error': str(e)
            }), 503
    
    # Document analysis endpoint
    @app.route('/api/analyze', methods=['POST'])
    @rate_limit(max_requests=5, window_seconds=300)  # 5 requests per 5 minutes
    @require_https()
    def analyze_document():
        """Upload and analyze a legal document"""
        try:
            # Import services
            from services.pdf_processor import pdf_processor
            from services.ai_analyzer import ai_analyzer
            from services.document_storage import document_storage
            from utils.validators import validate_pdf_file, sanitize_filename
            
            # Validate request
            if 'file' not in request.files:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'NO_FILE',
                        'message': 'No file provided',
                        'details': 'Please select a PDF file to upload'
                    }
                }), 400
            
            file = request.files['file']
            
            # Validate file
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'EMPTY_FILENAME',
                        'message': 'No file selected',
                        'details': 'Please select a valid PDF file'
                    }
                }), 400
            
            # Validate PDF file
            is_valid, error_message = validate_pdf_file(file, Config.MAX_FILE_SIZE)
            if not is_valid:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'INVALID_FILE',
                        'message': error_message,
                        'details': 'Please upload a valid PDF document'
                    }
                }), 400
            
            # Sanitize filename
            safe_filename = sanitize_filename(file.filename)
            logger.info(f"Processing document: {safe_filename}")
            
            # Extract text from PDF
            success, extracted_text, pdf_error = pdf_processor.extract_text(file)
            
            if not success:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'PDF_EXTRACTION_ERROR',
                        'message': 'Failed to extract text from PDF',
                        'details': pdf_error or 'Unable to read PDF content'
                    }
                }), 400
            
            # Store document text
            document_id = document_storage.store_document(extracted_text, safe_filename)

            # Index the uploaded document into the vector store (for retrieval-based Q&A)
            from services import rag_service
            rag_service.index_document(document_id, extracted_text)

            # Analyze document with AI (grounded on the legal knowledge base)
            analysis_result = ai_analyzer.analyze_document(extracted_text, safe_filename, document_id)

            # Update document with analysis results
            document_storage.update_analysis(document_id, analysis_result)

            # Prepare response
            response_data = {
                'success': True,
                'analysis': {
                    'summary': analysis_result.get('summary', 'Analysis completed'),
                    'key_points': analysis_result.get('key_points', []),
                    'warnings': analysis_result.get('warnings', []),
                    'document_id': document_id,
                    'risk_score': analysis_result.get('risk_score', 5),
                    'document_type': analysis_result.get('document_type', 'Legal Document'),
                    'sources': analysis_result.get('sources', []),
                },
                'document_info': {
                    'filename': safe_filename,
                    'text_length': len(extracted_text),
                    'processed_at': datetime.utcnow().isoformat() + 'Z'
                }
            }
            
            logger.info(f"Successfully analyzed document {document_id}")
            return jsonify(response_data), 200
            
        except Exception as e:
            logger.error(f"Document analysis error: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({
                'success': False,
                'error': {
                    'code': 'ANALYSIS_ERROR',
                    'message': 'Failed to analyze document',
                    'details': 'Please try again or contact support'
                }
            }), 500
    
    # Question answering endpoint
    @app.route('/api/question', methods=['POST'])
    @rate_limit(max_requests=20, window_seconds=300)  # 20 questions per 5 minutes
    @require_https()
    def answer_question():
        """Answer questions about an analyzed document"""
        try:
            # Import services
            from services.ai_analyzer import ai_analyzer
            from services.document_storage import document_storage
            from utils.validators import validate_question
            
            # Validate request
            if not request.is_json:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'INVALID_CONTENT_TYPE',
                        'message': 'Request must be JSON',
                        'details': 'Please send a JSON request with question and document_id'
                    }
                }), 400
            
            data = request.get_json()
            
            # Validate required fields
            if not data or 'question' not in data or 'document_id' not in data:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'MISSING_FIELDS',
                        'message': 'Missing required fields',
                        'details': 'Please provide both question and document_id'
                    }
                }), 400
            
            question = data.get('question', '').strip()
            document_id = data.get('document_id', '').strip()
            
            # Validate question
            is_valid, error_message = validate_question(question)
            if not is_valid:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'INVALID_QUESTION',
                        'message': error_message,
                        'details': 'Please provide a valid question about the document'
                    }
                }), 400
            
            # Retrieve document
            document = document_storage.get_document(document_id)
            if not document:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'DOCUMENT_NOT_FOUND',
                        'message': 'Document not found or expired',
                        'details': 'Please upload the document again or check the document ID'
                    }
                }), 404
            
            # Get document text
            document_text = document.get('text', '')
            if not document_text:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'NO_DOCUMENT_TEXT',
                        'message': 'Document text not available',
                        'details': 'Please re-upload the document'
                    }
                }), 400
            
            logger.info(f"Answering question for document {document_id}: {question[:50]}...")
            
            # Answer question using hybrid RAG (retrieved doc chunks + legal KB)
            answer_result = ai_analyzer.answer_question(document_text, question, document_id)

            # Prepare response
            response_data = {
                'success': True,
                'answer': answer_result.get('answer', 'Unable to provide answer'),
                'source_section': answer_result.get('source_section'),
                'confidence': answer_result.get('confidence', 'medium'),
                'sources': answer_result.get('sources', []),
                'document_id': document_id,
                'question': question,
                'answered_at': datetime.utcnow().isoformat() + 'Z'
            }
            
            # Include error information if present
            if 'error' in answer_result:
                response_data['warning'] = 'Answer may be incomplete due to processing issues'
            
            logger.info(f"Successfully answered question for document {document_id}")
            return jsonify(response_data), 200
            
        except Exception as e:
            logger.error(f"Question answering error: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({
                'success': False,
                'error': {
                    'code': 'QA_ERROR',
                    'message': 'Failed to answer question',
                    'details': 'Please try again or contact support'
                }
            }), 500
    
    # Root endpoint - serve React frontend
    @app.route('/', methods=['GET'])
    def root():
        """Serve the React frontend"""
        try:
            return app.send_static_file('index.html')
        except Exception as e:
            # Fallback to API info if static files not found
            logger.warning(f"Could not serve static files: {e}")
            return jsonify({
                'service': 'Legal EASE Backend',
                'version': '1.0.0',
                'status': 'running',
                'message': 'Frontend not available - serving API only',
                'endpoints': {
                    'health': '/api/health',
                    'analyze': '/api/analyze (POST)',
                    'question': '/api/question (POST)'
                }
            })
    
    # Serve static files for React frontend
    @app.route('/<path:filename>')
    def serve_static(filename):
        """Serve static files for React frontend"""
        try:
            # Handle specific static files
            if '.' in filename:
                return app.send_static_file(filename)
            else:
                # For React Router, serve index.html for routes without extensions
                return app.send_static_file('index.html')
        except Exception as e:
            logger.warning(f"Could not serve static file {filename}: {e}")
            # For React Router, serve index.html for unknown routes
            try:
                return app.send_static_file('index.html')
            except Exception:
                return jsonify({'error': 'Frontend not available'}), 404
    
    return app

# Create the Flask app
app = create_app()

if __name__ == '__main__':
    port = Config.PORT
    debug = Config.FLASK_ENV == 'development'
    
    logger.info(f"Starting Lexi Simplify Backend on port {port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Google Cloud Project: {Config.GOOGLE_CLOUD_PROJECT}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)