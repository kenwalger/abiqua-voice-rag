# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]





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