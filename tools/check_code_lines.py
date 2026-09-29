"""Fail when maintained source files exceed 200 physical lines."""

from pathlib import Path
import os


ROOT = Path(__file__).resolve().parents[1]
MAX_LINES = 200
SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".css", ".html", ".sh", ".zsh", ".sql"}
EXCLUDED_DIRS = {
    ".git", ".venv", ".zcode", "node_modules", "vendor", "smartedu_data",
    "uploads", "acceptance-runs", "deliverables", ".runtime", "dist",
    "build", "__pycache__", "coverage", "htmlcov",
}
# The SQL draft is a frozen v1.3 design reference; the HTML preview is generated.
EXCLUDED_FILES = {"database/001_schema_draft.sql", "tools/crawler/smartedu_preview.html"}


def maintained_files():
    for directory, folders, files in os.walk(ROOT):
        folders[:] = [name for name in folders if name not in EXCLUDED_DIRS]
        for name in files:
            path = Path(directory, name)
            relative = path.relative_to(ROOT).as_posix()
            if path.suffix in SUFFIXES and relative not in EXCLUDED_FILES and not path.is_symlink():
                yield path, relative


def main() -> int:
    oversized = []
    for path, relative in maintained_files():
        with path.open(encoding="utf-8", errors="replace") as source:
            lines = sum(1 for _ in source)
        if lines > MAX_LINES:
            oversized.append((relative, lines))
    for relative, lines in sorted(oversized):
        print(f"{relative}: {lines} lines (limit {MAX_LINES})")
    print(f"{len(oversized)} maintained files exceed {MAX_LINES} lines")
    return 1 if oversized else 0


if __name__ == "__main__":
    raise SystemExit(main())
