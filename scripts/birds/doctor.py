#!/usr/bin/env python3
"""
Health check for the bird pipeline: `rake birds:doctor`.

Checks every dependency the import relies on and prints what's wrong and how to
fix it. Written with only the standard library for its own checks, so it still
runs (and explains) when packages are broken. Exits non-zero if imports can't run;
a broken AI setup is reported but doesn't fail, since imports work without it.
"""

import argparse
import csv
import datetime
import json
import re
import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import bird_common

OK, FAIL, WARN = "✓", "✗", "!"
core_ok = True
ai_ok = True

_ISO_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


def report(status: str, message: str, fix: str = "", ai: bool = False) -> None:
    global core_ok, ai_ok
    print(f"  {status} {message}")
    if fix:
        print(f"      fix: {fix}")
    if status == FAIL:
        if ai:
            ai_ok = False
        else:
            core_ok = False


def _preview_list(items: List[str], limit: int = 5) -> str:
    return ", ".join(items[:limit]) + (", ..." if len(items) > limit else "")


pins = bird_common.parse_requirements_pins
in_names = bird_common.parse_requirements_in


def audit_catalog_integrity(catalog: List[Dict[str, Any]], photos_dir: Path) -> Dict[str, List[str]]:
    """
    Pure integrity audit of catalog entries against photos_dir.
    Returns lists of issues for missing_photos, orphan_photos, duplicates,
    invalid_dates, missing_locations, and slug_mismatches.
    """
    missing_photos: List[str] = []
    seen_missing: set = set()
    referenced_filenames: set = set()
    duplicates: List[str] = []
    seen_field_values: Dict[str, set] = {
        "slug": set(),
        "filename": set(),
        "source_id": set(),
        "species_common": set(),
    }
    recorded_duplicates: set = set()
    invalid_dates: List[str] = []
    missing_locations: List[str] = []
    slug_mismatches: List[str] = []

    now = datetime.datetime.now()

    for entry in catalog:
        label = str(entry.get("species_common") or entry.get("slug") or "?")

        # Missing photo files
        fname = str(entry.get("filename") or "").strip()
        if fname:
            referenced_filenames.add(fname)
            if not (photos_dir / fname).is_file() and fname not in seen_missing:
                missing_photos.append(fname)
                seen_missing.add(fname)
        else:
            marker = f"<missing filename: {label}>"
            if marker not in seen_missing:
                missing_photos.append(marker)
                seen_missing.add(marker)

        # Duplicates across key identifying fields
        for field, seen in seen_field_values.items():
            val = str(entry.get(field) or "").strip()
            if not val:
                continue
            if val in seen:
                dup_label = f"{field}: {val}"
                if dup_label not in recorded_duplicates:
                    duplicates.append(dup_label)
                    recorded_duplicates.add(dup_label)
            else:
                seen.add(val)

        # Date validation: exact YYYY-MM-DDTHH:MM:SS and not in the future
        raw_date = entry.get("date_taken")
        if not isinstance(raw_date, str) or not _ISO_TIMESTAMP_RE.match(raw_date):
            invalid_dates.append(f"{label}: {raw_date!r}")
        else:
            try:
                parsed = datetime.datetime.strptime(raw_date, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                invalid_dates.append(f"{label}: {raw_date!r}")
            else:
                if parsed > now:
                    invalid_dates.append(f"{label}: {raw_date} (future)")

        # Missing location
        if not str(entry.get("location") or "").strip():
            missing_locations.append(label)

        # Slug vs species_common consistency
        common = str(entry.get("species_common") or "")
        slug = str(entry.get("slug") or "")
        expected_slug = bird_common.slugify(common)
        if slug != expected_slug:
            slug_mismatches.append(f"{common}: {slug!r} (expected {expected_slug!r})")

    orphan_photos: List[str] = []
    if photos_dir.is_dir():
        orphan_photos = sorted(
            p.name
            for p in photos_dir.glob("*.webp")
            if p.is_file() and p.name not in referenced_filenames
        )

    return {
        "missing_photos": missing_photos,
        "orphan_photos": orphan_photos,
        "duplicates": duplicates,
        "invalid_dates": invalid_dates,
        "missing_locations": missing_locations,
        "slug_mismatches": slug_mismatches,
    }


def audit_photo_metadata(photos_dir: Path) -> Tuple[List[str], List[str]]:
    """
    Runs one batched exiftool call across all *.webp files in photos_dir.
    Returns (gps_leaks, missing_copyright) as sorted lists of filenames.
    Returns ([], []) if exiftool isn't installed or there are no .webp files.
    """
    if not shutil.which("exiftool") or not photos_dir.is_dir():
        return [], []
    webps = sorted(p for p in photos_dir.glob("*.webp") if p.is_file())
    if not webps:
        return [], []

    cmd = [
        "exiftool",
        "-j",
        "-FileName",
        "-GPSLatitude",
        "-GPSLongitude",
        "-EXIF:Copyright",
        "-XMP-dc:Rights",
        *(str(p) for p in webps),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if not res.stdout.strip():
        return [], []
    try:
        records = json.loads(res.stdout)
    except json.JSONDecodeError:
        return [], []

    gps_leaks: List[str] = []
    missing_copyright: List[str] = []
    for rec in records:
        name = rec.get("FileName") or Path(rec.get("SourceFile", "")).name
        if rec.get("GPSLatitude") not in (None, "") or rec.get("GPSLongitude") not in (None, ""):
            gps_leaks.append(name)
        has_exif_copy = bool(str(rec.get("Copyright") or "").strip())
        has_xmp_rights = bool(str(rec.get("Rights") or "").strip())
        if not (has_exif_copy and has_xmp_rights):
            missing_copyright.append(name)

    return sorted(gps_leaks), sorted(missing_copyright)


def check_packages(path: Path, ai: bool, check_in: bool = False) -> None:
    label = path.name
    fix = f"/opt/venv-birds/bin/pip install -r scripts/birds/{label}  (or rebuild the dev container)"
    if check_in:
        names = in_names(path)
        missing = []
        for name in names:
            try:
                metadata.version(name)
            except metadata.PackageNotFoundError:
                missing.append(name)
        if missing:
            report(FAIL, f"{label}: not installed: {', '.join(missing)}", fix, ai=ai)
        else:
            report(OK, f"{label}: all {len(names)} direct packages installed")
        return

    missing, drift = [], []
    pinned = pins(path)
    for name, wanted in pinned.items():
        try:
            have = metadata.version(name)
        except metadata.PackageNotFoundError:
            missing.append(name)
            continue
        if have != wanted:
            drift.append(f"{name} {have} (pinned {wanted})")
    if missing:
        report(FAIL, f"{label}: not installed: {', '.join(missing)}", fix, ai=ai)
    elif drift:
        report(WARN, f"{label}: versions differ from the pins: {', '.join(drift)}", fix)
    else:
        report(OK, f"{label}: all {len(pinned)} packages installed at their pinned versions")


def tool_version(cmd: List[str]) -> Tuple[bool, str]:
    if not shutil.which(cmd[0]):
        return False, ""
    out = subprocess.run(cmd, capture_output=True, text=True)
    return out.returncode == 0, (out.stdout or out.stderr).strip().splitlines()[0] if (out.stdout or out.stderr) else ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Check the bird pipeline's dependencies.")
    parser.add_argument("--require-ai", action="store_true", help="Also fail (exit 1) if AI suggestions aren't ready (used by update_deps.py)")
    parser.add_argument("--check-in", action="store_true", help="Check direct packages from requirements*.in instead of exact lock pins (used by update_deps.py)")
    args = parser.parse_args()

    print("System tools")
    found, version = tool_version(["exiftool", "-ver"])
    report(OK if found else FAIL, f"exiftool {version}" if found else "exiftool not found",
           "" if found else "apt-get install libimage-exiftool-perl (or rebuild the dev container)")
    magick = "magick" if shutil.which("magick") else "convert"
    found, version = tool_version([magick, "-version"])
    report(OK if found else FAIL, f"ImageMagick: {version}" if found else "ImageMagick not found",
           "" if found else "apt-get install imagemagick (or rebuild the dev container)")
    print(f"  {OK} Python {sys.version.split()[0]} ({sys.executable})")

    print("\nPython packages")
    if args.check_in:
        check_packages(SCRIPT_DIR / "requirements.in", ai=False, check_in=True)
        check_packages(SCRIPT_DIR / "requirements-ai.in", ai=True, check_in=True)
    else:
        check_packages(SCRIPT_DIR / "requirements.txt", ai=False)
        check_packages(SCRIPT_DIR / "requirements-ai.txt", ai=True)

    try:
        import update_deps
        state = update_deps.read_state()
        line = f"Last automatic update check: {update_deps.status_line()}"
        if state.get("result") == "failed":
            report(WARN, line, f"see scripts/birds/.deps-update.log; it retries automatically in {update_deps.RETRY_FAILED_DAYS} days")
        else:
            print(f"  {OK} {line}")
    except Exception:
        pass

    print("\nData")
    geojson = SCRIPT_DIR / "us_counties.geojson"
    try:
        features = json.loads(geojson.read_text(encoding="utf-8"))["features"]
        named = sum(1 for f in features if f.get("properties", {}).get("county_state"))
        report(OK if named == len(features) else FAIL, f"County boundaries: {len(features)} counties",
               "" if named == len(features) else "git checkout scripts/birds/us_counties.geojson")
    except Exception as exc:
        report(FAIL, f"County boundaries unreadable ({exc})",
               "git checkout scripts/birds/us_counties.geojson, or rake birds:setup -- --refresh-counties")

    taxonomy = SCRIPT_DIR / "taxonomy_sibley.csv"
    try:
        with open(taxonomy, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        coded = sum(1 for r in rows if r.get("ebird_code"))
        report(OK, f"Taxonomy: {len(rows)} species, {coded} with eBird codes")
        if coded < len(rows):
            report(WARN, f"{len(rows) - coded} species have no eBird code", "rake birds:setup")
    except Exception as exc:
        rows = []
        report(FAIL, f"Taxonomy unreadable ({exc})", "git checkout scripts/birds/taxonomy_sibley.csv")

    catalog = []
    photos = REPO_ROOT / "assets" / "img" / "birds"
    try:
        import yaml
        catalog = yaml.safe_load((REPO_ROOT / "_data" / "birds.yml").read_text(encoding="utf-8")) or []
        integrity = audit_catalog_integrity(catalog, photos)
        missing = integrity["missing_photos"]
        locked = sum(1 for b in catalog if b.get("locked"))
        report(
            OK if not missing else FAIL,
            f"Catalog: {len(catalog)} birds"
            + (f", {locked} locked" if locked else "")
            + (f"; missing photos: {_preview_list(missing)}" if missing else ", every photo present"),
            "" if not missing else "restore the missing files in assets/img/birds/ from git",
        )
        if integrity["duplicates"]:
            report(
                FAIL,
                f"Catalog duplicates ({len(integrity['duplicates'])}): {_preview_list(integrity['duplicates'])}",
                "deduplicate the conflicting entries in _data/birds.yml",
            )
        if integrity["orphan_photos"]:
            report(
                WARN,
                f"{len(integrity['orphan_photos'])} orphan photo(s) not in catalog: {_preview_list(integrity['orphan_photos'])}",
                "remove unused .webp files from assets/img/birds/ or add them to _data/birds.yml",
            )
        if integrity["invalid_dates"]:
            report(
                WARN,
                f"{len(integrity['invalid_dates'])} bird(s) with invalid or future date_taken: {_preview_list(integrity['invalid_dates'])}",
                "fix date_taken (YYYY-MM-DDTHH:MM:SS) in _data/birds.yml",
            )
        if integrity["missing_locations"]:
            report(
                WARN,
                f"{len(integrity['missing_locations'])} bird(s) missing location: {_preview_list(integrity['missing_locations'])}",
                "fill in location in _data/birds.yml",
            )
        if integrity["slug_mismatches"]:
            report(
                WARN,
                f"{len(integrity['slug_mismatches'])} bird(s) with slug mismatch: {_preview_list(integrity['slug_mismatches'])}",
                "update slug (and photo filename if needed) in _data/birds.yml, or run rake birds:migrate_taxonomy",
            )
        if not any(integrity.values()):
            report(OK, "Catalog integrity: no duplicates, orphans, bad dates, missing locations, or slug mismatches")

        by_code = {r["ebird_code"]: r for r in rows if r.get("ebird_code")}
        stale = []
        for b in catalog:
            row = by_code.get(b.get("ebird_code"))
            if not row or any(str(b.get(k)) != str(row.get(v)) for k, v in (
                    ("species_common", "common_name"), ("species_scientific", "scientific_name"),
                    ("banding_code", "banding_code"), ("taxonomic_order", "taxonomic_order"))):
                stale.append(b.get("species_common", "?"))
        if rows and stale:
            report(WARN, f"{len(stale)} bird(s) don't match the taxonomy (renamed, split or re-ordered): "
                   + _preview_list(stale),
                   "rake birds:migrate_taxonomy")
        elif rows:
            report(OK, "Every bird matches the taxonomy")
    except Exception as exc:
        report(FAIL, f"Catalog unreadable ({exc})", "check _data/birds.yml for YAML errors")

    if shutil.which("exiftool") and photos.is_dir():
        webp_count = sum(1 for p in photos.glob("*.webp") if p.is_file())
        if webp_count:
            gps_leaks, missing_copyright = audit_photo_metadata(photos)
            if gps_leaks:
                report(
                    FAIL,
                    f"Metadata audit: GPS tags found in {len(gps_leaks)} photo(s): {_preview_list(gps_leaks)}",
                    "strip GPS metadata with exiftool -overwrite_original -GPS:all= assets/img/birds/<file> (or re-import)",
                )
            if missing_copyright:
                report(
                    WARN,
                    f"Metadata audit: {len(missing_copyright)} photo(s) missing copyright tags: {_preview_list(missing_copyright)}",
                    "rake birds:copyright",
                )
            if not gps_leaks and not missing_copyright:
                report(OK, f"Metadata audit: {webp_count} photos checked, zero GPS tags, all copyright-stamped")
            elif not gps_leaks:
                report(OK, f"Metadata audit: {webp_count} photos checked, zero GPS tags")

    print("\nAI suggestions (optional)")
    try:
        import bird_model
    except Exception as exc:
        report(FAIL, f"bird_model.py won't load ({exc})", "", ai=True)
    else:
        print(f"  {OK} Pinned model: {bird_model.MODEL_REPO} @ {bird_model.MODEL_REVISION[:12]}")
        problems = bird_model.verify_model()
        if problems:
            report(FAIL, "Model files: " + "; ".join(problems), "rake birds:setup", ai=True)
        else:
            report(OK, f"Model files present and match model-checksums.txt ({bird_model.MODEL_DIR})")
            smoke_test(bird_model, rows, catalog)
        if bird_model.aba_codes():
            allowed, scope = bird_model.allowed_species(rows) if rows else (None, "")
            report(OK, f"ABA checklist {bird_model.aba_version()}: AI suggests {scope.split(' (')[0]} by default")
        else:
            report(WARN, "ABA checklist missing: AI suggestions consider every species (less accurate)", "rake birds:setup")

    print()
    print(f"Imports: {'ready' if core_ok else 'NOT ready (fix the ✗ items above)'}")
    print(f"AI suggestions: {'ready' if ai_ok else 'unavailable (imports still work with fuzzy search)'}")
    sys.exit(0 if core_ok and (ai_ok or not args.require_ai) else 1)


def smoke_test(bird_model, rows, catalog) -> None:
    """Loads the model and checks it recognises one known single photo from the catalog."""
    try:
        import torch  # noqa: F401  (fail early with a clear message if torch is broken)
        model, preprocess, tokenizer = bird_model.load_model()
        report(OK, "Model loads")
    except Exception as exc:
        report(FAIL, f"Model won't load ({exc})", "rake birds:doctor after rebuilding the dev container; "
               "if it persists run rake birds:update_deps; see 'Staying up to date (automatic)' in scripts/birds/README.md", ai=True)
        return

    if bird_model.embeddings_cache_valid(rows):
        report(OK, "Species embeddings cached for this model and taxonomy")
    else:
        report(WARN, "Species embeddings missing or stale (rebuilt automatically, ~1 min)", "rake birds:setup")

    sample = next((b for b in catalog if not bird_common.is_collage(str(b.get("source_filename", "")))), None)
    if not sample or not rows:
        return
    embeddings = bird_model.text_embeddings(model, tokenizer, rows, cache_key=bird_model.MODEL_REVISION)
    photo = REPO_ROOT / "assets" / "img" / "birds" / sample["filename"]
    allowed, _ = bird_model.allowed_species(rows, always_include=[b.get("species_common", "") for b in catalog])
    top = bird_model.predict(model, preprocess, embeddings, rows, photo, k=3, allowed=allowed)
    guesses = [r["common_name"] for r, _ in top]
    if sample["species_common"] in guesses:
        rank = guesses.index(sample["species_common"]) + 1
        report(OK, f"Recognises a known photo: {sample['species_common']} is suggestion #{rank} of 3"
               + ("" if rank == 1 else f" (top suggestion: {guesses[0]}, {top[0][1]:.0f}%)"))
    else:
        report(WARN, f"Didn't recognise a known photo: {sample['species_common']} → {', '.join(guesses)}",
               "rake birds:evaluate, to see whether accuracy has dropped overall")


if __name__ == "__main__":
    main()
