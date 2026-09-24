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

## Gemini analysis

Add your key to a local `.env` in the project root (use `.env.example` as a template):

```text
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.8-flash
```

Get a key from https://aistudio.google.com/apikey. Never commit `.env`. Open Analysis and click Check configuration; settings are reread without a restart. Keys stay on the backend. Running Analysis or Ask sends selected interview text to Google Gemini and may incur provider charges.

Select up to 50 interviews. Analysis answers the six original guide questions (editable), then compares common themes and differences. Ask retrieves up to three relevant 1,200-character expert excerpts from each selected interview. This is lexical retrieval, not an exhaustive reading for every question. Quote links open the original passage.

One background job runs at a time, processing interviews sequentially to bound provider traffic. Results and per-interview caches persist in SQLite. Cancel stops after the current provider request; restarting marks unfinished runs interrupted. Run again to reuse completed cached interviews and retry failures. Synthesis runs again each time. Saved runs remain available through the selector.

The server checks that each quoted span exists in the cited expert passage and computes its source offsets. This checks attribution, not whether the model's reasoning follows from the quote: review important conclusions. Unsupported or invalidly cited answers display an insufficient-evidence message. Very long interviews are split into bounded excerpts; cross-source synthesis uses compact validated answers and can miss nuance.

Automated tests cover 35-interview ingestion and jobs, caching, restart persistence, invalid citations, cancellation, partial failures and mocked Gemini HTTP responses. No live Gemini call has been validated yet; configure a key and review a small run before analyzing a large batch. API schema reference: https://ai.google.dev/gemini-api/docs/generate-content/structured-output

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

The default data directory is `data` beside this README. To choose another directory, pass `-DataDir` to the startup script or set `CLEARCALL_DATA_DIR` in the terminal. Gemini settings are loaded from the local `.env`; the data-directory setting remains a terminal/startup-script option. The ZIP contains no user database or secrets.

Later parts will use the same **clearcall** project root. Back up `data` and any future `.env` before replacing source files. Do not nest Part 2 inside Part 1. Schema v2 adds analysis jobs and cache tables without rewriting transcripts. Keep the server bound to 127.0.0.1: this version is a personal local tool, with no authentication or multi-user hosting layer.

## AI assistance disclosure

This implementation was created with OpenAI Codex assistance, including planning, coding, tests, and a generated visual reference. The final interface is native React/CSS, not an image. Source transcripts were supplied by the case-study pack and are not AI-generated by the application. The reader stays local; Analysis and Ask send selected source text to Gemini when you run them. Review the code, run the checks, and describe assistance accurately in your final case-study submission.
