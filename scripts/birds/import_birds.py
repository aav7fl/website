#!/usr/bin/env python3
"""
Interactive Offline Bird Portfolio Ingestion Pipeline
Designed for [https://github.com/aav7fl/website](https://github.com/aav7fl/website)

Features:
- Scans _staging/ in natural sort order (matches File Explorer order)
- Tracks imported photos via source_id ({filename}_{timestamp}_{sha256[:8]}); a replaced photo
  is forgotten, so it can be imported again later (e.g. under the correct species)
- Offline AI species top-3 suggestion (pinned local BioCLIP, see bird_model.py) with Fuzzy Search fallback
- Resolves GPS EXIF offline to "County, ST" via US Census GeoJSON + Shapely STRtree
- Orients upright, converts ICC profiles (e.g. Display P3) to sRGB, shrinks to at most 800px wide
  (without upscaling small crops), exports WebP, and strips all EXIF/ICC metadata (GPS, camera,
  timestamps), writing back only copyright tags in a single exiftool pass (see stamp_copyright)
- Shows a small preview of each photo in the terminal (and previews the existing catalog photo
  before confirming an overwrite): real image where supported, colored blocks where not (--preview)
- Lets you discard rejected photos from _staging/ with 'd' (after confirmation)
- Asks for an optional note on each import; when replacing a photo that has a note, keeps it,
  wipes it, or takes a new one
- Warns and asks for the real date and time when a photo is missing EXIF capture dates, and for
  Google Photos collages (e.g. 20261023_142445-COLLAGE.jpg), whose own timestamp is when the
  collage was made rather than when the photos were taken
- Never replaces a species whose catalog entry has `locked: true` (warns and leaves the file staged)
- Outputs chronologically sorted _data/birds.yml for Jekyll consumption
"""

import argparse
import base64
import datetime
import json
import os
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Force Hugging Face to strictly use the local cache and prevent network update checks
os.environ["HF_HUB_OFFLINE"] = "1"

import yaml
from natsort import natsorted
from prompt_toolkit import prompt
from prompt_toolkit.completion import FuzzyWordCompleter
from rich.console import Console
from rich.panel import Panel

from bird_common import (  # Shared stdlib-only helpers (scripts/birds/bird_common.py)
    COLLAGE_NAME_RE,
    COPYRIGHT_HOLDER,
    COPYRIGHT_LICENSE_URL,
    DEFAULT_DEST_DIR,
    DEFAULT_STAGING_DIR,
    DEFAULT_YAML_PATH,
    GEOJSON_PATH,
    REPO_ROOT,
    SCRIPT_DIR,
    TAXONOMY_CSV_PATH,
    build_source_id,
    compute_sha256_prefix,
    display_path,
    extract_timestamp,
    is_collage,
    load_taxonomy,
    normalize_timestamp,
    parse_user_timestamp,
    process_image_to_webp,
    sanitize_staged_filename,
    slugify,
    stamp_copyright,
)
import bird_model  # The pinned, local AI model (scripts/birds/bird_model.py)
import update_deps  # Tested, automatic package updates (scripts/birds/update_deps.py)

console = Console()

# --auto only accepts the AI's top suggestion above this confidence (percent)
AUTO_MIN_CONFIDENCE = 90.0

# Terminal preview of each staged photo (see show_preview)
PREVIEW_MODES = ("auto", "image", "blocks", "off")
PREVIEW_COLUMNS = 56  # Widest a preview gets, in terminal columns
PREVIEW_ROWS = 20     # Tallest a preview gets, in terminal rows

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic"}

# Sentinel returned when the user chooses to discard (delete) a staged photo
_DISCARD = object()

DEFAULT_RECENT_LOCATIONS = [
    "Ottawa County, MI",
    "Kent County, MI",
    "Allegan County, MI",
    "Muskegon County, MI",
]


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


def prompt_manual_timestamp(
    filepath: Path,
    fallback_timestamp: str,
    *,
    reason_banner: str,
    keep_label: str,
    warn_if_after_fallback: bool = False,
) -> Optional[str]:
    """
    Ask the user for the real date and time a photo was taken. Returns the timestamp,
    or None to skip the photo. Typing 'k' keeps fallback_timestamp.
    """
    fallback_display = fallback_timestamp.replace("T", " ")
    console.print(reason_banner)
    while True:
        answer = prompt(f"  Date and time taken ('k' to keep {keep_label}, 's' to skip): ").strip()
        if answer.lower() == "s":
            return None
        if answer.lower() == "k":
            return fallback_timestamp
        timestamp = parse_user_timestamp(answer)
        if not timestamp:
            console.print("[red]  Not a date and time. Use YYYY-MM-DD HH:MM (am/pm optional) or October 23, 2026 @ 1:16 PM.[/red]")
            continue
        if timestamp > datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"):
            console.print("[red]  That's in the future. Check the date and try again.[/red]")
            continue
        if warn_if_after_fallback and timestamp > fallback_timestamp:
            # The photos must be older than the collage made from them, unless its own date is off
            confirm = prompt(f"  That's after the collage was made ({fallback_display}). Use it anyway? [y/N]: ").strip().lower()
            if confirm != "y":
                continue
        console.print(f"  [dim]Using {timestamp.replace('T', ' ')} as the date taken.[/dim]")
        return timestamp


def prompt_collage_timestamp(filepath: Path, file_timestamp: str) -> Optional[str]:
    """Ask for when a Google Photos collage's photos were taken."""
    made = file_timestamp.replace("T", " ")
    banner = (
        f"  [bold yellow]{filepath.name} is a Google Photos collage.[/bold yellow] Its timestamp ({made}) is when the "
        "collage was made.\n"
        "  Enter the date and time of the most recent photo in it (shown in Google Photos' info panel), "
        "e.g. [bold]2025-04-12 9:09 am[/bold] or [bold]April 12, 2025 @ 9:09 AM[/bold]."
    )
    return prompt_manual_timestamp(
        filepath,
        file_timestamp,
        reason_banner=banner,
        keep_label="the collage's",
        warn_if_after_fallback=True,
    )


def prompt_missing_exif_timestamp(filepath: Path, file_timestamp: str) -> Optional[str]:
    """Warn that EXIF capture date is missing and ask for the real date and time."""
    mtime_display = file_timestamp.replace("T", " ")
    banner = (
        f"  [bold yellow]Warning: {filepath.name} has no EXIF date.[/bold yellow] "
        f"Its fallback timestamp ({mtime_display}) is the file's modified time.\n"
        "  Enter the real date and time it was taken, e.g. [bold]2025-04-12 9:09 am[/bold] "
        "or [bold]April 12, 2025 @ 9:09 AM[/bold]."
    )
    return prompt_manual_timestamp(
        filepath,
        file_timestamp,
        reason_banner=banner,
        keep_label="file modified time",
        warn_if_after_fallback=False,
    )


def _magick_thumbnail(filepath: Path, box: str, output: str) -> bytes:
    """A small, upright copy of the photo that fits `box` (e.g. "56x40"), in ImageMagick's `output` format."""
    magick_bin = "magick" if shutil.which("magick") else "convert"
    cmd = [
        magick_bin,
        f"{filepath}[0]",  # First frame only (multi-image HEIC/TIFF)
        "-auto-orient",
        "-thumbnail",
        box,
        "-colorspace",
        "sRGB",
        "-alpha",
        "remove",
        "-depth",
        "8",
        "-quality",
        "80",  # Only matters for the JPEG sent to the terminal
        output,
    ]
    return subprocess.run(cmd, capture_output=True, check=True).stdout


def _preview_blocks(filepath: Path) -> str:
    """
    The photo as colored half blocks: each character is two pixels, the top one in
    the foreground color of "▀" and the bottom one in its background. Needs only a
    24-bit color terminal, which VS Code's is.
    """
    ppm = _magick_thumbnail(filepath, f"{PREVIEW_COLUMNS}x{PREVIEW_ROWS * 2}", "ppm:-")
    # Binary PPM: "P6 <width> <height> <maxval>" then one whitespace byte and raw RGB
    header = re.match(rb"P6\s+(?:#[^\n]*\n\s*)*(\d+)\s+(\d+)\s+(\d+)\s", ppm)
    if not header:
        raise ValueError("unexpected thumbnail format")
    width, height = int(header.group(1)), int(header.group(2))
    pixels = ppm[header.end():]
    if len(pixels) < width * height * 3:
        raise ValueError("truncated thumbnail")

    def pixel(x: int, y: int) -> Tuple[int, int, int]:
        offset = (y * width + x) * 3
        return pixels[offset], pixels[offset + 1], pixels[offset + 2]

    lines = []
    for y in range(0, height, 2):
        cells = []
        for x in range(width):
            r, g, b = pixel(x, y)
            cell = f"\x1b[38;2;{r};{g};{b}m"
            if y + 1 < height:
                r, g, b = pixel(x, y + 1)
                cell += f"\x1b[48;2;{r};{g};{b}m"
            cells.append(cell + "▀\x1b[0m")
        lines.append("  " + "".join(cells))
    return "\n".join(lines) + "\n"


def _preview_image(filepath: Path) -> str:
    """
    The real photo, drawn by the terminal with the iTerm2 inline image protocol.
    VS Code's terminal supports it when "terminal.integrated.enableImages" is on.
    """
    jpeg = _magick_thumbnail(filepath, "640x480", "jpg:-")
    payload = base64.b64encode(jpeg).decode("ascii")
    return (
        f"  \x1b]1337;File=inline=1;size={len(jpeg)};height={PREVIEW_ROWS};preserveAspectRatio=1:"
        f"{payload}\x07\n"
    )


def _terminal_attributes(in_fd: int, out_fd: int, timeout: float = 0.5) -> List[str]:
    """
    Ask the terminal what it supports (the "primary device attributes" query, which
    every terminal answers) and return the attribute codes from its reply, e.g.
    ["62", "4", "9", "22"]. Empty if it doesn't answer in time.
    """
    import termios
    import tty

    saved = termios.tcgetattr(in_fd)
    reply = b""
    try:
        tty.setcbreak(in_fd)  # Read the reply as it arrives, without echoing it
        os.write(out_fd, b"\x1b[c")
        deadline = datetime.datetime.now() + datetime.timedelta(seconds=timeout)
        while not reply.endswith(b"c"):
            remaining = (deadline - datetime.datetime.now()).total_seconds()
            if remaining <= 0 or not select.select([in_fd], [], [], remaining)[0]:
                break
            chunk = os.read(in_fd, 64)
            if not chunk:
                break
            reply += chunk
    finally:
        termios.tcsetattr(in_fd, termios.TCSADRAIN, saved)
    match = re.search(rb"\x1b\[\?([0-9;]*)c", reply)
    return match.group(1).decode("ascii").split(";") if match else []


def detect_preview_mode() -> str:
    """
    'image' if this terminal can draw inline images (see _preview_image), else 'blocks'.
    iTerm2 and WezTerm always can. VS Code can only with "terminal.integrated.enableImages"
    on, and then it reports graphics support (attribute 4) when asked, which is how the
    setting is detected from inside the dev container.
    """
    if os.environ.get("TERM_PROGRAM") in {"iTerm.app", "WezTerm"} or os.environ.get("LC_TERMINAL") == "iTerm2":
        return "image"
    in_vscode = os.environ.get("TERM_PROGRAM") == "vscode" or "VSCODE_IPC_HOOK_CLI" in os.environ
    if in_vscode and sys.stdin.isatty() and sys.stdout.isatty():
        try:
            if "4" in _terminal_attributes(sys.stdin.fileno(), sys.stdout.fileno()):
                return "image"
        except Exception:
            pass  # No termios (not Unix) or an odd terminal: blocks work anywhere
    return "blocks"


def show_preview(filepath: Path, mode: str) -> None:
    """Print a small preview of a staged photo. Never fatal: a failure only prints a dim note."""
    if mode == "off" or not sys.stdout.isatty():
        return
    try:
        rendered = _preview_image(filepath) if mode == "image" else _preview_blocks(filepath)
    except Exception as exc:
        console.print(f"  [dim]No preview ({type(exc).__name__}).[/dim]")
        return
    sys.stdout.write(rendered)
    sys.stdout.flush()


def prompt_note(species_name: str, existing_note: str) -> str:
    """
    Ask for the bird's note. A new bird (or one without a note) gets an optional
    note. When the photo being replaced has one, it can be retained, wiped, or
    swapped for a new one typed right here.
    """
    if existing_note:
        console.print(f"  [bold yellow]Existing note on {species_name}:[/bold yellow] \"{existing_note}\"")
        while True:
            action = prompt("  [r]etain it, [w]ipe it, or write a [n]ew note? [R/w/n]: ").strip().lower() or "r"
            if action in {"r", "retain"}:
                console.print("  [dim]Retained existing note.[/dim]")
                return existing_note
            if action in {"w", "wipe"}:
                console.print("  [dim]Wiped existing note.[/dim]")
                return ""
            if action in {"n", "new"}:
                break
            console.print("[red]  Type r, w or n.[/red]")
        note = prompt("  New note (Enter to leave it empty): ").strip()
        console.print("  [dim]Replaced the note.[/dim]" if note else "  [dim]Wiped existing note.[/dim]")
        return note
    return prompt(f"  Note for {species_name} (Enter for none): ").strip()


class CountyLocator:
    """Offline point-in-polygon resolver using US Census County GeoJSON and Shapely STRtree."""

    def __init__(self, geojson_path: Path) -> None:
        self.geojson_path = geojson_path
        self.polygons: List[Any] = []
        self.labels: List[str] = []
        self._tree: Any = None
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

        from shapely import STRtree
        from shapely.geometry import shape

        with open(self.geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for feat in data.get("features", []):
            geom = feat.get("geometry")
            props = feat.get("properties", {})
            label = props.get("county_state")
            if geom and label:
                self.polygons.append(shape(geom))
                self.labels.append(label)

        if self.polygons:
            self._tree = STRtree(self.polygons)

    def resolve(self, lat: Optional[float], lon: Optional[float]) -> Optional[str]:
        if lat is None or lon is None:
            return None
        self._ensure_loaded()
        if not self.polygons or self._tree is None:
            return None

        from shapely.geometry import Point

        pt = Point(float(lon), float(lat))
        # intersects matches both interior and exact boundary points
        hits = self._tree.query(pt, predicate="intersects")
        if len(hits) > 0:
            return self.labels[int(hits[0])]

        nearest_idx = int(self._tree.nearest(pt))
        if self.polygons[nearest_idx].distance(pt) < 0.15:
            return self.labels[nearest_idx]
        return None


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
        try:
            return bird_model.predict(self.model, self.preprocess, self.text_features, self.taxonomy_rows, image_path, k, self.allowed)
        except Exception as exc:
            console.print(f"  [yellow]AI couldn't read {image_path.name} ({exc}); falling back to fuzzy search.[/yellow]")
            return []


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
    fd, tmp_name = tempfile.mkstemp(dir=yaml_path.parent, prefix=f".{yaml_path.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
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
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, yaml_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def confirm_discard(filepath: Path) -> bool:
    """Confirm and delete a rejected photo from staging. Returns True if deleted."""
    confirm = prompt(f"  Delete {filepath.name} from staging? [y/N]: ").strip().lower()
    if confirm != "y":
        console.print("  [dim]Left in staging.[/dim]")
        return False
    try:
        filepath.unlink()
        console.print(f"  [dim]Discarded {filepath.name} from staging.[/dim]")
        return True
    except OSError as exc:
        console.print(f"  [red]Failed to delete {filepath.name}: {exc}[/red]")
        return False


def prompt_fuzzy_species(
    taxonomy_rows: List[Dict[str, Any]],
    existing_slugs: set,
    locked_slugs: Optional[set] = None,
    allow_discard: bool = False,
) -> Any:
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
    hint = "'s' to skip, 'd' to discard" if allow_discard else "'s' to skip"
    while True:
        user_input = prompt(
            f"  Fuzzy search species (type common name or 4-letter code, or {hint}): ",
            completer=completer,
        ).strip()
        if not user_input or user_input.lower() == "s":
            return None
        if allow_discard and user_input.lower() == "d":
            return _DISCARD
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
    """Write copyright tags into every photo already in the catalog, batched by year."""
    by_year: Dict[str, List[Path]] = defaultdict(list)
    for entry in catalog:
        photo = dest_dir / str(entry.get("filename", ""))
        if not photo.is_file():
            console.print(f"  [yellow]Missing photo for {entry.get('species_common')}: {photo.name}[/yellow]")
            continue
        year = str(entry.get("date_taken", ""))[:4]
        by_year[year].append(photo)
    stamped = 0
    for year, photos in sorted(by_year.items()):
        stamp_copyright(photos, year)
        stamped += len(photos)
    console.print(f"[bold green]Stamped copyright into {stamped} of {len(catalog)} photos.[/bold green]")


def seed_recent_locations(catalog: List[Dict[str, Any]]) -> List[str]:
    """Build recent location choices from the catalog's most recent entries, plus defaults."""
    seen: List[str] = []
    for entry in reversed(catalog):
        loc = str(entry.get("location") or "").strip()
        if loc and loc not in seen:
            seen.append(loc)
    for loc in DEFAULT_RECENT_LOCATIONS:
        if loc not in seen:
            seen.append(loc)
    return seen


def choose_species(
    predictions: List[Tuple[Dict[str, Any], float]],
    taxonomy_rows: List[Dict[str, Any]],
    by_slug: Dict[str, Dict[str, Any]],
    locked_slugs: set,
    auto: bool,
) -> Any:
    """Pick a species via --auto threshold, AI suggestions menu, or fuzzy search. Returns row, None, or _DISCARD."""
    if auto:
        if predictions and predictions[0][1] > AUTO_MIN_CONFIDENCE:
            chosen = predictions[0][0]
            console.print(f"  [bold green][AUTO][/bold green] Selected {chosen['common_name']} ({predictions[0][1]:.1f}%)")
            return chosen
        conf = predictions[0][1] if predictions else 0.0
        console.print(
            f"  [yellow][AUTO-SKIP][/yellow] Highest confidence {conf:.1f}% is not above "
            f"{AUTO_MIN_CONFIDENCE:.0f}%. Left in staging for a manual run."
        )
        return None

    if predictions:
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
        console.print("    [[bold red]s[/bold red]] Skip this image (leave in staging)")
        console.print("    [[bold magenta]d[/bold magenta]] Discard this image (delete from staging)")

        choice = prompt("  Select option [1/2/3/f/s/d, default: 1]: ").strip().lower() or "1"
        if choice in {"1", "2", "3"} and int(choice) <= len(predictions):
            return predictions[int(choice) - 1][0]
        if choice == "s":
            return None
        if choice == "d":
            return _DISCARD

    return prompt_fuzzy_species(taxonomy_rows, set(by_slug.keys()), locked_slugs, allow_discard=True)


def confirm_overwrite(
    species_name: str,
    existing_entry: Dict[str, Any],
    dest_path: Path,
    preview_mode: str,
) -> str:
    """Preview the existing catalog photo and ask whether to 'overwrite', 'skip', or 'discard'."""
    old_src = existing_entry.get("source_filename", "unknown")
    old_dt = existing_entry.get("date_taken", "unknown")
    console.print(
        f"  [bold yellow]Current catalog photo for {species_name}[/bold yellow] "
        f"[dim](from {old_src} on {old_dt}):[/dim]"
    )
    if dest_path.is_file():
        show_preview(dest_path, preview_mode)
    confirm = prompt(
        f"  Overwrite '{species_name}' with the new photo? "
        "[y]es, [N]o (keep staged), [d]iscard staged [y/N/d]: "
    ).strip().lower()
    if confirm == "y":
        return "overwrite"
    if confirm == "d":
        return "discard"
    return "skip"


def resolve_location(
    exif: Dict[str, Any],
    locator: CountyLocator,
    recent_locations: List[str],
    auto: bool,
) -> Optional[str]:
    """Resolve county/state offline via GPS, or prompt interactively when GPS is absent/outside US."""
    lat = exif.get("GPSLatitude")
    lon = exif.get("GPSLongitude")
    county_state = locator.resolve(lat, lon)
    if county_state:
        console.print(f"  [dim]Offline GPS County Match:[/dim] [bold green]{county_state}[/bold green]")
        return county_state
    if auto:
        console.print("  [yellow][AUTO-SKIP][/yellow] No GPS location in the photo. Left in staging for a manual run.")
        return None

    if lat is not None and lon is not None:
        console.print(
            f"  [yellow]GPS ({float(lat):.4f}, {float(lon):.4f}) is outside US county boundaries.[/yellow]"
        )
    else:
        console.print("  [yellow]No GPS coordinates found in EXIF.[/yellow]")
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
    return county_state


def import_single_photo(
    idx: int,
    total: int,
    filepath: Path,
    *,
    args: argparse.Namespace,
    taxonomy_rows: List[Dict[str, Any]],
    catalog: List[Dict[str, Any]],
    by_slug: Dict[str, Dict[str, Any]],
    known_sources: Dict[str, str],
    locked_slugs: set,
    locator: CountyLocator,
    classifier: OfflineBirdClassifier,
    recent_locations: List[str],
    preview_mode: str,
) -> bool:
    """Process one staged photo. Mutates catalog/indexes in place and returns True if imported."""
    filepath = sanitize_staged_filename(filepath)

    exif = extract_exif(filepath)
    iso_dt, from_exif = extract_timestamp(exif, filepath)
    source_id = build_source_id(filepath, iso_dt)

    if source_id in known_sources and not args.force:
        console.print(
            f"[yellow][SKIP] [{idx}/{total}] {filepath.name} "
            f"already imported as {known_sources[source_id]} ({source_id})[/yellow]"
        )
        return False

    console.rule(f"[bold cyan]File [{idx}/{total}]: {filepath.name}[/bold cyan]")
    collage = is_collage(filepath)
    if collage:
        captured_note = "  [yellow](collage: when it was made; you'll be asked for the real date)[/yellow]"
    elif not from_exif:
        captured_note = "  [bold yellow](NO EXIF DATE — file modified time!)[/bold yellow]"
    else:
        captured_note = ""
    console.print(f"  [dim]Captured:[/dim] {iso_dt}{captured_note}   [dim]Source ID:[/dim] {source_id}")

    if collage and args.auto:
        console.print(
            "  [yellow][AUTO-SKIP][/yellow] Collages need their real date typed in. Left in staging for a manual run."
        )
        return False
    if not from_exif and args.auto:
        console.print(
            "  [yellow][AUTO-SKIP][/yellow] Photo has no EXIF capture date (only file modified time). "
            "Left in staging for a manual run."
        )
        return False

    if not args.auto:
        show_preview(filepath, preview_mode)

    predictions = classifier.predict_top_k(filepath, k=3)
    chosen_species = choose_species(predictions, taxonomy_rows, by_slug, locked_slugs, args.auto)
    if chosen_species is _DISCARD:
        confirm_discard(filepath)
        return False
    if not chosen_species:
        if not args.auto:
            console.print("  [dim]Skipped.[/dim]")
        return False

    slug = slugify(chosen_species["common_name"])
    dest_filename = f"{slug}.webp"
    dest_path = args.dest / dest_filename
    existing_entry = by_slug.get(slug)

    if existing_entry and existing_entry.get("locked"):
        console.print(
            f"  [bold red]WARNING: {chosen_species['common_name']} is locked, so this photo can't replace it.[/bold red]\n"
            f"  [yellow]Its entry in {display_path(args.yaml)} has 'locked: true', which holds the current photo "
            f"({existing_entry.get('source_filename', 'unknown')}, taken {existing_entry.get('date_taken', 'unknown')}) in place.\n"
            f"  {filepath.name} was left in {display_path(args.staging)}/ untouched. To replace the photo, remove "
            f"'locked: true' from that entry (or set it to false) and run the import again.[/yellow]"
        )
        return False

    if existing_entry and args.auto:
        console.print(
            f"  [yellow][AUTO-SKIP][/yellow] {chosen_species['common_name']} is already in the catalog. "
            "Auto mode never replaces a photo; left in staging for a manual run."
        )
        return False

    if existing_entry:
        decision = confirm_overwrite(chosen_species["common_name"], existing_entry, dest_path, preview_mode)
        if decision == "discard":
            confirm_discard(filepath)
            return False
        if decision != "overwrite":
            console.print("  [dim]Kept existing photo. Skipping.[/dim]")
            return False

    # source_id keeps the original/fallback timestamp so the same file stays recognised on later runs
    if collage:
        iso_dt = prompt_collage_timestamp(filepath, iso_dt)
        if not iso_dt:
            console.print("  [dim]Skipped.[/dim]")
            return False
    elif not from_exif:
        iso_dt = prompt_missing_exif_timestamp(filepath, iso_dt)
        if not iso_dt:
            console.print("  [dim]Skipped.[/dim]")
            return False

    county_state = resolve_location(exif, locator, recent_locations, args.auto)
    if not county_state:
        return False

    note = ""
    if not args.auto:
        existing_note = str(existing_entry.get("notes", "") or "").strip() if existing_entry else ""
        note = prompt_note(chosen_species["common_name"], existing_note)

    console.print(
        f"  [dim]Generating sRGB WebP (<=800px) and stripping metadata -> {display_path(dest_path)}[/dim]"
    )
    try:
        process_image_to_webp(filepath, dest_path, year=iso_dt[:4])
    except (subprocess.CalledProcessError, OSError) as exc:
        console.print(
            f"  [bold red]Failed to convert {filepath.name} ({exc}). Left in staging.[/bold red]"
        )
        return False

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
        "notes": note,
        "source_filename": filepath.name,
        "source_id": source_id,
    }

    if existing_entry:
        known_sources.pop(existing_entry.get("source_id", ""), None)
        catalog[:] = [e for e in catalog if e.get("slug") != slug]
    catalog.append(new_entry)
    by_slug[slug] = new_entry
    known_sources[source_id] = chosen_species["common_name"]

    save_catalog(args.yaml, catalog)
    console.print(f"  [bold green]Saved {chosen_species['common_name']} ({dest_filename})[/bold green]")

    try:
        filepath.unlink()
        console.print("  [dim]Removed original file from staging.[/dim]")
    except Exception as e:
        console.print(f"  [red]Failed to remove original file: {e}[/red]")
    return True


def main() -> None:
    if hasattr(signal, "SIGHUP"):
        # Ensure closing a terminal tab kills this process instead of leaving a ~1.5 GB model in RAM
        signal.signal(signal.SIGHUP, signal.SIG_DFL)

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
    parser.add_argument("--preview", choices=PREVIEW_MODES, default=os.environ.get("BIRDS_PREVIEW", "auto"),
                        help="Terminal preview of each photo: 'auto' (the real photo if the terminal can draw it, else blocks), "
                             "'image' (the real photo; in VS Code needs the terminal.integrated.enableImages setting), "
                             "'blocks' (colored characters, works anywhere) or 'off'. Default: auto, or $BIRDS_PREVIEW")
    parser.add_argument("--stamp-copyright", action="store_true", help="Write copyright tags into every photo already imported, then exit")
    parser.add_argument("--backfill-ebird-codes", action="store_true", help="Add eBird species codes to every bird already imported, then exit")
    args = parser.parse_args()
    if args.preview not in PREVIEW_MODES:  # A mistyped $BIRDS_PREVIEW
        parser.error(f"BIRDS_PREVIEW must be one of: {', '.join(PREVIEW_MODES)}")

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

    preview_mode = args.preview
    if preview_mode == "auto" and not args.auto:
        preview_mode = detect_preview_mode()
        if preview_mode == "blocks" and os.environ.get("TERM_PROGRAM") == "vscode":
            console.print(
                "[dim]Previews are colored blocks. For real photos, turn on VS Code's "
                "\"terminal.integrated.enableImages\" setting.[/dim]"
            )

    recent_locations = seed_recent_locations(catalog)
    modified_count = 0

    try:
        for idx, filepath in enumerate(staged_files, start=1):
            imported = import_single_photo(
                idx,
                len(staged_files),
                filepath,
                args=args,
                taxonomy_rows=taxonomy_rows,
                catalog=catalog,
                by_slug=by_slug,
                known_sources=known_sources,
                locked_slugs=locked_slugs,
                locator=locator,
                classifier=classifier,
                recent_locations=recent_locations,
                preview_mode=preview_mode,
            )
            if imported:
                modified_count += 1
    except (KeyboardInterrupt, EOFError):
        console.print(
            f"\n[yellow]Interrupted. Already saved {modified_count} photo(s) to {display_path(args.yaml)}; "
            "remaining files were left in staging.[/yellow]"
        )
        return

    console.rule("[bold green]Import Complete[/bold green]")
    console.print(f"Processed and updated [bold]{modified_count}[/bold] photo(s) in {args.yaml}.")


if __name__ == "__main__":
    main()