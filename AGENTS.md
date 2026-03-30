# AGENTS.md

## Project overview

**onsight-spots** is a community-contributed database of climbing spots for [OnSight](https://onsight.ovh), a climbing partner finder app. Spots are defined as individual YAML files, validated via CI, and inserted into a Supabase PostgreSQL database (with PostGIS) on merge to `main`.

## Tech stack

- Python 3.12 (no virtual env manager — dependencies installed via pip)
- PyYAML for spot file parsing
- jsonschema for YAML validation against `schema/spot.schema.json`
- psycopg2 for PostgreSQL/PostGIS database operations
- GitHub Actions for CI/CD

## Commands

```bash
# Validate all spot files against the JSON schema
python scripts/validate.py

# Validate specific files
python scripts/validate.py spots/ceuse.yaml spots/buoux.yaml

# Check for duplicate spots (within 500m)
python scripts/check_duplicates.py

# Insert new spots into the database (requires DATABASE_URL)
DATABASE_URL=... python scripts/insert.py

# Update coordinates/type for existing spots
DATABASE_URL=... python scripts/update_locations.py

# Rename a spot in the database
DATABASE_URL=... python scripts/rename_spot.py 'Old Name' 'New Name'
```

## Project structure

```
spots/                     # One YAML file per climbing spot
schema/
  spot.schema.json         # JSON Schema for spot validation
scripts/
  validate.py              # Validate YAML files against schema + filename conventions
  check_duplicates.py      # Detect spots within 500m of each other (Haversine)
  insert.py                # Insert new spots into Supabase (skips existing/nearby)
  update_locations.py      # Update coordinates and type for existing DB spots
  rename_spot.py           # Rename a spot in the database
SPOT_TEMPLATE.yaml         # Template for new spot contributions
.github/workflows/
  validate-pr.yml          # PR CI: validate + duplicate check on changed files
  insert-on-merge.yml      # Merge CI: insert new spots, update modified spots
```

## Spot file format

Each spot is a YAML file in `spots/` named with lowercase hyphens (e.g., `gorges-du-verdon.yaml`):

```yaml
name: Gorges du Verdon       # Required, max 100 chars
type: outdoor                # Optional: outdoor (default) or indoor
lat: 43.76475                # Required: WGS84 latitude
lon: 6.35979                 # Required: WGS84 longitude
climbing_type: sport,trad    # Required: comma-separated (sport, boulder, trad, multi-pitch)
# photo_url: https://...     # Optional
```

## CI/CD pipeline

- **On PR** (`validate-pr.yml`): validates changed spot files against schema, checks for duplicates within 500m
- **On merge to main** (`insert-on-merge.yml`): inserts new spots into Supabase, updates modified spots' coordinates/type
- **Manual dispatch**: backfills all spots (insert + update)

## Code conventions

- Filenames must be lowercase with hyphens, `.yaml` extension
- Coordinates use WGS84 (EPSG:4326); PostGIS stores them as `ST_MakePoint(lon, lat)`
- Duplicate threshold is 500m (Haversine in `check_duplicates.py`, `ST_DWithin` in `insert.py`)
- Scripts accept optional file paths as CLI args to operate on a subset of spots
- Inserted spots get `source = 'community'` in the database

## Environment

- `DATABASE_URL` — PostgreSQL connection string for Supabase (required for insert/update/rename scripts, set as GitHub secret for CI)

## Related repositories

- **onsight** — The main Next.js web app that displays spots on a map
- **onsight-sketch** — Generates ballpoint pen sketches of spots from photos via Gemini, uploads to Supabase
