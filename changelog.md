# ApplyMyFace.com — Changelog

---

## 2026-05-05 — Session 30: iPhone 15 / iOS 26.3.1 polish marathon

**File changed:** `mcfaces.html` (8 commits)

- **`f6cb9e8`** — `.viewer-buy` floating row anchored both sides (`left:10/right:10` + `space-between`); FAQ button no longer clips off the right edge on iPhone 15. Drawer height bumped `78dvh−150` → `85dvh−70` so iOS 26's persistent toolbar no longer hides Step 2.
- **`e7f6183`** — Step 1 collapses to a single green `✓ Character: <name>  [Change]` line once a skin is picked. Promotes Step 2 "Upload Face Photo" to the top of the drawer.
- **`14f3ad6`** + **`e8342ee`** — **Pick Your Character responsiveness** (huge perf win). Added `async` to skinview3d bundle so HTML parsing isn't blocked ~10s on cellular. Moved click-handler attachment from inside `loadSkinList()` (gated by `window.load`) to a `DOMContentLoaded` listener. Button now responsive instantly at app launch; flyout shows "Loading characters…" until the gallery resolves.
- **`47a8d51`** + **`9421e54`** + **`e6770fc`** — Drawer handle decluttered for iPhone 15: disclaimers pulled to edges (`left:18→4`, `right:8→4`), label shortened "▲ Start Over" / "▼ Tap to Close" → "▲ Open" / "▼ Close" across all 8 sites.
- **`fb68db6`** — `.face-panel` and `.photo-panel` mobile position `bottom:178px → 163px` so they no longer cover the character's face on iPhone 15.

**Open mystery deferred to next session:** iPhone 15 panels render ~10-15% larger than iPhone 13 with identical CSS (uniform scale across all internals — title, buttons, fp-label, padding). Page Zoom and Display Zoom both confirmed default. Hypothesis: iOS 26 changed default rem baseline. Next-session plan: instrument with `getComputedStyle(document.documentElement).fontSize` on iPhone 15 to confirm before changing CSS.

---

## 2026-04-22 — BrowserStack Mobile Polish (iPhone first)

**File changed:** `mcfaces.html`

- **A/W/D buttons smaller**: `.viewer-left-box` mobile scale reduced `1.17` → `0.82` (~30% smaller)
- **What's In The Box + Buy Now smaller**: `.viewer-buy` mobile rule — `transform: scale(0.6); transform-origin: bottom right` (40% smaller)
- **Drawer handle shorter**: padding `10px/6px` → `4px/3px`; peek `80px` → `50px` (~30px less height)
- **Deploy workflow corrected in CLAUDE.md**: git commit locally first → SCP → restart → git push

### Android S21 — Pending review next session
- Verify A/W/D scale(0.82) on Android (was rendering in document flow, not overlaid on viewer)
- Verify What's In The Box + Buy Now scale(0.6) on Android
- Investigate gray media overlay pill (Chrome detects skinview3d canvas as media — may block taps)
- All buttons/drawer non-functional on Android — likely pointer-events blocked by media overlay
- Raise character in 3D viewport: `viewer.controls.target.set(0, -8, 0)` on mobile — not yet implemented

---

## 2026-04-22 — Morning/Afternoon Session

**File changed:** `mcfaces.html`

- GitHub repo fully set up: github.com/axirad/Apply
- Memory files moved to OneDrive, CLAUDE.md updated with absolute paths
- Mouse legend + Animate/Walk/Default box → permanent `.viewer-left-box` lower-left of viewer
- Mobile face adjustments: title bars, pointer-events, panel positioning all fixed
- Crosshair auto-off when face adjustments closed (`markDirty()` added to `setControlsOpen(false)`)
- Mobile drawer delay: 1000ms → 500ms after character pick
- Desktop color correction panel: button height 34px → 29px; Auto+Reset left-aligned; Compare centered
- Compare button margin tweaks; vertical position corrected
- "Side" → "Side/Side" label in Move Face panel
- Rotate symbols: ◀▶ → ↶↷, `font-size: 2rem`
- Move Face reset ↺: `font-size: 1.5rem`
- Move Face panel shifted 15px right (`right: calc(50% + 145px)`)
- "What's In The Box" flyout: Back button added next to Buy Now; "Got It" centered when not ready
- "Adjustment Done" button label (was "✓ Done")
- ApplyMyFace logo position: `top: 0px`
