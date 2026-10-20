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
import json
import re
import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from typing import Dict, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

OK, FAIL, WARN = "✓", "✗", "!"
core_ok = True
ai_ok = True


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


def pins(path: Path) -> Dict[str, str]:
    """{normalised name: version} from a requirements file's `name==version` lines."""
    found = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*([A-Za-z0-9_.\-]+)==([^\s#]+)", line)
        if match:
            found[re.sub(r"[-_.]+", "-", match.group(1)).lower()] = match.group(2)
    return found


def check_packages(path: Path, ai: bool) -> None:
    missing, drift = [], []
    for name, wanted in pins(path).items():
        try:
            have = metadata.version(name)
        except metadata.PackageNotFoundError:
            missing.append(name)
            continue
        if have != wanted:
            drift.append(f"{name} {have} (pinned {wanted})")
    label = path.name
    fix = f"/opt/venv-birds/bin/pip install -r scripts/birds/{label}  (or rebuild the dev container)"
    if missing:
        report(FAIL, f"{label}: not installed: {', '.join(missing)}", fix, ai=ai)
    elif drift:
        report(WARN, f"{label}: versions differ from the pins: {', '.join(drift)}", fix)
    else:
        report(OK, f"{label}: all {len(pins(path))} packages installed at their pinned versions")


def tool_version(cmd: List[str]) -> Tuple[bool, str]:
    if not shutil.which(cmd[0]):
        return False, ""
    out = subprocess.run(cmd, capture_output=True, text=True)
    return out.returncode == 0, (out.stdout or out.stderr).strip().splitlines()[0] if (out.stdout or out.stderr) else ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Check the bird pipeline's dependencies.")
    parser.add_argument("--require-ai", action="store_true", help="Also fail (exit 1) if AI suggestions aren't ready (used by update_deps.py)")
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
    try:
        import yaml
        catalog = yaml.safe_load((REPO_ROOT / "_data" / "birds.yml").read_text(encoding="utf-8")) or []
        photos = REPO_ROOT / "assets" / "img" / "birds"
        missing = [b["filename"] for b in catalog if not (photos / b["filename"]).is_file()]
        locked = sum(1 for b in catalog if b.get("locked"))
        report(OK if not missing else FAIL,
               f"Catalog: {len(catalog)} birds" + (f", {locked} locked" if locked else "")
               + (f"; missing photos: {', '.join(missing[:5])}" if missing else ", every photo present"),
               "" if not missing else "restore the missing files in assets/img/birds/ from git")
    except Exception as exc:
        report(FAIL, f"Catalog unreadable ({exc})", "check _data/birds.yml for YAML errors")

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

    names = [r["common_name"] for r in rows]
    cache_valid = False
    if bird_model.EMBEDDINGS_PATH.exists():
        try:
            cached = torch.load(bird_model.EMBEDDINGS_PATH, map_location="cpu", weights_only=True)
            cache_valid = cached.get("model_revision") == bird_model.MODEL_REVISION and cached.get("common_names") == names
        except Exception:
            pass
    if cache_valid:
        report(OK, "Species embeddings cached for this model and taxonomy")
    else:
        report(WARN, "Species embeddings missing or stale (rebuilt automatically, ~1 min)", "rake birds:setup")

    sample = next((b for b in catalog if "COLLAGE" not in str(b.get("source_filename", ""))), None)
    if not sample:
        return
    embeddings = bird_model.text_embeddings(model, tokenizer, rows, cache_key=bird_model.MODEL_REVISION)
    photo = REPO_ROOT / "assets" / "img" / "birds" / sample["filename"]
    top = bird_model.predict(model, preprocess, embeddings, rows, photo, k=3)
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
