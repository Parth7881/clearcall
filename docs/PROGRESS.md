# Implementation ledger — docs/IMPLEMENTATION_PLAN.md

- Scope approved. Latest direction: restrained Google-inspired styling, subtle edges, no extra features.
- Ruling: use a separate deliverable directory rather than a Git worktree; this is a standalone ZIP, unrelated to the parent application. No parent code is changed.
- Pre-flight: API endpoints and passage fields are shared by backend and frontend; tests establish that contract before UI work.
- Ruling: actual expert metadata overrides incidental mistakes in the generated visual reference.
- Task 1: complete — 13 initial tests passed; 3 final-review regression cases added, observed failing, fixed, and all 16 passed.
- Task 2: complete — typed frontend production build passed; desktop and mobile exercised against real local API. Dialog focus wrapping/restoration and mobile source label verified after fixes.
- Task 3: startup script verified on port 8001 with a separate data directory; README, architecture diagrams, case pack and QA evidence prepared.
- Ruling: browser checks were performed through the available in-app browser; no separate browser automation framework is needed in the deliverable. Cost: browser regression checks are manual for now.
- Final review: independent reviewer found three Important parser issues; all fixed with failing-then-passing regression tests.
- Final: minor (deferred): Unicode lowercase expansion can shift search highlighting for rare characters such as İ; source text and supplied English files are unaffected.
