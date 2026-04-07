/* ── TypeScript interfaces for AgentHive API ─────────────────────── */

export interface DocumentMeta {
  id: string;
  filename: string;
  file_type: 'pdf' | 'excel';
  page_count?: number;
  columns?: string[];
  row_count?: number;
  uploaded_at: string;
  text_preview: string;
}

export interface UploadResponse {
  success: boolean;
  document: DocumentMeta;
  message: string;
}

export interface QueryRequest {
  query: string;
  document_id?: string;
  voice?: boolean;
}

export interface AgentInfo {
  name: string;
  icon: string;
  description: string;
}

export interface QueryResponse {
  success: boolean;
  agent: AgentInfo;
  answer: string;
  structured_data?: Record<string, unknown>;
  insights?: Record<string, unknown>;
  audio_text?: string;
  error?: string;
}

export interface HealthResponse {
  status: string;
  demo_mode: boolean;
  agents: string[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'agent';
  content: string;
  agent?: AgentInfo;
  structured_data?: Record<string, unknown>;
  insights?: Record<string, unknown>;
  timestamp: Date;
}
