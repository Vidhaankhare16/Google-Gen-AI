from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
import traceback

from config import Config
from services.pdf_processor import pdf_processor
from services.ai_analyzer import ai_analyzer
from services.document_storage import document_storage
from utils.validators import validate_pdf_file, validate_question, sanitize_filename

logger = logging.getLogger(__name__)

# Create blueprint for document-related routes
document_bp = Blueprint('document', __name__)

@document_bp.route('/delete/<document_id>', methods=['DELETE'])
def delete_document(document_id):
    """Delete a document and its analysis results"""
    try:
        if not document_id or not document_id.strip():
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_DOCUMENT_ID',
                    'message': 'Document ID is required',
                    'details': 'Please provide a valid document ID'
                }
            }), 400
        
        # Delete document from storage
        deleted = document_storage.delete_document(document_id.strip())
        
        if deleted:
            logger.info(f"Successfully deleted document {document_id}")
            return jsonify({
                'success': True,
                'message': 'Document deleted successfully',
                'document_id': document_id
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'DOCUMENT_NOT_FOUND',
                    'message': 'Document not found',
                    'details': 'Document may have already been deleted or expired'
                }
            }), 404
            
    except Exception as e:
        logger.error(f"Document deletion error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'DELETION_ERROR',
                'message': 'Failed to delete document',
                'details': 'Please try again or contact support'
            }
        }), 500

@document_bp.route('/info/<document_id>', methods=['GET'])
def get_document_info(document_id):
    """Get information about a document"""
    try:
        if not document_id or not document_id.strip():
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_DOCUMENT_ID',
                    'message': 'Document ID is required',
                    'details': 'Please provide a valid document ID'
                }
            }), 400
        
        # Retrieve document
        document = document_storage.get_document(document_id.strip())
        
        if not document:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'DOCUMENT_NOT_FOUND',
                    'message': 'Document not found or expired',
                    'details': 'Document may have been deleted or expired'
                }
            }), 404
        
        # Prepare document info (without full text for security)
        document_info = {
            'document_id': document_id,
            'filename': document.get('filename', 'Unknown'),
            'created_at': document.get('created_at').isoformat() + 'Z' if document.get('created_at') else None,
            'expires_at': document.get('expires_at').isoformat() + 'Z' if document.get('expires_at') else None,
            'text_length': len(document.get('text', '')),
            'has_analysis': document.get('analysis_result') is not None
        }
        
        # Include analysis summary if available
        if document.get('analysis_result'):
            analysis = document['analysis_result']
            document_info['analysis_summary'] = {
                'summary_length': len(analysis.get('summary', '')),
                'key_points_count': len(analysis.get('key_points', [])),
                'warnings_count': len(analysis.get('warnings', []))
            }
        
        return jsonify({
            'success': True,
            'document_info': document_info
        }), 200
        
    except Exception as e:
        logger.error(f"Document info error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INFO_ERROR',
                'message': 'Failed to retrieve document information',
                'details': 'Please try again or contact support'
            }
        }), 500

@document_bp.route('/stats', methods=['GET'])
def get_storage_stats():
    """Get storage statistics (for monitoring)"""
    try:
        stats = document_storage.get_stats()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_documents': stats.get('total_documents', 0),
                'oldest_document': stats.get('oldest_document').isoformat() + 'Z' if stats.get('oldest_document') else None,
                'newest_document': stats.get('newest_document').isoformat() + 'Z' if stats.get('newest_document') else None,
                'evicted_count': stats.get('evicted_count', 0),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Storage stats error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'STATS_ERROR',
                'message': 'Failed to retrieve storage statistics',
                'details': str(e)
            }
        }), 500