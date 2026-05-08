export interface SourceMeta {
  model: string;
  serial_range: string;
  year_start: number | null;
  year_end: number | null;
  record_count: number;
  confidence: number;
}

export interface CognitiveBudget {
  embedding_tokens: number;
  narration_input_tokens: number;
  narration_output_tokens: number;
  tts_characters: number;
  collections_queried: number;
  routing_decision: string;
  narration_model: string;
  embedding_cost_usd: number;
  narration_cost_usd: number;
  tts_cost_usd: number;
  total_cost_usd: number;
  daily_cost_at_10k_usd: number;
  pricing_date: string;
}

export interface QueryResponse {
  narration_text: string;
  audio_b64: string;
  audio_mime: string;
  source_meta: SourceMeta;
  query_type: string;
  collections_hit: string[];
  query_echo: string;
  latency_ms: number;
  record_url?: string | null;
  cognitive_budget: CognitiveBudget;
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
