import React, { useState } from 'react';
import type { QuestionExtractionResult, ExtractedQuestion, QuestionCategory } from '../types';

interface QuestionExplorerProps {
  data: QuestionExtractionResult;
}

export default function QuestionExplorer({ data }: QuestionExplorerProps) {
  const [filter, setFilter] = useState<QuestionCategory | 'all'>('all');
  const [search, setSearch] = useState('');

  if (!data || data.total_questions === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state__icon">📝</div>
        <div className="empty-state__text">
          No questions were found in this document.<br/>
          (Only forms and questionnaires typically contain extractable questions.)
        </div>
      </div>
    );
  }

  const categoryLabels: Record<QuestionCategory | 'all', string> = {
    all: 'All',
    open_ended: 'Open Ended',
    multiple_choice: 'Multiple Choice',
    rating: 'Rating Scale',
    yes_no: 'Yes / No',
    fill_in: 'Fill-in Text',
    demographic: 'Demographic',
    section_header: 'Section',
    unknown: 'Other'
  };

  // Build category counts
  const catCounts: Record<string, number> = { all: data.total_questions };
  const countCats = (qs: ExtractedQuestion[]) => {
    for (const q of qs) {
      if (q.category !== 'section_header') {
        catCounts[q.category] = (catCounts[q.category] || 0) + 1;
      }
      countCats(q.sub_questions);
    }
  };
  countCats(data.questions);

  // Filter fn
  const matchQuestion = (q: ExtractedQuestion): boolean => {
    if (q.category === 'section_header') return true;
    const matchesCat = filter === 'all' || q.category === filter;
    const matchesSearch = q.text.toLowerCase().includes(search.toLowerCase()) || 
                          (q.number && q.number.toLowerCase().includes(search.toLowerCase()));
    return matchesCat && !!matchesSearch;
  };

  // Track question numbering for display
  let questionCounter = 0;

  // Render a single question (recursive for sub-questions)
  const renderQuestion = (q: ExtractedQuestion, depth: number = 0) => {
    if (q.category === 'section_header') {
      return (
        <div key={q.question_id} className="qe-section-header">
          {q.text}
        </div>
      );
    }

    if (!matchQuestion(q) && q.sub_questions.length === 0) return null;

    questionCounter++;
    const currentNum = q.number || String(questionCounter);

    return (
      <div
        key={q.question_id}
        className={`qe-item ${q.is_required ? 'qe-item--required' : ''}`}
        style={{ marginLeft: depth * 24 }}
      >
        <div className="qe-item__num">{currentNum}</div>
        <div className="qe-item__body">
          <div className="qe-item__text">
            {q.text}
            {q.is_required && <span className="qe-item__required">*</span>}
          </div>

          {q.options && q.options.length > 0 && (
            <div style={{ marginTop: 8, display: 'grid', gap: 4 }}>
              {q.options.map((opt, i) => (
                <div key={i} className="qe-option">
                  <div className="qe-option__circle" />
                  {opt}
                </div>
              ))}
            </div>
          )}

          {q.sub_questions.length > 0 && (
            <div style={{ marginTop: 12 }}>
              {q.sub_questions.map(sq => renderQuestion(sq, depth + 1))}
            </div>
          )}
        </div>
        <div className="qe-item__cat">{categoryLabels[q.category]}</div>
      </div>
    );
  };

  return (
    <div className="fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h3 className="section-heading" style={{ marginBottom: 0 }}>
          Extracted Questions ({data.total_questions})
        </h3>
        <div style={{ fontSize: 12, color: 'var(--text-3)' }}>
          Confidence: {Math.round(data.extraction_confidence * 100)}%
        </div>
      </div>

      {/* Toolbar: Search + Filters */}
      <div className="qe-toolbar">
        <div className="qe-search-wrap">
          <span className="qe-search-icon">🔍</span>
          <input
            type="text"
            placeholder="Search questions..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="qe-search"
          />
        </div>
        {(Object.keys(catCounts) as (QuestionCategory | 'all')[]).map(cat => (
          <button
            key={cat}
            onClick={() => setFilter(cat)}
            className={`qe-filter-btn ${filter === cat ? 'qe-filter-btn--active' : ''}`}
          >
            {categoryLabels[cat]} ({catCounts[cat]})
          </button>
        ))}
      </div>

      {/* List */}
      <div style={{ paddingBottom: 40 }}>
        {data.questions.map(q => renderQuestion(q))}
      </div>
    </div>
  );
}
