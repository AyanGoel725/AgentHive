import React from 'react';
import type { DocumentType } from '../types';

interface DocumentTypeTagProps {
  type: DocumentType;
  size?: 'sm' | 'md';
}

const typeConfig: Record<DocumentType, { icon: string; color: string; bg: string }> = {
  questionnaire: { icon: '📋', color: '#a78bfa', bg: 'rgba(167,139,250,0.12)' },
  form: { icon: '📝', color: '#22d3ee', bg: 'rgba(34,211,238,0.12)' },
  report: { icon: '📊', color: '#60a5fa', bg: 'rgba(96,165,250,0.12)' },
  spreadsheet: { icon: '📈', color: '#34d399', bg: 'rgba(52,211,153,0.12)' },
  presentation: { icon: '🎬', color: '#fbbf24', bg: 'rgba(251,191,36,0.12)' },
  contract: { icon: '📜', color: '#f472b6', bg: 'rgba(244,114,182,0.12)' },
  invoice: { icon: '🧾', color: '#fb923c', bg: 'rgba(251,146,60,0.12)' },
  resume: { icon: '👤', color: '#818cf8', bg: 'rgba(129,140,248,0.12)' },
  academic: { icon: '🎓', color: '#a78bfa', bg: 'rgba(167,139,250,0.12)' },
  technical: { icon: '⚙️', color: '#94a3b8', bg: 'rgba(148,163,184,0.12)' },
  unknown: { icon: '📄', color: '#6b7280', bg: 'rgba(107,114,128,0.12)' },
};

export default function DocumentTypeTag({ type, size = 'md' }: DocumentTypeTagProps) {
  const config = typeConfig[type] || typeConfig.unknown;
  const fontSize = size === 'sm' ? 11 : 13;
  const padding = size === 'sm' ? '2px 8px' : '4px 12px';

  return (
    <span
      className="doc-type-tag"
      style={{
        padding,
        fontSize,
        color: config.color,
        background: config.bg,
        border: `1px solid ${config.color}25`,
      }}
    >
      <span style={{ fontSize: size === 'sm' ? 12 : 14 }}>{config.icon}</span>
      {type}
    </span>
  );
}
