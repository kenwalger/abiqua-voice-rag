import type { Voice } from "../types/api";

/** Stable, unique value for <select> options (voice ids repeat across models). */
export function voiceOptionValue(v: Voice): string {
  const model = (v.model_id ?? "").trim() || "_";
  return `${model}:${v.id}`;
}

/** Speaker id sent to POST /query (Rime `speaker`). */
export function voiceIdForApi(optionValue: string): string {
  const i = optionValue.indexOf(":");
  if (i < 0) {
    return optionValue;
  }
  return optionValue.slice(i + 1);
}

/** Rime `modelId` for the selected option (mist, arcana, …). */
export function voiceModelFromOption(optionValue: string): string | undefined {
  const i = optionValue.indexOf(":");
  if (i <= 0) {
    return undefined;
  }
  const model = optionValue.slice(0, i).trim();
  if (!model || model === "_") {
    return undefined;
  }
  return model;
}

/**
 * Rime's catalog repeats the same voice under multiple language buckets; the API
 * can return duplicate model+id rows. Keep first occurrence so React keys stay unique.
 */
export function dedupeVoices(voices: Voice[]): Voice[] {
  const seen = new Set<string>();
  const out: Voice[] = [];
  for (const v of voices) {
    const k = voiceOptionValue(v);
    if (seen.has(k)) {
      continue;
    }
    seen.add(k);
    out.push(v);
  }
  return out;
}
