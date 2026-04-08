import React, { useState } from 'react';

interface JsonViewerProps {
  data: Record<string, unknown>;
}

export default function JsonViewer({ data }: JsonViewerProps) {
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set(['root']));
  const [copied, setCopied] = useState(false);

  const toggleKey = (key: string) => {
    setExpandedKeys(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const expandAll = () => {
    const keys = new Set<string>();
    const walk = (obj: unknown, prefix: string) => {
      keys.add(prefix);
      if (obj && typeof obj === 'object') {
        Object.keys(obj as Record<string, unknown>).forEach(k => walk((obj as Record<string, unknown>)[k], `${prefix}.${k}`));
      }
    };
    walk(data, 'root');
    setExpandedKeys(keys);
  };

  const collapseAll = () => {
    setExpandedKeys(new Set(['root']));
  };

  const renderValue = (value: unknown, path: string, depth: number): React.ReactNode => {
    if (value === null || value === undefined) {
      return <span className="json-null">null</span>;
    }

    if (typeof value === 'boolean') {
      return <span className="json-boolean">{value.toString()}</span>;
    }

    if (typeof value === 'number') {
      return <span className="json-number">{value}</span>;
    }

    if (typeof value === 'string') {
      const display = value.length > 120 ? value.slice(0, 120) + '...' : value;
      return <span className="json-string">"{display}"</span>;
    }

    if (Array.isArray(value)) {
      if (value.length === 0) return <span className="json-null">[]</span>;

      const isExpanded = expandedKeys.has(path);
      return (
        <span>
          <button
            onClick={() => toggleKey(path)}
            className="json-toggle"
          >
            {isExpanded ? '▼' : '▶'}
          </button>
          <span className="json-bracket">[</span>
          {!isExpanded && (
            <span className="json-collapsed" onClick={() => toggleKey(path)}>
              {value.length} items
            </span>
          )}
          {isExpanded && (
            <div style={{ paddingLeft: 20 }}>
              {value.map((item, i) => (
                <div key={i} className="json-line">
                  {renderValue(item, `${path}[${i}]`, depth + 1)}
                  {i < value.length - 1 && <span className="json-comma">,</span>}
                </div>
              ))}
            </div>
          )}
          <span className="json-bracket">]</span>
        </span>
      );
    }

    if (typeof value === 'object') {
      const entries = Object.entries(value as Record<string, unknown>);
      if (entries.length === 0) return <span className="json-null">{'{}'}</span>;

      const isExpanded = expandedKeys.has(path);
      return (
        <span>
          <button
            onClick={() => toggleKey(path)}
            className="json-toggle"
          >
            {isExpanded ? '▼' : '▶'}
          </button>
          <span className="json-bracket">{'{'}</span>
          {!isExpanded && (
            <span className="json-collapsed" onClick={() => toggleKey(path)}>
              {entries.length} fields
            </span>
          )}
          {isExpanded && (
            <div style={{ paddingLeft: 20 }}>
              {entries.map(([key, val], i) => (
                <div key={key} className="json-line">
                  <span className="json-key">"{key}"</span>
                  <span className="json-colon">: </span>
                  {renderValue(val, `${path}.${key}`, depth + 1)}
                  {i < entries.length - 1 && <span className="json-comma">,</span>}
                </div>
              ))}
            </div>
          )}
          <span className="json-bracket">{'}'}</span>
        </span>
      );
    }

    return <span>{String(value)}</span>;
  };

  if (!data || Object.keys(data).length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state__icon">📦</div>
        <div className="empty-state__text">No structured data was extracted from this document.</div>
      </div>
    );
  }

  return (
    <div className="fade-in">
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 16
      }}>
        <h3 className="section-heading" style={{ marginBottom: 0 }}>
          <span className="section-heading__icon">📦</span> Extracted Structured Data
        </h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={expandAll} className="json-action-btn">Expand All</button>
          <button onClick={collapseAll} className="json-action-btn">Collapse All</button>
          <button
            onClick={handleCopy}
            className={`json-action-btn ${copied ? 'json-action-btn--copied' : ''}`}
          >
            {copied ? '✓ Copied' : '📋 Copy JSON'}
          </button>
        </div>
      </div>

      <div className="json-viewer">
        {renderValue(data, 'root', 0)}
      </div>
    </div>
  );
}
