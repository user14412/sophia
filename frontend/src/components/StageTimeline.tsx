import { GitBranch } from 'lucide-react';
import type { Manifest } from '../types';

const MAIN_STAGES = ['topic', 'director', 'agent_speechers', 'voice', 'image', 'editor'];
const LEGACY_STAGES = ['init', 'polish'];

export function StageTimeline({ manifest }: { manifest: Manifest | null }) {
  const stages = manifest?.stages ?? {};
  return (
    <section className="panel">
      <div className="panelHeader">
        <GitBranch size={18} />
        <h2>Pipeline</h2>
      </div>
      <div className="timeline">
        {MAIN_STAGES.map((stage) => {
          const status = stages[stage] ?? 'pending';
          return (
            <div className="stageStep" key={stage}>
              <span className={`statusDot ${status}`} />
              <div>
                <strong>{stage}</strong>
                <small className={`badge ${status}`}>{status}</small>
              </div>
            </div>
          );
        })}
      </div>
      <div className="legacyRow">
        {LEGACY_STAGES.map((stage) => (
          <span key={stage}>
            {stage}: <b>{stages[stage] ?? 'n/a'}</b>
          </span>
        ))}
      </div>
    </section>
  );
}
