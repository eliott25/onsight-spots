#!/usr/bin/env python3
"""Update location coordinates for existing spots in the database."""

import os
import sys
from pathlib import Path

import psycopg2
import yaml

SPOTS_DIR = Path(__file__).parent.parent / "spots"


def main():
    changed_files = sys.argv[1:] if len(sys.argv) > 1 else None

    if changed_files:
        files = [
            Path(f) for f in changed_files
            if f.startswith("spots/") and f.endswith(".yaml") and Path(f).exists()
        ]
    else:
        files = sorted(SPOTS_DIR.glob("*.yaml"))

    if not files:
        print("No spot files to update.")
        return

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        sys.exit(1)

    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    updated = 0
    skipped = 0

    try:
        for filepath in files:
            with open(filepath) as f:
                spot = yaml.safe_load(f)

            if not spot or "name" not in spot:
                skipped += 1
                continue

            cursor.execute(
                """
                UPDATE spots
                SET location = ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                    climbing_type = %s,
                    type = %s
                WHERE LOWER(name) = LOWER(%s)
                """,
                (
                    spot["lon"],
                    spot["lat"],
                    spot["climbing_type"],
                    spot.get("type", "outdoor"),
                    spot["name"],
                ),
            )

            if cursor.rowcount > 0:
                print(f"  UPDATE {filepath.name}: '{spot['name']}'")
                updated += 1
            else:
                print(f"  SKIP {filepath.name}: '{spot['name']}' not found in DB")
                skipped += 1

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

    print(f"\nDone: {updated} updated, {skipped} skipped.")


if __name__ == "__main__":
    main()
