#!/usr/bin/env python3
"""Rename a spot in the database. Usage: rename_spot.py 'Old Name' 'New Name'"""

import os
import sys

import psycopg2


def main():
    if len(sys.argv) != 3:
        print("Usage: rename_spot.py 'Old Name' 'New Name'")
        sys.exit(1)

    old_name, new_name = sys.argv[1], sys.argv[2]

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        sys.exit(1)

    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE spots SET name = %s WHERE LOWER(name) = LOWER(%s)",
            (new_name, old_name),
        )
        if cursor.rowcount == 0:
            print(f"No spot found with name '{old_name}'")
        else:
            print(f"Renamed '{old_name}' to '{new_name}' ({cursor.rowcount} row(s))")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
