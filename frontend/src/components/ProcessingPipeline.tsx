import React, { useState, useEffect } from 'react';

interface ProcessingPipelineProps {
  status: string;
}

export default function ProcessingPipeline({ status }: ProcessingPipelineProps) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const start = Date.now();
    const interval = setInterval(() => {
      setElapsed(Math.round((Date.now() - start) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const steps = [
    { key: 'ingesting', icon: '📥', label: 'Ingesting Document', desc: 'Reading all pages & content' },
    { key: 'classifying', icon: '🏷️', label: 'Classifying & Indexing', desc: 'Detecting type + building search index' },
    { key: 'summarizing', icon: '✍️', label: 'Analyzing & Summarizing', desc: 'Generating summary + extracting data' },
    { key: 'extracting', icon: '🧾', label: 'Extracting Questions', desc: 'Finding questions in forms' },
  ];

  const getStepState = (stepKey: string, currentStatus: string) => {
    if (currentStatus === 'complete') return 'complete';
    if (currentStatus === 'error') return 'error';

    const statusToStep: Record<string, number> = {
      pending: -1, ingesting: 0, classifying: 1, indexing: 1, summarizing: 2, extracting: 3
    };
    const currentStep = statusToStep[currentStatus] ?? -1;
    const stepIndex = steps.findIndex(s => s.key === stepKey);

    if (stepIndex < currentStep) return 'complete';
    if (stepIndex === currentStep) return 'active';
    return 'waiting';
  };

  return (
    <div className="pipeline-container">
      <div className="pipeline-header">
        <div className="pipeline-spinner" />
        <h3 style={{ marginBottom: 4, fontSize: 18, fontWeight: 600, letterSpacing: '-0.02em' }}>
          Processing Document
        </h3>
        <div style={{ fontSize: 13, color: 'var(--text-3)' }}>
          Elapsed: <span style={{ color: 'var(--accent)', fontWeight: 600 }}>{elapsed}s</span>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
        {steps.map((step, i) => {
          const state = getStepState(step.key, status);

          return (
            <React.Fragment key={step.key}>
              <div
                className={`pipeline-step pipeline-step--${state}`}
                style={{ animationDelay: `${i * 0.1}s` }}
              >
                <div className="pipeline-step__num">
                  {state === 'complete' ? '✓' : state === 'error' ? '✕' : i + 1}
                </div>

                <div style={{ flex: 1, textAlign: 'left' }}>
                  <div className="pipeline-step__label">{step.label}</div>
                  <div className="pipeline-step__desc">{step.desc}</div>
                </div>

                <div style={{ width: 24 }}>
                  {state === 'active' && (
                    <div className="pipeline-dot-pulse" />
                  )}
                </div>
              </div>

              {/* Connector line */}
              {i < steps.length - 1 && (
                <div className={`pipeline-connector ${state === 'complete' ? 'pipeline-connector--done' : ''}`} />
              )}
            </React.Fragment>
          );
        })}
      </div>

      <div className="pipeline-info-card">
        💡 Multiple AI agents are working in parallel to analyze your document faster
      </div>
    </div>
  );
}
