/**
 * AgentHive — Frontend API Client
 * Type-safe interface to the FastAPI backend.
 */

import type {
  UploadResponse,
  FullAnalysisResult,
  QueryResponse,
  DocumentMetadata,
} from '../types';

const API_BASE = '/api';

export class APIError extends Error {
  constructor(public message: string, public status?: number) {
    super(message);
    this.name = 'APIError';
  }
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new APIError(err.detail || `API Error: ${res.status}`, res.status);
  }

  return res.json();
}

/**
 * Check backend health and get configuration.
 */
export async function checkHealth(): Promise<{ status: string; mock_mode: boolean; agents: string[] }> {
  return request('/health');
}

/**
 * Upload a document and trigger the full analysis pipeline.
 * Returns immediately with pending status — poll for completion.
 */
export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new APIError(err.detail || `Upload failed: ${res.status}`, res.status);
  }

  return res.json();
}

/**
 * Get the current processing status of a document (for polling).
 */
export async function getProcessingStatus(docId: string): Promise<{ status: string; message: string }> {
  return request(`/documents/${docId}/status`);
}

/**
 * Retrieve the full analysis result for a document.
 */
export async function getAnalysis(docId: string): Promise<FullAnalysisResult> {
  return request(`/documents/${docId}/analysis`);
}

/**
 * Ask a follow-up question about an analyzed document (Q&A).
 */
export async function queryDocument(docId: string, query: string): Promise<QueryResponse> {
  return request('/query', {
    method: 'POST',
    body: JSON.stringify({ doc_id: docId, query }),
  });
}

/**
 * List all analyzed documents.
 */
export async function listDocuments(): Promise<DocumentMetadata[]> {
  return request('/documents');
}

/**
 * Delete a document and all its analysis data.
 */
export async function deleteDocument(docId: string): Promise<{ message: string }> {
  return request(`/documents/${docId}`, { method: 'DELETE' });
}

/**
 * Format text for speech output.
 */
export async function formatForSpeech(text: string): Promise<{ speech_text: string }> {
  return request('/voice/format', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}

/**
 * Export URLs. Use these directly in standard anchor tags (href).
 */
export const exportUrls = {
  json: (docId: string) => `${API_BASE}/documents/${docId}/export/json`,
  markdown: (docId: string) => `${API_BASE}/documents/${docId}/export/markdown`,
};
