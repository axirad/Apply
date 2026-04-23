# ApplyMyFace.com — Changelog

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
