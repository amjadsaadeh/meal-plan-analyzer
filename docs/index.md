---
title: Home
layout: home
nav_order: 1
---

# Meal Plan Analyzer

A Django web application for meal planning and nutritional analysis, powered by the [Bundeslebensmittelschlüssel (BLS)](https://www.blsdb.de/) — the German National Food Database.

## Features

- **Food Database** — Nutritional values per 100g including energy (kcal/kJ), macronutrients (protein, fat, carbs, fiber, sugar, n-3), vitamins (A, B12, C, D), and minerals (calcium, iron, magnesium, zinc)
- **Meal Planning** — Create multi-day meal plans with breakfast, lunch, and dinner
- **Nutritional Analysis** — Track total nutrient intake per day and per meal plan
- **Threshold Presets** — Define minimum/maximum nutrient targets and get visual feedback
- **Smart Search** — German umlaut-aware food search with alias support
- **PDF Export** — Generate printable meal plans with optional custom logo
- **REST API** — Full CRUD operations via Django REST Framework

## Quick Start

```bash
cp .env.example .env
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 6.0 + Django REST Framework |
| Database | PostgreSQL (SQLite for dev) |
| Frontend | Django templates + Vue 3 + SCSS |
| PDF | WeasyPrint |
| Testing | pytest + Playwright |
| Package manager | uv (Python), pnpm (JS) |
