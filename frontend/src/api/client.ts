import axios from "axios";
import {
  dedupeVoices,
  voiceIdForApi,
  voiceModelFromOption,
} from "../lib/voiceOptions";
import type { QueryResponse, Voice } from "../types/api";

function resolveApiBaseUrl(): string {
  const raw = import.meta.env.VITE_API_BASE_URL;
  if (typeof raw === "string" && raw.trim().length > 0) {
    return raw.trim().replace(/\/+$/, "");
  }
  if (import.meta.env.DEV) {
    console.warn(
      "[api] VITE_API_BASE_URL is not set — using http://localhost:8000. " +
        "Add VITE_API_BASE_URL to frontend/.env.local (see .env.example).",
    );
    return "http://localhost:8000";
  }
  throw new Error(
    "VITE_API_BASE_URL is missing. Set it in the environment for production builds.",
  );
}

const BASE = resolveApiBaseUrl();

const PIPELINE_DEBUG =
  import.meta.env.VITE_PIPELINE_DEBUG === "true" ||
  import.meta.env.VITE_PIPELINE_DEBUG === "1";

if (PIPELINE_DEBUG) {
  axios.interceptors.request.use((config) => {
    (config as { pipelineStarted?: number }).pipelineStarted = performance.now();
    const url = `${config.baseURL ?? ""}${config.url ?? ""}`;
    console.info("[pipeline]", config.method?.toUpperCase(), url);
    return config;
  });
  axios.interceptors.response.use(
    (response) => {
      const cfg = response.config as { pipelineStarted?: number };
      const ms =
        cfg.pipelineStarted != null
          ? Math.round(performance.now() - cfg.pipelineStarted)
          : undefined;
      console.info(
        "[pipeline]",
        response.status,
        response.config.url,
        ms != null ? `${ms}ms` : "",
      );
      return response;
    },
    (error) => {
      const cfg = error.config as { pipelineStarted?: number; url?: string } | undefined;
      const ms =
        cfg?.pipelineStarted != null
          ? Math.round(performance.now() - cfg.pipelineStarted)
          : undefined;
      console.warn(
        "[pipeline]",
        "error",
        (cfg as { method?: string }).method,
        cfg?.url,
        error.response?.status,
        ms != null ? `${ms}ms` : "",
        error.message,
      );
      return Promise.reject(error);
    },
  );
}

/** POST /query can take a long time (retrieval + Claude + TTS). */
const QUERY_TIMEOUT_MS = 180_000;
/** Cold start + Rime can exceed 25s in dev; duplicate Strict Mode mounts share one request via dedupe. */
const VOICES_TIMEOUT_MS = 60_000;

let voicesFetchInflight: Promise<Voice[]> | null = null;

function normalizeVoiceEntry(raw: unknown): Voice | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const o = raw as Record<string, unknown>;
  const idRaw = o.id ?? o.voice_id;
  const id = idRaw != null ? String(idRaw).trim() : "";
  if (!id) {
    return null;
  }
  const nameRaw = o.name ?? o.id;
  const name =
    nameRaw != null && String(nameRaw).trim().length > 0
      ? String(nameRaw)
      : id;
  const preview_url =
    typeof o.preview_url === "string" ? o.preview_url : null;
  const mid = o.model_id;
  const model_id =
    mid != null && String(mid).trim() ? String(mid) : null;
  return { id, name, preview_url, model_id };
}

export async function submitQuery(
  query: string,
  voiceOptionValue: string,
  topK = 5,
): Promise<QueryResponse> {
  const speaker = voiceIdForApi(voiceOptionValue);
  const voice_model_id = voiceModelFromOption(voiceOptionValue);
  const { data } = await axios.post<QueryResponse>(
    `${BASE}/query`,
    {
      query,
      voice_id: speaker || undefined,
      voice_model_id: voice_model_id ?? undefined,
      top_k: topK,
    },
    { timeout: QUERY_TIMEOUT_MS },
  );
  return data;
}

export async function fetchVoices(): Promise<Voice[]> {
  if (!voicesFetchInflight) {
    voicesFetchInflight = (async () => {
      try {
        const { data } = await axios.get<{ voices?: unknown }>(
          `${BASE}/voices`,
          { timeout: VOICES_TIMEOUT_MS },
        );
        const raw = data?.voices;
        const arr = Array.isArray(raw) ? raw : [];
        const voices = arr
          .map((item) => normalizeVoiceEntry(item))
          .filter((v): v is Voice => v !== null);
        return dedupeVoices(voices);
      } finally {
        voicesFetchInflight = null;
      }
    })();
  }
  return voicesFetchInflight;
}
