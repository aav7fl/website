#!/usr/bin/env python3
"""
Migrates the catalog (_data/birds.yml) to the current taxonomy_sibley.csv after an
eBird taxonomy update, so renamed, re-classified and split species don't have to be
deleted and re-imported. Run by `rake birds:update_taxonomy` (after the rebuild) and
`rake birds:migrate_taxonomy`.

Each bird is matched to the new taxonomy by its eBird species code (eBird's stable
id, which survives renames and genus changes), then by scientific name, then by common
name. From the match, every taxonomy field is refreshed:
  - a changed taxonomic order, category, family or banding code is applied silently;
  - a renamed species (common or scientific name) is shown and confirmed; a new common
    name also renames the slug and the photo file, like a fresh import would;
  - a species whose eBird code no longer exists (split, lumped or retired) is shown
    with the likely successors to choose from, since a split needs your judgement
    (e.g. Marsh Wren -> Eastern or Western Marsh Wren);
  - a species with no match at all can be picked with the fuzzy search, or skipped.
Nothing else in an entry (notes, date, location, locked, source) is touched.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table

import import_birds
from import_birds import (
    DEFAULT_DEST_DIR,
    DEFAULT_YAML_PATH,
    REPO_ROOT,
    TAXONOMY_CSV_PATH,
    display_path,
    load_catalog,
    load_taxonomy,
    prompt_fuzzy_species,
    save_catalog,
    slugify,
)

console = Console()

# Catalog field -> taxonomy column
TAXONOMY_FIELDS = {
    "species_common": "common_name",
    "species_scientific": "scientific_name",
    "banding_code": "banding_code",
    "family": "family",
    "sibley_category": "sibley_category",
    "sibley_category_order": "sibley_category_order",
    "taxonomic_order": "taxonomic_order",
    "ebird_code": "ebird_code",
}
# Changes to these are applied without asking: they don't change which bird it is
QUIET_FIELDS = {"banding_code", "family", "sibley_category", "sibley_category_order", "taxonomic_order"}


def genus(scientific_name: str) -> str:
    return (scientific_name or "").split(" ")[0]


def field_changes(entry: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
    """The catalog fields whose value differs from the taxonomy row: field -> (old, new)."""
    changes = {}
    for field, column in TAXONOMY_FIELDS.items():
        old, new = entry.get(field), row.get(column, "")
        if field in ("sibley_category_order", "taxonomic_order"):
            new = int(new)
            old = int(old) if old not in (None, "") else None
        if old != new:
            changes[field] = (old, new)
    return changes


def find_match(entry: Dict[str, Any], by_code: Dict[str, Any], by_sci: Dict[str, Any], by_common: Dict[str, Any]):
    """The taxonomy row this bird is now, and how it was found ("code", "scientific", "common" or None)."""
    code = entry.get("ebird_code") or ""
    if code and code in by_code:
        return by_code[code], "code"
    if entry.get("species_scientific") in by_sci:
        return by_sci[entry["species_scientific"]], "scientific"
    if entry.get("species_common") in by_common:
        return by_common[entry["species_common"]], "common"
    return None, None


def successor_candidates(entry: Dict[str, Any], taxonomy: List[Dict[str, Any]], limit: int = 8) -> List[Dict[str, Any]]:
    """
    Likely successors of a bird whose eBird code is gone: the same scientific name, the
    same common name, names containing the old name (Marsh Wren -> Eastern Marsh Wren),
    then the rest of its genus.
    """
    common = (entry.get("species_common") or "").lower()
    sci = entry.get("species_scientific") or ""
    old_genus = genus(sci)
    ranked: List[Dict[str, Any]] = []

    def add(rows):
        for r in rows:
            if r not in ranked:
                ranked.append(r)

    add(r for r in taxonomy if r["scientific_name"] == sci)
    add(r for r in taxonomy if r["common_name"].lower() == common)
    add(r for r in taxonomy if common and common in r["common_name"].lower())
    add(r for r in taxonomy if old_genus and genus(r["scientific_name"]) == old_genus)
    return ranked[:limit]


def describe_changes(changes: Dict[str, Any]) -> str:
    return ", ".join(f"{field}: {old!r} -> {new!r}" for field, (old, new) in changes.items())


def choose_successor(entry: Dict[str, Any], candidates: List[Dict[str, Any]], taxonomy: List[Dict[str, Any]],
                     reason: str, assume_yes: bool) -> Optional[Dict[str, Any]]:
    """Asks which taxonomy row the bird is now. Returns None to leave it unchanged."""
    console.print(f"\n[bold yellow]{entry.get('species_common')}[/bold yellow] ({entry.get('species_scientific')}, "
                  f"eBird {entry.get('ebird_code') or '?'}): {reason}")
    if candidates:
        table = Table(show_header=True, header_style="dim", box=None, pad_edge=False)
        table.add_column("#", justify="right")
        table.add_column("Common name")
        table.add_column("Scientific name")
        table.add_column("eBird")
        for i, r in enumerate(candidates, 1):
            table.add_row(str(i), r["common_name"], r["scientific_name"], r["ebird_code"])
        console.print(table)
    if assume_yes:
        if candidates:
            console.print(f"  [yellow]--yes: assuming #1, {candidates[0]['common_name']}. Check this one![/yellow]")
            return candidates[0]
        console.print("  [yellow]--yes: no candidate, left unchanged.[/yellow]")
        return None
    while True:
        answer = input(f"  Which is it now? [1-{len(candidates)}] number, 'f' fuzzy search, 's' skip"
                       f"{' [default: 1]' if candidates else ''}: ").strip().lower()
        if not answer and candidates:
            return candidates[0]
        if answer == "s":
            return None
        if answer == "f":
            return prompt_fuzzy_species(taxonomy, set())
        if answer.isdigit() and 1 <= int(answer) <= len(candidates):
            return candidates[int(answer) - 1]


def confirm(question: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    return (input(f"  {question} [Y/n]: ").strip().lower() or "y") in ("y", "yes")


def rename_photo(dest_dir: Path, old_name: str, new_name: str, dry_run: bool) -> bool:
    old_path, new_path = dest_dir / old_name, dest_dir / new_name
    if not old_path.is_file():
        console.print(f"  [red]Photo {display_path(old_path)} is missing; not renamed.[/red]")
        return False
    if new_path.exists():
        console.print(f"  [red]{display_path(new_path)} already exists; not renamed.[/red]")
        return False
    if dry_run:
        return True
    try:  # Keep git's rename tracking when the photo is committed
        subprocess.run(["git", "mv", str(old_path), str(new_path)], cwd=REPO_ROOT, check=True,
                       capture_output=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        old_path.rename(new_path)
    return True


def migrate(catalog: List[Dict[str, Any]], taxonomy: List[Dict[str, Any]], dest_dir: Path,
            dry_run: bool, assume_yes: bool) -> int:
    """Updates the catalog entries in place. Returns how many changed."""
    by_code = {r["ebird_code"]: r for r in taxonomy if r.get("ebird_code")}
    by_sci = {r["scientific_name"]: r for r in taxonomy}
    by_common = {r["common_name"]: r for r in taxonomy}
    slugs = {e.get("slug") for e in catalog}

    quiet_updates: List[str] = []
    renamed: List[str] = []
    skipped: List[str] = []
    changed = 0

    for entry in catalog:
        name = entry.get("species_common", "?")
        row, how = find_match(entry, by_code, by_sci, by_common)

        if how != "code":
            # The eBird code is gone (or was never there): a split, lump, retirement or
            # an old entry. The name match is only a suggestion; ask.
            candidates = successor_candidates(entry, taxonomy)
            if row and row not in candidates:
                candidates.insert(0, row)
            if entry.get("ebird_code"):
                reason = "its eBird code is no longer in the taxonomy (split, lumped or retired)"
            else:
                reason = "it has no eBird code to match on"
            row = choose_successor(entry, candidates, taxonomy, reason, assume_yes)
            if row is None:
                skipped.append(name)
                continue

        changes = field_changes(entry, row)
        if not changes:
            continue

        if set(changes) - QUIET_FIELDS or how != "code":
            console.print(f"\n[bold]{name}[/bold] -> [bold green]{row['common_name']}[/bold green] ({row['scientific_name']})")
            console.print(f"  {describe_changes(changes)}")
            if "species_common" in changes:
                console.print(f"  slug: {entry.get('slug')!r} -> {slugify(row['common_name'])!r}, photo renamed to match")
            if not confirm("Apply?", assume_yes):
                skipped.append(name)
                continue
        else:
            quiet_updates.append(f"{name} ({describe_changes(changes)})")

        if "species_common" in changes:
            new_slug = slugify(row["common_name"])
            new_filename = f"{new_slug}.webp"
            if new_slug != entry.get("slug") and new_slug in slugs:
                console.print(f"  [red]{new_slug} is already another bird in the catalog; left unchanged. "
                              f"Delete one of them and re-import if they're the same species.[/red]")
                skipped.append(name)
                continue
            if not rename_photo(dest_dir, entry.get("filename", ""), new_filename, dry_run):
                skipped.append(name)
                continue
            slugs.discard(entry.get("slug"))
            slugs.add(new_slug)
            entry["slug"] = new_slug
            entry["filename"] = new_filename
            renamed.append(f"{name} -> {row['common_name']}")

        for field, (_, new) in changes.items():
            entry[field] = new
        changed += 1

    console.rule("[bold]Taxonomy migration[/bold]" + (" (dry run, nothing written)" if dry_run else ""))
    if quiet_updates:
        console.print(f"[green]{len(quiet_updates)} bird(s) re-ordered or re-classified:[/green]")
        for line in quiet_updates:
            console.print(f"  {line}")
    if renamed:
        console.print(f"[green]{len(renamed)} bird(s) renamed:[/green] " + "; ".join(renamed))
    if skipped:
        console.print(f"[yellow]{len(skipped)} bird(s) left unchanged:[/yellow] " + ", ".join(skipped))
    console.print(f"{changed} of {len(catalog)} birds updated, {len(catalog) - changed - len(skipped)} already current.")
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Update the bird catalog after an eBird taxonomy update.")
    parser.add_argument("--check", action="store_true", help="Only report what would change; write nothing")
    parser.add_argument("--yes", action="store_true", help="Apply every change without asking (a split takes the first candidate)")
    parser.add_argument("--yaml", type=Path, default=DEFAULT_YAML_PATH, help="Catalog YAML path")
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST_DIR, help="Photos folder")
    parser.add_argument("--taxonomy", type=Path, default=TAXONOMY_CSV_PATH, help="Taxonomy CSV path")
    args = parser.parse_args()

    taxonomy = load_taxonomy(args.taxonomy)
    catalog = load_catalog(args.yaml)
    if not catalog:
        console.print(f"[yellow]No birds in {args.yaml}.[/yellow]")
        return

    changed = migrate(catalog, taxonomy, args.dest, dry_run=args.check, assume_yes=args.yes)
    if changed and not args.check:
        save_catalog(args.yaml, catalog)
        console.print(f"[bold green]Saved {display_path(args.yaml)}.[/bold green] Review `git diff` before committing.")
    elif changed:
        console.print("Run without --check to apply.")


if __name__ == "__main__":
    main()
