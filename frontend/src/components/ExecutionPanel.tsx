import { ActivitySquare } from 'lucide-react';
import type { ArtifactBundle } from '../types';

interface ExecutionPanelProps {
  execution: 'mock' | 'real';
  loading: boolean;
  bundle: ArtifactBundle | null;
}

export function ExecutionPanel({ execution, loading, bundle }: ExecutionPanelProps) {
  const manifest = bundle?.manifest;
  const sourcePath = bundle?.source_upload?.path ?? manifest?.config_snapshot?.uploaded_source;
  const sourcePathText = sourcePath ? String(sourcePath) : '';
  const recentLog = bundle?.run_log?.trim().split('\n').slice(-4).join('\n') || 'No backend log yet.';

  return (
    <section className="panel">
      <div className="panelHeader">
        <ActivitySquare size={16} />
        <h2>Execution</h2>
      </div>
      <div className="executionGrid">
        <div>
          <span>Mode</span>
          <strong>{execution === 'real' ? 'Real pipeline' : 'MOOC demo'}</strong>
        </div>
        <div>
          <span>Status</span>
          <strong>{loading ? 'running' : manifest ? 'ready' : 'idle'}</strong>
        </div>
        <div>
          <span>Source</span>
          <strong>{sourcePathText ? 'uploaded' : 'default or missing'}</strong>
          {sourcePathText && <small>{sourcePathText}</small>}
        </div>
        <div>
          <span>Logger</span>
          <strong>log/execution</strong>
          <small>Check the newest run_*.log file while Real pipeline is running.</small>
        </div>
      </div>
      <pre className="miniLog">{recentLog}</pre>
    </section>
  );
}
