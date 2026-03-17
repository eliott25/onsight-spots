#!/usr/bin/env python3
"""Validate spot YAML files against the JSON Schema."""

import json
import sys
from pathlib import Path

import jsonschema
import yaml

SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "spot.schema.json"
SPOTS_DIR = Path(__file__).parent.parent / "spots"


def load_schema() -> dict:
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def validate_file(filepath: Path, schema: dict) -> list[str]:
    """Validate a single YAML file. Returns list of error messages."""
    errors = []

    # Check filename convention: lowercase, hyphens, .yaml
    stem = filepath.stem
    if stem != stem.lower() or " " in stem or "_" in stem:
        errors.append(
            f"{filepath.name}: filename must be lowercase with hyphens "
            f"(e.g., 'gorges-du-verdon.yaml')"
        )

    try:
        with open(filepath) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        errors.append(f"{filepath.name}: invalid YAML — {e}")
        return errors

    if data is None:
        errors.append(f"{filepath.name}: file is empty")
        return errors

    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        errors.append(f"{filepath.name}: {e.message}")

    return errors


def get_files_to_validate(changed_files: list[str] | None = None) -> list[Path]:
    """Get YAML files to validate — either from changed files list or all spots."""
    if changed_files:
        return [
            Path(f) for f in changed_files
            if f.startswith("spots/") and f.endswith(".yaml") and Path(f).exists()
        ]
    return sorted(SPOTS_DIR.glob("*.yaml"))


def main():
    schema = load_schema()

    # If file paths are passed as arguments, validate only those
    changed = sys.argv[1:] if len(sys.argv) > 1 else None
    files = get_files_to_validate(changed)

    if not files:
        print("No spot files to validate.")
        return

    all_errors = []
    for filepath in files:
        errors = validate_file(filepath, schema)
        all_errors.extend(errors)

    if all_errors:
        print(f"Validation failed with {len(all_errors)} error(s):\n")
        for err in all_errors:
            print(f"  ✗ {err}")
        sys.exit(1)
    else:
        print(f"All {len(files)} spot file(s) passed validation.")


if __name__ == "__main__":
    main()
