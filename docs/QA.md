# Part 1 verification

Verified on Windows, Python 3.10 and Node 24, using the built frontend served by FastAPI.

## Automated checks

- **16 backend tests pass**: three supplied transcripts, 42 passages, 21 expert passages; exact download bytes; Unicode/BOM/CRLF offsets; persistence; renamed duplicate contents; atomic invalid batches; size/type/count limits; missing records; untrusted external origins; malformed timestamps; missing and empty metadata; speech missing a timestamp.
- TypeScript checking and Vite production build pass. Built JavaScript is approximately 241 kB (76 kB gzip).
- Three additional malformed-input regression cases failed before the parser fixes and pass after them.
- The pinned Starlette test client emits one deprecation warning for httpx; tests succeed. This does not affect runtime usage.

## Browser checks completed

Tested through the Codex in-app browser against actual local API/database responses, not mocked requests.

| Check | Result |
|---|---|
| Fresh empty workspace and sample import | 3 transcripts appear |
| Import samples again | 0 added, 3 duplicates |
| Choose France, Germany, UK | Correct source and metadata |
| Library search for Germany | Anna Keller only |
| Transcript search plus Expert only | Matching expert passage and highlighted search |
| Search with no matches; clear filters | Empty result message, then restored passages |
| Jump to 06:05 in Germany; reload | Same selected passage restored |
| Original file | Browser download triggered; exact bytes also checked by API test |
| Valid upload | Transcript count increases and new researcher appears |
| Invalid upload | Error remains in the dialog; no record added |
| Help and upload Escape | Dialog closes |
| Tab/Shift+Tab in help dialog | Focus wraps inside the dialog |
| Close dialog | Focus returns to Help |
| Desktop 1440 × 1000 | Split view renders correctly, no horizontal overflow |
| Mobile 390 × 844 | Library, reader and Back navigation work; no horizontal overflow |
| Mobile help | Dialog fits the viewport |
| Console | No captured warning/error messages in the final checked flow |
| Startup script, alternate port and data folder | Production app and samples load on port 8001 |

Screenshots: `design/desktop.png`, `design/mobile.png`. Browser verification is an exercised checklist, not a shipped automated browser suite. Backend regression tests are included.

## Independent review

A separate reviewer examined parser/API, source preservation, atomic uploads, duplicate detection, asynchronous reader selection, and modal behaviour. Three material parser findings were fixed and covered by regression tests. Browser QA also caught and fixed missing mobile download labels and dialog focus restoration/wrapping.

One deferred minor: search highlighting can be shifted for unusual Unicode characters whose lowercase representation changes length (for example İ). The supplied English transcripts are unaffected; original text and downloads remain intact.

## Your acceptance check

Extract the ZIP, follow the README, load samples, switch experts, search, toggle Expert only, jump to a timestamp, download a source, then restart the server. Confirm the saved library and the visual design before Part 2.


## Gemini and 30+ transcript extension — 2026-09-24

- 24 backend tests pass: 35-file atomic import; 35-source jobs; cached repeat analysis; Q&A; persisted results; missing key; exact quote/source/role checks; long passage splitting; sanitized Gemini transport errors; cancellation and busy responses; interrupted jobs; partial source failures; request limits.
- Production frontend typecheck/build passes.
- Browser verified with an isolated 35-interview database: source selection, missing-key state, saved analysis, and citation navigation to the correct 00:18 passage. Test-only provider fixtures were confined to ignored QA data; no fake results are installed in the user's database.
- Mobile Ask and citation reader checked at 390px viewport: no horizontal overflow. Configuration-dependent buttons remain disabled without a key.
- Live Gemini requests, answer quality and real quota behavior are not verified. API key configuration was explicitly deferred by the user.
