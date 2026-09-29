"""Local, deterministic diagram assets for the development workbench."""
from __future__ import annotations

import copy
import hashlib
import os
import re
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

ASSET_DIR = Path(__file__).resolve().parents[1] / ".runtime" / "assets"
ASSET_ID = re.compile(r"[0-9a-f]{64}\Z")


def render_counting_rods(spec: dict) -> tuple[bytes, str]:
    """Render only the vertical counting-rod forms 1–5, with exact labels."""
    if not isinstance(spec, dict) or set(spec) != {"kind", "values"} or spec["kind"] != "counting_rods":
        raise ValueError("Unsupported diagram specification")
    values = spec["values"]
    if (not isinstance(values, list) or not 1 <= len(values) <= 9
            or any(type(value) is not int or not 1 <= value <= 5 for value in values)):
        raise ValueError("Counting rods support only 1–5, up to nine groups")
    width = 28 + len(values) * 70
    groups = []
    for index, value in enumerate(values):
        center = 49 + index * 70
        rods = "".join(
            f'<line x1="{center + (rod - (value - 1) / 2) * 8:g}" y1="20" '
            f'x2="{center + (rod - (value - 1) / 2) * 8:g}" y2="57"/>'
            for rod in range(value)
        )
        groups.append(f'<g fill="none" stroke="#17212b" stroke-width="3" '
                      f'stroke-linecap="round">{rods}</g>'
                      f'<text x="{center}" y="82" text-anchor="middle" '
                      f'fill="#17212b" font-size="16">{value}</text>')
    alt = "算筹纵式记数：" + "；".join(f"{value} 对应 {value} 根竖棒" for value in values)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="96" '
           f'viewBox="0 0 {width} 96" role="img"><title>{escape(alt)}</title>'
           + "".join(groups) + '</svg>')
    return svg.encode("utf-8"), alt


def save_diagram(spec: dict) -> dict[str, str]:
    svg, alt = render_counting_rods(spec)
    asset_id = hashlib.sha256(svg).hexdigest()
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    path = ASSET_DIR / f"{asset_id}.svg"
    # Write once and atomically; a crash cannot leave a partial published SVG.
    if not path.exists():
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(dir=ASSET_DIR, suffix=".tmp", delete=False) as file:
                temporary = Path(file.name)
                file.write(svg)
            try:
                os.link(temporary, path)
            except FileExistsError:
                pass
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    if path.read_bytes() != svg:
        raise ValueError("Diagram asset hash collision or corruption")
    return {"type": "asset", "asset_id": asset_id, "alt": alt}


def load_diagram(asset_id: str) -> bytes | None:
    if not isinstance(asset_id, str) or not ASSET_ID.fullmatch(asset_id):
        return None
    path = ASSET_DIR / f"{asset_id}.svg"
    try:
        data = path.read_bytes()
    except OSError:
        return None
    return data if hashlib.sha256(data).hexdigest() == asset_id else None


def diagram_asset_matches(asset_id: str, alt: str) -> bool:
    """Accept only bytes reproducible by the trusted renderer, including alt."""
    if not isinstance(alt, str):
        return False
    data = load_diagram(asset_id)
    if data is None:
        return False
    prefix = "算筹纵式记数："
    if not alt.startswith(prefix):
        return False
    groups = alt[len(prefix):].split("；")
    values = []
    for group in groups:
        match = re.fullmatch(r"([1-5]) 对应 \1 根竖棒", group)
        if match is None:
            return False
        values.append(int(match.group(1)))
    try:
        expected_svg, expected_alt = render_counting_rods({"kind": "counting_rods", "values": values})
    except ValueError:
        return False
    return data == expected_svg and alt == expected_alt


def materialize_candidate(candidate: dict) -> dict:
    """Replace author diagram specs with server-issued asset references."""
    result = copy.deepcopy(candidate)

    def blocks(items: list) -> list:
        rendered = []
        for block in items:
            if block["type"] == "diagram":
                rendered.append(save_diagram(block["spec"]))
            elif block["type"] == "asset":
                # The author has no asset minting tool and may not invent IDs.
                raise ValueError("Author supplied an unresolved asset reference")
            else:
                rendered.append(block)
        return rendered

    def question(node: dict) -> None:
        node["prompt"] = blocks(node["prompt"])
        for option in node["options"]:
            option["content"] = blocks(option["content"])
        for child in node["children"]:
            question(child)

    question(result["public"])
    for answer in result["private"]["answers"]:
        if any(block["type"] in {"asset", "diagram"} for block in answer["solution"]):
            raise ValueError("Private solution diagrams are not supported")
    return result
