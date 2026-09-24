# Clearcall

A local workspace for the Hasamex European Robotic Surgery Market interviews. Minimal white interface, desktop and mobile layouts, original text and timestamps, and a real persistent backend.

The interface uses locally bundled Roboto, white and grey surfaces, a blue action color, and a focused mobile reader. See `docs/DESIGN_UPDATE.md` for design decisions and verification.

## Permanent project and GitHub updates

This is one project, not a series of nested ZIP folders. Continue using the same folder in VS Code. Local transcripts in `data/`, virtual environments, dependencies and secrets are ignored by Git.

After a future update is pushed to this repository, stop the server with Ctrl+C, run `git pull --ff-only` from this project folder, then run `./start.ps1`. If you have made your own code changes, commit or review them before pulling; do not force-reset the folder. A built frontend is committed so normal use does not require rebuilding it. Database migrations, when needed, will be documented with the relevant part.

## Run on Windows

1. Extract the ZIP. Open the **clearcall** folder in VS Code.
2. Install Python **3.10 or newer** if it is not already installed.
3. Open a PowerShell terminal in that folder and run:

```powershell
./start.ps1
```

If your computer blocks unsigned scripts, use the manual commands below; no policy change is necessary.

4. Open **http://127.0.0.1:8000** in your browser.
5. Click **Upload transcripts** and select your interview .txt files. The supplied interviews are available in `backend/samples` if needed.

First launch downloads Python dependencies. The production frontend is included: **Node is not needed just to run the ZIP**. Stop the server with Ctrl+C. Subsequent runs keep your transcripts. If port 8000 is occupied, use `./start.ps1 -Port 8001` and open port 8001 instead.

Manual launch, from the project root:

```powershell
py -3 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.lock.txt
./.venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --app-dir backend --host 127.0.0.1 --port 8000
```

On macOS/Linux use `python3 -m venv .venv` and `.venv/bin/python` in place of the Windows Python path.

## What works

- Upload interview files; repeated uploads of identical contents do not duplicate them.
- Upload up to 50 UTF-8 `.txt` files at once, up to 2 MiB per file and 50 MiB total per upload.
- Keep transcripts after a server restart in `data/clearcall.sqlite3`.
- Find experts by name, role or market; search within a transcript; show expert passages only.
- Jump to a timestamp and reopen the same passage through the address bar link.
- Download the untouched original file, with its original filename.
- Use the library and reader on mobile with a Back to transcripts action.
- Receive usable validation errors; an invalid batch saves none of its files.

## Groq analysis

Add your key to a local `.env` in the project root (use `.env.example` as a template):

```text
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

Get a key from https://console.groq.com/keys. Never commit `.env`. Open Guide answers and click Check configuration; settings are reread without a restart. Keys stay on the backend. Running Guide answers or Ask sends selected interview text to Groq and may incur provider charges.

Select up to 50 interviews. Guide answers starts empty. Enter one question per line, or explicitly load the supplied case-study guide. Each question produces one combined answer identifying expert views, shared findings and material differences. Source quotes expand on demand. Ask handles a single follow-up question. Ask splits expert passages into excerpts of up to 1,200 characters, includes the highest-ranked excerpt from every selected interview, then adds relevant excerpts within a 64,000-character budget. Short interviews can fit in full. This is lexical retrieval, not an exhaustive reading for every question. Quote links open the original passage.

One background job runs at a time, processing interviews sequentially to bound provider traffic. Results and per-interview caches persist in SQLite. Cancel stops after the current provider request; restarting marks unfinished runs interrupted. Run again to reuse completed cached interviews and retry failures. Synthesis runs again each time. Saved-run controls and automatic reopening of completed results have been removed. Current-session answers survive tab navigation; backend progress and caching remain persistent.

The server checks that each quoted span exists in the cited expert passage and computes its source offsets. This checks attribution, not whether the model's reasoning follows from the quote: review important conclusions. Unsupported or invalidly cited answers display an insufficient-evidence message. Very long interviews are split into bounded excerpts; cross-source synthesis uses compact validated answers and can miss nuance.

Automated tests cover 35-interview ingestion and jobs, caching, restart persistence, invalid citations, cancellation, partial failures and mocked Groq HTTP responses. Live verification results are recorded in docs/QA.md. Review a small run before analyzing a large batch; account rate and token limits can require retries. API schema reference: https://console.groq.com/docs/structured-outputs

## Transcript format

```text
Expert: Jane Smith
Role: Research Director
Market: United Kingdom

00:00
Interviewer: What is your view?

00:18
Jane Smith: The expert response.
```

The supplied `Expert 1 – Name` header is also supported. Headers must have values on the same line. Use one expert per file and a new timestamp before every speaker turn. Label questions `Interviewer`, `Moderator`, or `Host`; all other speaker labels are treated as the expert. Timestamps must increase or stay equal; formats are MM:SS or HH:MM:SS. Do not put a second speaker-labelled line inside a passage without a timestamp. Blank metadata, missing timestamps, invalid time values, binary data, and unexpected text before the first timestamp are rejected.

Quotes shown in the reader are source text, not generated summaries. Timestamps are passage starts; no audio, end times, or word-level timing is available. Offsets are Unicode character positions in the UTF-8-decoded source with any initial BOM removed. Original download bytes still include the BOM and original line endings.

## Develop in VS Code

Use Node **22.12+** (tested with Node 24) and Python 3.10+.

```powershell
# Terminal 1, project root
./.venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --app-dir backend --reload --host 127.0.0.1 --port 8000

# Terminal 2
cd frontend
npm ci
npm run dev
```

Open the Vite address shown in Terminal 2. It proxies `/api` to port 8000. To rebuild the included production UI, run `npm run build` in `frontend`, then refresh the browser at port 8000.

## Verify

```powershell
# Project root
./.venv/Scripts/python.exe -m pytest -q

# Frontend folder
npm run build
```

See `docs/QA.md` for the browser checklist and test results, and `docs/ARCHITECTURE.md` for the data flow and three-part delivery diagram. Interactive API documentation is at `/api/docs`.

## Data and upgrades

The default data directory is `data` beside this README. To choose another directory, pass `-DataDir` to the startup script or set `CLEARCALL_DATA_DIR` in the terminal. Groq settings are loaded from the local `.env`; the data-directory setting remains a terminal/startup-script option. The ZIP contains no user database or secrets.

Later parts will use the same **clearcall** project root. Back up `data` and any future `.env` before replacing source files. Do not nest Part 2 inside Part 1. Schema v2 adds analysis jobs and cache tables without rewriting transcripts. Keep the server bound to 127.0.0.1: this version is a personal local tool, with no authentication or multi-user hosting layer.

## AI assistance disclosure

This implementation was created with OpenAI Codex assistance, including planning, coding, tests, and a generated visual reference. The final interface is native React/CSS, not an image. Source transcripts were supplied by the case-study pack and are not AI-generated by the application. The reader stays local; Analysis and Ask send selected source text to Groq when you run them. Review the code, run the checks, and describe assistance accurately in your final case-study submission.


## Technical-round walkthrough

1. Upload the three supplied interviews from `backend/samples`.
2. Open Guide answers, click Use case-study guide, and run all three interviews.
3. Read one combined answer per question. Expand Sources and click a citation to verify its original text and timestamp.
4. Review shared views and differences within each answer. Compare the Germany-wide growth estimate with France's stronger-centre estimate without treating different scopes as a contradiction.
5. Open Ask and ask how budgets and ROI influence purchasing. Verify the cited experts and passages.
6. Explain scaling: 50-file atomic imports, bounded source chunks, one background job, persistent progress, per-source caching and retrieval across selected interviews. Rate limits remain account-dependent; 50-source support does not mean 50 simultaneous provider calls.

Groq hosts `openai/gpt-oss-120b`, selected for strict JSON-schema output and evidence extraction. This requires a Groq key, not an OpenAI key. The adapter retries transient failures and honors numeric Retry-After delays up to 60 seconds. Longer quota restrictions are returned as an actionable error; successful source work remains cached. No automatic provider fallback sends your interviews elsewhere.


Additional supported import format: `Expert ID: EXP-05`, `Role: Systems Engineer`, and optional `Core Subject: Infrastructure`, followed by the same timestamped speaker turns. A missing Market in this ID-based format is recorded as Not specified, never inferred. Source bytes and quote offsets remain unchanged. Uploads show a selected-file count and accept up to 50 files, 2 MiB each and 50 MiB total. Invalid batches still save no files.
