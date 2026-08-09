// API response types for the Legal EASE application

// A retrieved legal source (statute / precedent / red-flag / glossary) used to ground the answer.
export interface LegalSource {
  type?: string;        // statute | judgment | redflag | glossary | template
  source?: string;      // e.g. "The Indian Contract Act, 1872"
  section?: string;     // e.g. "Section 74"
  citation?: string;    // e.g. "AIR 2013 SUPREME COURT 3037"
  score?: number;       // retrieval similarity
}

export interface AnalysisResult {
  summary: string;
  key_points: string[];
  warnings: string[];
  document_id: string;
  risk_score?: number;
  document_type?: string;
  sources?: LegalSource[];
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
  sources?: LegalSource[];
}

export interface QuestionResponse {
  success: boolean;
  answer?: string;
  source_section?: string;
  confidence?: 'high' | 'medium' | 'low';
  sources?: LegalSource[];
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