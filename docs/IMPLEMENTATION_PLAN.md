# Clearcall Part 1 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. The user selected direct implementation in this session and approved the scope and architecture. Steps use checkbox syntax for tracking.

**Goal:** Deliver a polished, working local transcript workspace and tested ZIP.

**Architecture:** React consumes a typed FastAPI API. SQLite persists original source bytes and parsed timestamped passages. FastAPI serves the production frontend; development uses Vite's API proxy.

**Tech Stack:** React, TypeScript, Vite, CSS, FastAPI, sqlite3, pytest, Playwright for automated browser checks when necessary.

**Spec:** `docs/SPEC.md`

## Global constraints

- Part 1 only; no mock AI results or unrelated product features.
- White, clean Google-inspired responsive UI; no remote fonts/assets required at runtime.
- Windows-friendly local setup; Python 3.10+ and Node 22.12+.
- Store original bytes; derive all timestamps from the source.
- Maximum five .txt files, 2 MiB each; validate batches atomically.
- No user secrets or working database inside ZIP.

## Review focus

- Bad second file in a batch: reject all, keep database unchanged.
- Duplicate file contents with a renamed filename: keep one transcript.
- Unicode and CRLF: preserve source bytes and correct citation offsets.
- Fast selection/search changes: no stale transcript response replaces the selected file.
- Keyboard/mobile overlays: focus stays in the dialog, Escape closes it, no off-screen actions.

## Task 1 — parser and persistent API

Files: `backend/app/parser.py`, `backend/app/store.py`, `backend/app/main.py`, `backend/tests/test_api.py`, requirements files.

Interfaces: `parse_transcript(raw: bytes, filename: str) -> ParsedTranscript`; `create_app(data_dir: Path | None) -> FastAPI`. API: GET /api/health, GET /api/transcripts, GET /api/transcripts/{id}, GET /api/transcripts/{id}/source, POST /api/transcripts, POST /api/samples.

- [x] Write tests for sample count (3 transcripts, 42 passages, 21 expert passages), exact bytes, reloading persistent state, duplicate ingestion, malformed input, decreasing time, missing metadata, and atomic invalid batches.
- [x] Run `python -m pytest backend/tests -q`; expect missing implementation failure.
- [x] Implement parser with original offsets, strict metadata and timestamp validation; parameterized SQL and schema initialization; batch import transaction; bounded upload reading; safe source download.
- [x] Run the same suite; expect all tests pass.

## Task 2 — complete responsive workspace

Files: `frontend/src/App.tsx`, `frontend/src/api.ts`, `frontend/src/types.ts`, `frontend/src/components/*`, `frontend/src/styles.css` and Vite/TypeScript manifests.

Consumes the API above. Produces a production `frontend/dist` bundle.

- [x] Extract palette, spacing and split-pane layout from the generated reference into CSS tokens.
- [x] Implement library, reader, local filters, timestamp anchors, source download, upload dialog, help dialog, progress feedback and error retry paths.
- [x] Abort obsolete requests; preserve selection across refreshes; prevent duplicate sample/upload submissions.
- [x] Run `npm run build`; expect type checking and build success.
- [x] Exercise empty -> load samples -> select Germany -> search -> expert only -> clear search -> source download -> valid upload -> invalid upload. Expect true backend changes and no browser console errors.
- [x] Verify 1440px desktop and 390px mobile, keyboard modal behaviour and no horizontal overflow.

## Task 3 — local launch, verification and ZIP

Files: `start.ps1`, `README.md`, `.gitignore`, `docs/QA.md`, `docs/ARCHITECTURE.md`, `.env.example`.

- [x] Document single-origin setup and separate development commands; include original case-pack files.
- [x] Test built frontend served by FastAPI, not only the Vite dev server.
- [x] Run backend suite, frontend build and browser checks after fixes.
- [x] Conduct an independent review of parser/API and frontend state/accessibility while packaging documentation; fix material findings.
- [x] Create ZIP using an explicit allowlist; verify archive entries and absence of database, .env, .venv and node_modules.
- [x] Deliver ZIP and precise Part 1 scope plus test evidence. Wait for the user's verification before Part 2.

