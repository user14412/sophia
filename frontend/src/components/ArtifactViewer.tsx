import { FileJson, FileText } from 'lucide-react';
import { useMemo, useState } from 'react';
import type { ArtifactBundle } from '../types';

const TABS = ['source', 'log', 'topic', 'director', 'script', 'voice', 'images', 'video', 'manifest'] as const;
type ArtifactTab = (typeof TABS)[number];

function JsonBlock({ value }: { value: unknown }) {
  if (value === null || value === undefined) {
    return <p className="empty">No artifact.</p>;
  }
  return <pre className="jsonBlock">{JSON.stringify(value, null, 2)}</pre>;
}

function TopicView({ bundle }: { bundle: ArtifactBundle }) {
  if (!bundle.topic?.length) return <p className="empty">No topic artifact.</p>;
  return (
    <div className="artifactList">
      {bundle.topic.map((topic, index) => (
        <article className="artifactItem" key={String(topic.topic_id ?? index)}>
          <h3>{String(topic.topic_name ?? `Topic ${index + 1}`)}</h3>
          <p>{String(topic.core_concept ?? '')}</p>
          <small>{String(topic.zero_to_hero_logic ?? '')}</small>
        </article>
      ))}
    </div>
  );
}

function DirectorView({ bundle }: { bundle: ArtifactBundle }) {
  if (!bundle.director?.length) return <p className="empty">No director artifact.</p>;
  return (
    <div className="artifactList">
      {bundle.director.map((item, index) => {
        const stages = Array.isArray(item.stages) ? item.stages : [];
        return (
          <article className="artifactItem" key={`${String(item.topic_name ?? 'topic')}-${index}`}>
            <h3>{String(item.topic_name ?? `Director ${index + 1}`)}</h3>
            {stages.map((stage: Record<string, unknown>, stageIndex: number) => (
              <div className="nestedBlock" key={`${String(stage.stage_name ?? 'stage')}-${stageIndex}`}>
                <strong>{String(stage.stage_name ?? `Stage ${stageIndex + 1}`)}</strong>
                <ul>
                  {(Array.isArray(stage.bullets) ? stage.bullets : []).map((bullet: Record<string, unknown>, bulletIndex: number) => (
                    <li key={bulletIndex}>{String(bullet.intent ?? bullet.guidance ?? '')}</li>
                  ))}
                </ul>
              </div>
            ))}
          </article>
        );
      })}
    </div>
  );
}

function ScriptView({ bundle }: { bundle: ArtifactBundle }) {
  if (!bundle.script_text && !bundle.script_items) return <p className="empty">No script artifact.</p>;
  return (
    <div className="scriptGrid">
      <pre className="scriptText">{bundle.script_text ?? ''}</pre>
      <JsonBlock value={bundle.script_items} />
    </div>
  );
}

export function ArtifactViewer({ bundle }: { bundle: ArtifactBundle | null }) {
  const [tab, setTab] = useState<ArtifactTab>('topic');
  const filledCount = useMemo(() => {
    if (!bundle) return 0;
    return TABS.filter((key) => {
      if (key === 'script') return Boolean(bundle.script_text || bundle.script_items);
      if (key === 'source') return Boolean(bundle.source_upload);
      if (key === 'log') return Boolean(bundle.run_log);
      return Boolean(bundle[key]);
    }).length;
  }, [bundle]);

  return (
    <section className="panel artifactPanel">
      <div className="panelHeader">
        <FileText size={18} />
        <h2>Artifacts</h2>
        <span className="countPill">{filledCount}/9</span>
      </div>
      <div className="tabs">
        {TABS.map((item) => (
          <button className={item === tab ? 'active' : ''} key={item} onClick={() => setTab(item)}>
            <FileJson size={14} />
            <span>{item}</span>
          </button>
        ))}
      </div>
      {!bundle ? (
        <p className="empty">No session selected.</p>
      ) : (
        <div className="artifactContent">
          {tab === 'source' && <JsonBlock value={bundle.source_upload} />}
          {tab === 'log' && <pre className="scriptText">{bundle.run_log ?? 'No run log.'}</pre>}
          {tab === 'topic' && <TopicView bundle={bundle} />}
          {tab === 'director' && <DirectorView bundle={bundle} />}
          {tab === 'script' && <ScriptView bundle={bundle} />}
          {tab === 'voice' && <JsonBlock value={bundle.voice} />}
          {tab === 'images' && <JsonBlock value={bundle.images} />}
          {tab === 'video' && <JsonBlock value={bundle.video} />}
          {tab === 'manifest' && <JsonBlock value={bundle.manifest} />}
        </div>
      )}
    </section>
  );
}
