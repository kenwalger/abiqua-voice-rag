# Architecture Diagrams

Visual reference for the Abiqua Collection Voice RAG system architecture.
All diagrams render natively in GitHub markdown.

---

## 1. Full Request Flow

End-to-end pipeline from user query to synthesized audio response.

```mermaid
flowchart TD
    A([User query\nserial number or natural language]) --> B

    subgraph Frontend ["React Frontend (Vite + TypeScript)"]
        B[QueryForm\nsubmit query + voice_id]
        R[AudioPlayer\nplay base64 mp3]
        S[NarrationPanel\ndisplay narration text]
        T[MetadataPanel\nmodel · year · confidence · latency]
    end

    B -->|POST /query| C

    subgraph Backend ["FastAPI Backend (Python 3.11+)"]
        C[Request validation\nPydantic QueryRequest]
        C --> D[Stage 1\nQuery classification]
        D --> E[Stage 2\nOpenAI text-embedding-3-small\n1536-dim vector]
        E --> F{Query type?}
    end

    subgraph Retrieval ["Stage 3a — Atlas Vector Search"]
        F -->|serial_number| G[firearms direct lookup\nby serial_number field]
        G --> H[firearms_rag_chunks\nscoped by source_firearm_id]
        F -->|natural_language| I[firearms_rag_chunks]
        F -->|natural_language| J[historical_events_rag_chunks]
        F -->|natural_language| K[manufacturers_rag_chunks]
        I & J & K --> L[Merge + re-sort by score\nfilter below threshold 0.70]
    end

    subgraph Lookup ["Stage 3b — Secondary Lookup"]
        H --> M[Fetch parent firearms doc\nby source_firearm_id]
        L --> M
        M --> N[images · factory_letter\nserial · year · finish · short_url]
    end

    subgraph Synthesis ["Stages 4 + 5 — Narration"]
        N --> O[Build narration prompt\nchunk text + parent metadata]
        O --> P[Claude claude-haiku-4-5\nmax_tokens 400 · temp 0.3]
        P --> Q[narration_text]
    end

    subgraph Voice ["Rime TTS — Voice Layer"]
        Q --> V[_clean_narration\nstrip markdown]
        V --> W[Rime Arcana model\nspeaker: colby\nspeedAlpha: 0.95]
        W --> X[base64 mp3\n~875 KB · 22050 Hz]
    end

    X --> Y[Assemble response envelope\nnarration_text · audio_b64\nsource_meta · record_url · latency_ms]
    Y -->|JSON response| R
    Y --> S
    Y --> T

    style Frontend fill:#1c1917,stroke:#78716c,color:#e7e5e4
    style Backend fill:#1c1917,stroke:#78716c,color:#e7e5e4
    style Retrieval fill:#1c1917,stroke:#92400e,color:#e7e5e4
    style Lookup fill:#1c1917,stroke:#92400e,color:#e7e5e4
    style Synthesis fill:#1c1917,stroke:#1d4ed8,color:#e7e5e4
    style Voice fill:#1c1917,stroke:#15803d,color:#e7e5e4
```

---

## 2. Query Routing Logic

How the query classification decision determines retrieval behavior.

```mermaid
flowchart TD
    A([Incoming query]) --> B{classify_query}

    B -->|4-9 digit string\n optionally prefixed\n with hash or 'serial'| C[serial_number]
    B -->|everything else| D[natural_language]

    C --> E[extract_serial_number\nregex digit extraction]
    E --> F[Direct lookup\nfirearms collection\nby serial_number field]

    F --> G{Parent doc\nfound?}
    G -->|Yes| H[Scope chunk retrieval\nto source_firearm_id\nin firearms_rag_chunks]
    G -->|No| I[Semantic fallback\nfirearms_rag_chunks\nvector search only]

    H --> J[collections_hit:\nfirearms_direct_lookup]
    I --> K[collections_hit:\nserial_fallback_semantic]

    D --> L[Concurrent retrieval\nasyncio.gather]
    L --> M[firearms_rag_chunks]
    L --> N[historical_events_rag_chunks]
    L --> O[manufacturers_rag_chunks]

    M & N & O --> P[Merge results\nre-sort by similarity score\ndrop below threshold 0.70]
    P --> Q[collections_hit:\nall three collections]

    J & K & Q --> R[Stage 3b\nSecondary parent lookup\nfor display data]
    R --> S[Prompt synthesis\n→ Claude narration\n→ Rime TTS]

    style A fill:#292524,stroke:#78716c,color:#e7e5e4
    style C fill:#451a03,stroke:#b45309,color:#fef3c7
    style D fill:#042f2e,stroke:#0d9488,color:#ccfbf1
    style J fill:#14532d,stroke:#16a34a,color:#dcfce7
    style K fill:#431407,stroke:#c2410c,color:#ffedd5
    style Q fill:#14532d,stroke:#16a34a,color:#dcfce7
```

---

## 3. Collection Data Model

Relationships between the four MongoDB collections and the role each plays.

```mermaid
erDiagram
    FIREARMS {
        ObjectId _id PK
        string serial_number
        string model
        string series
        string manufacturer
        int year
        boolean estimated_year
        string caliber
        string finish
        float barrel_length
        string grips
        boolean factory_letter
        array images
        string sku
        string short_url
        string slug
        array embedding
    }

    FIREARMS_RAG_CHUNKS {
        ObjectId _id PK
        string source_firearm_id FK
        string chunk_id
        string text
        array embedding
        object metadata
        string created_at
    }

    HISTORICAL_EVENTS_RAG_CHUNKS {
        ObjectId _id PK
        string chunk_id
        string text
        array embedding
        object metadata
        string created_at
    }

    MANUFACTURERS_RAG_CHUNKS {
        ObjectId _id PK
        string chunk_id
        string text
        array embedding
        object metadata
        string created_at
    }

    FIREARMS ||--o{ FIREARMS_RAG_CHUNKS : "source_firearm_id references _id"
    FIREARMS_RAG_CHUNKS }o--|| FIREARMS : "secondary lookup for\nimages · factory_letter\nserial · year · short_url"
```

---

## 4. Demo vs. Production Decision Map

Where this build makes deliberate simplifications and what the production
upgrade path looks like for each.

```mermaid
flowchart LR
    subgraph Demo ["Demo Build"]
        D1[Sync retrieval\nfull pipeline before response]
        D2[base64 mp3\nin JSON envelope]
        D3[No authentication\nopen endpoints]
        D4[No rate limiting]
        D5[No caching\nevery query hits Atlas + Rime]
        D6[urllib.request\nin run_in_executor]
        D7[arcana model\nfull synthesis latency]
    end

    subgraph Production ["Production Upgrade Path"]
        P1[Streaming\nSSE + mistv3 model\nsub-500ms first audio byte]
        P2[Presigned CDN URL\nbinary audio endpoint\nseek bar support]
        P3[Bearer token auth\nper-tenant API keys]
        P4[API gateway\n60 req/min per IP]
        P5[Redis cache\nSHA-256 keyed by query + voice]
        P6[httpx.AsyncClient\nconnection pooling + retry]
        P7[mistv3 model\n~70ms time-to-first-audio]
    end

    D1 -->|enable streaming| P1
    D2 -->|move audio to CDN| P2
    D3 -->|add auth layer| P3
    D4 -->|enforce at gateway| P4
    D5 -->|add Redis| P5
    D6 -->|replace HTTP client| P6
    D7 -->|switch modelId| P7

    style Demo fill:#1c1917,stroke:#78716c,color:#e7e5e4
    style Production fill:#0f172a,stroke:#334155,color:#e2e8f0
```
