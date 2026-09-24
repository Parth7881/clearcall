# Clearcall — approved product scope and Part 1 design

The user approved the Hasamex case-study scope and three-part architecture on 24 September 2026, and confirmed a polished, clean Google-inspired frontend. Delivery is a runnable ZIP, developed directly in this session, followed by user verification before Part 2.

## Full product

Read/upload the three transcripts; answer six interview-guide questions for each expert; extract verbatim quotations with timestamps; identify common themes and disagreements; answer questions across transcripts. Evidence must be traceable. No invented information. The study concerns European robotic surgery adoption, not clinical advice.

## Part 1

A responsive transcript workspace with a real FastAPI backend, persistent SQLite storage, idempotent loading of the supplied samples, UTF-8 TXT uploads, expert/market filtering, a timestamped source reader, per-transcript search, expert-only filtering, source-file download, accessible help and upload dialogs, and meaningful empty/error/loading states. No pretend AI output and no inert links to unbuilt features.

Source text is retained, never replaced by generated content. Timestamps are segment starts, not precise quote durations. Maximum file size 2 MiB; maximum five files per upload; accept .txt only; reject invalid encoding, NUL bytes, missing metadata, malformed/missing timestamps, decreasing timestamps, unlabeled utterances, or files without expert speech. Validate an entire batch before saving any of it. Identical contents are deduplicated by SHA-256. Preserve original bytes for download. All data remains local; no LLM API is called in Part 1.

The source format contains an Expert header, Role and Market, then timestamp lines and speaker-labelled passages. The three supplied source files produce fourteen passages each, seven expert passages each. Passage text retains exact source characters and original offsets.

## Visual system

White reader, cool pale grey app background, charcoal text, restrained Google-blue actions, generous whitespace. Desktop: header, project introduction, split library/reader. Mobile: library view and full-width reader with a back action. Controls have keyboard focus, clear labels, sufficient contrast, and minimum 44px touch targets. No Google logos or implied affiliation. Use system sans-serif fonts; no remote font dependency. The generated reference is a visual guide; real file names, counts, accessible controls, errors and responsive behaviour take precedence over incidental image-generation text differences.

## Delivery boundaries

Part 1 is independently functional. Part 2 adds guide answers and evidence validation. Part 3 adds cross-call synthesis and Q&A, final evaluation and submission support. Each later ZIP will be cumulative with the same project root and instructions preserving .env and data.

## Architecture

React + TypeScript + Vite frontend, FastAPI/Pydantic backend, Python sqlite3. A built frontend is served by FastAPI from one origin for the simple local launch. Vite development mode proxies /api to FastAPI. A configurable data directory stores the database outside source modules. Schema versioning leaves an upgrade path. Imported text is rendered as escaped text, never HTML. Upload filenames are display metadata, never filesystem paths.

## Acceptance

All supplied files load once and persist across app restarts. Upload errors leave no partial records. Source download equals uploaded bytes. Switching experts, searching, toggling expert-only and opening a timestamp work together. Mobile at 390px has no horizontal overflow; keyboard users can complete upload and close dialogs. No uncaught browser errors on the primary workflows. The delivered ZIP excludes local databases, environments, caches, dependencies and secrets; contains source, lockfiles, setup script, samples, tests, built frontend and documentation.
