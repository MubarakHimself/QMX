---
name: QuantMindX Precision Workspace
colors:
  surface: '#f9f9ff'
  surface-dim: '#d7dae5'
  surface-bright: '#f9f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f3ff'
  surface-container: '#ebedf9'
  surface-container-high: '#e5e8f3'
  surface-container-highest: '#dfe2ed'
  on-surface: '#181c24'
  on-surface-variant: '#434655'
  inverse-surface: '#2c3039'
  inverse-on-surface: '#eef0fc'
  outline: '#737686'
  outline-variant: '#c3c6d7'
  surface-tint: '#0053db'
  primary: '#004ac6'
  on-primary: '#ffffff'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#b4c5ff'
  secondary: '#006c4a'
  on-secondary: '#ffffff'
  secondary-container: '#82f5c1'
  on-secondary-container: '#00714e'
  tertiary: '#824500'
  on-tertiary: '#ffffff'
  tertiary-container: '#a65900'
  on-tertiary-container: '#ffede1'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#85f8c4'
  secondary-fixed-dim: '#68dba9'
  on-secondary-fixed: '#002114'
  on-secondary-fixed-variant: '#005137'
  tertiary-fixed: '#ffdcc3'
  tertiary-fixed-dim: '#ffb77d'
  on-tertiary-fixed: '#2f1500'
  on-tertiary-fixed-variant: '#6e3900'
  background: '#f9f9ff'
  on-background: '#181c24'
  surface-variant: '#dfe2ed'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: -0.005em
  body-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 14px
    letterSpacing: 0em
  data-mono-lg:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: -0.02em
  data-mono-md:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: -0.01em
  data-mono-sm:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '400'
    lineHeight: 12px
    letterSpacing: 0em
  label-dense:
    fontFamily: Inter
    fontSize: 10px
    fontWeight: '600'
    lineHeight: 12px
    letterSpacing: 0.04em
  label-mono-tag:
    fontFamily: JetBrains Mono
    fontSize: 9px
    fontWeight: '600'
    lineHeight: 10px
    letterSpacing: 0.06em
spacing:
  gutter: 1px
  margin: 0px
  space-2xs: 0.125rem
  space-xs: 0.25rem
  space-sm: 0.375rem
  space-md: 0.5rem
  space-lg: 0.75rem
  space-xl: 1rem
---

## Brand & Style

This design system delivers a high-density, execution-focused operational workspace engineered for quantitative researchers, portfolio strategists, and financial systems engineers. The aesthetic fuses the absolute information density and keyboard-first utility of legacy institutional systems (Bloomberg Terminal, Launchpad) with the microscopic optical clarity and disciplined geometry of modern high-craft desktop applications.

### Core Tenets
- **Radical Information Density:** Every pixel serves operational comprehension. Zero ornamental padding, no floating empty cards, and no whimsical consumer-facing radius values. Layout space is compact, structured, and predictable.
- **Micro-Precision Visual Hierarchy:** Structural clarity is forged via 1px hairline division lines, high-contrast ink chrome, muted slate metadata, and specialized status-ink channels rather than dropped drop-shadows or volumetric gradients.
- **Instrument-Grade Restraint:** Motion is minimal (under 120ms, strictly mechanical curves). Visual accents are functional cues denoting live execution states, workspace link-groups, order routing channels, or delta anomalies.
- **Hybrid Chrome Contrast:** High-density dark graphite/ink contextual rails, toolbars, and global shell headers encapsulate light slate-stone internal working panels to protect cognitive endurance during prolonged quantitative model tuning, backtesting, and factor-risk attribution runs.

## Colors

The color system operates on an asymmetric hybrid model: deep graphite structural chrome surrounds luminous, neutral parchment-stone operational surfaces. This preserves deep visual grounding for workspace navigation while maximizing legibility across high-density tabular data grids, interactive matrices, and chart overlays.

### Palette Allocation & Semantic Tokens

- **Shell & Navigation Rails (Graphite Base):**
  - Rail / System Header Background: `#13161c`
  - Panel Strip / Dark Toolbar Background: `#1a1e26`
  - Sub-pane / Dock Container Background: `#232936`
  - Dark Mode Hairline Dividers: `#2d3546`

- **Canvas & Data Surfaces (Parchment Stone):**
  - Primary Active Surface: `#ffffff`
  - Secondary Workspace Panel / Inset: `#f4f5f7`
  - Tertiary Dense Header / Grouping Background: `#eef0f3`
  - Surface Hairline Border: `#dcdfe5`

- **Typography & Tonal Contrast:**
  - Ink Primary (Text & Data): `#0f172a`
  - Ink Secondary (Subheads, Metrics, Col Titles): `#334155`
  - Ink Muted (Metadata, Keys, Timestamp): `#64748b`
  - Dark Surface Text Primary: `#f8fafc`
  - Dark Surface Text Muted: `#94a3b8`

- **Functional & Financial Semantics:**
  - Primary Accent (System Selection, Focus Ring, Primary CTA): `#2563eb` (Interactive Hover: `#1d4ed8`)
  - Positive / Bid / Alpha Surplus: `#059669` (Dark surface pill: `#10b981`)
  - Negative / Ask / Drawdown Risk: `#dc2626` (Dark surface pill: `#ef4444`)
  - Warning / Alert / Stale Cache: `#d97706` (Amber 600)
  - Workspace Group Links: Group A (`#eab308`), Group B (`#06b6d4`), Group C (`#a855f7`), Group D (`#f97316`)

## Typography

Typography prioritizes extreme mechanical legibility and tabular density. Proportional text utilizes `Inter` with standard tracking adjustments for immediate recognition in constrained widths. Data-heavy elements, run parameters, code matrices, and numerical listings explicitly employ `JetBrains Mono` with OpenType tabular figures (`tnum`) activated by default.

### Typographic Implementation Rules
- **Tabular Figures Everywhere:** All financial quantities, portfolio deltas, order volumes, timestamps, and p-values must enforce monospace alignment. Proportional numbers are forbidden in data grids.
- **Letter Spacing & Casing:** `label-dense` and `label-mono-tag` are routinely configured with `text-transform: uppercase` to provide structural anchor points for column headers, status badges, and tab identifiers.
- **Hierarchy through Weight & Color:** Do not escalate font sizes to demonstrate importance. Size changes introduce jagged alignment in grid ribbons. Establish hierarchy through font weight (`500` vs `600`) and value shifts between `#0f172a`, `#64748b`, and specific semantic accent tones.

## Layout & Spacing

Layout geometry follows a zero-margin, tiled-dock viewport paradigm. The viewport is treated as a solid workbench subdivided by 1px hairline splitters (`gutter: 1px`). Margins are set to `0px` against the application frame to ensure every display unit is consumable by research workflows.

### Grid & Paneling Architecture
- **Panel-Based Tiling Grid:** No arbitrary loose margins or float-centered containers. Panels snap into vertical and horizontal splits. Toolbars, inspector sidebars, and matrix views span rigid 100% boundary boxes.
- **Toolbar & Row Heights:**
  - Global Top Header: `36px` fixed height.
  - Sub-Toolbars & Workstation Action Strips: `28px` fixed height.
  - Primary Tab Strips: `26px` height.
  - Data Grid Rows: `22px` (ultra-dense compact) or `26px` (standard quantitative inspection).
  - Inspector Field Rows: `24px` height.
- **Internal Padding Rhythm:**
  - Standard container padding: `space-sm` (6px) or `space-md` (8px).
  - Cell padding: 4px horizontal, 2px vertical.
  - Icon-to-label gaps: `space-xs` (4px).

## Elevation & Depth

Visual separation in this design system is driven by structural hairline borders, contrasting panel values, and surface tone shifts rather than drop shadows. Shadows in dense analytic workstations create optical smudge and reduce usable screen real estate.

### Depth Hierarchy

1. **Base Foundation (Level 0 - Structural Framework):**
   - Background: `#13161c` (Shell Rail), `#1a1e26` (Dock Header), or `#f4f5f7` (Workspace Base).
   - Border: Solid 1px `#2d3546` (dark frames) or `#dcdfe5` (light working panels).
   - Shadow: None.

2. **Inner Working Panels & Cells (Level 1 - Data Cells & Canvases):**
   - Background: `#ffffff`.
   - Separation: 1px solid horizontal and vertical grid dividers (`#eef0f3` or `#dcdfe5`).
   - Shadow: None.

3. **Active/Hover Elements (Level 2 - Row Selection & State):**
   - Hover Background: `#f8fafc` (light) or `#232936` (dark).
   - Active Selected Row: Inset left indicator border `2px solid #2563eb` with background `#eff6ff`.

4. **Floating Overlays & Context Menus (Level 3 - Ephemeral Overlays):**
   - Used exclusively for right-click context menus, quick search bars, formula auto-completes, and date-range pickers.
   - Background: `#1a1e26` (dark shell mode) or `#ffffff` (light sheet mode).
   - Border: 1px solid `#2d3546` or `#cbd5e1`.
   - Elevation Shadow: `0 4px 12px -2px rgba(15, 23, 42, 0.16), 0 2px 4px -1px rgba(15, 23, 42, 0.08)`. Rigid, sharp, restrained.

## Shapes

The workspace shape language is strictly **Sharp (0)** to minimal micro-chamfer (`2px` maximum on isolated interactive elements). Rounded corners consume coordinate precision and introduce visual distortion when tables, tabs, and charts are nested edge-to-edge.

### Shape Application Guidelines
- **Windows, Docks, & Panels:** Exactly `0px` radius. Every edge aligns flush with adjacent border lines.
- **Tabs, Buttons, & Text Fields:** `0px` to `2px` absolute radius. Interactive buttons in dark toolbars maintain square corners with 1px border contrast.
- **Link-Group Badges & Status Indicators:** Status indicators are rendered as solid 6px squares or sharp micro-rectangles, with link-group indicators taking the form of discrete `10px x 10px` grouped badges with sharp geometry.

## Components

### 1. Compact Toolbars & Workstation Strips
- **Dimensions:** Strict `28px` height. Flush layout with 1px bottom border (`#dcdfe5` light, `#2d3546` dark).
- **Contents:** Embedded link-group badge, model state dropdown, frequency selector pills, backtest trigger button, and latency telemetry monitor.
- **Styling:** Micro horizontal layout (`gap: 4px`), with integrated divider keys (vertical 12px lines `#cbd5e1`).

### 2. Workspace Link-Group Badges
- **Purpose:** Synchronize ticker symbol/dataset across disconnected panels (matching Bloomberg Launchpad link channels).
- **Visuals:** Compact `16px x 16px` squared badge displaying letter codes (`A`, `B`, `C`, `D`).
- **Color Coding:** High-saturation background matching group token (e.g. Group A: `#eab308`, Group B: `#06b6d4`) with black or white centered JetBrains Mono `9px` bold text.

### 3. Tab Strips & View Switchers
- **Height:** `24px` to `26px`.
- **States:**
  - *Inactive Tab:* Background transparent, text `#64748b`, 1px right border `#dcdfe5`.
  - *Active Tab:* Background `#ffffff`, text `#0f172a` (semi-bold), topped with a 2px horizontal accent line in `#2563eb`.
  - *Dirty/Modified Indicator:* 4px amber circle (`#d97706`) adjacent to tab label.

### 4. Buttons & Action Triggers
- **Primary:** Background `#2563eb`, border 1px solid `#1d4ed8`, text `#ffffff`, height `22px` or `26px`. Hover: `#1d4ed8`. Active: `#1e40af`.
- **Secondary / Ghost Toolbar Button:** Background `#ffffff`, border 1px solid `#dcdfe5`, text `#334155`. Hover: background `#f1f5f9`, border `#cbd5e1`.
- **Compact Icon Button:** `22px x 22px` square, no background, 1px border on hover.

### 5. Dense Data Tables & Quantitative Grids
- **Header:** Height `24px`, background `#f8fafc`, text `#64748b` (JetBrains Mono or Inter uppercase 10px), bottom border 1px solid `#cbd5e1`. Right-aligned for numerical data.
- **Rows:** Height `22px` (compact) or `26px` (regular). Border-bottom 1px solid `#f1f5f9`. Alternate striping (`zebra`) is optional; preferred default is solid white with `#f8fafc` row hover.
- **Numeric Alignment:** Always right-aligned, monospace figures (`JetBrains Mono`). Positive values include leading muted plus (`+0.84%`) in `#059669`. Negative values display in `#dc2626`.

### 6. Inputs & Code Inline Fields
- **Height:** `22px` (inline grid edit) or `26px` (toolbar parameter field).
- **Styling:** Background `#ffffff`, border 1px solid `#cbd5e1`, font `JetBrains Mono 11px`. Focus state triggers sharp 1px outline in `#2563eb` with no ambient blur.

### 7. Micro Scrollbars
- **Dimensions:** `5px` width and height.
- **Track:** Background transparent or matching adjacent chrome `#1a1e26` / `#f4f5f7`.
- **Thumb:** Flat `#94a3b8` (light) or `#334155` (dark), `0px` border-radius. Transitions to `#64748b` on active drag.