interface NarrationPanelProps {
  narration_text: string;
}

export function NarrationPanel({ narration_text }: NarrationPanelProps) {
  return (
    <div className="mt-4 p-4 rounded-lg bg-white/90 border border-[#593F26]/20 shadow-sm">
      <p className="text-stone-900 text-lg leading-relaxed font-serif">
        {narration_text}
      </p>
    </div>
  );
}
