---
name: meal-plan-analyzer-design
description: Use this skill to generate well-branded interfaces and assets for the RSOS Meal Plan Analyzer — a professional web application for nutritionists to analyze patient meal reports and create example meal plans. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping.
user-invocable: true
---

Read the design system README at `docs/design-system/README.md`, and explore the other files in `docs/design-system/`.

Key files:
- `docs/design-system/README.md` — full design system documentation (colors, type, spacing, components, iconography)
- `docs/design-system/colors_and_type.css` — CSS custom properties and typography base styles; import before component styles
- `docs/design-system/assets/logo.png` — carrot logo (PNG)
- `docs/design-system/preview/` — HTML previews for colors, typography, spacing, buttons, inputs, cards, badges, nav, modals
- `docs/design-system/screenshots/` — reference screenshots (plan-list, plan-detail, screens, ui-kit)
- `docs/design-system/ui_kits/app/index.html` — full click-thru app prototype (5 screens: login, plan list, plan detail, food database, threshold preset editor)

If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and create static HTML files for the user to view. If working on production code, read the design rules here to become an expert in designing with this brand — use `colors_and_type.css` as the token source.

If the user invokes this skill without any other guidance, ask them what they want to build or design, ask some questions, and act as an expert designer who outputs HTML artifacts _or_ production code, depending on the need.
