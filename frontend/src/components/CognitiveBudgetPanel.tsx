import { useState } from "react";
import type { CognitiveBudget } from "../types/api";

interface CognitiveBudgetPanelProps {
  budget: CognitiveBudget;
}

function usd(n: number, decimals: number): string {
  return `$${n.toFixed(decimals)}`;
}

export function CognitiveBudgetPanel({ budget }: CognitiveBudgetPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const chevron = expanded ? "▴" : "▾";
  const summaryTotal = usd(budget.total_cost_usd, 6);

  return (
    <div className="mt-4 p-4 rounded-lg bg-white/90 border border-[#593F26]/20 shadow-sm">
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="w-full text-left flex items-center justify-between gap-2 text-[#593F26] font-medium text-sm hover:text-amber-700"
      >
        <span>
          Cognitive Budget: ~{summaryTotal} est. · Routing: {budget.routing_decision}{" "}
          <span className="text-amber-600">{chevron}</span>
        </span>
      </button>

      {expanded ? (
        <div className="mt-4 space-y-4">
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-[#593F26]/20 text-stone-600 text-left">
                  <th className="py-2 pr-2 font-medium uppercase tracking-wide">Line item</th>
                  <th className="py-2 pr-2 font-medium uppercase tracking-wide">Detail</th>
                  <th className="py-2 font-medium uppercase tracking-wide text-right">Est. cost</th>
                </tr>
              </thead>
              <tbody className="text-stone-900">
                <tr className="border-b border-[#593F26]/10">
                  <td className="py-2 pr-2">Embedding</td>
                  <td className="py-2 pr-2">{budget.embedding_tokens} tokens</td>
                  <td className="py-2 text-right tabular-nums">{usd(budget.embedding_cost_usd, 8)}</td>
                </tr>
                <tr className="border-b border-[#593F26]/10">
                  <td className="py-2 pr-2">Narration</td>
                  <td className="py-2 pr-2">
                    {budget.narration_input_tokens} in / {budget.narration_output_tokens} out (Haiku)
                  </td>
                  <td className="py-2 text-right tabular-nums">{usd(budget.narration_cost_usd, 8)}</td>
                </tr>
                <tr className="border-b border-[#593F26]/10">
                  <td className="py-2 pr-2">TTS</td>
                  <td className="py-2 pr-2">{budget.tts_characters} chars (Arcana tier pricing)</td>
                  <td className="py-2 text-right tabular-nums">{usd(budget.tts_cost_usd, 8)}</td>
                </tr>
                <tr className="border-b border-[#593F26]/15 font-medium">
                  <td className="py-2 pr-2">Total</td>
                  <td className="py-2 pr-2" />
                  <td className="py-2 text-right tabular-nums">{usd(budget.total_cost_usd, 8)}</td>
                </tr>
                <tr className="font-medium text-[#593F26]">
                  <td className="py-2 pr-2">At 10,000/day</td>
                  <td className="py-2 pr-2" />
                  <td className="py-2 text-right tabular-nums">
                    {usd(budget.daily_cost_at_10k_usd, 2)}/day
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-xs text-stone-500 leading-relaxed">
            Estimates based on public API pricing as of {budget.pricing_date}. Routing:{" "}
            {budget.routing_decision} · {budget.collections_queried} collection(s) queried.
          </p>
        </div>
      ) : null}
    </div>
  );
}
