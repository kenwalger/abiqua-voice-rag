import { voiceOptionValue } from "../lib/voiceOptions";
import type { Voice } from "../types/api";

interface QueryFormProps {
  voices: Voice[];
  voicesReady: boolean;
  voicesError: string | null;
  voiceId: string;
  setVoiceId: (id: string) => void;
  loading: boolean;
  onSubmit: (query: string, voiceId: string) => void;
}

export function QueryForm({
  voices,
  voicesReady,
  voicesError,
  voiceId,
  setVoiceId,
  loading,
  onSubmit,
}: QueryFormProps) {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const input = form.elements.namedItem("query") as HTMLInputElement;
    const q = input.value.trim();
    if (!q || loading) {
      return;
    }
    onSubmit(q, voiceId);
  };

  return (
    <form onSubmit={handleSubmit} className="mt-6 space-y-3">
      <input
        name="query"
        type="text"
        placeholder="Natural language or serial number…"
        disabled={loading}
        className="w-full px-3 py-2 rounded-lg bg-white/90 border border-[#593F26]/30 text-stone-900 placeholder:text-stone-500 focus:outline-none focus:ring-2 focus:ring-[#593F26]/50 disabled:opacity-60"
      />
      <div className="space-y-1">
        <label
          htmlFor="voice-select"
          className="block text-sm font-medium text-[#593F26]"
        >
          Narration voice
        </label>
        {!voicesReady ? (
          <p
            id="voice-select"
            className="text-sm text-stone-600 py-2"
            aria-live="polite"
          >
            Loading voices…
          </p>
        ) : voices.length > 0 ? (
          <select
            id="voice-select"
            value={voiceId}
            onChange={(e) => setVoiceId(e.target.value)}
            disabled={loading}
            className="w-full px-3 py-2 rounded-lg bg-white/90 border border-[#593F26]/30 text-stone-900 focus:outline-none focus:ring-2 focus:ring-[#593F26]/50 disabled:opacity-60"
          >
            {voices.map((v) => {
              const optionVal = voiceOptionValue(v);
              const model = v.model_id?.trim();
              const label =
                model && model.length > 0
                  ? `${v.name} (${model})`
                  : v.name;
              return (
                <option key={optionVal} value={optionVal}>
                  {label}
                </option>
              );
            })}
          </select>
        ) : (
          <p
            id="voice-select"
            className="text-sm text-stone-600 py-2 border border-dashed border-[#593F26]/25 rounded-lg px-3 bg-white/50"
          >
            {voicesError ??
              "No voices were returned. The server default voice will be used."}
          </p>
        )}
      </div>
      <button
        type="submit"
        disabled={loading || !voicesReady}
        className="w-full py-2 rounded-lg bg-[#593F26] hover:bg-[#4a3320] text-[#F8F0E3] font-medium disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {loading ? "Narrating..." : "Narrate"}
      </button>
    </form>
  );
}
