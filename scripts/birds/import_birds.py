#!/usr/bin/env python3
"""
Interactive Offline Bird Portfolio Ingestion Pipeline
Designed for [https://github.com/aav7fl/website](https://github.com/aav7fl/website)

Features:
- Scans _staging/ in natural sort order (matches File Explorer order)
- Tracks imported photos via source_id ({filename}_{timestamp}_{sha256[:8]}); a replaced photo
  is forgotten, so it can be imported again later (e.g. under the correct species)
- Offline AI species top-3 suggestion (pinned local BioCLIP, see bird_model.py) with Fuzzy Search fallback
- Resolves GPS EXIF offline to "County, ST" via US Census GeoJSON + Shapely
- Converts colorspace to sRGB, resizes to 800px wide, exports WebP, and strips all EXIF/ICC metadata
  (GPS, camera, timestamps), then writes back only copyright tags (see stamp_copyright)
- Preserves or wipes user-authored 'notes' field when replacing an existing species photo
- Never replaces a species whose catalog entry has `locked: true` (warns and leaves the file staged)
- Outputs chronologically sorted _data/birds.yml for Jekyll consumption
"""

import argparse
import csv
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import os

# Force Hugging Face to strictly use the local cache and prevent network update checks
os.environ["HF_HUB_OFFLINE"] = "1"

import yaml
from natsort import natsorted
from prompt_toolkit import prompt
from prompt_toolkit.completion import FuzzyWordCompleter
from rich.console import Console
from rich.panel import Panel

import bird_model  # The pinned, local AI model (scripts/birds/bird_model.py)
import update_deps  # Tested, automatic package updates (scripts/birds/update_deps.py)

console = Console()

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent

DEFAULT_STAGING_DIR = REPO_ROOT / "_staging"
DEFAULT_DEST_DIR = REPO_ROOT / "assets" / "img" / "birds"
DEFAULT_YAML_PATH = REPO_ROOT / "_data" / "birds.yml"
TAXONOMY_CSV_PATH = SCRIPT_DIR / "taxonomy_sibley.csv"
GEOJSON_PATH = SCRIPT_DIR / "us_counties.geojson"

# --auto only accepts the AI's top suggestion above this confidence (percent)
AUTO_MIN_CONFIDENCE = 90.0

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic"}

# Embedded in every exported photo. The photos are all rights reserved
# (see assets/img/birds/LICENSE.txt), unlike the MIT-licensed code.
COPYRIGHT_HOLDER = "Kyle Niewiada"
COPYRIGHT_LICENSE_URL = "https://www.kyleniewiada.org/assets/img/birds/LICENSE.txt"


def display_path(path: Path) -> str:
    """Path relative to the repo when possible, for shorter messages."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"['’]", "", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def compute_sha256_prefix(filepath: Path, length: int = 8) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()[:length]


def extract_exif(filepath: Path) -> Dict[str, Any]:
    """Extract DateTimeOriginal and numeric GPS coordinates via exiftool."""
    cmd = [
        "exiftool",
        "-j",
        "-n",
        "-DateTimeOriginal",
        "-CreateDate",
        "-ModifyDate",
        "-GPSLatitude",
        "-GPSLongitude",
        str(filepath),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0 or not res.stdout.strip():
        return {}
    try:
        data = json.loads(res.stdout)
        return data[0] if data else {}
    except json.JSONDecodeError:
        return {}


def normalize_timestamp(exif: Dict[str, Any], filepath: Path) -> str:
    """Return ISO-8601 timestamp YYYY-MM-DDTHH:MM:SS from EXIF or file mtime."""
    raw_dt = (
        exif.get("DateTimeOriginal")
        or exif.get("CreateDate")
        or exif.get("ModifyDate")
    )
    if raw_dt and isinstance(raw_dt, str):
        raw_dt = raw_dt.strip()
        match = re.match(
            r"^(\d{4})[:\-](\d{2})[:\-](\d{2})[ T](\d{2}):(\d{2}):(\d{2})", raw_dt
        )
        if match:
            y, m, d, hh, mm, ss = match.groups()
            return f"{y}-{m}-{d}T{hh}:{mm}:{ss}"

    mtime = datetime.datetime.fromtimestamp(filepath.stat().st_mtime)
    return mtime.strftime("%Y-%m-%dT%H:%M:%S")


def build_source_id(filepath: Path, iso_timestamp: str) -> str:
    compact_ts = re.sub(r"[^0-9T]", "", iso_timestamp)
    sha_prefix = compute_sha256_prefix(filepath, 8)
    return f"{filepath.name}_{compact_ts}_{sha_prefix}"


class CountyLocator:
    """Offline point-in-polygon resolver using US Census County GeoJSON and Shapely."""

    def __init__(self, geojson_path: Path) -> None:
        self.geojson_path = geojson_path
        self.polygons: List[Tuple[Any, str]] = []
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self.geojson_path.exists():
            console.print(
                f"[yellow]Warning: Offline County GeoJSON not found at {self.geojson_path}. "
                "Run 'python3 scripts/birds/setup_offline_assets.py' first.[/yellow]"
            )
            return

        from shapely.geometry import shape

        with open(self.geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for feat in data.get("features", []):
            geom = feat.get("geometry")
            props = feat.get("properties", {})
            label = props.get("county_state")
            if geom and label:
                self.polygons.append((shape(geom), label))

    def resolve(self, lat: Optional[float], lon: Optional[float]) -> Optional[str]:
        if lat is None or lon is None:
            return None
        self._ensure_loaded()
        if not self.polygons:
            return None

        from shapely.geometry import Point

        pt = Point(float(lon), float(lat))
        for poly, label in self.polygons:
            if poly.contains(pt):
                return label
        best_label = None
        best_dist = 0.15
        for poly, label in self.polygons:
            dist = poly.distance(pt)
            if dist < best_dist:
                best_dist = dist
                best_label = label
        return best_label


class OfflineBirdClassifier:
    """
    Offline top-3 species suggestions from the pinned local BioCLIP model (see
    bird_model.py), restricted to the species in taxonomy_sibley.csv. Optional:
    if the AI packages or model files are missing, imports fall back to fuzzy search.
    """

    def __init__(self, taxonomy_rows: List[Dict[str, Any]], enabled: bool = True, allowed: Optional[List[int]] = None) -> None:
        self.taxonomy_rows = taxonomy_rows
        self.enabled = enabled
        self.allowed = allowed  # Taxonomy rows the AI may suggest (None: all); see bird_model.allowed_species
        self._initialized = False
        self.model = None
        self.preprocess = None
        self.text_features = None

    def _lazy_init(self) -> None:
        if self._initialized or not self.enabled:
            return
        self._initialized = True
        try:
            problems = bird_model.verify_model()
            if problems:
                raise RuntimeError("; ".join(problems))
            console.print("[dim]Loading offline BioCLIP model...[/dim]")
            self.model, self.preprocess, tokenizer = bird_model.load_model()
            self.text_features = bird_model.text_embeddings(
                self.model, tokenizer, self.taxonomy_rows, cache_key=bird_model.MODEL_REVISION
            )
        except Exception as exc:
            console.print(
                f"[yellow]AI suggestions unavailable ({exc}). Using fuzzy search instead.\n"
                "Run `rake birds:doctor` to see what's wrong, or `rake birds:setup` to download the model.[/yellow]"
            )
            self.enabled = False

    def predict_top_k(self, image_path: Path, k: int = 3) -> List[Tuple[Dict[str, Any], float]]:
        self._lazy_init()
        if not self.enabled or self.model is None or self.text_features is None:
            return []
        return bird_model.predict(self.model, self.preprocess, self.text_features, self.taxonomy_rows, image_path, k, self.allowed)


def load_taxonomy(csv_path: Path) -> List[Dict[str, Any]]:
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["sibley_category_order"] = int(row["sibley_category_order"])
            row["taxonomic_order"] = int(row["taxonomic_order"])
            rows.append(row)
    return rows


def load_catalog(yaml_path: Path) -> List[Dict[str, Any]]:
    if not yaml_path.exists():
        return []
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, list) else []


class _DoubleQuoted(str):
    """A string always written to YAML in double quotes."""


class _CatalogDumper(yaml.SafeDumper):
    """Writes every `notes` value in double quotes, so apostrophes ("Didn't") need no escaping."""


_CatalogDumper.add_representer(
    _DoubleQuoted, lambda dumper, value: dumper.represent_scalar("tag:yaml.org,2002:str", str(value), style='"')
)


def save_catalog(yaml_path: Path, entries: List[Dict[str, Any]]) -> None:
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    sorted_entries = sorted(entries, key=lambda x: str(x.get("date_taken", "")))
    sorted_entries = [
        {**e, "notes": _DoubleQuoted(e.get("notes") or "")} if "notes" in e else e
        for e in sorted_entries
    ]

    header = (
        "# Master Bird Portfolio Catalog\n"
        "# Automatically maintained by scripts/birds/import_birds.py\n"
        "# Sorted chronologically by date_taken.\n"
        "# Manual edits to the 'notes' field are preserved during photo upgrades.\n"
        "# Notes are in double quotes, so apostrophes need no escaping; write a double quote as \\\".\n"
        "# Add 'locked: true' to an entry to stop any import from replacing its photo.\n\n"
    )
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(header)
        yaml.dump(
            sorted_entries,
            f,
            Dumper=_CatalogDumper,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
            width=4096,  # Keeps each note on one line, for easy hand editing
        )


def prompt_fuzzy_species(
    taxonomy_rows: List[Dict[str, Any]],
    existing_slugs: set,
    locked_slugs: Optional[set] = None,
) -> Optional[Dict[str, Any]]:
    """Interactive fuzzy search across Common Name, 4-letter Banding Code, and Scientific Name."""
    lookup_map: Dict[str, Dict[str, Any]] = {}
    display_words: List[str] = []

    for row in taxonomy_rows:
        row_slug = slugify(row["common_name"])
        tag = " [locked]" if locked_slugs and row_slug in locked_slugs else " [existing]" if row_slug in existing_slugs else ""
        label = f"{row['common_name']} ({row['banding_code']} - {row['scientific_name']}){tag}"
        lookup_map[label] = row
        lookup_map[row["common_name"].lower()] = row
        lookup_map[row["banding_code"].lower()] = row
        display_words.append(label)

    completer = FuzzyWordCompleter(display_words, WORD=True)
    while True:
        user_input = prompt(
            "  Fuzzy search species (type common name or 4-letter code, or 's' to skip): ",
            completer=completer,
        ).strip()
        if not user_input or user_input.lower() == "s":
            return None
        if user_input in lookup_map:
            return lookup_map[user_input]
        if user_input.lower() in lookup_map:
            return lookup_map[user_input.lower()]
        matches = [
            r for r in taxonomy_rows
            if user_input.lower() in r["common_name"].lower()
            or user_input.lower() == r["banding_code"].lower()
        ]
        if len(matches) == 1:
            return matches[0]
        console.print("[red]  No exact match found. Pick from the autocomplete dropdown or try again.[/red]")


def stamp_copyright(dest_path: Path, year: str) -> None:
    """
    Write copyright tags into an exported WebP: EXIF Artist/Copyright plus the XMP
    fields (dc:creator, dc:rights, xmpRights:Marked/WebStatement) that image search
    and photo apps read. Nothing else is added, so GPS and camera data stay stripped.
    Compact XMP keeps this to under 1 KB per photo (default padding adds ~3 KB).
    """
    notice = f"© {year} {COPYRIGHT_HOLDER}. All rights reserved."
    cmd_exif = [
        "exiftool",
        "-overwrite_original",
        "-api",
        "Compact=All",
        f"-EXIF:Artist={COPYRIGHT_HOLDER}",
        f"-EXIF:Copyright={notice}",
        f"-XMP-dc:Creator={COPYRIGHT_HOLDER}",
        f"-XMP-dc:Rights={notice}",
        "-XMP-xmpRights:Marked=True",
        f"-XMP-xmpRights:WebStatement={COPYRIGHT_LICENSE_URL}",
        str(dest_path),
    ]
    subprocess.run(cmd_exif, capture_output=True, check=True)


def process_image_to_webp(src_path: Path, dest_path: Path, year: str, width: int = 800, quality: int = 84) -> None:
    """
    Convert image to sRGB, resize to 800px wide, sharpen subtly, strip metadata & color profiles,
    and run exiftool -all= as a belt-and-suspenders pass. Then write back only the copyright
    tags, using the year the photo was taken.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    magick_bin = "magick" if shutil.which("magick") else "convert"

    cmd_magick = [
        magick_bin,
        str(src_path),
        "-colorspace",
        "sRGB",
        "-filter",
        "Lanczos",
        "-resize",
        f"{width}x",
        "-unsharp",
        "0x0.75+0.75+0.008",
        "-strip",
        "-quality",
        str(quality),
        str(dest_path),
    ]
    subprocess.run(cmd_magick, check=True)

    cmd_exif = [
        "exiftool",
        "-all=",
        "-overwrite_original",
        str(dest_path),
    ]
    subprocess.run(cmd_exif, capture_output=True, check=True)

    stamp_copyright(dest_path, year)


def backfill_ebird_codes(yaml_path: Path, catalog: List[Dict[str, Any]], taxonomy_rows: List[Dict[str, Any]]) -> None:
    """
    Adds each catalog entry's eBird species code (from taxonomy_sibley.csv) for the
    "View on eBird" link in the photo viewer. Matches by scientific name, then common name.
    """
    by_sci = {r["scientific_name"]: r.get("ebird_code", "") for r in taxonomy_rows}
    by_common = {r["common_name"]: r.get("ebird_code", "") for r in taxonomy_rows}
    missing = []
    updated: List[Dict[str, Any]] = []
    for entry in catalog:
        code = by_sci.get(entry.get("species_scientific", "")) or by_common.get(entry.get("species_common", "")) or ""
        if not code:
            missing.append(entry.get("species_common", "?"))
        # Rebuild the entry so ebird_code sits next to the other taxonomy fields
        rebuilt: Dict[str, Any] = {}
        for key, value in entry.items():
            if key == "ebird_code":
                continue
            rebuilt[key] = value
            if key == "taxonomic_order":
                rebuilt["ebird_code"] = code
        rebuilt.setdefault("ebird_code", code)
        updated.append(rebuilt)
    save_catalog(yaml_path, updated)
    console.print(f"[bold green]Added eBird codes to {len(catalog) - len(missing)} of {len(catalog)} birds.[/bold green]")
    if missing:
        console.print(f"[yellow]No eBird code in taxonomy_sibley.csv for: {', '.join(missing)}. Run `rake birds:setup` first.[/yellow]")


def stamp_existing_photos(dest_dir: Path, catalog: List[Dict[str, Any]]) -> None:
    """Write the copyright tags into every photo already in the catalog (e.g. after changing the notice)."""
    stamped = 0
    for entry in catalog:
        photo = dest_dir / str(entry.get("filename", ""))
        if not photo.is_file():
            console.print(f"  [yellow]Missing photo for {entry.get('species_common')}: {photo.name}[/yellow]")
            continue
        stamp_copyright(photo, str(entry.get("date_taken", ""))[:4])
        stamped += 1
    console.print(f"[bold green]Stamped copyright into {stamped} of {len(catalog)} photos.[/bold green]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest staged bird photos into Jekyll portfolio.")
    parser.add_argument("--staging", type=Path, default=DEFAULT_STAGING_DIR, help="Staging folder path")
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST_DIR, help="Destination images folder")
    parser.add_argument("--yaml", type=Path, default=DEFAULT_YAML_PATH, help="Catalog YAML path")
    parser.add_argument("--force", action="store_true", help="Re-import even if source_id already exists")
    parser.add_argument("--no-ai", action="store_true", help="Skip offline AI suggestions and go straight to fuzzy search")
    parser.add_argument("--no-update", action="store_true", help="Skip this run's automatic package update check")
    parser.add_argument("--americas", action="store_true",
                        help="AI considers all of North and Central America (the whole taxonomy, ~2,000 species, incl. strays), "
                             "not just regular US/Canada birds. For trips to Mexico or Central America; not worldwide")
    parser.add_argument("--auto", action="store_true", help=f"Import only confident (>{AUTO_MIN_CONFIDENCE:.0f}%%) AI matches of new species with GPS, without prompts; everything else stays staged")
    parser.add_argument("--stamp-copyright", action="store_true", help="Write copyright tags into every photo already imported, then exit")
    parser.add_argument("--backfill-ebird-codes", action="store_true", help="Add eBird species codes to every bird already imported, then exit")
    args = parser.parse_args()

    if args.stamp_copyright:
        stamp_existing_photos(args.dest, load_catalog(args.yaml))
        return
    if args.backfill_ebird_codes:
        backfill_ebird_codes(args.yaml, load_catalog(args.yaml), load_taxonomy(TAXONOMY_CSV_PATH))
        return

    # About once a month: try the newest packages, switching only if they pass the
    # checks. If they were installed, restart so this whole run uses them.
    if not args.no_update and update_deps.maybe_update():
        os.environ["BIRDS_NO_UPDATE"] = "1"
        os.execv(sys.executable, [sys.executable] + sys.argv)

    if args.auto and args.no_ai:
        console.print("[yellow]--auto relies on AI suggestions, so with --no-ai every photo will be skipped.[/yellow]")

    if not args.staging.exists():
        console.print(f"[red]Staging directory not found: {args.staging}[/red]")
        sys.exit(1)

    taxonomy_rows = load_taxonomy(TAXONOMY_CSV_PATH)
    catalog = load_catalog(args.yaml)
    locator = CountyLocator(GEOJSON_PATH)
    allowed, species_scope = bird_model.allowed_species(
        taxonomy_rows,
        always_include=[e.get("species_common", "") for e in catalog],
        americas=args.americas,
    )
    classifier = OfflineBirdClassifier(taxonomy_rows, enabled=not args.no_ai, allowed=allowed)

    staged_files = natsorted(
        [
            p for p in args.staging.iterdir()
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        ],
        key=lambda p: p.name,
    )

    if not staged_files:
        console.print(f"[yellow]No image files found in {args.staging}[/yellow]")
        return

    console.print(
        Panel(
            f"Found [bold cyan]{len(staged_files)}[/bold cyan] staged file(s) in [bold]{args.staging}[/bold]\n"
            f"Catalog: [bold]{args.yaml}[/bold] ({len(catalog)} existing species)\n"
            f"AI species: {species_scope if not args.no_ai else 'AI off (--no-ai)'}\n"
            f"Auto Mode: [bold {'green' if args.auto else 'red'}]{'ON' if args.auto else 'OFF'}[/]",
            title="Bird Portfolio Ingestion Pipeline",
        )
    )

    known_sources: Dict[str, str] = {}
    by_slug: Dict[str, Dict[str, Any]] = {}
    for entry in catalog:
        slug = entry.get("slug", "")
        species_name = entry.get("species_common", slug)
        if slug:
            by_slug[slug] = entry
        if entry.get("source_id"):
            known_sources[entry["source_id"]] = species_name

    # Species whose photo is held in place with `locked: true` in the catalog
    locked_slugs = {slug for slug, entry in by_slug.items() if entry.get("locked")}

    recent_locations = ["Ottawa County, MI", "Kent County, MI", "Allegan County, MI", "Muskegon County, MI"]
    modified_count = 0

    for idx, filepath in enumerate(staged_files, start=1):
        # --- NEW SANITIZATION BLOCK ---
        # ImageMagick interprets square brackets as frame modifiers. 
        # Sanitize them out of the filename before processing.
        if "[" in filepath.name or "]" in filepath.name:
            clean_name = filepath.name.replace("[", "").replace("]", "")
            new_filepath = filepath.with_name(clean_name)
            filepath.rename(new_filepath)
            filepath = new_filepath
        # ------------------------------

        exif = extract_exif(filepath)
        iso_dt = normalize_timestamp(exif, filepath)
        source_id = build_source_id(filepath, iso_dt)

        if source_id in known_sources and not args.force:
            console.print(
                f"[yellow][SKIP] [{idx}/{len(staged_files)}] {filepath.name} "
                f"already imported as {known_sources[source_id]} ({source_id})[/yellow]"
            )
            continue

        console.rule(f"[bold cyan]File [{idx}/{len(staged_files)}]: {filepath.name}[/bold cyan]")
        console.print(f"  [dim]Captured:[/dim] {iso_dt}   [dim]Source ID:[/dim] {source_id}")

        chosen_species: Optional[Dict[str, Any]] = None
        predictions = classifier.predict_top_k(filepath, k=3)

        if args.auto:
            # Only a confident top suggestion is taken without asking; anything else
            # stays in staging for a manual run
            if predictions and predictions[0][1] > AUTO_MIN_CONFIDENCE:
                chosen_species = predictions[0][0]
                console.print(f"  [bold green][AUTO][/bold green] Selected {chosen_species['common_name']} ({predictions[0][1]:.1f}%)")
            else:
                conf = predictions[0][1] if predictions else 0.0
                console.print(
                    f"  [yellow][AUTO-SKIP][/yellow] Highest confidence {conf:.1f}% is not above "
                    f"{AUTO_MIN_CONFIDENCE:.0f}%. Left in staging for a manual run."
                )
                continue
        elif predictions:
            for rank, (sp, conf) in enumerate(predictions, start=1):
                sp_entry = by_slug.get(slugify(sp["common_name"]))
                exists_badge = (
                    " [bold red](locked, can't be replaced)[/bold red]"
                    if sp_entry and sp_entry.get("locked")
                    else " [bold yellow](already in catalog)[/bold yellow]"
                    if sp_entry
                    else ""
                )
                console.print(
                    f"    [[bold green]{rank}[/bold green]] {sp['common_name']} "
                    f"[dim]({sp['scientific_name']})[/dim] — {conf:.1f}%{exists_badge}"
                )
            console.print("    [[bold cyan]f[/bold cyan]] Fuzzy search taxonomy manually")
            console.print("    [[bold red]s[/bold red]] Skip this image")

            choice = prompt("  Select option [1/2/3/f/s, default: 1]: ").strip().lower() or "1"
            if choice in {"1", "2", "3"} and int(choice) <= len(predictions):
                chosen_species = predictions[int(choice) - 1][0]
            elif choice == "s":
                console.print("  [dim]Skipped.[/dim]")
                continue
            else:
                chosen_species = prompt_fuzzy_species(taxonomy_rows, set(by_slug.keys()), locked_slugs)
        else:
            chosen_species = prompt_fuzzy_species(taxonomy_rows, set(by_slug.keys()), locked_slugs)

        if not chosen_species:
            console.print("  [dim]Skipped.[/dim]")
            continue

        slug = slugify(chosen_species["common_name"])
        dest_filename = f"{slug}.webp"
        dest_path = args.dest / dest_filename

        existing_entry = by_slug.get(slug)
        retained_note = ""

        if existing_entry and existing_entry.get("locked"):
            # Checked before anything is processed, so a locked photo and its entry are never touched
            console.print(
                f"  [bold red]WARNING: {chosen_species['common_name']} is locked, so this photo can't replace it.[/bold red]\n"
                f"  [yellow]Its entry in {display_path(args.yaml)} has 'locked: true', which holds the current photo "
                f"({existing_entry.get('source_filename', 'unknown')}, taken {existing_entry.get('date_taken', 'unknown')}) in place.\n"
                f"  {filepath.name} was left in {display_path(args.staging)}/ untouched. To replace the photo, remove "
                f"'locked: true' from that entry (or set it to false) and run the import again.[/yellow]"
            )
            continue

        if existing_entry and args.auto:
            console.print(
                f"  [yellow][AUTO-SKIP][/yellow] {chosen_species['common_name']} is already in the catalog. "
                "Auto mode never replaces a photo; left in staging for a manual run."
            )
            continue

        if existing_entry:
            old_src = existing_entry.get("source_filename", "unknown")
            old_dt = existing_entry.get("date_taken", "unknown")
            confirm = prompt(
                f"  '{chosen_species['common_name']}' already exists (from {old_src} on {old_dt}). "
                "Overwrite with this photo? [y/N]: "
            ).strip().lower()
            if confirm != "y":
                console.print("  [dim]Kept existing photo. Skipping.[/dim]")
                continue

            existing_note = str(existing_entry.get("notes", "") or "").strip()
            if existing_note:
                console.print(
                    f"  [bold yellow]Existing note on {chosen_species['common_name']}:[/bold yellow] \"{existing_note}\""
                )
                note_action = prompt(
                    "  Do you want to [r]etain or [w]ipe the existing note? [R/w]: "
                ).strip().lower() or "r"
                if note_action == "w":
                    retained_note = ""
                    console.print("  [dim]Wiped existing note.[/dim]")
                else:
                    retained_note = existing_note
                    console.print("  [dim]Retained existing note.[/dim]")

        lat = exif.get("GPSLatitude")
        lon = exif.get("GPSLongitude")
        county_state = locator.resolve(lat, lon)

        if county_state:
            console.print(f"  [dim]Offline GPS County Match:[/dim] [bold green]{county_state}[/bold green]")
        elif args.auto:
            console.print("  [yellow][AUTO-SKIP][/yellow] No GPS location in the photo. Left in staging for a manual run.")
            continue
        else:
            console.print("  [yellow]No GPS coordinates found in EXIF (or outside US county boundaries).[/yellow]")
            for i, loc in enumerate(recent_locations[:4], start=1):
                console.print(f"    [{i}] {loc}")
            loc_choice = prompt(
                "  Select location [1-4] or type custom 'County, ST' [default: 1]: "
            ).strip() or "1"
            if loc_choice.isdigit() and 1 <= int(loc_choice) <= len(recent_locations[:4]):
                county_state = recent_locations[int(loc_choice) - 1]
            else:
                county_state = loc_choice
            if county_state not in recent_locations:
                recent_locations.insert(0, county_state)

        console.print(
            f"  [dim]Generating 800px sRGB WebP and stripping metadata -> {display_path(dest_path)}[/dim]"
        )
        process_image_to_webp(filepath, dest_path, year=iso_dt[:4])

        new_entry: Dict[str, Any] = {
            "species_common": chosen_species["common_name"],
            "species_scientific": chosen_species["scientific_name"],
            "banding_code": chosen_species["banding_code"],
            "slug": slug,
            "filename": dest_filename,
            "family": chosen_species["family"],
            "sibley_category": chosen_species["sibley_category"],
            "sibley_category_order": int(chosen_species["sibley_category_order"]),
            "taxonomic_order": int(chosen_species["taxonomic_order"]),
            "ebird_code": chosen_species.get("ebird_code", ""),
            "date_taken": iso_dt,
            "location": county_state,
            "notes": retained_note,
            "source_filename": filepath.name,
            "source_id": source_id,
        }

        if existing_entry:
            catalog = [e for e in catalog if e.get("slug") != slug]
        catalog.append(new_entry)
        by_slug[slug] = new_entry
        known_sources[source_id] = chosen_species["common_name"]
        modified_count += 1

        save_catalog(args.yaml, catalog)
        console.print(
            f"  [bold green]Saved {chosen_species['common_name']} ({dest_filename})[/bold green]"
        )

        # Remove the original file from the _staging folder now that it's processed
        try:
            filepath.unlink()
            console.print("  [dim]Removed original file from staging.[/dim]")
        except Exception as e:
            console.print(f"  [red]Failed to remove original file: {e}[/red]")
        # --------------------------

    console.rule("[bold green]Import Complete[/bold green]")
    console.print(f"Processed and updated [bold]{modified_count}[/bold] photo(s) in {args.yaml}.")


if __name__ == "__main__":
    main()