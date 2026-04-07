import { useState, useCallback, useEffect } from 'react';
import './index.css';
import type { DocumentMeta, ChatMessage, AgentInfo } from './types';
import { queryDocument, voiceQuery, deleteDocument, healthCheck } from './api/client';
import { speakText } from './components/VoiceButton';
import FileUpload from './components/FileUpload';
import ChatPanel from './components/ChatPanel';
import OutputDisplay from './components/OutputDisplay';
import AgentStatus from './components/AgentStatus';

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

export default function App() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [activeDocId, setActiveDocId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeAgent, setActiveAgent] = useState<AgentInfo | null>(null);
  const [demoMode, setDemoMode] = useState(false);

  // Health check on mount
  useEffect(() => {
    healthCheck()
      .then(h => setDemoMode(h.demo_mode))
      .catch(() => setDemoMode(true));
  }, []);

  const handleUpload = useCallback((doc: DocumentMeta) => {
    setDocuments(prev => [...prev, doc]);
    setActiveDocId(doc.id);
    // Add a system message
    setMessages(prev => [...prev, {
      id: generateId(),
      role: 'agent',
      content: `📥 **${doc.filename}** uploaded successfully!\n\n${
        doc.file_type === 'pdf'
          ? `📄 ${doc.page_count} page(s) extracted and indexed.`
          : `📊 ${doc.row_count} rows × ${doc.columns?.length} columns loaded.`
      }\n\nYou can now ask questions about this document. Try "Summarize this document" or "Extract structured data".`,
      agent: { name: 'Ingestion Agent', icon: '📥', description: 'File processed' },
      timestamp: new Date(),
    }]);
  }, []);

  const handleDelete = useCallback(async (docId: string) => {
    try {
      await deleteDocument(docId);
      setDocuments(prev => prev.filter(d => d.id !== docId));
      if (activeDocId === docId) {
        setActiveDocId(null);
      }
    } catch (err) {
      console.error('Delete failed:', err);
    }
  }, [activeDocId]);

  const handleSendMessage = useCallback(async (text: string, voice = false) => {
    // Add user message
    const userMsg: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);
    setActiveAgent({ name: 'Orchestrator Agent', icon: '🎯', description: 'Routing query...' });

    try {
      const response = voice
        ? await voiceQuery(text, activeDocId || undefined)
        : await queryDocument(text, activeDocId || undefined);

      setActiveAgent(response.agent);

      const agentMsg: ChatMessage = {
        id: generateId(),
        role: 'agent',
        content: response.success
          ? response.answer
          : `❌ Error: ${response.error}`,
        agent: response.agent,
        structured_data: response.structured_data,
        insights: response.insights,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, agentMsg]);

      // Voice: read response aloud
      if (voice && response.audio_text) {
        speakText(response.audio_text);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Request failed';
      setMessages(prev => [...prev, {
        id: generateId(),
        role: 'agent',
        content: `❌ ${message}`,
        agent: { name: 'System', icon: '⚠️', description: 'Error' },
        timestamp: new Date(),
      }]);
    } finally {
      setLoading(false);
      setTimeout(() => setActiveAgent(null), 2000);
    }
  }, [activeDocId]);

  return (
    <div className="app-layout">
      {/* Header */}
      <header className="app-header">
        <div className="app-header__brand">
          <span className="app-header__logo">🐝</span>
          <div>
            <div className="app-header__title">AgentHive</div>
            <div className="app-header__subtitle">Multi-Agent Document Intelligence</div>
          </div>
        </div>
        <div className="app-header__status">
          <span className={`status-dot ${demoMode ? 'status-dot--demo' : ''}`} />
          {demoMode ? 'Demo Mode' : 'Connected'}
          {documents.length > 0 && (
            <span style={{ marginLeft: 12, color: 'var(--text-muted)' }}>
              {documents.length} doc(s)
            </span>
          )}
        </div>
      </header>

      {/* Sidebar */}
      <div className="sidebar">
        <FileUpload onUpload={handleUpload} />

        <div className="sidebar__section" style={{ flex: 0, paddingTop: 0 }}>
          <div className="sidebar__title">Documents ({documents.length})</div>
        </div>

        <div className="doc-list">
          {documents.length === 0 ? (
            <div style={{
              textAlign: 'center',
              padding: '24px 16px',
              color: 'var(--text-muted)',
              fontSize: 13,
            }}>
              No documents uploaded yet
            </div>
          ) : (
            documents.map(doc => (
              <div
                key={doc.id}
                className={`doc-item ${activeDocId === doc.id ? 'doc-item--active' : ''}`}
                onClick={() => setActiveDocId(doc.id)}
              >
                <div className={`doc-item__icon doc-item__icon--${doc.file_type}`}>
                  {doc.file_type === 'pdf' ? '📄' : '📊'}
                </div>
                <div className="doc-item__info">
                  <div className="doc-item__name">{doc.filename}</div>
                  <div className="doc-item__meta">
                    {doc.file_type === 'pdf'
                      ? `${doc.page_count} page(s)`
                      : `${doc.row_count} rows × ${doc.columns?.length} cols`}
                  </div>
                </div>
                <button
                  className="doc-item__delete"
                  onClick={e => { e.stopPropagation(); handleDelete(doc.id); }}
                  title="Delete document"
                >
                  ✕
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Chat */}
      <ChatPanel
        messages={messages}
        loading={loading}
        hasDocument={documents.length > 0}
        onSendMessage={handleSendMessage}
      />

      {/* Output */}
      <div className="output-panel">
        <AgentStatus activeAgent={activeAgent} processing={loading} />
        <OutputDisplay messages={messages} />
      </div>
    </div>
  );
}
