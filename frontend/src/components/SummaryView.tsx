import type { FullAnalysisResult } from '../types';
import ConfidenceBar from './ConfidenceBar';
import DocumentTypeTag from './DocumentTypeTag';

interface SummaryViewProps {
  analysis: FullAnalysisResult;
}

export default function SummaryView({ analysis }: SummaryViewProps) {
  const { summary, classification, metadata } = analysis;

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
  };

  return (
    <div className="fade-in" style={{ paddingBottom: 40 }}>
      {/* Stats Cards Row */}
      <div className="summary-stats-grid">
        <div className="stat-card">
          <div className="stat-card__label">Document Type</div>
          <div style={{ marginTop: 6 }}>
            <DocumentTypeTag type={classification.document_type} size="md" />
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card__label">Classification Confidence</div>
          <div style={{ marginTop: 8 }}>
            <ConfidenceBar value={classification.confidence} size="md" />
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card__label">Word Count (Approx)</div>
          <div className="stat-card__value">{summary.word_count_original.toLocaleString()}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card__label">Reading Time</div>
          <div className="stat-card__value">~{analysis.processing_time_seconds} s</div>
        </div>
        <div className="stat-card">
          <div className="stat-card__label">File Size</div>
          <div className="stat-card__value">{formatBytes(metadata.file_size_bytes)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card__label">Tone</div>
          <div className="stat-card__value" style={{ textTransform: 'capitalize' }}>
            {summary.sentiment === 'positive' ? '😊' : summary.sentiment === 'negative' ? '😟' : '😐'}{' '}
            {summary.sentiment}
          </div>
        </div>
      </div>

      {/* Executive Summary Card */}
      <div className="exec-summary-card">
        <div className="exec-summary-card__bar" />
        <h3 className="section-heading" style={{ marginBottom: 12 }}>
          <span className="section-heading__icon">✨</span> Executive Summary
        </h3>
        <div className="exec-summary-card__text">
          {summary.executive_summary}
        </div>
      </div>

      {/* Topics */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 28 }}>
        {summary.topics.map(t => (
          <span key={t} className="topic-tag">
            {t}
          </span>
        ))}
      </div>

      {/* Key Points */}
      <h3 className="section-heading">
        <span className="section-heading__icon">📌</span> Key Points
      </h3>
      <div style={{ display: 'grid', gap: 4, marginBottom: 28 }}>
        {summary.key_points.map((kp, i) => (
          <div key={i} className="key-point">
            <div className={`key-point__dot key-point__dot--${kp.importance}`} />
            <div>
              <div className="key-point__text">{kp.point}</div>
              {kp.page_reference && (
                <div className="key-point__ref">📄 {kp.page_reference}</div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Detailed Summary */}
      <h3 className="section-heading">
        <span className="section-heading__icon">📖</span> Detailed Breakdown
      </h3>
      <div className="detailed-summary">
        {summary.detailed_summary}
      </div>

      {/* Compression Ratio */}
      {summary.summary_compression_ratio > 0 && (
        <div className="compression-note">
          Compression ratio: {Math.round(summary.summary_compression_ratio * 100)}% of original
          ({summary.word_count_original.toLocaleString()} words → ~{Math.round(summary.word_count_original * summary.summary_compression_ratio).toLocaleString()} words)
        </div>
      )}
    </div>
  );
}
