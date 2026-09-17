"""Hermes Skills Loader.

Parses skills/*/SKILL.md to extract metadata and system prompts for each agent role.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any
import yaml

ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT / "skills"

@dataclass(frozen=True)
class HermesSkill:
    name: str
    description: str
    system_prompt: str
    file_path: Path
    raw_content: str

def parse_skill_markdown(path: Path) -> HermesSkill:
    """Parse a SKILL.md file with YAML frontmatter."""
    if not path.is_file():
        raise FileNotFoundError(f"Skill file not found: {path}")

    text = path.read_text(encoding="utf-8")
    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    
    if not frontmatter_match:
        # Fallback if no frontmatter
        name = path.parent.name
        description = f"Hermes skill for {name}"
        system_prompt = text.strip()
    else:
        meta_yaml, body = frontmatter_match.groups()
        meta = yaml.safe_load(meta_yaml) or {}
        name = meta.get("name", path.parent.name)
        description = meta.get("description", "")
        system_prompt = body.strip()

    return HermesSkill(
        name=name,
        description=description,
        system_prompt=system_prompt,
        file_path=path,
        raw_content=text,
    )

def load_skill(skill_name: str) -> HermesSkill:
    """Load a skill by directory name under skills/."""
    target = SKILLS_DIR / skill_name / "SKILL.md"
    if not target.exists():
        raise FileNotFoundError(f"Unknown Hermes skill '{skill_name}' at {target}")
    return parse_skill_markdown(target)

def list_available_skills() -> list[str]:
    """List all available skills in the skills/ directory."""
    if not SKILLS_DIR.exists():
        return []
    return sorted(
        d.name for d in SKILLS_DIR.iterdir()
        if d.is_dir() and (d / "SKILL.md").is_file()
    )
