#!/usr/bin/env python3
"""Check for duplicate spots using Haversine distance (500m threshold)."""

import math
import sys
from pathlib import Path

import yaml

SPOTS_DIR = Path(__file__).parent.parent / "spots"
DUPLICATE_THRESHOLD_M = 500


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in meters between two WGS84 points."""
    R = 6_371_000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_spot(filepath: Path) -> dict | None:
    try:
        with open(filepath) as f:
            data = yaml.safe_load(f)
        if data and "lat" in data and "lon" in data and "name" in data:
            return data
    except (yaml.YAMLError, OSError):
        pass
    return None


def load_all_spots() -> list[tuple[Path, dict]]:
    spots = []
    for filepath in sorted(SPOTS_DIR.glob("*.yaml")):
        spot = load_spot(filepath)
        if spot:
            spots.append((filepath, spot))
    return spots


def main():
    # Files to check (passed as args, or all)
    changed_files = sys.argv[1:] if len(sys.argv) > 1 else None

    all_spots = load_all_spots()

    if changed_files:
        files_to_check = {
            Path(f).resolve()
            for f in changed_files
            if f.startswith("spots/") and f.endswith(".yaml")
        }
    else:
        files_to_check = {fp.resolve() for fp, _ in all_spots}

    warnings = []

    for i, (path_a, spot_a) in enumerate(all_spots):
        if path_a.resolve() not in files_to_check:
            continue

        for j, (path_b, spot_b) in enumerate(all_spots):
            if i >= j:
                continue

            dist = haversine(spot_a["lat"], spot_a["lon"], spot_b["lat"], spot_b["lon"])
            if dist < DUPLICATE_THRESHOLD_M:
                warnings.append(
                    f"⚠ {path_a.name} ({spot_a['name']}) is {dist:.0f}m from "
                    f"{path_b.name} ({spot_b['name']})"
                )

    if warnings:
        print(f"Found {len(warnings)} potential duplicate(s):\n")
        for w in warnings:
            print(f"  {w}")
        # Exit with 1 to fail CI — reviewer can override if it's intentional
        sys.exit(1)
    else:
        print("No duplicate spots detected.")


if __name__ == "__main__":
    main()
