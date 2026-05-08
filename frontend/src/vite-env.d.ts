/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  /** Set to "true" for browser console [pipeline] logs (axios timing). */
  readonly VITE_PIPELINE_DEBUG?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
