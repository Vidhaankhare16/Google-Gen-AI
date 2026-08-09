import axios, { AxiosResponse } from 'axios';
import {
  AnalysisResponse,
  QuestionResponse,
  QuestionRequest,
  HealthResponse,
  DocumentDeleteResponse,
} from '../types/api';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || '/api',
  // A cold container has to load InLegalBERT and open the vector index before it can
  // answer, and a long agreement then costs several Gemini calls. 60s was short enough
  // that the first upload after a scale-from-zero could time out client-side while the
  // server was still working.
  timeout: 180000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export class ApiService {
  /**
   * Check API health status
   */
  static async checkHealth(): Promise<HealthResponse> {
    try {
      const response: AxiosResponse<HealthResponse> = await api.get('/health');
      return response.data;
    } catch (error) {
      throw new Error('Failed to check API health');
    }
  }

  /**
   * Upload and analyze a document
   */
  static async analyzeDocument(file: File): Promise<AnalysisResponse> {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response: AxiosResponse<AnalysisResponse> = await api.post('/analyze', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            console.log(`Upload progress: ${progress}%`);
          }
        },
      });

      return response.data;
    } catch (error: any) {
      if (error.response?.data?.error) {
        throw new Error(error.response.data.error.message || 'Document analysis failed');
      }
      throw new Error('Failed to analyze document');
    }
  }

  /**
   * Ask a question about a document
   */
  static async askQuestion(documentId: string, question: string): Promise<QuestionResponse> {
    try {
      const requestData: QuestionRequest = {
        document_id: documentId,
        question: question.trim(),
      };

      const response: AxiosResponse<QuestionResponse> = await api.post('/question', requestData);
      return response.data;
    } catch (error: any) {
      if (error.response?.data?.error) {
        throw new Error(error.response.data.error.message || 'Failed to answer question');
      }
      throw new Error('Failed to get answer');
    }
  }

  /**
   * Delete a document
   */
  static async deleteDocument(documentId: string): Promise<DocumentDeleteResponse> {
    try {
      const response: AxiosResponse<DocumentDeleteResponse> = await api.delete(`/document/delete/${documentId}`);
      return response.data;
    } catch (error: any) {
      if (error.response?.data?.error) {
        throw new Error(error.response.data.error.message || 'Failed to delete document');
      }
      throw new Error('Failed to delete document');
    }
  }

  /**
   * Validate file before upload
   */
  static validateFile(file: File): { isValid: boolean; error?: string } {
    // Check file type
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      return { isValid: false, error: 'Only PDF files are supported' };
    }

    // Check file size (10MB limit)
    const maxSize = 10 * 1024 * 1024; // 10MB in bytes
    if (file.size > maxSize) {
      return { isValid: false, error: 'File size must be less than 10MB' };
    }

    // Check if file is empty
    if (file.size === 0) {
      return { isValid: false, error: 'File cannot be empty' };
    }

    return { isValid: true };
  }

  /**
   * Format file size for display
   */
  static formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  /**
   * Format date for display
   */
  static formatDate(dateString: string): string {
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch (error) {
      return dateString;
    }
  }
}

export default ApiService;