import { useMemo, useState } from "react";
import type { ImageRef } from "../types/api";

interface ImageGalleryProps {
  image_refs: ImageRef[];
  image_count: number;
}

export function ImageGallery({ image_refs, image_count }: ImageGalleryProps) {
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);

  const ordered = useMemo(() => {
    const copy = [...image_refs];
    copy.sort((a, b) => {
      if (a.primary === b.primary) {
        return 0;
      }
      return a.primary ? -1 : 1;
    });
    return copy;
  }, [image_refs]);

  if (image_count === 0) {
    return null;
  }

  return (
    <div className="mt-4">
      <h3 className="text-[#593F26] text-sm font-medium mb-2">
        Images ({image_count})
      </h3>
      <div className="flex flex-nowrap gap-2 overflow-x-auto pb-2">
        {ordered.map((ref) => (
          <button
            key={`${ref.image_id}-${ref.url}`}
            type="button"
            onClick={() => setLightboxUrl(ref.url)}
            className={`shrink-0 rounded border border-[#593F26]/30 overflow-hidden focus:outline-none focus:ring-2 focus:ring-[#593F26]/50 ${
              ref.primary ? "w-24 h-24" : "w-20 h-20"
            }`}
          >
            <img
              src={ref.url}
              alt={ref.caption ?? ""}
              className="w-full h-full object-cover"
            />
          </button>
        ))}
      </div>

      {lightboxUrl ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/85 p-4">
          <button
            type="button"
            className="absolute top-4 right-4 text-[#F8F0E3] bg-[#593F26] hover:bg-[#4a3320] border border-[#593F26] px-3 py-1 rounded text-sm"
            onClick={() => setLightboxUrl(null)}
            aria-label="Close image"
          >
            Close
          </button>
          <img
            src={lightboxUrl}
            alt=""
            className="max-h-[90vh] max-w-full object-contain"
          />
        </div>
      ) : null}
    </div>
  );
}
