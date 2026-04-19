#!/usr/bin/env python3
"""Scrape climbing spots from grimper.com/site-escalade-france.

Writes one YAML file per new spot (5 fields: name, type, lat, lon, climbing_type)
and a photos.csv at repo root mapping slug -> name -> photo URL for later use.

Usage:
    uv run python scripts/scrape_grimper.py            # scrape all France spots
    uv run python scripts/scrape_grimper.py <slug>...  # scrape specific slugs
"""

from __future__ import annotations

import csv
import html as html_lib
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).parent.parent
SPOTS_DIR = REPO / "spots"
CACHE_DIR = REPO / ".scrape-cache"
PHOTOS_CSV = REPO / "photos.csv"

BASE = "https://www.grimper.com"
INDEX_PAGES = [f"{BASE}/site-escalade-france"] + [
    f"{BASE}/site-escalade-france/{i}" for i in range(2, 11)
]
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def fetch(url: str, retries: int = 3) -> str:
    """Fetch a URL via curl, caching responses on disk. Retries on failure."""
    CACHE_DIR.mkdir(exist_ok=True)
    key = re.sub(r"[^a-z0-9]+", "_", url.lower()).strip("_") + ".html"
    cache_file = CACHE_DIR / key
    if cache_file.exists() and cache_file.stat().st_size > 10_000:
        return cache_file.read_text(encoding="utf-8")

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            result = subprocess.run(
                ["curl", "-sL", "--max-time", "60", "--retry", "2", "-A", UA, url],
                capture_output=True,
                check=True,
            )
            body = result.stdout.decode("utf-8", errors="replace")
            if len(body) < 10_000:
                raise RuntimeError(f"response too small ({len(body)}B)")
            cache_file.write_text(body, encoding="utf-8")
            time.sleep(0.3)
            return body
        except (subprocess.CalledProcessError, RuntimeError) as e:
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"fetch failed after {retries} retries: {last_err}")


def list_france_spots() -> list[str]:
    """Return all real climbing-spot slugs from grimper.com's France index (paginated)."""
    slugs: set[str] = set()
    pattern = re.compile(
        r'class="nomStationListe"><a ref="#" href="site-escalade-([a-z0-9-]+)"'
    )
    for url in INDEX_PAGES:
        for m in pattern.finditer(fetch(url)):
            slugs.add(m.group(1))
    return sorted(slugs)


def extract_text(html: str, start_marker: str, end_marker: str | None = None) -> str:
    """Extract text between two markers, stripping HTML tags."""
    i = html.find(start_marker)
    if i < 0:
        return ""
    chunk = html[i:]
    if end_marker:
        j = chunk.find(end_marker)
        if j >= 0:
            chunk = chunk[:j]
    chunk = re.sub(r"<[^>]+>", " ", chunk)
    return html_lib.unescape(re.sub(r"\s+", " ", chunk)).strip()


def parse_spot(slug: str, html: str) -> dict | None:
    """Extract spot fields from a grimper.com spot page."""
    # Name
    name_m = re.search(r'<span id="titre-station">([^<]+)</span>', html)
    if not name_m:
        return None
    name = html_lib.unescape(name_m.group(1)).strip()

    # Coords from Google Maps iframe: !2d<lon>!3d<lat>  (may be negative)
    coord_m = re.search(r"!2d(-?[\d.]+)!3d(-?[\d.]+)", html)
    if not coord_m:
        return None
    lon = float(coord_m.group(1))
    lat = float(coord_m.group(2))

    # Highlights block (Type, Hauteur, Nombre de voies/blocs)
    highlights = {}
    for m in re.finditer(
        r'<span class="typeFalaise">([^<]+)</span><br/><span>([^<]+)</span>', html
    ):
        highlights[m.group(1).strip().lower()] = m.group(2).strip()

    # Climbing type inference
    outdoor_type = highlights.get("type", "").lower()
    count_label = " ".join(highlights.keys())
    hauteur_str = highlights.get("hauteur", "")

    # parse max height (e.g. "5 à 25 m", "80 m", "600 m")
    heights = [int(n) for n in re.findall(r"\d+", hauteur_str)]
    max_height = max(heights) if heights else 0

    # Main prose for discipline signals
    prose = extract_text(html, '<p class="chapo-station">', "</p>")
    rocher = extract_text(
        html, 'id="panel-rocher-escalade"', 'id="panel-acces'
    )
    corpus = (prose + " " + rocher).lower()

    climbing_types: list[str] = []
    if "bloc" in outdoor_type or "bloc" in count_label:
        climbing_types.append("boulder")
    else:
        climbing_types.append("sport")
        if max_height >= 50 or re.search(r"grande[s]? (voie|longueur)", corpus):
            climbing_types.append("multi-pitch")
        if re.search(r"\b(friend|coinceur|terrain d.aventure|fissure)", corpus):
            climbing_types.append("trad")

    # Photo — first lightbox image in #plan-pistes2, fallback to first sites/ image
    photo_rel = None
    lightbox_m = re.search(
        r'<a class="lightbox" href="(media/[^"]+\.(?:jpg|jpeg|png))"', html
    )
    if lightbox_m:
        photo_rel = lightbox_m.group(1)
    photo_url = f"{BASE}/{photo_rel}" if photo_rel else ""

    return {
        "slug": slug,
        "name": name,
        "type": "outdoor",
        "lat": lat,
        "lon": lon,
        "climbing_type": ",".join(climbing_types),
        "photo_url": photo_url,
        "_debug_height": max_height,
        "_debug_highlights": highlights,
    }


def write_yaml(spot: dict) -> Path:
    """Write a 5-field YAML file for a spot."""
    path = SPOTS_DIR / f"{spot['slug']}.yaml"
    content = (
        f"name: {spot['name']}\n"
        f"type: {spot['type']}\n"
        f"lat: {spot['lat']}\n"
        f"lon: {spot['lon']}\n"
        f"climbing_type: {spot['climbing_type']}\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


def main():
    argv_slugs = sys.argv[1:]
    slugs = argv_slugs if argv_slugs else list_france_spots()

    existing = {p.stem for p in SPOTS_DIR.glob("*.yaml")}
    photos_rows: list[dict] = []
    scraped = 0
    skipped = 0
    failed: list[str] = []

    for slug in slugs:
        try:
            html = fetch(f"{BASE}/site-escalade-{slug}")
            spot = parse_spot(slug, html)
        except Exception as e:
            failed.append(f"{slug}: {e}")
            continue
        if not spot:
            failed.append(f"{slug}: could not parse (no name or coords)")
            continue

        photos_rows.append(
            {"slug": slug, "name": spot["name"], "photo_url": spot["photo_url"]}
        )

        if slug in existing:
            skipped += 1
            continue

        write_yaml(spot)
        scraped += 1
        print(
            f"  {slug:35s} {spot['name']:30s} "
            f"{spot['lat']:.5f},{spot['lon']:.5f}  {spot['climbing_type']}"
        )

    # Write photos.csv
    if photos_rows:
        with open(PHOTOS_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["slug", "name", "photo_url"])
            w.writeheader()
            w.writerows(photos_rows)

    print(
        f"\nDone: {scraped} scraped, {skipped} skipped (already exist), "
        f"{len(failed)} failed"
    )
    if failed:
        print("\nFailures:")
        for f in failed:
            print(f"  ✗ {f}")


if __name__ == "__main__":
    main()
