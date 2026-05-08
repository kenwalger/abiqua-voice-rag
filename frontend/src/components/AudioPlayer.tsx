import { useEffect, useRef } from "react";

interface AudioPlayerProps {
  audio_b64: string;
  audio_mime: string;
}

export function AudioPlayer({ audio_b64, audio_mime }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const src = `data:${audio_mime};base64,${audio_b64}`;

  useEffect(() => {
    const el = audioRef.current;
    if (!el) {
      return;
    }
    el.load();
    void el.play().catch(() => {});
  }, [audio_b64]);

  return (
    <audio
      ref={audioRef}
      controls
      className="w-full mt-4"
      src={src}
    />
  );
}
