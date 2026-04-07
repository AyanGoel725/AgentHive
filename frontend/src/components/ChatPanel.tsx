import { useState, useRef, useEffect, useCallback } from 'react';
import type { ChatMessage } from '../types';
import VoiceButton from './VoiceButton';

interface ChatPanelProps {
  messages: ChatMessage[];
  loading: boolean;
  hasDocument: boolean;
  onSendMessage: (text: string, voice?: boolean) => void;
}

const QUICK_ACTIONS = [
  { label: '✍️ Summarize', query: 'Summarize this document' },
  { label: '🧾 Extract Data', query: 'Extract structured data as JSON' },
  { label: '📊 Analyze Trends', query: 'Analyze this data for trends and insights' },
  { label: '🔍 Search', query: 'Search for key information' },
];

export default function ChatPanel({ messages, loading, hasDocument, onSendMessage }: ChatPanelProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = useCallback(() => {
    const text = input.trim();
    if (!text || loading) return;
    onSendMessage(text);
    setInput('');
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
    }
  }, [input, loading, onSendMessage]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Auto-resize
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  };

  const handleVoiceResult = (text: string) => {
    onSendMessage(text, true);
  };

  return (
    <div className="chat-panel">
      <div className="chat-panel__messages">
        {messages.length === 0 ? (
          <div className="chat-panel__empty">
            <div className="chat-panel__empty-icon">🐝</div>
            <div className="chat-panel__empty-title">Welcome to AgentHive</div>
            <div className="chat-panel__empty-hint">
              {hasDocument
                ? 'Your document is ready! Ask a question or use a quick action below.'
                : 'Upload a PDF or Excel file to get started. Our AI agents will analyze it for you.'}
            </div>
            {hasDocument && (
              <div className="quick-actions">
                {QUICK_ACTIONS.map((action) => (
                  <button
                    key={action.label}
                    className="quick-action"
                    onClick={() => onSendMessage(action.query)}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <div key={msg.id} className={`message message--${msg.role}`}>
                <div className="message__avatar">
                  {msg.role === 'user' ? '👤' : msg.agent?.icon || '🤖'}
                </div>
                <div className="message__content">
                  {msg.role === 'agent' && msg.agent && (
                    <div className="message__agent-name">
                      {msg.agent.icon} {msg.agent.name}
                    </div>
                  )}
                  <div className="message__bubble">{msg.content}</div>
                </div>
              </div>
            ))}

            {loading && (
              <div className="message message--agent">
                <div className="message__avatar">🤖</div>
                <div className="message__content">
                  <div className="message__bubble">
                    <div className="typing-indicator">
                      <div className="typing-indicator__dot" />
                      <div className="typing-indicator__dot" />
                      <div className="typing-indicator__dot" />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input">
        <textarea
          ref={inputRef}
          id="chat-input-field"
          className="chat-input__field"
          placeholder={hasDocument ? 'Ask about your document...' : 'Upload a document first...'}
          value={input}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          disabled={!hasDocument || loading}
          rows={1}
        />
        <VoiceButton onResult={handleVoiceResult} disabled={!hasDocument || loading} />
        <button
          id="send-btn"
          className="chat-input__btn chat-input__send"
          onClick={handleSend}
          disabled={!input.trim() || loading || !hasDocument}
          title="Send message"
        >
          ↑
        </button>
      </div>
    </div>
  );
}
