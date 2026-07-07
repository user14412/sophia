import { Database, Loader2, Podcast } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import {
  getArtifacts,
  getHealth,
  getSession,
  listSessions,
  runFull,
  runSmokeTest,
  runStage,
  uploadSource,
  uploadStageInput
} from './api';
import { ArtifactViewer } from './components/ArtifactViewer';
import { EngineeringPanel } from './components/EngineeringPanel';
import { ExecutionPanel } from './components/ExecutionPanel';
import { HealthPanel } from './components/HealthPanel';
import { RunControls } from './components/RunControls';
import { SmokePanel } from './components/SmokePanel';
import { StageTimeline } from './components/StageTimeline';
import { UploadPanel } from './components/UploadPanel';
import type { ArtifactBundle, HealthSummary, Manifest, SessionSummary, SmokeTestResult } from './types';

const DEFAULT_SESSION = 'frontend-demo';

export default function App() {
  const [sessionId, setSessionId] = useState(DEFAULT_SESSION);
  const [stage, setStage] = useState('voice');
  const [execution, setExecution] = useState<'mock' | 'real'>('mock');
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [health, setHealth] = useState<HealthSummary | null>(null);
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [artifacts, setArtifacts] = useState<ArtifactBundle | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [smokeResults, setSmokeResults] = useState<Record<string, SmokeTestResult>>({});

  const selectedSession = useMemo(
    () => sessions.find((item) => item.session_id === sessionId),
    [sessions, sessionId]
  );

  async function refreshSessions() {
    const data = await listSessions();
    setSessions(data);
  }

  async function loadSession(target = sessionId) {
    if (!target.trim()) return;
    setError(null);
    setManifest(null);
    setArtifacts(null);
    try {
      const [manifestData, artifactData] = await Promise.all([getSession(target), getArtifacts(target)]);
      setManifest(manifestData);
      setArtifacts(artifactData);
    } catch (caught) {
      setManifest(null);
      setArtifacts(null);
      const text = caught instanceof Error ? caught.message : String(caught);
      if (!text.includes('does not have a manifest')) {
        setError(text);
      }
    }
  }

  function selectSession(nextSessionId: string) {
    setSessionId(nextSessionId);
    setManifest(null);
    setArtifacts(null);
    setMessage(null);
    setError(null);
  }

  function createNewSession() {
    const timestamp = new Date()
      .toISOString()
      .replace(/[-:]/g, '')
      .replace(/\..+/, '')
      .replace('T', '-');
    const suffix = Math.random().toString(36).slice(2, 6);
    selectSession(`user-session-${timestamp}-${suffix}`);
  }

  async function refreshAll(target = sessionId) {
    setError(null);
    const [healthData] = await Promise.all([getHealth(), refreshSessions()]);
    setHealth(healthData);
    await loadSession(target);
  }

  async function runWithFeedback(action: () => Promise<{ ok: boolean; message: string }>) {
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const result = await action();
      if (result.ok) {
        setMessage(result.message);
      } else {
        setError(result.message);
      }
      await refreshAll(sessionId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setLoading(false);
    }
  }

  async function uploadWithFeedback(action: () => Promise<{ ok: boolean; message: string }>) {
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const result = await action();
      if (result.ok) {
        setMessage(result.message);
      } else {
        setError(result.message);
      }
      await refreshAll(sessionId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setLoading(false);
    }
  }

  async function handleSmoke(target: string) {
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const result = await runSmokeTest(target);
      setSmokeResults((current) => ({ ...current, [target]: result }));
      if (result.ok) {
        setMessage(`${target} smoke passed: ${result.message}`);
      } else {
        setError(`${target} smoke failed: ${result.message}`);
      }
      const healthData = await getHealth();
      setHealth(healthData);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setLoading(true);
    refreshAll(DEFAULT_SESSION)
      .catch((caught) => setError(caught instanceof Error ? caught.message : String(caught)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="appShell">
      <aside className="sidebar">
        <div className="brand">
          <Podcast size={26} />
          <div>
            <h1>Sophia Agent Podcast</h1>
            <p>Local workflow console</p>
          </div>
        </div>
        <div className="sessionList">
          <div className="sidebarHeader">
            <Database size={16} />
            <span>Sessions</span>
          </div>
          {sessions.length === 0 ? (
            <p className="empty">No sessions.</p>
          ) : (
            sessions.map((item) => (
              <button
                className={`sessionButton ${item.session_id === sessionId ? 'selected' : ''}`}
                key={item.session_id}
                onClick={() => {
                  selectSession(item.session_id);
                  loadSession(item.session_id);
                }}
              >
                <strong>{item.session_id}</strong>
                <small>{item.mode ?? 'no manifest'}</small>
              </button>
            ))
          )}
        </div>
      </aside>

      <main className="mainArea">
        <RunControls
          sessionId={sessionId}
          stage={stage}
          execution={execution}
          loading={loading}
          onSessionChange={selectSession}
          onStageChange={setStage}
          onExecutionChange={setExecution}
          onNewSession={createNewSession}
          onRunPipeline={() =>
            runWithFeedback(() =>
              runFull({
                session_id: sessionId,
                execution,
                force_new_session: execution === 'mock',
                use_uploaded_source: true
              })
            )
          }
          onRunStage={() =>
            runWithFeedback(() =>
              runStage({
                session_id: sessionId,
                stage,
                execution,
                use_uploaded_source: true
              })
            )
          }
          onRefresh={() => {
            setLoading(true);
            refreshAll(sessionId)
              .catch((caught) => setError(caught instanceof Error ? caught.message : String(caught)))
              .finally(() => setLoading(false));
          }}
        />

        {(message || error || loading) && (
          <div className={`notice ${error ? 'error' : ''}`}>
            {loading && <Loader2 className="spin" size={16} />}
            <span>{loading ? 'Running...' : error ?? message}</span>
          </div>
        )}

        <div className="summaryStrip">
          <div>
            <span>Current Session</span>
            <strong>{sessionId}</strong>
          </div>
          <div>
            <span>Manifest</span>
            <strong>{selectedSession?.has_manifest || manifest ? 'available' : 'missing'}</strong>
          </div>
          <div>
            <span>Updated</span>
            <strong>{manifest?.updated_at ? new Date(manifest.updated_at).toLocaleString() : 'n/a'}</strong>
          </div>
        </div>

        <div className="contentGrid">
          <div className="leftColumn">
            <StageTimeline manifest={manifest} />
            <ArtifactViewer bundle={artifacts} />
          </div>
          <div className="rightColumn">
            <ExecutionPanel execution={execution} loading={loading} bundle={artifacts} />
            <HealthPanel health={health} />
            <UploadPanel
              sessionId={sessionId}
              loading={loading}
              onUploadSource={(file) => uploadWithFeedback(() => uploadSource(sessionId, file))}
              onUploadStageInput={(inputStage, file) =>
                uploadWithFeedback(() => uploadStageInput(sessionId, inputStage, file))
              }
            />
            <SmokePanel loading={loading} results={smokeResults} onRun={handleSmoke} />
            <EngineeringPanel />
          </div>
        </div>
      </main>
    </div>
  );
}
