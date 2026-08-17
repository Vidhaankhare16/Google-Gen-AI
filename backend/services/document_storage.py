import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import threading

class DocumentStorage:
    """
    In-memory document storage for the prototype
    In production, this would be replaced with a proper database or cloud storage
    """
    
    def __init__(self, session_timeout: int = 3600, max_documents: int = 500):
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.session_timeout = session_timeout
        if max_documents < 1:
            raise ValueError('max_documents must be at least 1')
        self.max_documents = max_documents
        self._evicted_count = 0
        self._lock = threading.Lock()
        # Optional callback invoked with a document_id whenever a document is removed (deleted or
        # expired) so its vector-store chunks can be cleaned up too. Set by the app after wiring RAG.
        self.on_evict = None

        # Start cleanup thread
        self._start_cleanup_thread()

    def _evict(self, document_id: str) -> None:
        """Notify the eviction callback (outside the lock) so vector chunks get cleaned up."""
        if self.on_evict:
            try:
                self.on_evict(document_id)
            except Exception:
                pass
    
    def store_document(self, text: str, filename: str = None) -> str:
        """
        Store document text and return unique document ID
        
        Args:
            text: Extracted document text
            filename: Original filename (optional)
        
        Returns:
            Unique document ID
        """
        
        document_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(seconds=self.session_timeout)
        
        with self._lock:
            # Evict inline instead of calling delete_document(). _lock is a plain
            # Lock rather than an RLock, so re-acquiring it here would deadlock.
            while len(self.documents) >= self.max_documents:
                oldest_id = min(
                    self.documents,
                    key=lambda doc_id: self.documents[doc_id]['created_at']
                )
                del self.documents[oldest_id]
                self._evicted_count += 1

            self.documents[document_id] = {
                'text': text,
                'filename': filename,
                'created_at': datetime.utcnow(),
                'expires_at': expires_at,
                'analysis_result': None
            }
        
        return document_id
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve document by ID
        
        Args:
            document_id: Document identifier
        
        Returns:
            Document data or None if not found/expired
        """
        
        expired = False
        with self._lock:
            if document_id not in self.documents:
                return None

            document = self.documents[document_id]

            # Check if expired
            if datetime.utcnow() > document['expires_at']:
                del self.documents[document_id]
                expired = True
            else:
                result = document.copy()
        if expired:
            self._evict(document_id)
            return None
        return result
    
    def update_analysis(self, document_id: str, analysis_result: Dict[str, Any]) -> bool:
        """
        Update document with analysis results
        
        Args:
            document_id: Document identifier
            analysis_result: Analysis results from AI service
        
        Returns:
            True if updated successfully, False if document not found
        """
        
        with self._lock:
            if document_id not in self.documents:
                return False
            
            # Check if expired
            if datetime.utcnow() > self.documents[document_id]['expires_at']:
                del self.documents[document_id]
                return False
            
            self.documents[document_id]['analysis_result'] = analysis_result
            return True
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete document by ID
        
        Args:
            document_id: Document identifier
        
        Returns:
            True if deleted, False if not found
        """
        
        with self._lock:
            existed = document_id in self.documents
            if existed:
                del self.documents[document_id]
        if existed:
            self._evict(document_id)
        return existed
    
    def cleanup_expired(self) -> int:
        """
        Remove expired documents
        
        Returns:
            Number of documents removed
        """
        
        current_time = datetime.utcnow()
        expired_ids = []
        
        with self._lock:
            for doc_id, document in self.documents.items():
                if current_time > document['expires_at']:
                    expired_ids.append(doc_id)
            
            for doc_id in expired_ids:
                del self.documents[doc_id]

        for doc_id in expired_ids:   # evict vectors outside the lock
            self._evict(doc_id)

        return len(expired_ids)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics
        
        Returns:
            Dictionary with storage stats
        """
        
        with self._lock:
            return {
                'total_documents': len(self.documents),
                'oldest_document': min(
                    (doc['created_at'] for doc in self.documents.values()),
                    default=None
                ),
                'newest_document': max(
                    (doc['created_at'] for doc in self.documents.values()),
                    default=None
                ),
                'evicted_count': self._evicted_count
            }
    
    def _start_cleanup_thread(self):
        """Start background thread for cleaning up expired documents"""
        
        def cleanup_worker():
            while True:
                try:
                    removed = self.cleanup_expired()
                    if removed > 0:
                        print(f"Cleaned up {removed} expired documents")
                    time.sleep(300)  # Run every 5 minutes
                except Exception as e:
                    print(f"Error in cleanup thread: {e}")
                    time.sleep(60)  # Wait 1 minute before retrying
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()

# Global document storage instance
document_storage = DocumentStorage()