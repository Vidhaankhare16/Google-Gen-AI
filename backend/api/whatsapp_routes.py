#!/usr/bin/env python3
"""
WhatsApp webhook routes for Legal EASE
Handles incoming WhatsApp messages and document uploads
"""
import os
import logging
import tempfile
from flask import Blueprint, request, jsonify
from werkzeug.datastructures import FileStorage
import io

from services.whatsapp_service import whatsapp_service
from services.pdf_processor import pdf_processor
from services.ai_analyzer import ai_analyzer
from services.document_storage import document_storage
from utils.security import rate_limit

logger = logging.getLogger(__name__)

# Create blueprint for WhatsApp routes
whatsapp_bp = Blueprint('whatsapp', __name__)

# Store user sessions for document context
user_sessions = {}

@whatsapp_bp.route('/webhook', methods=['GET'])
def verify_webhook():
    """Verify WhatsApp webhook (for Twilio)"""
    # This is for webhook verification
    return "WhatsApp webhook verified", 200

@whatsapp_bp.route('/webhook', methods=['POST'])
@rate_limit(max_requests=50, window_seconds=300)  # Higher limit for WhatsApp
def handle_whatsapp_message():
    """Handle incoming WhatsApp messages"""
    try:
        # Get message data from Twilio
        message_data = request.form.to_dict()
        from_number = message_data.get('From', '')
        message_body = message_data.get('Body', '').strip().lower()
        media_url = message_data.get('MediaUrl0', '')
        media_content_type = message_data.get('MediaContentType0', '')
        
        logger.info(f"📱 WhatsApp message from {from_number}: {message_body[:50]}...")
        
        # Handle different message types
        if media_url and 'pdf' in media_content_type.lower():
            # Handle PDF document upload
            return handle_document_upload(from_number, media_url, message_data)
        elif message_body in ['help', 'start', 'hello', 'hi']:
            # Send help message
            whatsapp_service.send_help_message(from_number)
        elif message_body in ['new', 'reset', 'clear']:
            # Clear user session
            if from_number in user_sessions:
                del user_sessions[from_number]
            whatsapp_service.send_message(from_number, "🔄 Session cleared! Send me a new document to analyze.")
        elif from_number in user_sessions and message_body:
            # Handle Q&A for existing document
            return handle_question(from_number, message_body)
        else:
            # Send welcome message for new users
            whatsapp_service.send_welcome_message(from_number)
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"❌ WhatsApp webhook error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def handle_document_upload(from_number: str, media_url: str, message_data: dict) -> tuple:
    """Handle PDF document upload from WhatsApp"""
    try:
        logger.info(f"📄 Processing document upload from {from_number}")
        
        # Send processing message
        whatsapp_service.send_message(from_number, "📄 *Analyzing your document...* \n\nThis may take a few moments. I'll send you the results shortly! ⏳")
        
        # Download the PDF file
        auth_header = f"Basic {request.authorization}" if request.authorization else ""
        pdf_content = whatsapp_service.download_media(media_url, auth_header)
        
        if not pdf_content:
            whatsapp_service.handle_error(from_number, "Could not download your document. Please try sending it again.")
            return jsonify({'error': 'Failed to download media'}), 400
        
        # Extract text from PDF
        try:
            text_content = pdf_processor.extract_text_from_bytes(pdf_content)
            if not text_content or len(text_content.strip()) < 10:
                whatsapp_service.handle_error(from_number, "Could not extract readable text from your PDF. Please ensure it contains text (not just images).")
                return jsonify({'error': 'No readable text found'}), 400
        except Exception as e:
            logger.error(f"PDF processing error: {str(e)}")
            whatsapp_service.handle_error(from_number, "There was an error processing your PDF. Please make sure it's a valid PDF file.")
            return jsonify({'error': 'PDF processing failed'}), 400
        
        # Store document
        document_id = document_storage.store_document(text_content, "whatsapp_document.pdf")
        
        # Analyze document with AI
        try:
            analysis_result = ai_analyzer.analyze_document(text_content, "whatsapp_document.pdf")
            
            # Store analysis results
            document_storage.update_analysis(document_id, analysis_result)
            
            # Store user session for Q&A
            user_sessions[from_number] = {
                'document_id': document_id,
                'document_text': text_content,
                'analysis_result': analysis_result
            }
            
            # Send analysis results
            whatsapp_service.send_analysis_results(from_number, analysis_result, "your document")
            
            logger.info(f"✅ Document analysis completed for {from_number}")
            
        except Exception as e:
            logger.error(f"AI analysis error: {str(e)}")
            whatsapp_service.handle_error(from_number, "There was an error analyzing your document. Please try again.")
            return jsonify({'error': 'Analysis failed'}), 500
        
        return jsonify({'status': 'success', 'message': 'Document processed'}), 200
        
    except Exception as e:
        logger.error(f"❌ Document upload error: {str(e)}")
        whatsapp_service.handle_error(from_number, "An unexpected error occurred. Please try again.")
        return jsonify({'error': 'Upload failed'}), 500

def handle_question(from_number: str, question: str) -> tuple:
    """Handle Q&A about uploaded document"""
    try:
        session = user_sessions.get(from_number)
        if not session:
            whatsapp_service.send_message(from_number, "❓ Please upload a document first before asking questions!")
            return jsonify({'error': 'No document session'}), 400
        
        logger.info(f"❓ Q&A from {from_number}: {question[:50]}...")
        
        # Send typing indicator
        whatsapp_service.send_message(from_number, "🤖 *Thinking...* Let me find that information in your document...")
        
        # Get answer from AI
        try:
            document_text = session['document_text']
            answer_result = ai_analyzer.answer_question(document_text, question)
            
            # Send answer
            whatsapp_service.send_qa_response(from_number, question, answer_result)
            
            logger.info(f"✅ Q&A response sent to {from_number}")
            
        except Exception as e:
            logger.error(f"Q&A error: {str(e)}")
            whatsapp_service.handle_error(from_number, "I couldn't process your question. Please try rephrasing it.")
            return jsonify({'error': 'Q&A failed'}), 500
        
        return jsonify({'status': 'success', 'message': 'Question answered'}), 200
        
    except Exception as e:
        logger.error(f"❌ Q&A handling error: {str(e)}")
        whatsapp_service.handle_error(from_number, "An error occurred while processing your question.")
        return jsonify({'error': 'Question handling failed'}), 500