#!/usr/bin/env python3
"""
Compact git history for the bird photos: remove every old version of
assets/img/birds/*.webp from all commits, keeping only the versions that are
current on some branch or tag. The photos on the site don't change; only the
history behind them is dropped, which shrinks the repository.

THIS REWRITES GIT HISTORY. Every commit ID changes, the result has to be
force-pushed, and any other clone must be re-cloned afterwards.

Safety:
- Dry run by default: reports what would be removed and how much space it frees.
- --apply refuses to run with uncommitted changes, asks for a typed confirmation,
  and first saves a full backup bundle next to the repository.
- Never pushes. It prints the force-push commands for you to run yourself.

Uses git-filter-repo (https://github.com/newren/git-filter-repo), the tool GitHub
recommends for removing files from history.
"""

import argparse
import datetime
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
PHOTO_DIR = "assets/img/birds/"
CONFIRM_WORD = "compact"


def git(*args: str, capture: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, check=True, text=True,
        capture_output=capture,
    )
    return result.stdout if capture else ""


def photo_blobs_in_history() -> Dict[str, str]:
    """Every version of a bird photo ever committed, as {blob id: path}."""
    blobs: Dict[str, str] = {}
    for line in git("rev-list", "--all", "--objects", "--", PHOTO_DIR).splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2 and parts[1].startswith(PHOTO_DIR) and parts[1].endswith(".webp"):
            blobs[parts[0]] = parts[1]
    return blobs


def photo_blobs_at_ref_tips() -> Set[str]:
    """Photo versions that are current at the tip of any branch, remote branch, or tag (kept)."""
    keep: Set[str] = set()
    refs = git("for-each-ref", "--format=%(objectname)", "refs/heads", "refs/remotes", "refs/tags").split()
    for ref in set(refs):
        if git("cat-file", "-t", ref).strip() not in {"commit", "tag"}:
            continue
        for line in git("ls-tree", "-r", ref, "--", PHOTO_DIR).splitlines():
            meta, path = line.split("\t", 1)
            if path.endswith(".webp"):
                keep.add(meta.split()[2])
    return keep


def blob_sizes(blob_ids: List[str]) -> Tuple[int, int]:
    """
    (full size, size on disk) of the given versions, in bytes. Git stores a version
    that barely differs from another (e.g. only its metadata changed) as a small
    delta, so removing it frees much less than its full size.
    """
    if not blob_ids:
        return 0, 0
    out = subprocess.run(
        ["git", "cat-file", "--batch-check=%(objectsize) %(objectsize:disk)"],
        cwd=REPO_ROOT, check=True, text=True, capture_output=True, input="\n".join(blob_ids) + "\n",
    ).stdout
    pairs = [tuple(map(int, line.split())) for line in out.splitlines()]
    return sum(p[0] for p in pairs), sum(p[1] for p in pairs)


def repo_size_mb() -> float:
    sizes = dict(
        line.split(": ", 1) for line in git("count-objects", "-v").splitlines() if ": " in line
    )
    return (int(sizes.get("size", 0)) + int(sizes.get("size-pack", 0))) / 1024


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove old versions of bird photos from git history.")
    parser.add_argument("--apply", action="store_true", help="Actually rewrite history (default is a dry run)")
    args = parser.parse_args()

    all_blobs = photo_blobs_in_history()
    keep = photo_blobs_at_ref_tips()
    old = sorted(oid for oid in all_blobs if oid not in keep)
    full_bytes, disk_bytes = blob_sizes(old)

    print(f"Bird photo versions in history: {len(all_blobs)}")
    print(f"Current on a branch or tag (kept): {len(keep)}")
    print(f"Old versions to remove: {len(old)} ({full_bytes / 1048576:.1f} MB as files, "
          f"~{disk_bytes / 1048576:.1f} MB actually stored, which is roughly what removing them frees)")
    print(f"Repository object size now: {repo_size_mb():.1f} MB")
    if old:
        print("Examples:", ", ".join(sorted({all_blobs[oid].rsplit('/', 1)[1] for oid in old})[:8]), "...")

    loose = dict(line.split(": ", 1) for line in git("count-objects", "-v").splitlines() if ": " in line)
    if int(loose.get("count", 0)):
        print(f"Note: {loose['count']} recent git objects ({int(loose.get('size', 0)) / 1024:.1f} MB) aren't packed yet, so "
              "their size above is overstated. Run `git gc` first: it compresses near-identical versions "
              "without rewriting history, and may free most of this on its own.")

    if not old:
        print("Nothing to compact.")
        return
    if not args.apply:
        print("\nDry run only; nothing changed. Run with --apply to rewrite history "
              "(rake birds:compact_history -- --apply).")
        return

    if not shutil.which("git-filter-repo") and not Path(sys.executable).with_name("git-filter-repo").exists():
        sys.exit("git-filter-repo isn't installed. Run `rake birds:setup` (it's in scripts/birds/requirements.txt).")
    if git("status", "--porcelain").strip():
        sys.exit("You have uncommitted changes. Commit or stash them first, so nothing is lost in the rewrite.")

    print(
        "\nThis REWRITES GIT HISTORY for every branch and tag:\n"
        "  - every commit ID changes, so the result must be force-pushed\n"
        "  - any other clone of this repo must be deleted and re-cloned afterwards\n"
        "  - open pull requests based on the old history will break\n"
        "A full backup bundle is saved first."
    )
    if input(f"Type '{CONFIRM_WORD}' to continue: ").strip() != CONFIRM_WORD:
        sys.exit("Cancelled. Nothing changed.")

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = REPO_ROOT.parent / f"{REPO_ROOT.name}-history-backup-{stamp}.bundle"
    print(f"Saving backup bundle to {backup} ...")
    git("bundle", "create", str(backup), "--all", capture=False)

    # git-filter-repo removes the 'origin' remote as a safety measure; put it back afterwards
    origin_url = ""
    if "origin" in git("remote").split():
        origin_url = git("remote", "get-url", "origin").strip()

    filter_repo = shutil.which("git-filter-repo") or str(Path(sys.executable).with_name("git-filter-repo"))
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("\n".join(old) + "\n")
        ids_file = f.name
    print("Rewriting history with git-filter-repo ...")
    subprocess.run([filter_repo, "--strip-blobs-with-ids", ids_file, "--force"], cwd=REPO_ROOT, check=True)
    Path(ids_file).unlink()

    if origin_url and "origin" not in git("remote").split():
        git("remote", "add", "origin", origin_url)

    print(f"\nDone. Repository object size now: {repo_size_mb():.1f} MB")
    print(f"Backup bundle: {backup}  (restore with: git clone {backup} restored-repo)")
    print(
        "\nNothing has been pushed. When you've checked the site still builds:\n"
        "  git push --force --all origin\n"
        "  git push --force --tags origin\n"
        "GitHub may keep the old images reachable in its caches for a while; contact GitHub Support\n"
        "if you need them purged. Re-clone any other copies of the repository."
    )


if __name__ == "__main__":
    main()
