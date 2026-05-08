import { useEffect, useState } from "react";
import axios from "axios";
import { fetchVoices, submitQuery } from "./api/client";
import { AudioPlayer } from "./components/AudioPlayer";
import { CognitiveBudgetPanel } from "./components/CognitiveBudgetPanel";
import { MetadataPanel } from "./components/MetadataPanel";
import { NarrationPanel } from "./components/NarrationPanel";
import { QueryForm } from "./components/QueryForm";
import { StatusBar } from "./components/StatusBar";
import { voiceOptionValue } from "./lib/voiceOptions";
import type { QueryResponse, Voice } from "./types/api";

function detailToString(detail: unknown): string {
  if (typeof detail === "string") {
    return detail;
  }
  if (detail == null) {
    return "Something went wrong — check the console.";
  }
  try {
    return JSON.stringify(detail);
  } catch {
    return "Something went wrong — check the console.";
  }
}

function isErrorEnvelope(data: unknown): data is Record<string, unknown> {
  if (!data || typeof data !== "object") {
    return false;
  }
  const o = data as Record<string, unknown>;
  return o.ok === false && typeof o.status === "number" && typeof o.error === "string";
}

function describeVoicesFetchError(err: unknown): string {
  if (!axios.isAxiosError(err)) {
    return "Could not load the voice list. The server default voice will be used.";
  }
  if (err.code === "ECONNABORTED" || err.code === "ERR_CANCELED") {
    return "Loading voices timed out. The server default voice will be used.";
  }
  const st = err.response?.status;
  const raw = err.response?.data;
  let detail = "";
  if (raw && typeof raw === "object" && "detail" in raw) {
    detail = detailToString((raw as Record<string, unknown>).detail);
  }
  if (st == null && !err.response) {
    const msg = err.message || "Network error";
    return `Could not reach the API (${msg}). Is the backend running at the URL in VITE_API_BASE_URL? The default voice will be used.`;
  }
  const bits = [
    "Could not load the voice list.",
    st != null ? `HTTP ${st}.` : "",
    detail ? detail : "",
    "The server default voice will be used.",
  ].filter(Boolean);
  return bits.join(" ");
}

function App() {
  const [voiceId, setVoiceId] = useState<string>("");
  const [voices, setVoices] = useState<Voice[]>([]);
  const [voicesReady, setVoicesReady] = useState<boolean>(false);
  const [voicesError, setVoicesError] = useState<string | null>(null);
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [echoQuery, setEchoQuery] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setVoicesReady(false);
      setVoicesError(null);
      try {
        const list = await fetchVoices();
        if (cancelled) {
          return;
        }
        setVoices(list);
        if (list.length > 0) {
          setVoiceId(voiceOptionValue(list[0]));
        }
        setVoicesError(null);
      } catch (err: unknown) {
        if (!cancelled) {
          setVoices([]);
          setVoicesError(describeVoicesFetchError(err));
        }
      } finally {
        setVoicesReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSubmit = async (query: string, selectedVoiceId: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await submitQuery(query, selectedVoiceId);
      setResponse(data);
      setEchoQuery(data.query_echo);
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        if (err.code === "ECONNABORTED") {
          setError(
            "Request timed out. Retrieval and TTS can take a few minutes — try again or check the API.",
          );
        } else if (err.response?.data) {
          const data = err.response.data;
          if (isErrorEnvelope(data) && "detail" in data) {
            setError(detailToString(data.detail));
          } else if (typeof data === "object" && data !== null && "detail" in data) {
            setError(detailToString((data as Record<string, unknown>).detail));
          } else {
            setError("Something went wrong — check the console.");
          }
        } else {
          setError(
            err.message ||
              "Network error — check that the API is running (e.g. http://localhost:8000).",
          );
        }
      } else {
        setError("Something went wrong — check the console.");
      }
    } finally {
      setLoading(false);
    }
  };

  const statusEcho = loading || error ? null : echoQuery;

  return (
    <div className="min-h-screen bg-[#F8F0E3] text-stone-900">
      <div className="max-w-[800px] mx-auto px-4 py-8">
        <header className="border-b border-[#593F26]/25 pb-6">
          <h1 className="text-2xl font-semibold text-[#593F26] tracking-tight">
            The Abiqua Collection
          </h1>
          <p className="mt-2 text-stone-700 text-sm leading-relaxed">
            Voice RAG over historical firearms provenance — ask in natural language
            or enter a serial number.
          </p>
        </header>

        <QueryForm
          voices={voices}
          voicesReady={voicesReady}
          voicesError={voicesError}
          voiceId={voiceId}
          setVoiceId={setVoiceId}
          loading={loading}
          onSubmit={handleSubmit}
        />

        <StatusBar loading={loading} error={error} queryEcho={statusEcho} />

        {response ? (
          <>
            <AudioPlayer
              audio_b64={response.audio_b64}
              audio_mime={response.audio_mime}
            />
            <NarrationPanel narration_text={response.narration_text} />
            <MetadataPanel
              source_meta={response.source_meta}
              record_url={response.record_url}
              latency_ms={response.latency_ms}
              query_echo={response.query_echo}
            />
            {response.cognitive_budget ? (
              <CognitiveBudgetPanel budget={response.cognitive_budget} />
            ) : null}
          </>
        ) : null}
      </div>
    </div>
  );
}

export default App;
