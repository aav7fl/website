"""
Shared, standard-library-only utilities for the bird portfolio pipeline.

Kept free of third-party imports at module top level so doctor.py (which must run
even when the venv is broken) and the unit test suite (which runs in CI without
installing pip packages) can import everything here directly.
"""

import csv
import datetime
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]

DEFAULT_STAGING_DIR = REPO_ROOT / "_staging"
DEFAULT_DEST_DIR = REPO_ROOT / "assets" / "img" / "birds"
DEFAULT_YAML_PATH = REPO_ROOT / "_data" / "birds.yml"
TAXONOMY_CSV_PATH = SCRIPT_DIR / "taxonomy_sibley.csv"
GEOJSON_PATH = SCRIPT_DIR / "us_counties.geojson"

# Embedded in every exported photo. The photos are all rights reserved
# (see assets/img/birds/LICENSE.txt), unlike the MIT-licensed code.
COPYRIGHT_HOLDER = "Kyle Niewiada"
COPYRIGHT_LICENSE_URL = "https://www.kyleniewiada.org/assets/img/birds/LICENSE.txt"

# Google Photos names the collages it makes like 20261023_142445-COLLAGE.jpg.
COLLAGE_NAME_RE = re.compile(r"-COLLAGE\b", re.IGNORECASE)

# Locale-independent English month names for parse_user_timestamp
_MONTH_NAMES = (
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
)


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


def is_collage(filepath: Union[Path, str]) -> bool:
    stem = filepath.stem if isinstance(filepath, Path) else Path(filepath).stem
    return bool(COLLAGE_NAME_RE.search(stem))


def norm_pkg_name(name: str) -> str:
    """PEP 503 normalised package name (e.g. PyYAML -> pyyaml, prompt_toolkit -> prompt-toolkit)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_requirements_pins(path: Path) -> Dict[str, str]:
    """{normalised name: version} from a requirements file's `name==version` lines."""
    found: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*([A-Za-z0-9_.\-]+)==([^\s#]+)", line)
        if match:
            found[norm_pkg_name(match.group(1))] = match.group(2)
    return found


def parse_requirements_in(path: Path, normalize: bool = True) -> List[str]:
    """Direct package names listed in a requirements.in file."""
    names: List[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line and not line.startswith("-"):
            raw = re.split(r"[\s<>=!~\[;]", line, maxsplit=1)[0]
            names.append(norm_pkg_name(raw) if normalize else raw)
    return names


def load_taxonomy(csv_path: Path = TAXONOMY_CSV_PATH) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["sibley_category_order"] = int(row["sibley_category_order"])
            row["taxonomic_order"] = int(row["taxonomic_order"])
            rows.append(row)
    return rows


def compute_sha256_prefix(filepath: Path, length: int = 8) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()[:length]


def build_source_id(filepath: Path, iso_timestamp: str) -> str:
    compact_ts = re.sub(r"[^0-9T]", "", iso_timestamp)
    sha_prefix = compute_sha256_prefix(filepath, 8)
    return f"{filepath.name}_{compact_ts}_{sha_prefix}"


def extract_timestamp(exif: Dict[str, Any], filepath: Path) -> Tuple[str, bool]:
    """
    Return (ISO-8601 timestamp YYYY-MM-DDTHH:MM:SS, from_exif).
    from_exif is True when the date came from EXIF tags, False when it fell back to file mtime.
    """
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
            return f"{y}-{m}-{d}T{hh}:{mm}:{ss}", True

    mtime = datetime.datetime.fromtimestamp(filepath.stat().st_mtime)
    return mtime.strftime("%Y-%m-%dT%H:%M:%S"), False


def normalize_timestamp(exif: Dict[str, Any], filepath: Path) -> str:
    """Return ISO-8601 timestamp YYYY-MM-DDTHH:MM:SS from EXIF or file mtime."""
    return extract_timestamp(exif, filepath)[0]


def parse_user_timestamp(text: str) -> Optional[str]:
    """
    Parse a typed date and time into YYYY-MM-DDTHH:MM:SS, or None if it isn't one.
    Accepts 24-hour or am/pm times, with or without seconds, e.g.
    "2025-04-12 09:09", "2025-04-12 9:09 am", "2025-04-12T21:09:30", and the
    style of the collage captions in Google Photos: "October 23, 2026 @ 1:16 PM"
    (month names may be abbreviated, and "at" works in place of "@").
    """
    time_part = r"(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([ap]\.?m\.?)?"
    numeric = re.fullmatch(r"\s*(\d{4})-(\d{1,2})-(\d{1,2})[ T]+" + time_part + r"\s*", text, re.IGNORECASE)
    written = re.fullmatch(r"\s*([a-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})\s*(?:@|at|,|•|-)?\s*" + time_part + r"\s*", text, re.IGNORECASE)
    if numeric:
        year, month, day, hour, minute, second, meridiem = numeric.groups()
    elif written:
        month_name, day, year, hour, minute, second, meridiem = written.groups()
        # Full names, or abbreviations of at least three letters ("Oct", "Sept")
        month = next(
            (i for i, name in enumerate(_MONTH_NAMES, start=1)
             if len(month_name) >= 3 and name.startswith(month_name.lower())),
            None,
        )
        if not month:
            return None
    else:
        return None
    hour = int(hour)
    if meridiem:
        if not 1 <= hour <= 12:
            return None
        hour = hour % 12 + (12 if meridiem.lower().startswith("p") else 0)
    try:
        parsed = datetime.datetime(int(year), int(month), int(day), hour, int(minute), int(second or 0))
    except ValueError:
        return None
    return parsed.strftime("%Y-%m-%dT%H:%M:%S")


def sanitize_staged_filename(filepath: Path) -> Path:
    """
    ImageMagick interprets square brackets as frame modifiers; strip them safely
    without overwriting another file that already has the cleaned name.
    """
    if "[" not in filepath.name and "]" not in filepath.name:
        return filepath
    clean_name = filepath.name.replace("[", "").replace("]", "")
    candidate = filepath.with_name(clean_name)
    counter = 1
    while candidate.exists() and candidate != filepath:
        candidate = filepath.with_name(f"{Path(clean_name).stem}_{counter}{Path(clean_name).suffix}")
        counter += 1
    filepath.rename(candidate)
    return candidate


def _srgb_icc_bytes() -> Optional[bytes]:
    """Standard sRGB ICC profile bytes via Pillow's built-in ImageCms (OS-independent)."""
    try:
        from PIL import ImageCms

        return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    except Exception:
        return None


def stamp_copyright(dest_paths: Union[Path, Sequence[Path]], year: str, strip_all: bool = False) -> None:
    """
    Write copyright tags into one or more exported WebPs: EXIF Artist/Copyright plus
    the XMP fields (dc:creator, dc:rights, xmpRights:Marked/WebStatement) that image
    search and photo apps read. When strip_all=True, strips every existing metadata
    tag in the same exiftool invocation before writing only copyright tags.
    Compact XMP keeps this to under 1 KB per photo (default padding adds ~3 KB).
    """
    paths = [dest_paths] if isinstance(dest_paths, Path) else list(dest_paths)
    if not paths:
        return
    notice = f"© {year} {COPYRIGHT_HOLDER}. All rights reserved."
    cmd_exif = [
        "exiftool",
        "-overwrite_original",
    ]
    if strip_all:
        cmd_exif.append("-all=")
    cmd_exif.extend([
        "-api",
        "Compact=All",
        f"-EXIF:Artist={COPYRIGHT_HOLDER}",
        f"-EXIF:Copyright={notice}",
        f"-XMP-dc:Creator={COPYRIGHT_HOLDER}",
        f"-XMP-dc:Rights={notice}",
        "-XMP-xmpRights:Marked=True",
        f"-XMP-xmpRights:WebStatement={COPYRIGHT_LICENSE_URL}",
        *(str(p) for p in paths),
    ])
    subprocess.run(cmd_exif, capture_output=True, check=True)


def process_image_to_webp(src_path: Path, dest_path: Path, year: str, width: int = 800, quality: int = 84) -> None:
    """
    Orient upright, convert wide-gamut ICC profiles (e.g. Display P3, Adobe RGB) to sRGB,
    shrink images wider than `width` px without upscaling smaller crops, sharpen subtly,
    strip all metadata & color profiles, and write back only copyright tags in a single
    exiftool pass. Writes atomically via a temp file so dest_path is never left corrupt.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    magick_bin = "magick" if shutil.which("magick") else "convert"

    fd, tmp_name = tempfile.mkstemp(dir=dest_path.parent, prefix=f".{dest_path.stem}.", suffix=".webp")
    os.close(fd)
    tmp_path = Path(tmp_name)
    icc_path: Optional[Path] = None

    try:
        cmd_magick = [
            magick_bin,
            f"{src_path.resolve()}[0]",  # First frame only (multi-image HEIC/TIFF/motion photos)
            "-auto-orient",
        ]
        srgb_bytes = _srgb_icc_bytes()
        if srgb_bytes:
            icc_fd, icc_name = tempfile.mkstemp(prefix=".srgb-", suffix=".icc")
            with os.fdopen(icc_fd, "wb") as f:
                f.write(srgb_bytes)
            icc_path = Path(icc_name)
            cmd_magick.extend(["-profile", str(icc_path)])
        cmd_magick.extend([
            "-colorspace",
            "sRGB",
            "-filter",
            "Lanczos",
            "-resize",
            f"{width}x>",  # Never upscale small crops narrower than `width`
            "-unsharp",
            "0x0.75+0.75+0.008",
            "-strip",
            "-quality",
            str(quality),
            str(tmp_path),
        ])
        subprocess.run(cmd_magick, check=True)

        # Single exiftool pass: strip any residual metadata and write back only copyright tags
        stamp_copyright(tmp_path, year, strip_all=True)
        os.replace(tmp_path, dest_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    finally:
        if icc_path is not None:
            icc_path.unlink(missing_ok=True)
