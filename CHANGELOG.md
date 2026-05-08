# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added (2026-05 Updates)

- Opt-in pipeline diagnostics:
  - Backend `PIPELINE_DEBUG` flag with `[pipeline]` timing logs for `/voices`,
    retrieval, Anthropic narration, and TTS phases.
  - Frontend `VITE_PIPELINE_DEBUG` flag with axios request/response timing logs.
- Global backend error visibility improvements:
  - Early logging configuration for Windows/uvicorn terminals.
  - Explicit traceback logging for unhandled request exceptions.
  - Optional `EXPOSE_INTERNAL_ERRORS` setting to surface exception detail in
    local debugging responses.
- `source_meta.short_url` and `source_meta.record_url` in `/query` responses
  when a direct parent firearm record is resolved.

### Changed (2026-05 Updates)

- Rime defaults and model handling:
  - Added `RIME_DEFAULT_MODEL` setting and switched default model/voice pairing
    to `mist` + `abbie`.
  - `/query` now accepts and forwards `voice_model_id` so selected voice/model
    combinations stay valid.
- Backend settings now load `.env` from an absolute path based on
  `backend/app/settings.py`, preventing launch-directory drift.
- Frontend metadata panel updates:
  - Removed `Series` row.
  - Renamed `Serial Range` to `Serial Number`.
  - Shows linked serial value with `(View)` when a record URL is present.
  - Changed `Production years` display to `Year Shipped` single-year format.
- Image gallery is no longer rendered in `App.tsx` (component file retained).

### Fixed (2026-05 Updates)

- Duplicate voice selector keys caused by repeated model/voice rows from Rime
  catalog flattening.
- Missing/ambiguous voice selector behavior by adding explicit loading/error
  states and defensive voice payload normalization.
- CORS behavior on error envelopes by ensuring error responses include
  appropriate origin headers.
- Silent 500 diagnosis blocker by forcing terminal-visible debug entry prints
  and richer backend exception logging.
- LlamaIndex MongoDB ObjectId compatibility issue (`TextNode.id_` expecting
  string under Pydantic v2) via runtime patching/normalization.
- Review hardening fixes before Spec 06:
  - `/query` and `/voices` route debug `print()` calls are now gated by
    `PIPELINE_DEBUG`.
  - `ResponseValidationError` now respects `EXPOSE_INTERNAL_ERRORS` and returns
    `"Response validation failed"` by default.
  - `llama_mongodb_patch` no longer swallows unexpected exceptions silently;
    it logs a warning and re-raises.
  - API envelope cleanup: canonical top-level `record_url` retained, duplicated
    `short_url` response field removed.





### Added

- Deterministic serial number lookup path querying firearms collection
directly before vector retrieval for serial_number classified queries
- Exact serial match uses source_firearm_id to scope chunk retrieval to
the correct parent record
- Synthetic context chunk fallback when a parent doc exists but no linked
chunks are found — guarantees exact-record response for any serial query
- Secondary lookup reuses direct parent doc when already fetched,
eliminating a redundant Atlas round trip

collections_hit field in response envelope reflecting retrieval path  
taken: 'firearms_direct_lookup', 'firearms_notes', or  
'serial_fallback_semantic'  
- Rime TTS integration using Arcana model with configurable regional

  endpoint via RIME_BASE_URL environment variable

- synthesize() async function using urllib.request in run_in_executor(),

  no additional HTTP libraries required

- *clean*narration() markdown stripping before synthesis

- get_voices() with 5-minute module-level cache and fallback to

  static voice list when regional /v1/voices returns 400

- GET /voices endpoint proxying Rime voice list to frontend

- 503 error mapping for rime_api_error and rime_unreachable conditions

- Full pipeline now end-to-end: query → Atlas retrieval → Claude

  narration → Rime synthesis → base64 mp3 in response envelope

### Changed

- /query endpoint no longer returns RIME_PLACEHOLDER_AUDIO_B64 —

- audio_b64 now contains real synthesized audio

### Fixed

- Serial number queries now return the exact matching firearm record
rather than semantic near-matches (serial 143960 now correctly returns
the .32 New Departure 2nd Model, 1905, nickel, 4 images)
- Removed mixed include/exclude MongoDB projection that caused runtime
failures in parent document lookup
- Score threshold fallback retains top-k raw results for serial queries
when thresholded results are empty

### Added

- Initial project structure and specification documents
- FastAPI backend scaffold with /query, /health, /ready, and /voices routes
- LlamaIndex orchestration layer with MongoDB Atlas Vector Search integration
- Rime TTS integration using Arcana model with configurable regional endpoint
- React + TypeScript frontend with Vite and Tailwind CSS
- Serial number query classification with Atlas pre-filter support
- Base64 audio delivery in JSON response envelope
- search_text field migration script for existing Atlas documents
- MIT license with dataset exclusion notice

### Architecture decisions recorded

- Sync retrieval over streaming for demo simplicity (streaming noted as
production upgrade path throughout spec docs)
- arcana model over mistv3 for narration expressiveness
- users-west.rime.ai as default regional endpoint, configurable via RIME_BASE_URL
- text-embedding-3-small assumed for 1536-dim Atlas Vector Search index
- base64 mp3 in JSON envelope over presigned URL for demo zero-infrastructure
- All state in App.tsx — no context, no reducer, no external state library

---

## Version history

Releases will be tagged on GitHub. Initial public release will be v0.1.0
once the core pipeline is functional end-to-end.