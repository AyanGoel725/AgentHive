import React, { useCallback, useRef, useState } from 'react';
import { uploadDocument } from '../api/client';
import type { DocumentMetadata } from '../types';

interface FileUploadProps {
  onUpload: (doc: DocumentMetadata) => void;
}

export default function FileUpload({ onUpload }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const validExts = ['.pdf', '.xlsx', '.xls', '.csv'];

  const handleFile = useCallback(async (file: File) => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!validExts.includes(ext)) {
      setError(`Unsupported file type. Use: ${validExts.join(', ')}`);
      return;
    }

    if (file.size > 50 * 1024 * 1024) {
       setError('File is too large. Maximum size is 50MB.');
       return;
    }

    setError('');
    setUploading(true);

    try {
      const result = await uploadDocument(file);
      onUpload(result.metadata);
      setUploading(false);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      setError(message);
      setUploading(false);
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
      <div className="sidebar__label" style={{ padding: 0, marginBottom: 8 }}>Upload Document</div>
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
          {uploading ? 'Uploading...' : 'Drop files here or click to browse'}
        </div>
        <div className="upload-zone__hint">PDF, XLSX, XLS, CSV (Max 50MB)</div>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.xlsx,.xls,.csv"
          onChange={handleInputChange}
        />
      </div>

      {error && (
        <div className="upload-error">
          {error}
        </div>
      )}
    </div>
  );
}
