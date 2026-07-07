import { Activity, Zap } from 'lucide-react';
import type { SmokeTestResult } from '../types';

interface SmokePanelProps {
  loading: boolean;
  results: Record<string, SmokeTestResult>;
  onRun: (target: string) => void;
}

const TARGETS = [
  { id: 'llm', label: 'LLM' },
  { id: 'tts', label: 'TTS' },
  { id: 'ffmpeg', label: 'FFmpeg' },
  { id: 'image', label: 'Image Config' }
];

export function SmokePanel({ loading, results, onRun }: SmokePanelProps) {
  return (
    <section className="panel">
      <div className="panelHeader">
        <Activity size={16} />
        <h2>Smoke Tests</h2>
      </div>
      <div className="smokeGrid">
        {TARGETS.map((target) => {
          const result = results[target.id];
          return (
            <div className="smokeItem" key={target.id}>
              <div>
                <strong>{target.label}</strong>
                <p className={result ? (result.ok ? 'okText' : 'badText') : ''}>
                  {result ? `${result.message} (${result.elapsed_ms} ms)` : 'Not tested'}
                </p>
              </div>
              <button disabled={loading} onClick={() => onRun(target.id)}>
                <Zap size={15} />
                <span>Test</span>
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
}
