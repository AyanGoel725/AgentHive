/**
 * AgentHive — API Client
 * Type-safe wrapper for all backend API calls.
 */

import type { UploadResponse, QueryResponse, HealthResponse, DocumentMeta } from '../types';

const API_BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API Error: ${res.status}`);
  }

  return res.json();
}

export async function healthCheck(): Promise<HealthResponse> {
  return request<HealthResponse>('/health');
}

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Upload failed: ${res.status}`);
  }

  return res.json();
}

export async function queryDocument(
  query: string,
  documentId?: string,
  voice = false,
): Promise<QueryResponse> {
  return request<QueryResponse>('/query', {
    method: 'POST',
    body: JSON.stringify({
      query,
      document_id: documentId,
      voice,
    }),
  });
}

export async function voiceQuery(
  query: string,
  documentId?: string,
): Promise<QueryResponse> {
  return request<QueryResponse>('/voice/query', {
    method: 'POST',
    body: JSON.stringify({
      query,
      document_id: documentId,
      voice: true,
    }),
  });
}

export async function listDocuments(): Promise<{ documents: DocumentMeta[] }> {
  return request<{ documents: DocumentMeta[] }>('/documents');
}

export async function deleteDocument(docId: string): Promise<{ success: boolean }> {
  return request<{ success: boolean }>(`/documents/${docId}`, {
    method: 'DELETE',
  });
}
