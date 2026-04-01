# AGENTS.md

## Project overview

**onsight-spots** is the community-contributed climbing spot database for [OnSight](https://onsight.ovh) — a climbing partner finder app. Contributors add spots via YAML files and pull requests; CI validates them and merges insert them into the Supabase PostgreSQL database (with PostGIS).

This repo is part of a three-repo system:
- **onsight** — Next.js web app (the main product)
- **onsight-spots** — this repo: spot data + insertion scripts
- **onsight-sketch** — generates ballpoint pen sketches of spots via Gemini API

## Tech stack

- Python 3.12
- PyYAML, jsonschema, psycopg2-binary
- Supabase PostgreSQL with PostGIS for geospatial queries
- GitHub Actions for CI/CD

## Project structure

```
spots/                     # One YAML file per climbing spot (the core data)
schema/spot.schema.json    # JSON Schema for spot validation
scripts/
  validate.py              # Validate spot YAML files against schema
  check_duplicates.py      # Flag spots within 500m of each other (Haversine)
  insert.py                # Insert new spots into Supabase (with duplicate guard)
  update_locations.py      # Update coordinates/type for existing spots
  rename_spot.py           # Rename a spot in the DB: rename_spot.py 'Old' 'New'
SPOT_TEMPLATE.yaml         # Template for contributors
.github/workflows/
  validate-pr.yml          # PR CI: validate + duplicate check on changed files
  insert-on-merge.yml      # Merge CI: insert new spots, update modified ones
```

## Spot file format

Each file in `spots/` is a YAML file named `lowercase-with-hyphens.yaml`:

```yaml
name: Gorges du Verdon
type: outdoor              # outdoor | indoor (defaults to outdoor)
lat: 43.76475              # WGS84 latitude
lon: 6.35979               # WGS84 longitude
climbing_type: sport,multi-pitch,trad  # sport, boulder, trad, multi-pitch
# photo_url:               # optional
```

Required fields: `name`, `lat`, `lon`, `climbing_type`. Filename must be lowercase with hyphens, no underscores or spaces.

## Running scripts

Always use `uv run` to run Python scripts — never bare `python`.

```bash
uv run python scripts/validate.py                    # Validate all spots
uv run python scripts/validate.py spots/foo.yaml     # Validate specific files
uv run python scripts/check_duplicates.py            # Check all for duplicates
uv run python scripts/insert.py                      # Insert all spots into DB
uv run python scripts/update_locations.py            # Update all spot locations
uv run python scripts/rename_spot.py 'Old' 'New'     # Rename in DB
```

Database scripts require `DATABASE_URL` environment variable (Supabase PostgreSQL connection string).

## CI/CD

- **On PR** (`validate-pr.yml`): validates changed spot files + checks duplicates
- **On merge to main** (`insert-on-merge.yml`): inserts new spots, updates modified ones
- **Manual dispatch**: backfills all spots into the database

## Code conventions

- Spot filenames: lowercase, hyphens only, `.yaml` extension
- Duplicate threshold: 500m (Haversine distance)
- DB inserts use PostGIS `ST_MakePoint(lon, lat)` with SRID 4326
- All scripts accept optional file paths as CLI args to scope to changed files only
- The `source` column is set to `'community'` for all spots inserted from this repo

## Git

- Remote uses SSH alias `github-personal` (`git@github-personal:eliott25/onsight-spots.git`)
- Use the `eliott25` GitHub account
- Required secret in repo settings: `DATABASE_URL`
