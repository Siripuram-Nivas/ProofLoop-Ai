# ProofLoop AI — Design System

## Palette (single source: `frontend/src/index.css` `@theme`)

| Token | Hex | Role |
|---|---|---|
| `--color-ink` | `#171923` | Primary text, dark surfaces, sidebar |
| `--color-powder` | `#80B9F0` | Primary accent, active states, proof links |
| `--color-lavender` | `#E9E8F8` | Page wash, cards, quiet surfaces |
| `--color-peach` | `#F5B69E` | Human/uncertainty accent, highlights |
| `ink-soft` | `#4B4F5C` | Secondary text |
| `line` | `#D8D8E6` | Borders |
| surface | `#F7F6FC` | App background |
| support | `#2F7D5D` | Supported evidence only |
| contradict | `#B4443C` | Contradicted evidence only |
| caution | `#A9711F` | Insufficient / stale |

Semantic colours are used **only** for evidence meaning and status, always paired with text labels
(never colour-only). Contrast targets: body text ≥ 7:1, secondary ≥ 4.5:1, focus rings visible.

## Typography

- Display: `Instrument Serif` (Google Fonts, `display=swap`) with Georgia fallback. Tight tracking,
  large sizes, used for headlines and report titles only.
- Body/UI: `Inter` with Segoe UI/system fallback. Weights 400/500/600/700; tabular numbers for metrics.
- Scale: display 44–84px, h1 32–40, h2 24–28, body 15–16, meta 12–13. Line height 1.55 body.

## Space, radius, elevation

- Spacing on a 4px grid; section rhythm 96–128px landing, 24–32px app.
- Radii: `sm 10px`, `md 14px`, `lg 20px`, `xl 28px`, pills 999px.
- Shadows: soft two-layer (`0 1px 2px` + `0 18px 50px -30px`), never neon glow.

## Components

Buttons (primary = ink on lavender-ish? primary = ink background/white, accent = powder tint),
secondary (outline), ghost, danger. Focus ring 2px powder offset 2. Disabled 40% + no pointer.
Cards: white/lavender surface, 1px line, radius lg. Badges: tinted background + dark text + dot.
Inputs: 44px min height, visible label, helper/error text. Tables: generous rows, sticky header.
Graph nodes: rounded rectangles with icon chip, type-coloured left border, selected ring.

## Motion

- 150–250ms ease-out for UI; hero sculpture drifts over 18–24s.
- `prefers-reduced-motion: reduce` disables all continuous animation.
- No animation that blocks reading or moves targets.

## Accessibility

- Skip link, landmark elements, labelled controls, `aria-live` for pipeline status and toasts.
- Keyboard: graph supports tab-to-node + Enter to inspect; dialogs close on Escape; drawer traps focus.
- Status always encoded as icon + text; no red/green-only meaning.
- Responsive at 360, 768, 1024, 1440. Sidebar collapses to a sheet below `lg`.

## Anti-patterns banned

Fake metrics, invented testimonials/logos, glassmorphism over text, animations for decoration without
meaning, tiny uppercase labels below 11px, rainbow gradients, purple-blue "AI startup" cliché.
