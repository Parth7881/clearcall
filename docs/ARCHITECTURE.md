# Product and architecture

## Required outcome

Convert three expert interviews into answers to the six guide questions per expert, evidence-backed quotes, common themes and disagreements, and cross-transcript Q&A. Important answers must be traceable to actual source passages. This Part 1 establishes the source layer only.

```mermaid
flowchart LR
  A[Supplied interviews or TXT upload] --> B[Validate entire batch]
  B --> C[(SQLite: original bytes and timestamped passages)]
  C --> D[Transcript library]
  D --> E[Reader: search and source timestamps]
  E --> F[Original file download]
  C -. Part 2 .-> G[6 guide answers per expert]
  G -.-> H[Verbatim quotes and validated citations]
  H -. Part 3 .-> I[Themes, disagreements and cross-call Q&A]
```

## Part 1 implementation

```mermaid
flowchart TD
  UI[React + TypeScript frontend] -->|same-origin /api| API[FastAPI]
  API --> Parser[UTF-8 parser: metadata, timestamps, speakers, offsets]
  Parser --> Batch[Atomic import + SHA-256 deduplication]
  Batch --> DB[(SQLite schema v1)]
  API -->|exact bytes| Download[Source download]
  DB --> API
  Static[Built Vite assets] -->|served by FastAPI| UI
```

API endpoints: GET `/api/health`, GET `/api/transcripts`, GET `/api/transcripts/{id}`, GET `/api/transcripts/{id}/source`, POST `/api/transcripts` (multipart field `files`), POST `/api/samples`.

Transcripts store an immutable ID, source hash, original filename, expert, role, market, original bytes, and parsed passages. Each passage stores ordinal, timestamp, seconds, speaker, expert flag, text, and exact source character offsets. A JSON passage column is sufficient for these small transcripts; separate indexed passage tables can follow if required. All SQL parameters are bound. React renders plain text. Obsolete detail requests are aborted and ID-checked.

## Delivery gates

| Part | Working result | Approval gate |
|---|---|---|
| 1 | Upload, persistent library, source reader and responsive UI | User runs the ZIP and checks the workflow |
| 2 | 18 guide answers, verbatim quotes, validated source citations and uncertainty handling | Test against all supplied interviews; user verifies |
| 3 | Themes, carefully scoped disagreements, cross-call Q&A and submission documentation | End-to-end checks and user demo |

For Part 2, use a backend-only model provider adapter. For three short transcripts, explicit full-context extraction is simpler than a vector database. Validate every returned quote against its cited source span. Unsupported claims should be marked as insufficient evidence. Preserve conditions and geographic scope when comparing growth estimates; a centre-level estimate is not automatically a market-wide contradiction.

At 30+ transcripts, add queued ingestion/extraction, bounded concurrency, per-source caching and passage retrieval when the context budget requires it. Keep original source IDs and offsets through that change. These are architecture notes, not extra implemented features.
