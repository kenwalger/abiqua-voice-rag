export interface ImageRef {
  image_id: string;
  url: string;
  caption: string | null;
  primary: boolean;
}

export interface SourceMeta {
  model: string;
  serial_range: string;
  year_start: number | null;
  year_end: number | null;
  record_count: number;
  confidence: number;
  short_url?: string | null;
  record_url?: string | null;
}

export interface QueryResponse {
  narration_text: string;
  audio_b64: string;
  audio_mime: string;
  image_count: number;
  image_refs: ImageRef[];
  source_meta: SourceMeta;
  query_type: string;
  collections_hit: string[];
  query_echo: string;
  latency_ms: number;
}

export interface Voice {
  id: string;
  name: string;
  preview_url: string | null;
  /** Rime model bucket (e.g. arcana, mist); same voice id can appear under more than one. */
  model_id?: string | null;
}

export interface ApiError {
  ok: false;
  status: number;
  error: string;
  detail: string;
}
