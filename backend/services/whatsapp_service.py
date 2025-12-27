#!/usr/bin/env python3
"""
WhatsApp Business API integration for Legal EASE
Handles document uploads, analysis, and Q&A through WhatsApp
"""
import os
import logging
import requests
import json
from typing import Dict, Any, Optional, List
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
import tempfile
import base64

logger = logging.getLogger(__name__)

class WhatsAppService:
    """WhatsApp Business API service for Legal EASE"""
    
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')  # Twilio Sandbox
        
        if self.account_sid and self.auth_token and self.account_sid != 'demo':
            self.client = Client(self.account_sid, self.auth_token)
            self.enabled = True
            logger.info("✅ WhatsApp service initialized with Twilio")
        else:
            self.client = None
            self.enabled = False
            logger.warning("⚠️ WhatsApp service disabled - missing Twilio credentials")
    
    def send_message(self, to_number: str, message: str) -> bool:
        """Send a text message via WhatsApp"""
        if not self.enabled:
            logger.error("WhatsApp service not enabled")
            return False
        
        try:
            # Ensure the number has whatsapp: prefix
            if not to_number.startswith('whatsapp:'):
                to_number = f'whatsapp:{to_number}'
            
            message = self.client.messages.create(
                body=message,
                from_=self.whatsapp_number,
                to=to_number
            )
            
            logger.info(f"✅ WhatsApp message sent to {to_number}: {message.sid}")
            return True
            
        except TwilioException as e:
            logger.error(f"❌ Failed to send WhatsApp message: {str(e)}")
            return False
    
    def send_analysis_results(self, to_number: str, analysis_result: Dict[str, Any], filename: str = "document") -> bool:
        """Send formatted analysis results via WhatsApp"""
        if not self.enabled:
            return False
        
        try:
            # Format the analysis in a WhatsApp-friendly way
            message = self._format_analysis_for_whatsapp(analysis_result, filename)
            return self.send_message(to_number, message)
        except Exception as e:
            logger.error(f"❌ Failed to send analysis results: {str(e)}")
            return False
    
    def send_qa_response(self, to_number: str, question: str, answer_result: Dict[str, Any]) -> bool:
        """Send Q&A response via WhatsApp"""
        if not self.enabled:
            return False
        
        try:
            message = self._format_qa_for_whatsapp(question, answer_result)
            return self.send_message(to_number, message)
        except Exception as e:
            logger.error(f"❌ Failed to send Q&A response: {str(e)}")
            return False
    
    def send_welcome_message(self, to_number: str) -> bool:
        """Send welcome message to new users"""
        welcome_msg = """🏛️ *Welcome to Legal EASE!*

I'm your AI legal document assistant. I can help you understand complex legal documents in plain English.

📄 *How to use:*
• Send me a PDF document
• I'll analyze it and explain the key points
• Ask me questions about specific clauses
• Get warnings about concerning terms

🚀 *Try it now:* Send me any legal document (rental agreement, contract, terms of service, etc.)

💡 *Example questions:*
• "What is the monthly rent?"
• "Can I have pets?"
• "What are the termination conditions?"
• "Are there any concerning clauses?"

Let's make legal documents easy to understand! 📚✨"""
        
        return self.send_message(to_number, welcome_msg)
    
    def _format_analysis_for_whatsapp(self, analysis_result: Dict[str, Any], filename: str) -> str:
        """Format analysis results for WhatsApp display"""
        summary = analysis_result.get('summary', 'Analysis completed')
        key_points = analysis_result.get('key_points', [])
        warnings = analysis_result.get('warnings', [])
        
        message = f"""📄 *Document Analysis: {filename}*

📋 *SUMMARY*
{summary}

✅ *KEY POINTS*"""
        
        for i, point in enumerate(key_points[:5], 1):  # Limit to 5 points for WhatsApp
            message += f"\n{i}. {point}"
        
        if warnings:
            message += f"\n\n⚠️ *IMPORTANT WARNINGS*"
            for i, warning in enumerate(warnings[:3], 1):  # Limit to 3 warnings
                message += f"\n{i}. {warning}"
        
        message += f"""

💬 *Ask me questions about this document!*
Examples:
• "What are the payment terms?"
• "What happens if I terminate early?"
• "Are there any hidden fees?"

Type your question and I'll find the answer in your document! 🤖"""
        
        return message
    
    def _format_qa_for_whatsapp(self, question: str, answer_result: Dict[str, Any]) -> str:
        """Format Q&A response for WhatsApp"""
        answer = answer_result.get('answer', 'I could not find an answer to that question.')
        source = answer_result.get('source_section', '')
        confidence = answer_result.get('confidence', 'medium')
        
        # Confidence emoji
        confidence_emoji = {
            'high': '🎯',
            'medium': '📊', 
            'low': '🤔'
        }.get(confidence, '📊')
        
        message = f"""❓ *Your Question:*
{question}

🤖 *Legal EASE AI Answer:*
{answer}"""
        
        if source:
            message += f"""

📄 *Source Reference:*
{source}"""
        
        message += f"""

{confidence_emoji} *Confidence: {confidence.title()}*

💡 *Ask another question or send a new document to analyze!*"""
        
        return message
    
    def download_media(self, media_url: str, auth_header: str) -> Optional[bytes]:
        """Download media file from WhatsApp"""
        try:
            headers = {'Authorization': auth_header}
            response = requests.get(media_url, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Failed to download media: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error downloading media: {str(e)}")
            return None
    
    def handle_error(self, to_number: str, error_message: str) -> bool:
        """Send error message to user"""
        error_msg = f"""❌ *Oops! Something went wrong*

{error_message}

🔄 *Please try again:*
• Make sure your PDF is readable
• File size should be under 10MB
• Send one document at a time

Need help? Just ask! 💬"""
        
        return self.send_message(to_number, error_msg)
    
    def send_help_message(self, to_number: str) -> bool:
        """Send help information"""
        help_msg = """🆘 *Legal EASE Help*

📄 *Document Analysis:*
• Send any PDF legal document
• Get instant AI analysis
• Understand key terms & conditions
• Identify potential concerns

💬 *Ask Questions:*
• "What is the rent amount?"
• "Can I terminate early?"
• "What are my obligations?"
• "Are there penalty fees?"

🚀 *Supported Documents:*
• Rental agreements
• Employment contracts
• Terms of service
• Loan agreements
• Insurance policies
• And more!

📱 *Commands:*
• Send "help" - Show this message
• Send "new" - Start fresh analysis
• Send PDF - Analyze document
• Ask questions - Get answers

Ready to analyze your document? Send it now! 📤"""
        
        return self.send_message(to_number, help_msg)

# Global WhatsApp service instance
whatsapp_service = WhatsAppService()