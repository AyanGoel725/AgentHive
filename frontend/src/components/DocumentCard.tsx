import React from 'react';
import type { DocumentMetadata } from '../types';

interface DocumentCardProps {
  doc: DocumentMetadata;
  isActive: boolean;
  onClick: () => void;
  onDelete: () => void;
  index?: number;
}

export default function DocumentCard({ doc, isActive, onClick, onDelete, index = 0 }: DocumentCardProps) {
  const getIcon = () => {
    switch (doc.file_type) {
      case 'pdf': return '📄';
      case 'excel': return '📊';
      case 'csv': return '📑';
      default: return '📄';
    }
  };

  const getMetaString = () => {
    const size = (doc.file_size_bytes / 1024 / 1024).toFixed(1) + 'MB';
    if (doc.file_type === 'pdf' && doc.page_count) return `${size} • ${doc.page_count} pages`;
    if (doc.row_count) return `${size} • ${doc.row_count} rows`;
    return size;
  };

  return (
    <div
      onClick={onClick}
      className={`doc-item ${isActive ? 'doc-item--active' : ''}`}
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <div className={`doc-item__icon doc-item__icon--${doc.file_type}`}>
        {getIcon()}
      </div>
      <div className="doc-item__info">
        <div className="doc-item__name" title={doc.filename}>{doc.filename}</div>
        <div className="doc-item__meta">{getMetaString()}</div>
      </div>
      <button
        className="doc-item__delete"
        onClick={(e) => { e.stopPropagation(); onDelete(); }}
        title="Delete Document"
      >
        ✕
      </button>
    </div>
  );
}
