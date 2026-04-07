import { useState, useCallback } from 'react';
import type { ChatMessage } from '../types';

interface OutputDisplayProps {
  messages: ChatMessage[];
}

type Tab = 'summary' | 'json' | 'insights' | 'raw';

export default function OutputDisplay({ messages }: OutputDisplayProps) {
  const [activeTab, setActiveTab] = useState<Tab>('summary');
  const [copied, setCopied] = useState(false);

  // Find last agent message with each type of data
  const lastAgentMsg = [...messages].reverse().find(m => m.role === 'agent');
  const lastJsonMsg = [...messages].reverse().find(m => m.role === 'agent' && m.structured_data);
  const lastInsightMsg = [...messages].reverse().find(m => m.role === 'agent' && m.insights);

  const tabs: { id: Tab; label: string; enabled: boolean }[] = [
    { id: 'summary', label: '✍️ Summary', enabled: !!lastAgentMsg },
    { id: 'json', label: '🧾 JSON', enabled: !!lastJsonMsg },
    { id: 'insights', label: '📊 Insights', enabled: !!lastInsightMsg },
    { id: 'raw', label: '📝 Raw', enabled: !!lastAgentMsg },
  ];

  const handleCopy = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, []);

  const renderJson = (data: Record<string, unknown>) => {
    const json = JSON.stringify(data, null, 2);
    // Simple syntax highlighting
    const highlighted = json
      .replace(/"([^"]+)":/g, '<span class="json-key">"$1"</span>:')
      .replace(/: "([^"]+)"/g, ': <span class="json-string">"$1"</span>')
      .replace(/: (\d+\.?\d*)/g, ': <span class="json-number">$1</span>')
      .replace(/: (true|false)/g, ': <span class="json-boolean">$1</span>')
      .replace(/: (null)/g, ': <span class="json-null">$1</span>');
    return highlighted;
  };

  const renderInsights = (insights: Record<string, unknown>) => {
    const cards: JSX.Element[] = [];

    // Row/column count
    if (insights.row_count) {
      cards.push(
        <div key="rows" className="insight-card">
          <div className="insight-card__title">📋 Dataset Size</div>
          <div className="insight-card__value">{String(insights.row_count)} rows × {String(insights.column_count)} cols</div>
        </div>
      );
    }

    // Top values
    const topValues = insights.top_values as Record<string, Record<string, number>> | undefined;
    if (topValues) {
      Object.entries(topValues).slice(0, 4).forEach(([col, vals]) => {
        cards.push(
          <div key={`top-${col}`} className="insight-card">
            <div className="insight-card__title">📈 {col}</div>
            <div className="insight-card__value">
              {vals.mean != null ? vals.mean.toFixed(2) : '—'}
            </div>
            <div className="insight-card__detail">
              Min: {vals.min?.toFixed(2) ?? '—'} &nbsp;|&nbsp; Max: {vals.max?.toFixed(2) ?? '—'} &nbsp;|&nbsp; Median: {vals.median?.toFixed(2) ?? '—'}
            </div>
          </div>
        );
      });
    }

    // Correlations
    const correlations = insights.correlations as Array<{ col1: string; col2: string; correlation: number; strength: string }> | undefined;
    if (correlations && correlations.length > 0) {
      correlations.slice(0, 3).forEach((c, i) => {
        cards.push(
          <div key={`corr-${i}`} className="insight-card">
            <div className="insight-card__title">🔗 Correlation</div>
            <div className={`insight-card__value ${c.correlation > 0 ? 'trend-up' : 'trend-down'}`}>
              {c.correlation > 0 ? '↑' : '↓'} {c.correlation.toFixed(3)}
            </div>
            <div className="insight-card__detail">
              {c.col1} ↔ {c.col2} ({c.strength})
            </div>
          </div>
        );
      });
    }

    // Columns
    const columns = insights.columns as string[] | undefined;
    if (columns) {
      cards.push(
        <div key="columns" className="insight-card">
          <div className="insight-card__title">🏷️ Columns</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
            {columns.map(col => (
              <span key={col} style={{
                padding: '4px 10px',
                borderRadius: 12,
                background: 'var(--glass-bg)',
                border: '1px solid var(--border-subtle)',
                fontSize: 12,
                color: 'var(--text-secondary)'
              }}>{col}</span>
            ))}
          </div>
        </div>
      );
    }

    return cards.length > 0 ? cards : (
      <div className="empty-state">
        <div className="empty-state__icon">📊</div>
        <div className="empty-state__text">No structured insights available</div>
      </div>
    );
  };

  return (
    <>
      <div className="output-panel__tabs">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`output-tab ${activeTab === tab.id ? 'output-tab--active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
            disabled={!tab.enabled}
            style={{ opacity: tab.enabled ? 1 : 0.4 }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="output-panel__content">
        {!lastAgentMsg ? (
          <div className="empty-state">
            <div className="empty-state__icon">🔮</div>
            <div className="empty-state__text">
              Agent responses will appear here.<br />
              Upload a document and ask a question to get started.
            </div>
          </div>
        ) : (
          <div className="fade-in">
            {activeTab === 'summary' && lastAgentMsg && (
              <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7, fontSize: 14 }}>
                {lastAgentMsg.content}
              </div>
            )}

            {activeTab === 'json' && lastJsonMsg?.structured_data && (
              <>
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
                  <button
                    className={`copy-btn ${copied ? 'copy-btn--copied' : ''}`}
                    onClick={() => handleCopy(JSON.stringify(lastJsonMsg.structured_data, null, 2))}
                  >
                    {copied ? '✓ Copied' : '📋 Copy JSON'}
                  </button>
                </div>
                <div
                  className="json-viewer"
                  dangerouslySetInnerHTML={{ __html: renderJson(lastJsonMsg.structured_data) }}
                />
              </>
            )}

            {activeTab === 'insights' && lastInsightMsg?.insights && (
              <div>{renderInsights(lastInsightMsg.insights)}</div>
            )}

            {activeTab === 'raw' && lastAgentMsg && (
              <div className="json-viewer" style={{ fontSize: 12 }}>
                {JSON.stringify(
                  {
                    agent: lastAgentMsg.agent,
                    content: lastAgentMsg.content.slice(0, 500),
                    structured_data: lastAgentMsg.structured_data || null,
                    insights: lastAgentMsg.insights || null,
                  },
                  null,
                  2,
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}
