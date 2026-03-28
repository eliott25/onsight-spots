#!/usr/bin/env python3
"""Insert validated spots into Supabase PostgreSQL (with PostGIS)."""

import os
import sys
from pathlib import Path

import psycopg2
import yaml

SPOTS_DIR = Path(__file__).parent.parent / "spots"
DUPLICATE_THRESHOLD_M = 500


def get_db_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        sys.exit(1)
    return psycopg2.connect(database_url)


def spot_exists_nearby(cursor, name: str, lat: float, lon: float) -> bool:
    """Check if a spot with the same name exists within 500m."""
    cursor.execute(
        """
        SELECT EXISTS(
            SELECT 1 FROM spots
            WHERE LOWER(name) = LOWER(%s)
               OR ST_DWithin(
                    location::geography,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                    %s
                  )
        )
        """,
        (name, lon, lat, DUPLICATE_THRESHOLD_M),
    )
    return cursor.fetchone()[0]


def insert_spot(cursor, spot: dict):
    cursor.execute(
        """
        INSERT INTO spots (name, type, location, climbing_type, photo_url, source)
        VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, 'community')
        """,
        (
            spot["name"],
            spot.get("type", "outdoor"),
            spot["lon"],
            spot["lat"],
            spot["climbing_type"],
            spot.get("photo_url"),
        ),
    )


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
        print("No spot files to insert.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    inserted = 0
    skipped = 0

    try:
        for filepath in files:
            with open(filepath) as f:
                spot = yaml.safe_load(f)

            if not spot or "name" not in spot:
                print(f"  SKIP {filepath.name}: invalid data")
                skipped += 1
                continue

            if spot_exists_nearby(cursor, spot["name"], spot["lat"], spot["lon"]):
                print(f"  SKIP {filepath.name}: '{spot['name']}' already exists nearby")
                skipped += 1
                continue

            insert_spot(cursor, spot)
            print(f"  INSERT {filepath.name}: '{spot['name']}'")
            inserted += 1

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

    print(f"\nDone: {inserted} inserted, {skipped} skipped.")


if __name__ == "__main__":
    main()
