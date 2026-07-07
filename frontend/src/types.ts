export type StageStatus = 'pending' | 'running' | 'done' | 'failed' | 'skipped' | string;

export interface HealthCheck {
  name: string;
  available: boolean;
  required: boolean;
  message: string;
}

export interface SessionSummary {
  session_id: string;
  mode: string | null;
  updated_at: string | null;
  stage_counts: Record<string, number>;
  has_manifest: boolean;
}

export interface StageArtifact {
  stage: string;
  session_id: string;
  path: string;
  created_at: string;
  summary: string;
  payload: Record<string, unknown>;
}

export interface Manifest {
  session_id: string;
  mode: string;
  started_at: string;
  updated_at: string;
  config_snapshot: Record<string, unknown>;
  stages: Record<string, StageStatus>;
  artifacts: StageArtifact[];
  errors: string[];
}

export interface ArtifactBundle {
  manifest: Manifest | null;
  source_upload: UploadResult | null;
  run_log: string | null;
  topic: Array<Record<string, unknown>> | null;
  director: Array<Record<string, unknown>> | null;
  script_items: Array<Record<string, unknown>> | null;
  script_text: string | null;
  voice: Record<string, unknown> | null;
  images: Array<Record<string, unknown>> | null;
  video: Record<string, unknown> | null;
}

export interface ApiResult<T = Record<string, unknown>> {
  ok: boolean;
  message: string;
  data: T | null;
}

export interface UploadResult {
  session_id: string;
  filename: string;
  path?: string;
  target?: string;
  stage?: string;
  size_bytes: number;
  uploaded_at?: string;
}

export interface SmokeTestResult {
  target: string;
  ok: boolean;
  message: string;
  elapsed_ms: number;
  details: Record<string, unknown>;
}

export interface RunPayload {
  session_id: string;
  force_new_session?: boolean;
  ref_chapter?: string | null;
  stage?: string | null;
  execution?: 'mock' | 'real';
  llm_mode?: string | null;
  tts_mode?: string | null;
  image_mode?: string | null;
  video_mode?: string | null;
  use_uploaded_source?: boolean;
}

export type HealthSummary = {
  demo: HealthCheck[];
  full: HealthCheck[];
};
