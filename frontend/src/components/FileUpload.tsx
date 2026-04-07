import React, { useCallback, useRef, useState } from 'react';
import { uploadDocument } from '../api/client';
import type { DocumentMeta } from '../types';

interface FileUploadProps {
  onUpload: (doc: DocumentMeta) => void;
}

export default function FileUpload({ onUpload }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const validExts = ['.pdf', '.xlsx', '.xls', '.csv'];

  const handleFile = useCallback(async (file: File) => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!validExts.includes(ext)) {
      setError(`Unsupported file type. Use: ${validExts.join(', ')}`);
      return;
    }

    setError('');
    setUploading(true);
    setProgress(20);

    try {
      // Simulate progress stages
      const progressTimer = setInterval(() => {
        setProgress(prev => Math.min(prev + 15, 85));
      }, 300);

      const result = await uploadDocument(file);
      clearInterval(progressTimer);
      setProgress(100);

      if (result.success) {
        onUpload(result.document);
        setTimeout(() => {
          setUploading(false);
          setProgress(0);
        }, 600);
      } else {
        throw new Error(result.message || 'Upload failed');
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      setError(message);
      setUploading(false);
      setProgress(0);
    }
  }, [onUpload]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleClick = () => inputRef.current?.click();

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = '';
  };

  return (
    <div className="sidebar__section">
      <div className="sidebar__title">Upload Document</div>
      <div
        id="upload-zone"
        className={`upload-zone ${isDragging ? 'upload-zone--active' : ''}`}
        onClick={handleClick}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <div className="upload-zone__icon">{uploading ? '⏳' : '📄'}</div>
        <div className="upload-zone__text">
          {uploading ? 'Processing document...' : 'Drop files here or click to browse'}
        </div>
        <div className="upload-zone__hint">PDF, XLSX, XLS, CSV</div>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.xlsx,.xls,.csv"
          onChange={handleInputChange}
        />

        {uploading && (
          <div className="upload-progress">
            <div className="upload-progress__bar">
              <div
                className="upload-progress__fill"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {error && (
        <div style={{
          marginTop: 8,
          fontSize: 12,
          color: 'var(--accent-rose)',
          padding: '8px 12px',
          borderRadius: 'var(--radius-sm)',
          background: 'rgba(251,113,133,0.08)',
        }}>
          {error}
        </div>
      )}
    </div>
  );
}
