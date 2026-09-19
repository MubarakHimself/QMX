# Lieflat → Quantum IDUX grammar

Source: `imports/lieflat-charts` (https://github.com/larashero3-dotcom/lieflat-charts)
License: PolyForm Noncommercial 1.0.0 — visual grammar only. Do not ship their templates.

## Thesis

Paper grey and charcoal at the poles. Lightness is hierarchy: the blackest mark is the most important number. Hairlines, ledger rails, and whitespace do the work that boxes and drop shadows usually fake. Two reading speeds, not two products: **Lupi** (slow, record-level, annotations) and **Glance** (fast, pre-aggregated, conclusion first). Color is optional and never mixed: Mono, Porcelain, Palm, or Wire — one system per surface.

## Mono tokens (from `mono-tokens.js`)

| Role | Hex | Use |
|---|---|---|
| ink | `#1C1C1A` | titles, primary data |
| paper | `#F0EFEB` | page and card (same; no card stroke) |
| muted | `#8F8E88` | subtitles, legends |
| faint | `#C6C5BF` | source line, ticks |
| grid | `#DEDDD6` | hairlines, rails |
| ladder | `#1C1C1A #4A4944 #6A6963 #8F8E88 #B0AFA9 #C6C5BF #D8D7D1` | multi-series by importance |

Dark card: bg `#1C1C1A`, ink `#F0EFEB`, faint `#55554F`, grid `#2E2D29`.

Type: Inter. Title 16.5/700/−0.02em. Display 19/700. Sub 11.5/400. Source 9.5/500/+0.08em uppercase. Values 800. Axis 9.5/600. Min size 6.5 (half card) / 5.5 (wide).

Shape: card radius 24, pad 28/28/20, bar capsule 99, tooltip 12.

Motion: 900ms enter, quarticOut, no bounce. Honor `prefers-reduced-motion`.

## Color presets (from `color-presets.js`)

- **Porcelain** (ordinal blue): bg `#F7F2EB`, hero `#081F5C`, data `#334EAC`, CAT4 `#081F5C #334EAC #7096D1 #BAD6EB`. Ordered series only, ≤4 bins.
- **Palm** (categorical green/amber): data `#43593B`, hero `#D4A017`, CAT4 `#43593B #77835A #ACAD79 #F2D17E`. Unordered categories ≤4.
- **Wire** (mono + one orange): hero `#F5572F` on one element only. Default accent for IDUX kill/alert.

Color strokes scale ×1.8 and opacity floor 0.85.

## Adopt vs reject

Adopt: mono spine, hairlines, two speeds, Inter, dark-card inversion, Wire as single accent, Porcelain for ordered live series.

Reject: report-poster templates, Moxt workflow, decorative blob noise as density, mixing presets on one screen, neon trading-terminal greens/reds as the whole palette.

## IDUX mapping

One spine, two themes (`scheme/Paper`, `scheme/Terminal`). Inter for UI/prose. IBM Plex Mono for money and quantities. Semantic extras (not in Lieflat): `color.kill` `#F5572F`, `color.live` `#334EAC`, `color.gain` `#3D6B4F`, `color.loss` `#A33B32`.
