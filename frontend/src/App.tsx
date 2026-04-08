import React, { useEffect, useRef, useState } from 'react';
import './index.css';

import {
  checkHealth,
  deleteDocument,
  formatForSpeech,
  getAnalysis,
  getProcessingStatus,
  listDocuments,
  queryDocument,
} from './api/client';

import type { ActiveTab, DocumentMetadata, FullAnalysisResult, QueryResponse } from './types';

import DocumentCard from './components/DocumentCard';
import ExportMenu from './components/ExportMenu';
import FileUpload from './components/FileUpload';
import JsonViewer from './components/JsonViewer';
import ProcessingPipeline from './components/ProcessingPipeline';
import QuestionExplorer from './components/QuestionExplorer';
import SummaryView from './components/SummaryView';

interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  response?: QueryResponse;
}

const SpeechRecognition =
  (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
const hasSpeechRecognition = !!SpeechRecognition;
const hasSpeechSynthesis = 'speechSynthesis' in window;

const SUGGESTED_QUERIES = [
  'What is the main conclusion?',
  'Summarize the key findings',
  'List any action items',
  'What are the key dates mentioned?',
  'Who are the main stakeholders?',
];

export default function App() {
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [activeDocId, setActiveDocId] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<FullAnalysisResult | null>(null);
  const [processingStatus, setProcessingStatus] = useState<string>('');
  const [activeTab, setActiveTab] = useState<ActiveTab>('summary');
  const [demoMode, setDemoMode] = useState(false);
  const [error, setError] = useState('');
  const pollRef = useRef<number | null>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    checkHealth()
      .then(h => setDemoMode(h.mock_mode))
      .catch(() => setDemoMode(true));
    refreshDocuments();
  }, []);

  useEffect(() => () => {
    if (pollRef.current) window.clearInterval(pollRef.current);
  }, []);

  useEffect(() => {
    setMessages([]);
    setChatInput('');
  }, [activeDocId]);

  useEffect(() => {
    const el = messagesContainerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, chatLoading]);

  const refreshDocuments = async () => {
    try {
      const docs = await listDocuments();
      setDocuments(
        docs.sort((a, b) =>
          new Date(b.upload_timestamp).getTime() -
          new Date(a.upload_timestamp).getTime(),
        ),
      );
    } catch { }
  };

  useEffect(() => {
    if (!activeDocId) { setAnalysis(null); setProcessingStatus(''); return; }
    const load = async () => {
      try {
        const result = await getAnalysis(activeDocId);
        setAnalysis(result);
        setProcessingStatus('complete');
        setActiveTab(
          result.classification.is_form_or_questionnaire &&
            result.questions?.total_questions
            ? 'questions' : 'summary',
        );
      } catch {
        try {
          const { status } = await getProcessingStatus(activeDocId);
          if (status !== 'complete' && status !== 'error') {
            setProcessingStatus(status);
            startPolling(activeDocId);
          } else {
            setError('Failed to load document analysis.');
          }
        } catch {
          setError('Failed to load document analysis.');
        }
      }
    };
    load();
  }, [activeDocId]);

  const startPolling = (docId: string) => {
    if (pollRef.current) window.clearInterval(pollRef.current);
    pollRef.current = window.setInterval(async () => {
      try {
        const { status } = await getProcessingStatus(docId);
        setProcessingStatus(status);
        if (status === 'complete' || status === 'error') {
          window.clearInterval(pollRef.current!);
          pollRef.current = null;
          if (status === 'complete') {
            const result = await getAnalysis(docId);
            setAnalysis(result);
            refreshDocuments();
            setActiveTab(
              result.classification.is_form_or_questionnaire && result.questions
                ? 'questions' : 'summary',
            );
          } else {
            setError('Document processing failed.');
          }
        }
      } catch {
        window.clearInterval(pollRef.current!);
        pollRef.current = null;
      }
    }, 1500);
  };

  const handleUpload = (doc: DocumentMetadata) => {
    setError('');
    setActiveDocId(doc.doc_id);
    setAnalysis(null);
    setProcessingStatus('pending');
    setActiveTab('pipeline');
    setDocuments(prev => [doc, ...prev]);
    startPolling(doc.doc_id);
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteDocument(id);
      setDocuments(prev => prev.filter(d => d.doc_id !== id));
      if (activeDocId === id) { setActiveDocId(null); setAnalysis(null); }
    } catch {
      setError('Failed to delete document.');
      setTimeout(() => setError(''), 3000);
    }
  };

  const speakText = async (text: string) => {
    if (!hasSpeechSynthesis || !ttsEnabled) return;
    window.speechSynthesis.cancel();
    try {
      const { speech_text } = await formatForSpeech(text);
      const utt = new SpeechSynthesisUtterance(speech_text);
      const voices = window.speechSynthesis.getVoices();
      const v = voices.find(v =>
        v.name.includes('Google') ||
        v.name.includes('Microsoft') ||
        v.name.includes('Samantha'),
      );
      if (v) utt.voice = v;
      utt.onstart = () => setIsSpeaking(true);
      utt.onend = () => setIsSpeaking(false);
      utt.onerror = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utt);
    } catch {
      const utt = new SpeechSynthesisUtterance(text.slice(0, 500));
      utt.onstart = () => setIsSpeaking(true);
      utt.onend = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utt);
    }
  };

  const stopSpeaking = () => { window.speechSynthesis.cancel(); setIsSpeaking(false); };

  const handleSend = async (text: string = chatInput) => {
    if (!text.trim() || chatLoading || !activeDocId) return;
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setChatInput('');
    setChatLoading(true);
    try {
      const res = await queryDocument(activeDocId, text);
      setMessages(prev => [
        ...prev,
        { id: Date.now() + 'a', role: 'agent', content: res.answer, response: res },
      ]);
      if (ttsEnabled) speakText(res.answer);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          id: Date.now() + 'e',
          role: 'agent',
          content: `Error: ${err instanceof Error ? err.message : 'Query failed'}`,
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const startRecording = () => {
    if (!hasSpeechRecognition) return;
    const r = new SpeechRecognition();
    r.continuous = false; r.interimResults = true; r.lang = 'en-US';
    r.onstart = () => setIsRecording(true);
    r.onresult = (e: any) =>
      setChatInput(Array.from(e.results).map((r: any) => r[0].transcript).join(''));
    r.onend = () => {
      setIsRecording(false);
      setChatInput(prev => { if (prev.trim()) handleSend(prev); return prev; });
    };
    r.onerror = () => setIsRecording(false);
    recognitionRef.current = r;
    r.start();
  };

  const stopRecording = () => { recognitionRef.current?.stop(); setIsRecording(false); };

  const tabs: { id: ActiveTab; label: string; count?: number }[] = [
    { id: 'summary', label: 'Summary' },
    { id: 'questions', label: 'Questions', count: analysis?.questions?.total_questions },
    { id: 'query', label: 'Q&A Chat' },
    { id: 'extracted', label: 'Extracted Data' },
    { id: 'pipeline', label: 'Pipeline' },
  ];

  const showTabs = !!(analysis && processingStatus === 'complete');
  const showChatBar = showTabs && activeTab === 'query';

  const renderTabContent = () => {
    if (!analysis) return null;

    switch (activeTab) {
      case 'summary':
        return (
          <div className="tab-content-scroll">
            <SummaryView analysis={analysis} />
          </div>
        );

      case 'questions':
        return (
          <div className="tab-content-scroll">
            {analysis.questions ? (
              <QuestionExplorer data={analysis.questions} />
            ) : (
              <div className="empty-state">
                <div className="empty-state__icon">📝</div>
                <div className="empty-state__text">
                  No questions found in this document.<br />
                  Only forms and questionnaires contain extractable questions.
                </div>
              </div>
            )}
          </div>
        );

      case 'query':
        return (
          <div className="tab-content-scroll" ref={messagesContainerRef} style={{ padding: '16px 24px' }}>
            {messages.length === 0 ? (
              <div className="empty-state" style={{ minHeight: 240 }}>
                <div className="empty-state__icon">🧠</div>
                <div className="empty-state__text" style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-2)' }}>
                  Ask anything about this document
                </div>
                <p className="empty-state__text">
                  The Understanding Agent searches the full text and returns
                  a precise answer with confidence scoring.
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center', marginTop: 8 }}>
                  {SUGGESTED_QUERIES.map(q => (
                    <button key={q} onClick={() => handleSend(q)} className="quick-action">
                      {q}
                    </button>
                  ))}
                </div>
                {hasSpeechRecognition && (
                  <p style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 8 }}>
                    🎙️ Voice input available — use the microphone in the bar below
                  </p>
                )}
              </div>
            ) : (
              <div style={{ maxWidth: 760, margin: '0 auto' }}>
                {messages.map(msg => (
                  <div key={msg.id} className={`message message--${msg.role}`}>
                    <div className="message__avatar">
                      {msg.role === 'user' ? '👤' : '🧠'}
                    </div>
                    <div className="message__content" style={{ width: '100%' }}>
                      <div className="message__bubble">{msg.content}</div>
                      {msg.role === 'agent' && msg.response && (
                        <div className="message__meta">
                          <span>
                            Confidence: {Math.round((msg.response.confidence || 0) * 100)}%
                          </span>
                          <div style={{ width: 60, height: 3, background: 'var(--bg-elevated)', borderRadius: 2, overflow: 'hidden' }}>
                            <div style={{
                              width: `${Math.round((msg.response.confidence || 0) * 100)}%`,
                              height: '100%',
                              background: msg.response.confidence > 0.7 ? 'var(--success)' : msg.response.confidence > 0.4 ? 'var(--warning)' : 'var(--danger)',
                              borderRadius: 2,
                            }} />
                          </div>
                          {hasSpeechSynthesis && (
                            <button onClick={() => speakText(msg.content)} title="Read aloud">
                              🔊
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {chatLoading && (
                  <div className="message message--agent">
                    <div className="message__avatar">🧠</div>
                    <div className="message__content">
                      <div className="message__bubble">
                        <div className="typing-indicator">
                          <div className="typing-indicator__dot" />
                          <div className="typing-indicator__dot" />
                          <div className="typing-indicator__dot" />
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 4 }}>
                          Searching document and generating answer...
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div style={{ height: 8 }} />
              </div>
            )}
          </div>
        );

      case 'extracted':
        return (
          <div className="tab-content-scroll">
            <JsonViewer data={analysis.extracted_data || {}} />
          </div>
        );

      case 'pipeline':
        return (
          <div className="tab-content-scroll">
            <h3 className="pipeline-completed-header">
              Agent Execution Pipeline
            </h3>
            <div className="pipeline-completed-flow">
              {analysis.agent_pipeline.map((agent, i) => (
                <React.Fragment key={i}>
                  <div className="agent-badge agent-badge--active">{agent}</div>
                  {i < analysis.agent_pipeline.length - 1 && (
                    <span className="pipeline-completed-arrow">→</span>
                  )}
                </React.Fragment>
              ))}
            </div>
            <div className="stat-card" style={{ maxWidth: 240 }}>
              <div className="stat-card__label">Total Processing Time</div>
              <div className="stat-card__value">{analysis.processing_time_seconds}s</div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  const renderMainArea = () => {
    if (error) {
      return (
        <div className="tab-content-scroll">
          <div className="empty-state">
            <div className="empty-state__icon">⚠️</div>
            <div className="empty-state__text" style={{ color: 'var(--danger)' }}>{error}</div>
            <button onClick={() => setError('')} className="quick-action" style={{ marginTop: 12 }}>
              Dismiss
            </button>
          </div>
        </div>
      );
    }

    if (!activeDocId) {
      return (
        <div className="welcome-screen">
          <div className="welcome-logo">🐝</div>
          <h1 className="welcome-title">AgentHive</h1>
          <p className="welcome-subtitle">
            Drop any PDF, Excel, or CSV into the sidebar and watch a team of AI
            agents classify, summarize, and extract every insight — in seconds.
          </p>
          <div className="welcome-features">
            {[
              { icon: '📥', label: 'PDF & Excel Ingestion' },
              { icon: '🏷️', label: 'Auto Classification' },
              { icon: '✍️', label: 'Deep Summarization' },
              { icon: '❓', label: 'Question Extraction' },
              { icon: '🧠', label: 'Semantic Q&A' },
              { icon: '📦', label: 'Structured Export' },
            ].map(f => (
              <div key={f.label} className="welcome-feature-pill">
                <span>{f.icon}</span><span>{f.label}</span>
              </div>
            ))}
          </div>
          <div className="welcome-arrow">
            <span>←</span><span>Upload a document to get started</span>
          </div>
        </div>
      );
    }

    if (processingStatus !== 'complete' && !analysis) {
      return (
        <div className="tab-content-scroll">
          <ProcessingPipeline status={processingStatus} />
        </div>
      );
    }

    return renderTabContent();
  };

  return (
    <div className="app-layout">

      <header className="app-header">
        <div className="app-header__brand">
          <span className="app-header__logo">🐝</span>
          <span className="app-header__title">AgentHive</span>
          <span className="app-header__sep" />
          <span className="app-header__subtitle">Document Intelligence</span>
        </div>
        <div className="app-header__right">
          {analysis && <ExportMenu docId={analysis.doc_id} />}
          <div className="status-pill">
            <span className={`status-pill__dot ${demoMode ? 'status-pill__dot--demo' : ''}`} />
            {demoMode ? 'Mock' : 'Connected'}
          </div>
        </div>
      </header>

      <aside className="sidebar">
        <FileUpload onUpload={handleUpload} />
        <div className="sidebar__label">Documents ({documents.length})</div>
        <div className="doc-list">
          {documents.length === 0 ? (
            <div style={{
              padding: '20px 16px', textAlign: 'center',
              color: 'var(--text-3)', fontSize: 11, lineHeight: 1.6,
            }}>
              No documents yet.<br />Upload one above to begin.
            </div>
          ) : documents.map((doc, i) => (
            <DocumentCard
              key={doc.doc_id}
              doc={doc}
              isActive={activeDocId === doc.doc_id}
              onClick={() => setActiveDocId(doc.doc_id)}
              onDelete={() => handleDelete(doc.doc_id)}
              index={i}
            />
          ))}
        </div>
      </aside>

      <main className="main-content">
        <div className="main-glow main-glow--1" />
        <div className="main-glow main-glow--2" />

        {showTabs && (
          <div className="tab-bar">
            {tabs.map(tab => (
              <button
                key={tab.id}
                className={`tab-btn ${activeTab === tab.id ? 'tab-btn--active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
                {tab.count !== undefined && tab.count > 0 && (
                  <span className="tab-pill">{tab.count}</span>
                )}
              </button>
            ))}
          </div>
        )}

        <div className="main-content__body">
          {renderMainArea()}
        </div>

        {showChatBar && (
          <div className="chat-input-bar">
            <div className="chat-input-bar__inner">
              {hasSpeechRecognition && (
                <button
                  onClick={isRecording ? stopRecording : startRecording}
                  className={`chat-input__btn voice-btn ${isRecording ? 'voice-btn--recording' : ''}`}
                  title={isRecording ? 'Stop recording' : 'Voice input'}
                >
                  {isRecording ? '⏹' : '🎙️'}
                </button>
              )}

              <input
                type="text"
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
                placeholder={isRecording ? 'Listening...' : 'Ask a question about the document...'}
                disabled={chatLoading}
                className="chat-input__field"
                style={{ flex: 1 }}
                autoFocus={activeTab === 'query'}
              />

              {hasSpeechSynthesis && (
                <button
                  onClick={() => { if (isSpeaking) stopSpeaking(); else setTtsEnabled(p => !p); }}
                  className={`chat-input__btn voice-btn ${isSpeaking ? 'voice-btn--recording' : ''}`}
                  title={isSpeaking ? 'Stop speaking' : ttsEnabled ? 'Auto-read ON' : 'Auto-read OFF'}
                  style={{ opacity: ttsEnabled || isSpeaking ? 1 : 0.45 }}
                >
                  {isSpeaking ? '⏸️' : ttsEnabled ? '🔊' : '🔇'}
                </button>
              )}

              <button
                onClick={() => handleSend()}
                disabled={!chatInput.trim() || chatLoading}
                className="chat-input__btn chat-input__send"
              >
                ↑
              </button>
            </div>
          </div>
        )}
      </main>

    </div>
  );
}