// API response types for the Legal EASE application

export interface AnalysisResult {
  summary: string;
  key_points: string[];
  warnings: string[];
  document_id: string;
}

export interface DocumentInfo {
  filename: string;
  text_length: number;
  processed_at: string;
}

export interface AnalysisResponse {
  success: boolean;
  analysis: AnalysisResult;
  document_info: DocumentInfo;
  error?: ApiError;
}

export interface QuestionAnswer {
  answer: string;
  source_section?: string;
  confidence: 'high' | 'medium' | 'low';
  document_id: string;
  question: string;
  answered_at: string;
}

export interface QuestionResponse {
  success: boolean;
  answer?: string;
  source_section?: string;
  confidence?: 'high' | 'medium' | 'low';
  document_id?: string;
  question?: string;
  answered_at?: string;
  warning?: string;
  error?: ApiError;
}

export interface ApiError {
  code: string;
  message: string;
  details: string;
}

export interface HealthResponse {
  status: 'healthy' | 'unhealthy';
  timestamp: string;
  version: string;
  service: string;
}

export interface DocumentDeleteResponse {
  success: boolean;
  message?: string;
  document_id?: string;
  error?: ApiError;
}

// Request types
export interface QuestionRequest {
  document_id: string;
  question: string;
}

// UI state types
export interface UploadState {
  isUploading: boolean;
  progress: number;
  error: string | null;
}

export interface QAState {
  isLoading: boolean;
  questions: QuestionAnswer[];
  error: string | null;
}