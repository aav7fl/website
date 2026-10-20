#!/usr/bin/env python3
"""
Setup for the Bird Portfolio Pipeline. Safe to re-run; it only fetches what's missing.
1. US county boundaries (us_counties.geojson) are committed to the repo. Rebuilt from
   the US Census-derived source only with --refresh-counties.
2. Taxonomy (taxonomy_sibley.csv) is committed. Rebuilt from eBird only if missing or
   with --force, and older files get their eBird codes filled in.
3. The AI model (optional): the pinned BioCLIP revision is downloaded once into
   scripts/birds/models/ and verified against model-checksums.txt (see bird_model.py),
   then the species text embeddings are pre-computed.
Run `rake birds:doctor` afterwards to check everything.
"""

import argparse
import csv
import io
import json
import re
import urllib.request
import zipfile
from typing import Dict, List
from pathlib import Path

import bird_model  # The pinned, local AI model

FIPS_TO_STATE = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT",
    "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL",
    "18": "IN", "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD",
    "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE",
    "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV",
    "55": "WI", "56": "WY", "72": "PR"
}

COUNTY_GEOJSON_URL = (
    "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
)
# The page links the current ABA Checklist CSV; its file name changes with each version
ABA_CHECKLIST_PAGE = "https://www.aba.org/aba-checklist/"
ABA_CHECKLIST_FALLBACK_URL = "https://www.aba.org/wp-content/uploads/2026/03/ABA_Checklist-8.19.csv.zip"
EBIRD_TAXONOMY_CSV_URL = (
    "https://api.ebird.org/v2/ref/taxonomy/ebird?cat=species&fmt=csv&locale=en_US"
)

BASE_DIR = Path(__file__).resolve().parent
GEOJSON_PATH = BASE_DIR / "us_counties.geojson"
TAXONOMY_PATH = BASE_DIR / "taxonomy_sibley.csv"
MAP_PATH = BASE_DIR / "sibley_family_map.json"


def generate_fallback_banding_code(common_name: str) -> str:
    cleaned = re.sub(r"['’]", "", common_name)
    words = [w for w in re.split(r"[\s\-]+", cleaned) if w]
    if not words:
        return "BIRD"
    if len(words) == 1:
        return words[0][:4].upper()
    if len(words) == 2:
        return (words[0][:2] + words[1][:2]).upper()
    if len(words) == 3:
        return (words[0][0] + words[1][0] + words[2][:2]).upper()
    return "".join(w[0] for w in words[:4]).upper()


def download_county_geojson(force: bool = False) -> None:
    if GEOJSON_PATH.exists() and not force:
        print(f"[OK] County GeoJSON already cached at {GEOJSON_PATH}")
        return

    print(f"Downloading US Counties GeoJSON from {COUNTY_GEOJSON_URL}...")
    req = urllib.request.Request(COUNTY_GEOJSON_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("latin-1"))

    for feat in data.get("features", []):
        props = feat.get("properties", {})
        state_fips = str(props.get("STATE", "")).zfill(2)
        state_abbr = FIPS_TO_STATE.get(state_fips, state_fips)
        name = props.get("NAME", "Unknown")
        lsad = props.get("LSAD", "County")
        if lsad and not name.endswith(lsad):
            full_county = f"{name} {lsad}"
        else:
            full_county = name
        props["county_state"] = f"{full_county}, {state_abbr}"

    with open(GEOJSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)
    print(f"[OK] Saved normalized US Counties GeoJSON to {GEOJSON_PATH}")


def download_aba_checklist(force: bool = False) -> None:
    """
    Downloads the ABA Checklist (which species are regular in the US/Canada) to
    scripts/birds/data/aba_checklist.csv, used to limit AI suggestions. It's
    copyrighted, so it stays local (gitignored) and is never committed. Optional:
    if it can't be downloaded, AI suggestions consider every species.
    """
    path = bird_model.ABA_PATH
    if path.exists() and not force:
        print(f"[OK] ABA checklist present (version {bird_model.aba_version() or '?'}, {path})")
        return
    try:
        url = ABA_CHECKLIST_FALLBACK_URL
        try:
            req = urllib.request.Request(ABA_CHECKLIST_PAGE, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                page = resp.read().decode("utf-8", "replace")
            links = re.findall(r'href="([^"]+ABA_Checklist[^"]*\.csv\.zip)"', page)
            if links:
                url = links[0]
        except Exception as exc:
            print(f"[WARN] Couldn't read {ABA_CHECKLIST_PAGE} ({exc}); trying the last known checklist URL")
        print(f"Downloading the ABA checklist from {url}...")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            archive = zipfile.ZipFile(io.BytesIO(resp.read()))
        name = next(n for n in archive.namelist() if n.lower().endswith(".csv"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(archive.read(name))
        print(f"[OK] Saved ABA checklist version {bird_model.aba_version() or '?'} to {path} (local only)")
    except Exception as exc:
        print(f"[WARN] ABA checklist unavailable ({exc}). AI suggestions will consider every species.")


def download_ebird_taxonomy() -> List[Dict[str, str]]:
    """Downloads the official eBird species taxonomy (no API key needed) as a list of rows."""
    print(f"Fetching official eBird taxonomy from {EBIRD_TAXONOMY_CSV_URL}...")
    req = urllib.request.Request(EBIRD_TAXONOMY_CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        csv_text = resp.read().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(csv_text)))


def add_ebird_codes_to_taxonomy() -> bool:
    """
    Fills the `ebird_code` column (eBird's 6-letter species code, e.g. "grhowl",
    used in https://ebird.org/species/<code>) into the existing taxonomy_sibley.csv.
    Every other value is left untouched, so names, taxonomic order, and the AI
    embeddings built from this file don't change. Matches by scientific name,
    falling back to common name. Skips the download if every row already has a code.
    """
    if not TAXONOMY_PATH.exists():
        return False
    with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    if "ebird_code" in fieldnames and all(r.get("ebird_code") for r in rows):
        print(f"[OK] eBird codes already present for all {len(rows)} species")
        return False

    by_sci: Dict[str, str] = {}
    by_common: Dict[str, str] = {}
    for row in download_ebird_taxonomy():
        code = (row.get("SPECIES_CODE") or "").strip()
        if code:
            by_sci.setdefault((row.get("SCIENTIFIC_NAME") or "").strip(), code)
            by_common.setdefault((row.get("COMMON_NAME") or "").strip(), code)

    missing = []
    for row in rows:
        row["ebird_code"] = by_sci.get(row["scientific_name"]) or by_common.get(row["common_name"]) or ""
        if not row["ebird_code"]:
            missing.append(row["common_name"])

    if "ebird_code" not in fieldnames:
        fieldnames.append("ebird_code")
    with open(TAXONOMY_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] Added eBird codes to {len(rows) - len(missing)} of {len(rows)} species in {TAXONOMY_PATH}")
    if missing:
        print(f"[WARN] No eBird code found for: {', '.join(missing)}")
    return True


# Species recorded in the US/Canada that eBird gives no banding code, which the builder
# would otherwise skip. They get a generated code (generate_fallback_banding_code).
SPECIES_WITHOUT_BANDING_CODES = {
    "Circus cyaneus",        # Hen Harrier
    "Pernis ptilorhynchus",  # Oriental Honey-buzzard
    "Pterodroma deserta",    # Desertas Petrel
}


def build_full_ebird_sibley_taxonomy(force: bool = False) -> bool:
    """
    Downloads the official eBird taxonomy CSV and writes all North American species
    mapped to Sibley's 34 categories into taxonomy_sibley.csv.
    """
    existing_count = 0
    if TAXONOMY_PATH.exists():
        with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
            existing_count = sum(1 for _ in f) - 1

    if existing_count >= 1000 and not force:
        print(f"[OK] Full taxonomy already present ({existing_count} species in {TAXONOMY_PATH})")
        return False

    with open(MAP_PATH, "r", encoding="utf-8") as f:
        family_map = json.load(f)

    extra_families = {
        "Burhinidae": {"sibley_category": "Shorebirds", "sibley_category_order": 9},
        "Glareolidae": {"sibley_category": "Shorebirds", "sibley_category_order": 9},
        "Trogonidae": {"sibley_category": "Trogons and Kingfishers", "sibley_category_order": 16},
        "Upupidae": {"sibley_category": "Trogons and Kingfishers", "sibley_category_order": 16},
        "Psittacidae": {"sibley_category": "Parrots", "sibley_category_order": 18},
        "Locustellidae": {"sibley_category": "Kinglets, Old World Warblers, and Thrush Allies", "sibley_category_order": 25},
        "Acrocephalidae": {"sibley_category": "Kinglets, Old World Warblers, and Thrush Allies", "sibley_category_order": 25},
        "Prunellidae": {"sibley_category": "Wagtails and Pipits", "sibley_category_order": 27},
        "Emberizidae": {"sibley_category": "Towhees, Sparrows, and Juncos", "sibley_category_order": 31},
        "Viduidae": {"sibley_category": "Old World Sparrows and Weaver Finches", "sibley_category_order": 35},
    }
    for k, v in extra_families.items():
        family_map.setdefault(k, v)

    reader = download_ebird_taxonomy()
    output_rows = []
    seen_common = set()

    for row in reader:
        if row.get("CATEGORY") != "species":
            continue

        family = (row.get("FAMILY_SCI_NAME") or "").strip()
        if family not in family_map:
            continue

        raw_banding = (row.get("BANDING_CODES") or "").strip()
        common_name = (row.get("COMMON_NAME") or "").strip()
        sci_name = (row.get("SCIENTIFIC_NAME") or "").strip()
        if not raw_banding and sci_name not in SPECIES_WITHOUT_BANDING_CODES:
            continue
        if not common_name or not sci_name or common_name in seen_common:
            continue

        banding_code = raw_banding.split(",")[0].strip()
        if len(banding_code) != 4:
            banding_code = generate_fallback_banding_code(common_name)

        try:
            tax_order = int(float(row.get("TAXON_ORDER") or 0))
        except ValueError:
            tax_order = 99999

        sib_info = family_map[family]
        output_rows.append({
            "common_name": common_name,
            "scientific_name": sci_name,
            "banding_code": banding_code,
            "family": family,
            "sibley_category": sib_info["sibley_category"],
            "sibley_category_order": sib_info["sibley_category_order"],
            "taxonomic_order": tax_order,
            "ebird_code": (row.get("SPECIES_CODE") or "").strip(),
        })
        seen_common.add(common_name)

    output_rows.sort(key=lambda r: (r["sibley_category_order"], r["taxonomic_order"]))

    with open(TAXONOMY_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "common_name",
                "scientific_name",
                "banding_code",
                "family",
                "sibley_category",
                "sibley_category_order",
                "taxonomic_order",
                "ebird_code",
            ],
        )
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"[OK] Wrote {len(output_rows)} species to {TAXONOMY_PATH}")
    return True


def cache_ai_models(force: bool = False) -> None:
    """Downloads/verifies the pinned AI model and pre-computes the species text embeddings."""
    bird_model.download_model(force=force)
    print("Loading the AI model and pre-computing species embeddings...")
    model, _, tokenizer = bird_model.load_model()
    with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    bird_model.text_embeddings(model, tokenizer, rows, cache_key=bird_model.MODEL_REVISION)
    print(f"[OK] Species embeddings ready for {len(rows)} species ({bird_model.EMBEDDINGS_PATH})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Set up the bird pipeline's offline data and the optional AI model.")
    parser.add_argument("--force", action="store_true", help="Rebuild the taxonomy from eBird and re-download the AI model")
    parser.add_argument("--skip-models", action="store_true", help="Skip the AI model (imports still work with fuzzy search)")
    parser.add_argument("--refresh-counties", action="store_true", help="Re-download and rebuild the committed county boundaries")
    parser.add_argument("--refresh-aba", action="store_true", help="Re-download the ABA checklist (e.g. after a new version)")
    args = parser.parse_args()

    if args.refresh_counties or not GEOJSON_PATH.exists():
        download_county_geojson(force=True)
    else:
        print(f"[OK] County boundaries present ({GEOJSON_PATH.name}, committed to the repo)")
    taxonomy_updated = build_full_ebird_sibley_taxonomy(force=args.force)
    if not taxonomy_updated:
        add_ebird_codes_to_taxonomy()  # Older taxonomy files predate the ebird_code column
    download_aba_checklist(force=args.refresh_aba)
    if not args.skip_models:
        cache_ai_models(force=args.force or taxonomy_updated)


if __name__ == "__main__":
    main()