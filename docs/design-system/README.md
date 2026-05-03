# Meal Plan Analyzer — Design System

## Product Overview

**RSOS Meal Plan Analyzer** is a professional web application for nutritionists and dietitians to:
- Create and manage patient **meal plans** (by day and meal type: breakfast / lunch / dinner)
- Assign foods from the **BLS (Bundes Lebensmittel Schlüssel)** German national food database
- Track **nutrient totals** against configurable min/max thresholds
- Export plans as **PDFs** for patient reports
- Manage **threshold presets** (reusable nutrient reference templates)
- Browse/edit foods and add custom aliases

**Primary users:** Nutritionists, dietitians, clinical nutrition professionals  
**Stack:** Django 6 + Vue 3 SPA  
**Live:** https://www.saadeh.dev/meal-plan-analyzer/  
**GitHub:** https://github.com/amjadsaadeh/meal-plan-analyzer  

---

## Source Materials

| Source | Location |
|---|---|
| Codebase | GitHub `amjadsaadeh/meal-plan-analyzer` (branch: `main`) |
| SCSS design tokens | `meals/static/meals/scss/_variables.scss` |
| Layout SCSS | `meals/static/meals/scss/_layout.scss` |
| Page SCSS | `mealplan_detail.scss`, `mealplan_list.scss`, `login.scss`, `threshold_preset.scss`, `food_editor.scss` |
| Vue SPA components | `frontend/src/mealplan-detail/components/` |
| Logo | `assets/logo.png` (carrot icon, PNG) |

---

## CONTENT FUNDAMENTALS

### Tone & Voice
- **Clinical and precise** — language is functional, not warm or marketing-y
- **Professional and efficient** — aimed at nutritionists, not end consumers
- **Bilingual** — German (default) and English; default names are German:
  - *Neuer Plan*, *Neuer Tag*, *Frühstück*, *Mittagessen*, *Abendessen*
- **No emoji** — icon-only decorative elements
- **Sentence case** for most labels; **UPPERCASE + letter-spacing** for table column headers
- Units always explicit: `kcal`, `g`, `mg`, `µg`, `kJ`
- Numbers use `font-variant-numeric: tabular-nums` for table alignment
- Nutrient precision: 1 decimal for major nutrients; 2 decimals for trace (B12, Vit D, Omega-3)

### Copy Examples
- *"New Plan"*, *"Add Day"*, *"Export PDF"*, *"Save as Template"*
- *"Subtotal"*, *"Loading..."*, *"Saved"*, *"Error: 500"*
- *"Day 1 - Summary"*, *"Threshold Presets"*, *"Food Database"*
- Ingredient names from BLS are in German (e.g. "Vollmilch 3,5% Fett")

---

## VISUAL FOUNDATIONS

### Colors
Clinical-teal primary on a near-white background — calm, professional, hygienic.

| Token | Value | Usage |
|---|---|---|
| `--primary` | `#6AD9C6` | CTAs, active states, highlights, progress |
| `--primary-hover` | `#4fada0` | Hover on primary, active links |
| `--primary-glow` | `rgba(106,217,198,0.2)` | Focus rings, badge backgrounds, row tint |
| `--bg` | `#f8fafc` | Page background (very light blue-gray) |
| `--card-bg` | `rgba(255,255,255,0.9)` | Cards/panels (frosted glass effect) |
| `--text-main` | `#2c3338` | Primary text |
| `--text-dim` | `#666E73` | Secondary text, labels, metadata |
| `--glass-border` | `rgba(0,0,0,0.08)` | Card borders, dividers |
| `--shadow` | `0 4px 15px rgba(0,0,0,0.03)` | Subtle card elevation |
| `--row-hover` | `rgba(106,217,198,0.05)` | Table row hover |
| `--success` | `#41A66D` | Saved state, in-range nutrients |
| `--warning` | `#DEACA4` | Pending/warning (muted rose) |
| `--danger` | `#A64143` | Errors, delete, out-of-range nutrients |

**Gradient text:** `linear-gradient(135deg, #4180A6 0%, #666E73 100%)` clipped to text — used on all h1 titles.

### Typography
System font stack (no custom font). Design relies on weight and size hierarchy.

| Role | Size | Weight | Notes |
|---|---|---|---|
| Page title h1 | 3rem / 2.5rem | 400 | Gradient clip text |
| Day title h2 | 1.8rem | 400 | Underlined with `--primary` |
| Meal header h3 | 1.4rem | 400 | Dimmed text color |
| Body / table | 1rem | 400 | `--text-main` |
| Labels / meta | 0.9rem | 400 | `--text-dim` |
| Table headers | 0.82–0.9rem | 600 | UPPERCASE, letter-spacing 0.05em |
| Micro / badges | 0.75–0.8rem | 400–600 | Nutrient badges, BLS codes |

### Spacing & Layout
- Top bar height: `60px`, sticky, `backdrop-filter: blur(12px)`
- Container max-width: `1200px`, padding `2rem 2.5%`
- Card border-radius: `20px` (main cards), `12px` (inputs/buttons), `8–10px` (small elements)
- Gap rhythm: `0.5rem`, `0.8rem`, `1rem`, `1.5rem`, `2rem`, `2.5rem`
- Breakpoints: `600px` (sm), `768px` (md), `1280px` (lg)

### Cards & Surfaces
- Cards: `background: rgba(255,255,255,0.9)`, `backdrop-filter: blur(12px)`, `border: 1px solid rgba(0,0,0,0.08)`, `border-radius: 20px`, `box-shadow: 0 10px 30px rgba(0,0,0,0.05)`
- Glassmorphism feel — frosted white on light gray background
- No strong drop shadows; very subtle `0.03` opacity blacks

### Buttons
- **Primary:** `background: #6AD9C6`, white text, `border-radius: 12px`, `box-shadow: 0 4px 10px var(--primary-glow)`, hover: `translateY(-2px)` lift
- **Secondary:** `background: rgba(primary, 0.05)`, primary color text/border, hover fills to solid primary
- **Danger:** transparent with danger color border, hover fills to danger
- **Icon buttons:** transparent, rounded, hover: tint background + color shift
- Transitions: `all 0.2–0.3s cubic-bezier(0.4,0,0.2,1)` (smooth spring-ish)

### Animations & Interactions
- Easing: `cubic-bezier(0.4, 0, 0.2, 1)` (material decelerate) for most transitions
- Modal entry: `cubic-bezier(0.16, 1, 0.3, 1)` (spring) — slides up from `translateY(20px)`
- Sticky bar: slides in with `transform: translateY(-200%) → 0` on scroll
- Button hover: `translateY(-2px)` lift on primary CTA
- Spinner: `spin 0.8s linear infinite` for loading states
- No heavy page transitions; micro-interactions only

### Icons
Inline SVG only — stroke-based, 2px stroke-width, `stroke-linecap: round`, `stroke-linejoin: round`. Lucide-style icons. Sizes: 16px, 18px, 20px.  
See **ICONOGRAPHY** section below.

---

## ICONOGRAPHY

Icons are **inline SVG strokes** throughout — no icon font, no external icon library loaded at runtime. The style matches **Lucide Icons** (stroke, rounded caps/joins, 24×24 viewBox, 2px stroke).

### Icons Used in the App

| Context | Icon | Description |
|---|---|---|
| Back navigation | Arrow left + line | `<line x1="19" y1="12" x2="5" y2="12">` + polyline |
| Edit field | Pencil/square | `M11 4H4...` + `M18.5 2.5a2.121...` |
| Delete / trash | Trash 2 | Polyline + path with line marks |
| Add / create | Plus | Two crossing lines |
| Breakfast | Custom sun/egg | Circle + dot pattern |
| Lunch | Clock circle | Circle + `M12 6v6l4 2` |
| Dinner | Moon | Custom moon path |
| Save / preset | Floppy disk | Path + polylines |
| Export PDF | Document | File-text variant |
| Columns | Columns | Vertical bar pairs |
| Sync saved | Check circle | `var(--success)` color |
| Sync pending | Dot / dots | `var(--warning)` animated |
| Collapse chevron | Chevron down | Rotates when expanded |

**CDN alternative:** Lucide CDN (`https://unpkg.com/lucide@latest`) can be used for design mocks when inline SVG is not convenient.

---

## Files in This Design System

| File | Purpose |
|---|---|
| `README.md` | This file — full design system documentation |
| `colors_and_type.css` | CSS custom properties and typography base styles |
| `assets/logo.png` | Carrot logo (PNG) |
| `preview/colors-brand.html` | Brand color palette card |
| `preview/colors-semantic.html` | Semantic / status color card |
| `preview/type-scale.html` | Typography scale specimen |
| `preview/spacing-tokens.html` | Spacing, radius, shadow tokens |
| `preview/components-buttons.html` | Button variants |
| `preview/components-inputs.html` | Form inputs and fields |
| `preview/components-cards.html` | Card and table-card patterns |
| `preview/components-badges.html` | Badges, status indicators, energy badge |
| `preview/components-nav.html` | Top bar and nav link states |
| `preview/components-modals.html` | Modal and overlay pattern |
| `ui_kits/app/index.html` | Full click-thru app prototype (5 screens) |
| `SKILL.md` | Agent skill manifest |

---

## UI Kit Surfaces

### Web App (`ui_kits/app/`)
Covers the core screens of the Django + Vue SPA:
1. **Login** — centered card, gradient title, form fields
2. **Meal Plan List** — table with search, pagination, create button
3. **Meal Plan Detail** — day sections, meal tables, side panel with thresholds
4. **Food Database** — searchable food table with BLS codes
5. **Threshold Preset Editor** — nutrient min/max form, two-column grid
