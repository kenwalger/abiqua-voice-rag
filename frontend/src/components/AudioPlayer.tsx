import { useEffect, useRef } from "react";

interface AudioPlayerProps {
  audio_b64: string;
  audio_mime: string;
}

export function AudioPlayer({ audio_b64, audio_mime }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const src = `data:${audio_mime};base64,${audio_b64}`;

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.load();
      audioRef.current.play().catch(() => {
        // Autoplay blocked — controls remain visible
      });
    }
    return () => {
      // Pause only — do not clear `src` here. React commits the new `src` prop
      // before this cleanup runs; setting src="" would wipe the new data URL and
      // leave the element with no source for the next effect's load()/play().
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
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
