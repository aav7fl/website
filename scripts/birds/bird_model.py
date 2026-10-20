"""
The AI species-suggestion model, in one place: which model, where it lives, how
it's downloaded and verified, and how it's loaded. Used by setup_offline_assets.py,
import_birds.py, doctor.py and evaluate_model.py.

The model is pinned to an exact Hugging Face revision and kept in a local folder
(scripts/birds/models/, gitignored), checked against committed checksums
(model-checksums.txt). Once downloaded, nothing here touches the network, so the
model keeps working even if it changes or disappears upstream. Back up the
models/ folder with your photos; it's the one thing that can't be re-downloaded
if Hugging Face removes the model.

To try a replacement model, see "Replacing the AI model" in README.md and
evaluate_model.py. torch and open_clip are imported only inside functions, so the
rest of the pipeline works without the optional AI packages.
"""

import csv
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent

# --- The pinned model. Change these three together (plus model-checksums.txt). ---
MODEL_REPO = "imageomics/bioclip"
MODEL_REVISION = "ce901ab3c6a913f9e9ef94ce6d27761069f4f01c"  # Hugging Face commit, Feb 2026
MODEL_FILES = ["open_clip_config.json", "open_clip_pytorch_model.bin"]

MODEL_DIR = SCRIPT_DIR / "models" / "bioclip"
CHECKSUMS_PATH = SCRIPT_DIR / "model-checksums.txt"
EMBEDDINGS_PATH = SCRIPT_DIR / "bioclip_species_embeddings.pt"

# --- Which species the AI may suggest ---
# The ABA Checklist (American Birding Association) gives every species recorded in
# the US and Canada a code: 1-2 regular, 3 rare, 4 casual, 5 accidental, 6 extinct or
# unlikely. Suggestions are limited to codes 1-3, which keeps the model from picking
# a Eurasian look-alike. The checklist is copyrighted, so setup downloads it and it
# stays local (scripts/birds/data/, gitignored). Fuzzy search is never limited.
ABA_PATH = SCRIPT_DIR / "data" / "aba_checklist.csv"
ABA_MAX_CODE = 3


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_checksums() -> Dict[str, str]:
    """{filename: sha256} from model-checksums.txt ("<sha256>  <filename>" per line)."""
    if not CHECKSUMS_PATH.exists():
        return {}
    sums = {}
    for line in CHECKSUMS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            digest, name = line.split(None, 1)
            sums[name.strip()] = digest
    return sums


def verify_model(model_dir: Path = MODEL_DIR) -> List[str]:
    """Problems with the local model files, or an empty list if they're all present and match."""
    expected = expected_checksums()
    if not expected:
        return [f"{CHECKSUMS_PATH.name} is missing or empty"]
    problems = []
    for name in MODEL_FILES:
        path = model_dir / name
        if not path.is_file():
            problems.append(f"missing {path}")
        elif name not in expected:
            problems.append(f"no checksum recorded for {name} in {CHECKSUMS_PATH.name}")
        elif sha256_of(path) != expected[name]:
            problems.append(f"checksum mismatch for {path} (corrupt, or a different model revision)")
    return problems


def download_model(force: bool = False) -> None:
    """
    Makes sure the pinned model is in MODEL_DIR. Uses no network if the local files
    already match the recorded checksums. Otherwise downloads exactly MODEL_REVISION
    and verifies it; refuses to continue on a mismatch rather than use a different model.
    """
    if not force and not verify_model():
        print(f"[OK] AI model present and verified ({MODEL_REPO} @ {MODEL_REVISION[:12]}, {MODEL_DIR})")
        return

    from huggingface_hub import hf_hub_download

    print(f"Downloading AI model {MODEL_REPO} @ {MODEL_REVISION[:12]} into {MODEL_DIR} ...")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for name in MODEL_FILES:
        hf_hub_download(MODEL_REPO, name, revision=MODEL_REVISION, local_dir=MODEL_DIR)

    if not expected_checksums():
        # First download for this revision: record what we got, to be committed
        lines = [f"# sha256 of the AI model files ({MODEL_REPO} @ {MODEL_REVISION})"]
        lines += [f"{sha256_of(MODEL_DIR / name)}  {name}" for name in MODEL_FILES]
        CHECKSUMS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[OK] Recorded checksums in {CHECKSUMS_PATH}; commit this file.")
        return

    problems = verify_model()
    if problems:
        raise SystemExit(
            "Downloaded model doesn't match the recorded checksums:\n  - "
            + "\n  - ".join(problems)
            + f"\nThe files at {MODEL_REPO} @ {MODEL_REVISION} have changed or were corrupted in transit."
            "\nSee 'Replacing the AI model' in scripts/birds/README.md."
        )
    print(f"[OK] AI model downloaded and verified ({MODEL_DIR})")


def load_model(model_dir: Path = MODEL_DIR) -> Tuple[Any, Any, Any]:
    """(model, preprocess, tokenizer) for an open_clip model stored in a local folder."""
    import open_clip

    spec = f"local-dir:{model_dir}"
    model, _, preprocess = open_clip.create_model_and_transforms(spec)
    model.eval()
    return model, preprocess, open_clip.get_tokenizer(spec)


def species_prompt(row: Dict[str, Any]) -> str:
    return f"a photo of {row['common_name']} ({row['scientific_name']}), family {row['family']}"


def text_embeddings(model: Any, tokenizer: Any, rows: List[Dict[str, Any]], cache_key: Optional[str] = None) -> Any:
    """
    Normalised text embeddings for every species in the taxonomy. With a cache_key
    (the pinned model's revision), they're cached in EMBEDDINGS_PATH and rebuilt
    whenever the model revision or the species list changes.
    """
    import torch

    names = [r["common_name"] for r in rows]
    if cache_key and EMBEDDINGS_PATH.exists():
        try:
            cached = torch.load(EMBEDDINGS_PATH, map_location="cpu", weights_only=True)
            if cached.get("model_revision") == cache_key and cached.get("common_names") == names:
                return cached["embeddings"]
        except Exception:
            pass

    feats = []
    with torch.no_grad():
        for start in range(0, len(rows), 256):
            batch = model.encode_text(tokenizer([species_prompt(r) for r in rows[start:start + 256]]))
            feats.append((batch / batch.norm(dim=-1, keepdim=True)).cpu())
    embeddings = torch.cat(feats, dim=0)

    if cache_key:
        torch.save({"model_revision": cache_key, "common_names": names, "embeddings": embeddings}, EMBEDDINGS_PATH)
    return embeddings


def _name_variants(name: str) -> List[str]:
    """Lowercase forms of a checklist name that may hold an alternative in parentheses."""
    name = name.strip().replace("\u2019", "'")
    match = re.match(r"^(.*?)\s*\(([^)]*)\)\s*(.*)$", name)
    if not match:
        return [name.lower()] if name else []
    before, inside, after = (part.strip() for part in match.groups())
    variants = {f"{before} {after}".strip()}
    # A scientific name's alternative is just the species part: "Genus a (b)" -> "Genus b"
    if " " in before and not after and before.split()[0][:1].isupper() and inside.islower():
        variants.add(f"{before.split()[0]} {inside}")
    else:
        variants.add(f"{before} {inside} {after}".replace("  ", " ").strip())
        variants.add(f"{inside} {after}".strip())
    return [v.lower() for v in variants if v]


def aba_codes() -> Dict[str, int]:
    """
    {name: ABA code} from the local checklist, keyed by scientific name and by English
    name (lowercase; both of the checklist's names where it lists two). Empty if missing.
    """
    if not ABA_PATH.exists():
        return {}
    codes: Dict[str, int] = {}
    with open(ABA_PATH, encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            # Species rows: [blank, English, French, scientific, alpha code, ABA code]
            if len(row) < 6 or not row[5].strip().isdigit():
                continue
            code = int(row[5].strip())
            # Where eBird and the AOS disagree, both names are listed, one in parentheses,
            # e.g. "Setophaga aestiva (petechia)" or "Northern Yellow (Yellow) Warbler"
            for name in _name_variants(row[3]) + _name_variants(row[1]):
                codes[name] = code
    return codes


def aba_version() -> str:
    """The checklist's version line, e.g. "8.19", or "" if unknown."""
    if not ABA_PATH.exists():
        return ""
    match = re.search(r"Version\s+([0-9.]+)", ABA_PATH.read_text(encoding="utf-8-sig")[:500])
    return match.group(1) if match else ""


def allowed_species(rows: List[Dict[str, Any]], always_include: Iterable[str] = (), americas: bool = False) -> Tuple[Optional[List[int]], str]:
    """
    (indices of the taxonomy rows the AI may suggest, a description for the console).
    None means "the whole taxonomy" (North and Central America plus strays recorded
    there; not worldwide): with americas, or when the ABA checklist is missing.
    always_include adds species by common name (the catalog's own birds, so a
    re-photographed rarity is still suggested).
    """
    if americas:
        return None, f"all {len(rows)} species of North and Central America (--americas)"
    codes = aba_codes()
    if not codes:
        return None, f"all {len(rows)} species (ABA checklist missing; run `rake birds:setup`)"
    extra = {name.lower() for name in always_include}
    allowed = []
    for i, row in enumerate(rows):
        code = codes.get(row["scientific_name"].lower(), codes.get(row["common_name"].lower()))
        if (code is not None and code <= ABA_MAX_CODE) or row["common_name"].lower() in extra:
            allowed.append(i)
    return allowed, f"{len(allowed)} species (ABA checklist codes 1-{ABA_MAX_CODE}, US/Canada; --americas for Mexico/Central America)"


def predict(model: Any, preprocess: Any, embeddings: Any, rows: List[Dict[str, Any]], image_path: Path, k: int = 3, allowed: Optional[List[int]] = None) -> List[Tuple[Dict[str, Any], float]]:
    """
    Top-k (species row, confidence %) for one photo, averaging the full frame and a
    centre crop. With `allowed`, only those taxonomy rows are considered, so the
    confidences are relative to plausible species.
    """
    import torch
    from PIL import Image

    with Image.open(image_path) as img:
        rgb = img.convert("RGB")
        w, h = rgb.size
        centre = rgb.crop((int(w * 0.15), int(h * 0.15), int(w * 0.85), int(h * 0.85)))
        batch = torch.stack([preprocess(rgb), preprocess(centre)])

    with torch.no_grad():
        feats = model.encode_image(batch)
        feats = feats / feats.norm(dim=-1, keepdim=True)
        avg = feats.mean(dim=0, keepdim=True)
        avg = avg / avg.norm(dim=-1, keepdim=True)
        candidates = list(range(len(rows))) if allowed is None else allowed
        probs = (100.0 * avg @ embeddings[candidates].T).softmax(dim=-1)[0]
        top_probs, top_idxs = torch.topk(probs, k=min(k, len(candidates)))

    return [(rows[candidates[i]], p * 100.0) for p, i in zip(top_probs.tolist(), top_idxs.tolist())]
