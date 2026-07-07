import type {
  ApiResult,
  ArtifactBundle,
  HealthSummary,
  Manifest,
  RunPayload,
  SessionSummary,
  SmokeTestResult,
  UploadResult
} from './types';

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {})
    },
    ...init
  });

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail ?? payload?.message ?? response.statusText;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return payload as T;
}

async function requestForm<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetch(path, {
    method: 'POST',
    body: formData
  });

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail ?? payload?.message ?? response.statusText;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return payload as T;
}

export function getHealth(): Promise<HealthSummary> {
  return requestJson<HealthSummary>('/api/health');
}

export function listSessions(): Promise<SessionSummary[]> {
  return requestJson<SessionSummary[]>('/api/sessions');
}

export function getSession(sessionId: string): Promise<Manifest> {
  return requestJson<Manifest>(`/api/sessions/${encodeURIComponent(sessionId)}`);
}

export function getArtifacts(sessionId: string): Promise<ArtifactBundle> {
  return requestJson<ArtifactBundle>(`/api/sessions/${encodeURIComponent(sessionId)}/artifacts`);
}

export function runDemo(payload: RunPayload): Promise<ApiResult<{ manifest: Manifest }>> {
  return requestJson<ApiResult<{ manifest: Manifest }>>('/api/runs/demo', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function runFull(payload: RunPayload): Promise<ApiResult<{ manifest: Manifest }>> {
  return requestJson<ApiResult<{ manifest: Manifest }>>('/api/runs/full', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function runStage(payload: RunPayload): Promise<ApiResult<{ artifact: Record<string, unknown> }>> {
  return requestJson<ApiResult<{ artifact: Record<string, unknown> }>>('/api/runs/stage', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function uploadSource(sessionId: string, file: File): Promise<ApiResult<UploadResult>> {
  const formData = new FormData();
  formData.append('session_id', sessionId);
  formData.append('file', file);
  return requestForm<ApiResult<UploadResult>>('/api/uploads/source', formData);
}

export function uploadStageInput(sessionId: string, stage: string, file: File): Promise<ApiResult<UploadResult>> {
  const formData = new FormData();
  formData.append('session_id', sessionId);
  formData.append('stage', stage);
  formData.append('file', file);
  return requestForm<ApiResult<UploadResult>>('/api/uploads/stage-input', formData);
}

export function runSmokeTest(target: string): Promise<SmokeTestResult> {
  return requestJson<SmokeTestResult>('/api/smoke', {
    method: 'POST',
    body: JSON.stringify({ target })
  });
}
