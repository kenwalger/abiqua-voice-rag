import type { SourceMeta } from "../types/api";
import type { ReactNode } from "react";

interface MetadataPanelProps {
  source_meta: SourceMeta;
  record_url: string | null | undefined;
  latency_ms: number;
  query_echo: string;
}

function formatYear(value: number | null): string {
  return value === null || value === undefined ? "?" : String(value);
}

export function MetadataPanel({
  source_meta,
  record_url,
  latency_ms,
  query_echo: _query_echo,
}: MetadataPanelProps) {
  const {
    model,
    serial_range,
    year_start,
    year_end,
    record_count,
    confidence,
  } =
    source_meta;
  const yearShipped = year_start ?? year_end;
  const yearShippedDisplay = yearShipped === null || yearShipped === undefined ? "?" : String(yearShipped);
  const confidencePct = `${Math.round(confidence * 100)}%`;
  const latencySec = `${(latency_ms / 1000).toFixed(1)}s`;
  const fullRecordUrl = (record_url ?? "").trim();

  const row = (label: string, value: ReactNode) => (
    <div className="grid grid-cols-[1fr_2fr] gap-2 py-2 border-b border-[#593F26]/15 last:border-0">
      <dt className="text-stone-600 text-sm uppercase tracking-wide">{label}</dt>
      <dd className="text-stone-900">{value}</dd>
    </div>
  );

  const serialValue = serial_range || "—";
  const serialNode = fullRecordUrl && serialValue !== "—" ? (
    <a
      href={fullRecordUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="text-amber-500 hover:text-amber-400 text-sm underline underline-offset-2"
    >
      {serialValue} <span className="text-xs">(View)</span>
    </a>
  ) : (
    serialValue
  );

  return (
    <div className="mt-4 p-4 rounded-lg bg-white/90 border border-[#593F26]/20 shadow-sm">
      <dl>
        {row("Model", model || "—")}
        {row("Serial Number", serialNode)}
        {row("Year Shipped", yearShippedDisplay)}
        {row("Records found", String(record_count))}
        {row("Confidence", confidencePct)}
        {row("Pipeline latency", latencySec)}
      </dl>
    </div>
  );
}
