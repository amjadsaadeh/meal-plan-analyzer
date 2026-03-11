"""
build_scss – Compile all SCSS entry-point files to CSS.

Run this before collectstatic in CI/CD or Docker deployments so that
the CssFinder can locate the compiled CSS during collectstatic.
During development the {% sass_src %} template tag handles on-demand
compilation automatically.

Usage:
    uv run python manage.py build_scss
    uv run python manage.py build_scss --output-style expanded
    uv run python manage.py collectstatic   (run build_scss first)
"""

import os
from pathlib import Path

import sass
from django.conf import settings
from django.core.management.base import BaseCommand


def _scss_root() -> Path:
    """Return the configured SASS_PROCESSOR_ROOT or STATIC_ROOT as fallback."""
    return Path(getattr(settings, "SASS_PROCESSOR_ROOT", settings.STATIC_ROOT))


def _find_entry_points(static_dirs) -> list[tuple[Path, Path]]:
    """
    Find all non-partial SCSS files (entry points) across the app's
    static directories and return (scss_path, css_output_path) pairs.

    Entry points are files whose name does NOT start with '_'.
    Partials (prefixed with '_') are imported by entry points.
    """
    pairs = []
    for static_dir in static_dirs:
        static_dir = Path(static_dir)
        for scss_file in static_dir.rglob("*.scss"):
            if scss_file.name.startswith("_"):
                continue
            # Mirror the directory structure under SASS_PROCESSOR_ROOT
            rel = scss_file.relative_to(static_dir)
            css_path = _scss_root() / rel.with_suffix(".css")
            pairs.append((scss_file, css_path))
    return pairs


def _collect_static_dirs() -> list[Path]:
    """Return all directories that staticfiles finders would scan."""
    dirs = list(getattr(settings, "STATICFILES_DIRS", []))

    # Add each installed app's static/ folder
    from django.apps import apps

    for app_config in apps.get_app_configs():
        candidate = Path(app_config.path) / "static"
        if candidate.is_dir():
            dirs.append(candidate)
    return [Path(d) for d in dirs]


class Command(BaseCommand):
    help = (
        "Compile all SCSS entry-point files to CSS using libsass. "
        "This is called automatically before collectstatic when "
        "sass_processor.finders.CssFinder is listed in STATICFILES_FINDERS."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-style",
            default="compressed",
            choices=["nested", "expanded", "compact", "compressed"],
            help="Output style for the compiled CSS (default: compressed).",
        )
        parser.add_argument(
            "--watch",
            action="store_true",
            help="Not implemented; included for API compatibility.",
        )

    def handle(self, *args, **options):
        output_style = options["output_style"]
        static_dirs = _collect_static_dirs()
        pairs = _find_entry_points(static_dirs)

        if not pairs:
            self.stdout.write(self.style.WARNING("No SCSS entry-point files found."))
            return

        errors = 0
        for scss_path, css_path in sorted(pairs):
            css_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                css = sass.compile(
                    filename=str(scss_path),
                    output_style=output_style,
                    source_map_filename=None,
                )
                css_path.write_text(css, encoding="utf-8")
                self.stdout.write(
                    self.style.SUCCESS(f"  compiled: {scss_path} → {css_path}")
                )
            except sass.CompileError as exc:
                self.stderr.write(self.style.ERROR(f"  error: {scss_path}\n    {exc}"))
                errors += 1

        if errors:
            self.stderr.write(
                self.style.ERROR(f"\n{errors} file(s) failed to compile.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSuccessfully compiled {len(pairs)} SCSS file(s)."
                )
            )
