import React from 'react';

interface ConfidenceBarProps {
  value: number; // 0-1
  label?: string;
  size?: 'sm' | 'md';
}

export default function ConfidenceBar({ value, label, size = 'md' }: ConfidenceBarProps) {
  const pct = Math.round(value * 100);
  const height = size === 'sm' ? 4 : 6;

  const getColor = () => {
    if (pct >= 80) return 'var(--success)';
    if (pct >= 60) return 'var(--warning)';
    return 'var(--danger)';
  };

  return (
    <div className="confidence-bar">
      {label && (
        <span className="confidence-bar__label">{label}</span>
      )}
      <div className="confidence-bar__track" style={{ height }}>
        <div className="confidence-bar__fill" style={{
          width: `${pct}%`,
          background: getColor(),
          boxShadow: `0 0 8px ${getColor()}40`,
        }} />
      </div>
      <span className="confidence-bar__value" style={{ color: getColor() }}>
        {pct}%
      </span>
    </div>
  );
}
