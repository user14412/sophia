import { FilePlus2, Play, RefreshCcw, RotateCcw } from 'lucide-react';

interface RunControlsProps {
  sessionId: string;
  stage: string;
  execution: 'mock' | 'real';
  loading: boolean;
  onSessionChange: (value: string) => void;
  onStageChange: (value: string) => void;
  onExecutionChange: (value: 'mock' | 'real') => void;
  onNewSession: () => void;
  onRunPipeline: () => void;
  onRunStage: () => void;
  onRefresh: () => void;
}

export function RunControls({
  sessionId,
  stage,
  execution,
  loading,
  onSessionChange,
  onStageChange,
  onExecutionChange,
  onNewSession,
  onRunPipeline,
  onRunStage,
  onRefresh
}: RunControlsProps) {
  return (
    <section className="toolbar" aria-label="运行控制">
      <div className="field">
        <label htmlFor="session-input">Session</label>
        <input
          id="session-input"
          value={sessionId}
          onChange={(event) => onSessionChange(event.target.value)}
          placeholder="frontend-demo"
        />
      </div>
      <button onClick={onNewSession} disabled={loading} title="Create a clean local session">
        <FilePlus2 size={16} />
        <span>New Session</span>
      </button>
      <div className="field compact">
        <label htmlFor="execution-select">Mode</label>
        <select
          id="execution-select"
          value={execution}
          onChange={(event) => onExecutionChange(event.target.value as 'mock' | 'real')}
        >
          <option value="mock">MOOC demo</option>
          <option value="real">Real pipeline</option>
        </select>
      </div>
      <button className="primary" onClick={onRunPipeline} disabled={loading || !sessionId.trim()}>
        <Play size={16} />
        <span>Run Pipeline</span>
      </button>
      <div className="field compact">
        <label htmlFor="stage-select">Stage</label>
        <select id="stage-select" value={stage} onChange={(event) => onStageChange(event.target.value)}>
          <option value="topic">topic</option>
          <option value="director">director</option>
          <option value="agent_speechers">agent_speechers</option>
          <option value="voice">voice</option>
          <option value="image">image</option>
          <option value="editor">editor</option>
        </select>
      </div>
      <button onClick={onRunStage} disabled={loading || !sessionId.trim()}>
        <RotateCcw size={16} />
        <span>Run Stage</span>
      </button>
      <button className="iconButton" onClick={onRefresh} disabled={loading} title="Refresh">
        <RefreshCcw size={16} />
      </button>
    </section>
  );
}
