// ── Enums ────────────────────────────────────────────────────────────────────

export type DocumentType =
  | 'questionnaire' | 'form' | 'report' | 'spreadsheet'
  | 'presentation'  | 'contract' | 'invoice' | 'resume'
  | 'academic'      | 'technical' | 'unknown';

export type ProcessingStatus =
  | 'pending' | 'ingesting' | 'classifying'
  | 'summarizing' | 'extracting' | 'indexing' | 'complete' | 'error';

export type QuestionCategory =
  | 'demographic' | 'open_ended' | 'multiple_choice'
  | 'rating' | 'yes_no' | 'fill_in' | 'section_header' | 'unknown';

export type Importance = 'high' | 'medium' | 'low';
export type Sentiment  = 'positive' | 'neutral' | 'negative';

// ── Document Metadata ─────────────────────────────────────────────────────────

export interface DocumentMetadata {
  doc_id: string;
  filename: string;
  file_type: 'pdf' | 'excel' | 'csv';
  file_size_bytes: number;
  page_count?: number;
  sheet_names?: string[];
  row_count?: number;
  column_count?: number;
  upload_timestamp: string;
}

// ── Classification ────────────────────────────────────────────────────────────

export interface ClassificationResult {
  document_type: DocumentType;
  confidence: number;
  is_form_or_questionnaire: boolean;
  reasoning: string;
  detected_sections: string[];
  language: string;
  estimated_reading_time_minutes: number;
}

// ── Summary ───────────────────────────────────────────────────────────────────

export interface KeyPoint {
  point: string;
  importance: Importance;
  page_reference?: string;
}

export interface SummaryResult {
  doc_id: string;
  executive_summary: string;
  detailed_summary: string;
  key_points: KeyPoint[];
  topics: string[];
  sentiment: Sentiment;
  word_count_original: number;
  summary_compression_ratio: number;
}

// ── Questions ─────────────────────────────────────────────────────────────────

export interface ExtractedQuestion {
  question_id: string;
  number?: string;
  text: string;
  category: QuestionCategory;
  is_required?: boolean;
  options: string[];
  section?: string;
  page_number?: number;
  sub_questions: ExtractedQuestion[];
}

export interface QuestionExtractionResult {
  doc_id: string;
  total_questions: number;
  sections: string[];
  questions: ExtractedQuestion[];
  has_rating_scales: boolean;
  has_open_ended: boolean;
  has_multiple_choice: boolean;
  extraction_confidence: number;
}

// ── Full Analysis ─────────────────────────────────────────────────────────────

export interface FullAnalysisResult {
  doc_id: string;
  metadata: DocumentMetadata;
  classification: ClassificationResult;
  summary: SummaryResult;
  questions?: QuestionExtractionResult;
  extracted_data?: Record<string, unknown>;
  processing_time_seconds: number;
  agent_pipeline: string[];
}

// ── Upload ────────────────────────────────────────────────────────────────────

export interface UploadResponse {
  doc_id: string;
  metadata: DocumentMetadata;
  status: ProcessingStatus;
  message: string;
}

// ── Query ─────────────────────────────────────────────────────────────────────

export interface QueryRequest {
  doc_id: string;
  query: string;
  context_window?: number;
}

export interface QueryResponse {
  doc_id: string;
  query: string;
  answer: string;
  relevant_sections: string[];
  confidence: number;
}

// ── UI State ──────────────────────────────────────────────────────────────────

export type ActiveTab = 'summary' | 'questions' | 'query' | 'extracted' | 'pipeline';

export interface ProcessingStep {
  agent: string;
  label: string;
  status: 'waiting' | 'active' | 'complete' | 'error';
  icon: string;
}
