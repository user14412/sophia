import { Activity, AlertTriangle, CheckCircle2 } from 'lucide-react';
import type { HealthCheck, HealthSummary } from '../types';

function HealthList({ title, checks }: { title: string; checks: HealthCheck[] }) {
  return (
    <div className="healthGroup">
      <h3>{title}</h3>
      <div className="healthItems">
        {checks.map((item) => {
          const className = item.available ? 'ok' : item.required ? 'danger' : 'muted';
          const Icon = item.available ? CheckCircle2 : AlertTriangle;
          return (
            <div className={`healthItem ${className}`} key={`${title}-${item.name}`}>
              <Icon size={16} />
              <div>
                <div className="healthTitle">
                  <span>{item.name}</span>
                  <small>{item.required ? 'required' : 'optional'}</small>
                </div>
                <p>{item.message}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function HealthPanel({ health }: { health: HealthSummary | null }) {
  return (
    <section className="panel">
      <div className="panelHeader">
        <Activity size={18} />
        <h2>Runtime Health</h2>
      </div>
      {!health ? (
        <p className="empty">No health data.</p>
      ) : (
        <div className="healthGrid">
          <HealthList title="demo" checks={health.demo} />
          <HealthList title="full" checks={health.full} />
        </div>
      )}
    </section>
  );
}
