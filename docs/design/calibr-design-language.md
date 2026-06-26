# SignalLoop Design Language (Calibr-derived)

Status: implemented (June 2026)
Source: `Downloads/calibr.html` (Calibr — Assessment Platform reference UI)
Applies to: the employer portal (`/employer`, `/admin`) and the candidate workspace
(`/invite/[inviteToken]`), plus the evidence report view.

This document defines a single dark design language for SignalLoop, derived from the
Calibr reference. It also records which parts of the Calibr UX SignalLoop actually
supports, so we adopt the *look* without implying features we don't have.

---

## 1. Design principles

- **Dark, dense, instrument-panel feel.** Deep navy backgrounds, hairline borders,
  small type, generous use of monospace for numbers. The product should read like a
  precision tool, not a marketing site.
- **One accent does the work.** Blue (`#3B82F6`) is the primary action / selection
  color. Other hues (green/amber/red/purple/cyan/orange/indigo) are *semantic only* —
  status, score thresholds, and per-module identity — never decoration.
- **Surfaces stack by elevation.** Five background steps (`bg0`–`bg4`) communicate depth
  instead of shadows. Higher = more elevated/interactive.
- **Numbers are monospace.** Scores, counts, timers, minutes — anything quantitative —
  use JetBrains Mono so columns align and values feel measured.
- **Selection is shown with color + tint + border**, never with a checkbox alone: an
  active card gets the accent border and a faint accent-tinted background.

---

## 2. Color tokens

Taken verbatim from the Calibr reference `C` palette. These become the CSS custom
properties for the whole app (see §7 for the variable names).

### Surfaces (elevation, dark → light)
| Token | Hex | Use |
|-------|-----|-----|
| `bg0` | `#0A0F1A` | App canvas / outermost background |
| `bg1` | `#0F1629` | Top bar, sidebars, side panels |
| `bg2` | `#141E35` | Cards, list rows, stat tiles |
| `bg3` | `#1C2840` | Active nav item, nested rows |
| `bg4` | `#1E2D4A` | Inputs, selects, pill backgrounds |

### Borders
| Token | Hex | Use |
|-------|-----|-----|
| `b0` | `#1A2A45` | Default card / divider border (hairline) |
| `b1` | `#243357` | Input border, stronger divider |
| `b2` | `#2E4070` | Toggle track border |

### Text
| Token | Hex | Use |
|-------|-----|-----|
| `t0` | `#EEF2FF` | Primary text, headings, values |
| `t1` | `#7C91B8` | Secondary text, descriptions |
| `t2` | `#445577` | Muted labels, placeholders, "—" |

### Semantic / accent pairs (foreground + tinted background)
| Token | Fg | Bg | Meaning |
|-------|-----|-----|---------|
| blue | `#3B82F6` | `#0E1F42` | Primary action, selection, "in progress" |
| green | `#10B981` | `#052E1C` | Success, submitted, score ≥ 80, integrity |
| amber | `#F59E0B` | `#2A1A03` | Warning, invited/pending, score 60–79 |
| red | `#EF4444` | `#2A0A0A` | Error, score < 60, high risk |
| purple | `#A78BFA` | `#1A0F35` | Accent (status variety) |
| cyan | `#22D3EE` | `#041E2A` | Accent |
| orange | `#FB923C` | `#2A1005` | Accent |
| indigo | `#818CF8` | `#0F0F30` | Accent |

**Score thresholds (canonical):** `≥80 → green`, `60–79 → amber`, `<60 → red`.
**Status mapping:** submitted → green, in progress → blue, invited → amber.

---

## 3. Typography

- **Sans:** `Inter` (weights 400/500/600). System-ui fallback.
- **Mono:** `JetBrains Mono` (400/500) — for all numbers, scores, timers, code-ish tags,
  language names, and email/token strings.
- **Scale (px):** 28 (big stat value), 24 (stat value), 22 (panel stat), 18 (logo),
  17 (section title), 15 (drawer name), 13 (body/card title), 12 (body), 11 (label),
  10 (chip), 9 (uppercase eyebrow label).
- **Letter-spacing:** headings tighten slightly (`-0.2px` to `-0.3px`); uppercase eyebrow
  labels expand (`0.07em–0.08em`).
- **Eyebrow labels:** 9px, uppercase, weight 600, `t2`, letter-spacing `0.07em` — used on
  stat tiles and section sub-headers ("STATUS", "MODULES", "TOTAL TIME").

---

## 4. Spacing, radius, layout

- **Radius:** pills/badges `20px`; cards `12px`; tiles/panels `8–10px`; inputs/buttons
  `6–8px`; icon tiles `9px`.
- **Card padding:** `16px` (module/candidate cards), `10–14px` (stat tiles), `24px`
  (drawers / page gutters).
- **Borders:** hairline `1px` default; selected cards `1.5px` accent.
- **App frame:** fixed top bar (50–64px) + left sidebar (~196px) + scrollable page +
  optional right context panel (~248px) or right drawer (~420px).
- **Card grids:** `repeat(auto-fill, minmax(290–300px, 1fr))`, gap `12px`.
- **Stat grids:** `repeat(4, 1fr)` (overview), `1fr 1fr` (side panel summary), gap `8–12px`.

---

## 5. Component patterns

These are the reusable atoms from the reference. All page UIs should be built from these.

- **Stat tile** — `bg2`, `b0` border, radius 10. Eyebrow label (9px uppercase) + big mono
  value (24–28px) + small unit caption (`t2`).
- **Status badge** — pill (radius 20), 11px/500, tinted bg + colored fg per status.
- **Score bar** — thin track (`b1`, 3–4px) + colored fill (green/amber/red by threshold) +
  mono value. `—` in `t2` mono when no score.
- **Card (module / candidate)** — `bg2` default; when selected/active, accent-tinted bg
  (`abg`) + accent border. 38px rounded icon tile top-left, toggle top-right.
- **Toggle** — 40×22 track, `b1`/accent, white 14px knob that slides.
- **Pill button (filter / difficulty)** — radius 20, accent border + accent-tint bg when
  active, `b1`/transparent when inactive.
- **Segmented option group** — equal-width buttons sharing a row; active = accent border +
  accent-tint bg + accent text. Used for "Timing enforcement".
- **Tabs** — text buttons with a 2px bottom border; active = blue text + blue underline.
- **Right context panel** — `bg1`, left border `b0`, holds the assessment summary + send
  controls.
- **Right drawer** — fixed, 420px, `bg1`, slides over a `rgba(0,0,0,0.65)` scrim; used for
  candidate profile detail.
- **Input / select** — `bg4` bg, `b1` border, radius 6–7, `t0` text, no outline on focus
  (border is the affordance). Selects/values that are code-ish use mono.
- **Icon tile** — rounded square, module-tinted bg (`abg`) + `{accent}44` border + colored
  Tabler/Lucide icon.

---

## 6. What SignalLoop supports vs. the Calibr reference

The Calibr reference shows a broad assessment suite. SignalLoop adopts its **visual
language only**. The product surface is narrower. This table is the contract — build the
UI to it, do not re-introduce unsupported features just because the reference shows them.

### Assessment modules

| Calibr module | SignalLoop |
|---------------|-----------|
| Coding challenge | **Supported — the only module.** |
| Debugging & code review | Folded into the coding challenge (not a separate module) |
| System design | Not supported |
| AI & LLM awareness | Not supported |
| Logical reasoning | Not supported |
| Psychometric profile | Not supported |
| SQL & data querying | Not supported |
| Communication & language | Not supported |

So the "module grid" collapses to a **single coding-challenge module** (or a small set of
coding variants), not eight cards.

### Coding-challenge "languages" → assessment levels

Calibr's coding card lists languages (Python, Java, Go, JS, TS, C++). SignalLoop is
Python-only and instead exposes our two real assessment packs as **levels**:

| Reference concept | SignalLoop value | Backed by |
|-------------------|------------------|-----------|
| Language picker | **Python — Basic** | `fastapi_task_api_standard_v2` (Standard FastAPI v2) |
| | **Python — Advanced** | `fastapi_task_api_advanced_v1` (Advanced FastAPI v1) |

(Other languages are dropped. The selector reads "Python · Basic / Advanced".)

### Configuration controls

| Calibr control | SignalLoop |
|----------------|-----------|
| Assessment summary (modules, total time) | **Supported — keep.** Drive from selected level's recommended minutes. |
| Timing enforcement (Strict / Soft / Untimed) | **Supported — but simplified.** We map to **Strict** (timed, hard expiry) vs **Untimed**. "Soft limit" is not a real backend mode; do not offer it. |
| Score visibility (Employer only / Shared) | **Not supported — remove the control.** Reports are employer-only by default. |
| Difficulty (Adaptive / Standard / Hard) | Not supported as a live control — difficulty is fixed by the chosen pack (Basic/Advanced). Drop the difficulty pills. |
| Advanced tab (integrity monitoring, contradiction probing, ATS, webcam, copy-paste) | Mostly aspirational in the reference. SignalLoop has real proctoring (webcam consent, focus-loss) and AI-collaboration integrity already — surface only those, not the unimplemented toggles. |

### Pages

| Calibr page | SignalLoop |
|-------------|-----------|
| Overview | Maps to employer/admin landing — candidate counts, totals, recent activity. Supported. |
| Assessments (build assessment) | Maps to the employer invite-creation flow (pick level, timing, send invite). Supported, simplified per above. |
| Candidates | Maps to the employer attempt list + candidate drawer. Supported. |
| Reports | Maps to the evidence report view. Supported. |

---

## 7. Implementation: CSS custom properties

Replace the current light palette in `apps/web/src/app/globals.css` `:root` with the dark
token set below. Both employer and candidate pages already consume these variables, so the
theme flips in one place; component CSS then refers only to tokens (never raw hex).

```css
:root {
  /* surfaces */
  --bg0: #0A0F1A;  --bg1: #0F1629;  --bg2: #141E35;  --bg3: #1C2840;  --bg4: #1E2D4A;
  /* borders */
  --b0: #1A2A45;   --b1: #243357;   --b2: #2E4070;
  /* text */
  --t0: #EEF2FF;   --t1: #7C91B8;   --t2: #445577;
  /* semantic fg / bg */
  --blue: #3B82F6;   --blue-bg: #0E1F42;
  --green: #10B981;  --green-bg: #052E1C;
  --amber: #F59E0B;  --amber-bg: #2A1A03;
  --red: #EF4444;    --red-bg: #2A0A0A;
  --purple: #A78BFA; --purple-bg: #1A0F35;
  --cyan: #22D3EE;   --cyan-bg: #041E2A;
  --orange: #FB923C; --orange-bg: #2A1005;
  --indigo: #818CF8; --indigo-bg: #0F0F30;
  /* type */
  --font-mono: "JetBrains Mono", ui-monospace, monospace;

  /* legacy aliases kept so existing selectors don't break during migration */
  --bg: var(--bg0);
  --panel: var(--bg2);
  --panel-2: var(--bg3);
  --text: var(--t0);
  --muted: var(--t1);
  --border: var(--b0);
  --accent: var(--blue);
  --accent-dark: #2563EB;
  --danger: var(--red);
  --warning: var(--amber);
  --code-bg: #0A0F1A;
}
```

Load `JetBrains Mono` alongside the existing `Inter` (Tabler icons in the reference are
already covered by the app's `lucide-react`).

---

## 8. Rollout (completed)

All steps below shipped, each behind `tsc --noEmit`, `next build`, and the Playwright e2e
suite (30 passed / 2 live-only skipped), plus in-browser visual checks.

1. **Tokens** — `:root` in `apps/web/src/app/globals.css` holds the dark palette + legacy
   aliases; all raw-hex selectors were remapped to tokens. Inter + JetBrains Mono load via
   `<link>` in `layout.tsx`; numeric values use `var(--font-mono)`.
2. **Employer portal app shell** — top bar + left sidebar (Workspace: Overview / Assessments
   / Candidates / Reports; Account: Settings / Help & docs) with client-side view switching.
   - **Overview** — colored stat tiles + recent-activity feed.
   - **Assessments** — the single live "Coding challenge (Python)" card with a Basic/Advanced
     level selector and the assessment-summary + send-invite panel (timing Strict/Untimed; no
     score-visibility or difficulty controls), plus a **"Coming soon" roadmap grid** of the
     other Calibr module types as non-selectable previews (coding remains the only supported
     module).
   - **Candidates** — filterable attempt table; each row has an **Assessment** link to the
     candidate's invite URL plus the report link when submitted.
   - **Reports** — submitted attempts with report links.
3. **Evidence report + admin portal** — restyled to the dark tokens (score ring, bars,
   badges, banners). Admin reuses employer styling.
4. **Candidate workspace** — IDE shell on the dark tokens; Monaco runs in `vs-dark`.
5. **Brand + auth** — logo recolored to the blue/cyan accent. The Clerk sign-in modal and
   UserButton keep Clerk's default readable surface with only `colorPrimary` tinted blue;
   forcing a dark `colorBackground` made the modal/popover text and the "Continue with Google"
   button invisible, so it was removed (`@clerk/themes` `dark` did not apply in this version).
