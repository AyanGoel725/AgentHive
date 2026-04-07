import type { AgentInfo } from '../types';

interface AgentStatusProps {
  activeAgent: AgentInfo | null;
  processing: boolean;
}

const ALL_AGENTS = [
  { key: 'ingestion', icon: '📥', name: 'Ingestion' },
  { key: 'understanding', icon: '🧠', name: 'Understanding' },
  { key: 'summarization', icon: '✍️', name: 'Summary' },
  { key: 'extraction', icon: '🧾', name: 'Extraction' },
  { key: 'excel', icon: '📊', name: 'Excel Insight' },
  { key: 'voice', icon: '🔊', name: 'Voice' },
  { key: 'orchestrator', icon: '🎯', name: 'Orchestrator' },
];

export default function AgentStatus({ activeAgent, processing }: AgentStatusProps) {
  const getActiveKey = (): string | null => {
    if (!activeAgent) return null;
    const name = activeAgent.name.toLowerCase();
    if (name.includes('summar')) return 'summarization';
    if (name.includes('extract')) return 'extraction';
    if (name.includes('excel') || name.includes('insight')) return 'excel';
    if (name.includes('understand') || name.includes('search')) return 'understanding';
    if (name.includes('voice')) return 'voice';
    if (name.includes('orchestrat')) return 'orchestrator';
    if (name.includes('ingest')) return 'ingestion';
    return null;
  };

  const activeKey = processing ? getActiveKey() : null;

  return (
    <div className="agent-status">
      <div className="sidebar__title">Agent Pipeline</div>
      <div className="agent-status__pipeline">
        {ALL_AGENTS.map((agent, i) => (
          <span key={agent.key} style={{ display: 'contents' }}>
            <span
              className={`agent-badge ${activeKey === agent.key ? 'agent-badge--active' : ''}`}
            >
              {agent.icon} {agent.name}
            </span>
            {i < ALL_AGENTS.length - 1 && <span className="agent-arrow">→</span>}
          </span>
        ))}
      </div>
    </div>
  );
}
