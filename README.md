# onsight-spots

Community-contributed climbing spots for [OnSight](https://onsight.ovh) — the climbing partner finder.

## How to add a spot

1. **Fork** this repo
2. **Copy** `SPOT_TEMPLATE.yaml` to `spots/your-spot-name.yaml`
3. **Fill in** the spot details (name, coordinates, climbing type)
4. **Open a PR** — CI will validate your file automatically
5. Once merged, the spot appears on the OnSight map

### Spot file format

```yaml
name: Gorges du Verdon
type: outdoor
lat: 43.76475
lon: 6.35979
climbing_type: sport,multi-pitch,trad
```

### Rules

- **One file per spot** — filename must be lowercase with hyphens (e.g., `gorges-du-verdon.yaml`)
- **Required fields**: `name`, `lat`, `lon`, `climbing_type`
- **Optional fields**: `type` (`outdoor` or `indoor`, defaults to `outdoor`), `photo_url`
- **Valid climbing types**: `sport`, `boulder`, `trad`, `multi-pitch` (comma-separated)
- **No duplicates** — spots within 500m of an existing spot will be flagged
- **Coordinates** — use [Google Maps](https://maps.google.com) or [OpenStreetMap](https://openstreetmap.org) to find lat/lon (right-click → "What's here?")

## For maintainers

### Setup

```bash
pip install pyyaml jsonschema psycopg2-binary
```

### Scripts

```bash
# Validate all spots
python scripts/validate.py

# Check for duplicates
python scripts/check_duplicates.py

# Insert into database (requires DATABASE_URL env var)
DATABASE_URL=... python scripts/insert.py
```

### Required secrets (GitHub repo settings)

- `DATABASE_URL` — PostgreSQL connection string for Supabase
