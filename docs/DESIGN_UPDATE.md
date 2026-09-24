# Research workspace redesign

The direction uses the supplied references for strong hierarchy, purposeful color, balanced space and confident typography. It retains the transcript workflow; no commerce, billing, account or marketing features were copied.

## Visual system

- Manrope variable headings: distinct shapes, compact labels, clear hierarchy.
- Source Sans 3 variable body: 17px expert text and 16px interviewer text, comfortable line spacing, approximately 74-character maximum reading width.
- Ink #182b4b for structure; blue #245de0 for actions and selection; white for source reading; pale blue-grey for the surrounding workspace.
- Teal and amber distinguish source avatars and market markers. All distinctions also have text labels.
- Compact transient-position success message, persistent until dismissed; no layout displacement.
- Source text, timestamps, controls and source downloads retain their original behavior.

Fonts are served locally. Their OFL licenses are in docs/licenses. No external font service is used at runtime.

## Phone layout

The library retains the study overview and upload controls. Selecting an interview opens a focused reading view with a Back action. The overview is hidden during reading so the transcript gets the screen space. Narrow controls use 16px input/select text.

## Verification

- TypeScript and Vite production build passed.
- Browser checks at 1440px desktop, 390px phone and 320px narrow width found no horizontal overflow.
- Selection, transcript search with expert-only filtering, mobile back navigation, upload dialog, Escape, and Tab focus containment exercised.
- Checked named normal-text color pairs; low-contrast footer and empty-state colors were darkened. Representative ratios: body-muted on white 5.02:1; interviewer on white 5.03:1; source eyebrow on white 4.67:1; expert label on its pale surface 4.87:1.
- This is not a complete screen-reader or cross-browser certification. Existing backend regressions run separately.

Current screenshots: docs/design/redesign-desktop.png and redesign-mobile.png. Earlier screenshots are retained as before-state evidence.
