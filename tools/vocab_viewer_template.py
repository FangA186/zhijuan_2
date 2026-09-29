"""Assemble the vocabulary viewer page from small, editable assets."""
from pathlib import Path

_ASSET_DIR = Path(__file__).with_name("vocab_viewer_static")
_CSS = (
    "base.css",
    "sidebar.css",
    "tree.css",
    "workspace.css",
    "smart-actions.css",
    "delete-mode.css",
    "image-area.css",
    "image-cards.css",
    "selection-state.css",
    "smart-badges.css",
    "smart-highlights.css",
    "vocab-banner.css",
    "mode-banner.css",
    "floating-bar.css",
    "lightbox.css",
    "toast.css",
    "trash-modal.css",
)
_JS = (
    "client-globals-tree.js",
    "client-tree-grade.js",
    "client-tree-edition.js",
    "client-navigation.js",
    "client-image-detection.js",
    "client-selection.js",
    "client-delete.js",
    "client-lightbox.js",
    "client-trash-and-keyboard.js",
)


def _read(name: str) -> str:
    return (_ASSET_DIR / name).read_text(encoding="utf-8")


HTML_TEMPLATE = (
    _read("page-head.html")
    + "".join(_read(name) for name in _CSS)
    + _read("page-body.html")
    + _read("page-script-open.html")
    + "".join(_read(name) for name in _JS)
    + _read("page-tail.html")
)
