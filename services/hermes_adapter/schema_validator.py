"""Schema validator for Hermes generated candidates and public projections.

Uses jsonschema to validate outputs against contracts/*.schema.json.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import jsonschema

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = ROOT / "contracts"

class SchemaValidationError(ValueError):
    """Raised when generated output violates schema invariants."""

def load_schema(schema_filename: str) -> dict[str, Any]:
    schema_path = CONTRACTS_DIR / schema_filename
    if not schema_path.is_file():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    return json.loads(schema_path.read_text(encoding="utf-8"))

def validate_candidate(data: dict[str, Any]) -> None:
    """Validate full candidate structure (public + private answers)."""
    schema = load_schema("candidate.schema.json")
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as err:
        error = SchemaValidationError(f"GeneratedCandidate invalid: {err.validator} at path {list(err.path)}")
        error.diagnostic_code = f"{err.validator}:" + "/".join(map(str, err.absolute_schema_path))
        raise error from err

def validate_public_question(data: dict[str, Any]) -> None:
    """Validate public question projection (must not contain private answers)."""
    schema = load_schema("public-question.schema.json")
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as err:
        raise SchemaValidationError(f"PublicQuestion invalid: {err.validator} at path {list(err.path)}") from err
