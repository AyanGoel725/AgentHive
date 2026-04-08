import React, { useState, useEffect, useRef } from 'react';
import { exportUrls } from '../api/client';

interface ExportMenuProps {
  docId: string;
}

export default function ExportMenu({ docId }: ExportMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [isOpen]);

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    setIsOpen(false);
  };

  return (
    <div className="export-wrap" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="export-btn"
      >
        <span>⬇️</span> Export
      </button>

      {isOpen && (
        <div className="export-menu fade-in">
          <a
            href={exportUrls.markdown(docId)}
            download
            className="export-menu__item"
            onClick={() => setIsOpen(false)}
          >
            📄 Report (.md)
          </a>
          <a
            href={exportUrls.json(docId)}
            download
            className="export-menu__item"
            onClick={() => setIsOpen(false)}
          >
            {'{ }'} Raw Data (.json)
          </a>
          <button
            onClick={handleCopyLink}
            className="export-menu__item export-menu__item--btn"
            style={{ color: copied ? 'var(--success)' : undefined }}
          >
            {copied ? '✓ Link Copied' : '🔗 Copy Share Link'}
          </button>
        </div>
      )}
    </div>
  );
}
