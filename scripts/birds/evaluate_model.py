#!/usr/bin/env python3
"""
Measure how well an AI model identifies your birds: `rake birds:evaluate`.

Runs the model on every photo in the catalog (each one already labelled with its
species) and reports how often the right species is the top suggestion (top-1) or
among the three suggestions shown during import (top-3). Collages are reported
separately, since several birds in one image are harder.

Use it to judge a replacement model before switching to it:
    rake birds:evaluate                                   # the pinned model
    rake birds:evaluate -- --model-dir path/to/candidate  # any open_clip model folder
See "Replacing the AI model" in README.md. Results are a guide, not a benchmark:
the catalog is small, and some labels were chosen with this model's help.
"""

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import yaml  # noqa: E402

import bird_model  # noqa: E402
from import_birds import load_taxonomy, TAXONOMY_CSV_PATH  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure AI species-identification accuracy on the catalog photos.")
    parser.add_argument("--model-dir", type=Path, default=bird_model.MODEL_DIR,
                        help="Folder with an open_clip model (open_clip_config.json + weights); default: the pinned model")
    parser.add_argument("--limit", type=int, default=0, help="Only evaluate the first N photos (quick check)")
    parser.add_argument("--americas", action="store_true", help="Consider the whole taxonomy (North and Central America), not just ABA codes 1-3 (the old behaviour)")
    parser.add_argument("--json", action="store_true", help="Print only a JSON summary (used by update_deps.py)")
    args = parser.parse_args()
    say = (lambda *a, **k: None) if args.json else print

    pinned = args.model_dir.resolve() == bird_model.MODEL_DIR.resolve()
    if pinned:
        problems = bird_model.verify_model()
        if problems:
            sys.exit("The pinned model isn't ready: " + "; ".join(problems) + "\nRun `rake birds:setup` first.")

    rows = load_taxonomy(TAXONOMY_CSV_PATH)
    catalog = yaml.safe_load((REPO_ROOT / "_data" / "birds.yml").read_text(encoding="utf-8")) or []
    if args.limit:
        catalog = catalog[: args.limit]

    # The same species limit as imports, but without adding the catalog's own birds, so
    # the result reflects what a brand-new photo would get
    allowed, scope = bird_model.allowed_species(rows, americas=args.americas)
    say(f"Model: {args.model_dir}" + (f" ({bird_model.MODEL_REPO} @ {bird_model.MODEL_REVISION[:12]})" if pinned else ""))
    say(f"AI species: {scope}")
    model, preprocess, tokenizer = bird_model.load_model(args.model_dir)
    # Only the pinned model uses (and refreshes) the embeddings cache
    embeddings = bird_model.text_embeddings(model, tokenizer, rows, cache_key=bird_model.MODEL_REVISION if pinned else None)

    stats = {"single": Counter(), "collage": Counter()}
    misses = []
    started = time.perf_counter()
    for i, bird in enumerate(catalog, start=1):
        kind = "collage" if "COLLAGE" in str(bird.get("source_filename", "")) else "single"
        photo = REPO_ROOT / "assets" / "img" / "birds" / bird["filename"]
        top = bird_model.predict(model, preprocess, embeddings, rows, photo, k=3, allowed=allowed)
        guesses = [r["common_name"] for r, _ in top]
        stats[kind]["total"] += 1
        stats[kind]["top1"] += guesses[:1] == [bird["species_common"]]
        stats[kind]["top3"] += bird["species_common"] in guesses
        if guesses[:1] != [bird["species_common"]]:
            misses.append((bird["species_common"], guesses[0], top[0][1], bird["species_common"] in guesses))
        say(f"\r  {i}/{len(catalog)} photos", end="", flush=True)
    elapsed = time.perf_counter() - started
    say()

    overall = stats["single"] + stats["collage"]
    if args.json:
        print(json.dumps({
            "photos": overall["total"], "top1": overall["top1"], "top3": overall["top3"],
            "species_considered": len(allowed) if allowed is not None else len(rows),
            "seconds_per_photo": round(elapsed / max(1, overall["total"]), 3),
        }))
        return

    def line(label: str, c: Counter) -> str:
        if not c["total"]:
            return f"  {label:<9} (none)"
        return (f"  {label:<9} {c['total']:>3} photos   top-1 {100 * c['top1'] / c['total']:5.1f}%   "
                f"top-3 {100 * c['top3'] / c['total']:5.1f}%")

    print("\nResults (top-3 is what the import shows you)")
    print(line("Singles", stats["single"]))
    print(line("Collages", stats["collage"]))
    print(line("Overall", overall))
    print(f"  Speed     {elapsed / max(1, overall['total']):.2f} s per photo")

    if misses:
        print(f"\nTop suggestion wrong ({len(misses)}), worst-confidence first:")
        for actual, guess, conf, in_top3 in sorted(misses, key=lambda m: -m[2])[:15]:
            print(f"  {actual:<30} → {guess} ({conf:.0f}%){'' if in_top3 else '  [not in top 3]'}")


if __name__ == "__main__":
    main()
