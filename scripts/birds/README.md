# Bird Photo Life List: Import Pipeline

This folder (`scripts/birds/`) holds the tools behind the bird photography page (`/birds/`). They take photos from `_staging/`, suggest the species with an offline AI model, look up the county from GPS, convert each photo to a copyright-stamped 800px WebP, and record everything in `_data/birds.yml`, which Jekyll turns into the page.

Everything runs in the dev container. Commands are Rake tasks; options go after `--` (for example `rake birds:import -- --americas`).

---

## Quick start

    rake birds:setup     # After a container rebuild: makes sure the AI model and data are in place
    rake birds:import    # Import whatever is in _staging/
    rake birds:doctor    # If anything seems wrong: checks everything and says how to fix it

1. Put photos (JPEG, PNG, TIFF, WebP, HEIC) in `_staging/`.
2. Run `rake birds:import` and answer the prompts. Each imported photo is removed from `_staging/`; anything skipped stays there for next time.
3. Commit `_data/birds.yml` and the new or changed files in `assets/img/birds/`.

---

## Everyday use

### Importing photos (`rake birds:import`)
For each photo in `_staging/` (in natural filename order, so `DSC_0099` comes before `DSC_0100`):

1. **Already imported?** If this exact photo is a bird's current photo, it's skipped (`[SKIP]`).
2. **Species.** The AI shows its top 3 guesses with confidence. Press `1`, `2` or `3` to pick one, `f` to search by name, or `s` to skip the photo.
   - Fuzzy search matches the common name, scientific name or 4-letter banding code across every species, even ones the AI isn't considering.
   - Guesses are marked "(already in catalog)" or "(locked, can't be replaced)".
3. **Replacing a photo.** If the species is already in the catalog, it asks before overwriting. If that bird has a note, choose `r` to keep it or `w` to wipe it.
4. **Location.** The county comes from the photo's GPS, offline. Without GPS, pick one of your recent counties or type `County, ST`.
5. **Saved.** The photo is converted and stamped, the catalog entry is written, and the staged original is removed.

### Options

| Command | What it does |
|---|---|
| `rake birds:import` | Interactive import (AI suggestions limited to regular US/Canada birds) |
| `rake birds:import -- --americas` | AI considers all 2,065 species of North and Central America, including strays. For trips to Mexico or Central America (not worldwide) |
| `rake birds:import -- --no-ai` | Skip the AI; go straight to fuzzy search |
| `rake birds:import -- --no-update` | Skip this run's monthly package update check |
| `rake birds:reimport` | `--force`: re-import photos even if they're already a bird's current photo |
| `rake birds:auto` | Import only the safe cases with no prompts (see below) |

### Auto mode (`rake birds:auto`)
Imports without any prompts, but only when it's safe:
- the AI's top suggestion is above 90% confidence,
- the species isn't already in the catalog (auto mode never replaces a photo), and
- the photo has GPS, so the county is known.

Everything else is logged as `[AUTO-SKIP]` with the reason and left in `_staging/`, so a normal `rake birds:import` afterwards handles just the leftovers.

### Locking a photo
To keep a species' photo from ever being replaced, add `locked: true` to its entry in `_data/birds.yml`:

    - species_common: Great Horned Owl
      ...
      locked: true

If an import picks a locked species, it prints a warning naming the protected photo and how to unlock it, then skips the file (it stays in `_staging/`). This holds even with `--force` and in auto mode. To replace it later, remove the line and import again.

### Notes
Add or edit `notes:` on any entry in `_data/birds.yml` (for example `notes: 'Vagrant!'`). Notes show on the bird's card and in the full-size photo viewer, and are kept (or wiped, your choice) when you replace that bird's photo.

### Fixing a mistake
- **Wrong date or location:** edit `date_taken` or `location` in `_data/birds.yml`. Photos are recognised by their `source_id`, not by these fields, so editing them never causes a re-import.
- **Imported under the wrong species:** the photo can be imported again. Re-stage the original and pick the right species. A replaced photo is forgotten (no history is kept), so it imports like any new photo.

---

## All commands

| Command | Purpose |
|---|---|
| `rake birds:setup` | Puts everything in place: eBird codes, the ABA checklist, the pinned AI model (downloaded once, verified) and its species embeddings. Safe to re-run; only downloads what's missing. Options: `-- --skip-models`, `--force`, `--refresh-counties`, `--refresh-aba` |
| `rake birds:import` | Interactive import (see "Options" above) |
| `rake birds:auto` | No-prompt import of the safe cases |
| `rake birds:reimport` | Import with `--force` |
| `rake birds:doctor` | Health check of every dependency, with the fix for anything broken |
| `rake birds:evaluate` | AI accuracy on your own catalog photos. Options: `-- --limit N`, `--americas`, `--model-dir DIR` |
| `rake birds:update_deps` | Check for Python package updates now (normally automatic, about monthly) |
| `rake birds:copyright` | Re-stamp the copyright tags into every photo (e.g. after changing the wording) |
| `rake birds:compact_history` | Rare: remove old photo versions from git history (dry run unless `-- --apply`) |

`scripts/birds/import_birds.py --backfill-ebird-codes` (run with `/opt/venv-birds/bin/python`) re-adds eBird codes to every catalog entry, e.g. after codes are added to the taxonomy.

---

## Setup and health

### After a container rebuild
The rebuild installs the system tools and Python packages automatically (see "Container and dependencies"). Then run:

    rake birds:setup
    rake birds:doctor

The AI model lives on your Mac's disk (`scripts/birds/models/`), so it survives rebuilds and isn't downloaded again.

### When something breaks
Run `rake birds:doctor`. It checks:
- the system tools (exiftool, ImageMagick)
- every locked package
- the county map, the taxonomy and the catalog's photo files
- the ABA checklist
- the AI model (checksums, loading, and recognising a known photo)
- the last automatic update check

Each problem prints a ✗ with the command that fixes it. The last two lines say whether imports work and whether AI suggestions do.

**A broken AI never blocks imports.** They fall back to fuzzy search automatically, or use `-- --no-ai`.

---

## How it works

### Recognising photos already imported
Each photo gets a `source_id`: `{filename}_{capture time}_{first 8 characters of its SHA-256}`, for example `DSC_4102.JPG_20260814T093012_a9f4c21b`. The capture time comes from the photo's EXIF (or the file's modified time if it has none). If a staged photo's `source_id` is some bird's current photo, it's skipped.

### Species suggestions
The AI is [BioCLIP](https://huggingface.co/imageomics/bioclip), a model trained on biology images. It runs offline from `scripts/birds/models/bioclip/` (see `bird_model.py`).

1. **Text embeddings, once.** Setup turns a description of every species ("a photo of American Kestrel (Falco sparverius), family Falconidae") into a text embedding, cached in `bioclip_species_embeddings.pt`.
2. **Image embedding, per photo.** Each photo is encoded twice: the full frame and a 70% centre crop. The two are averaged and compared against every allowed species' text embedding. The three closest are suggested.
3. **Which species are allowed.** Suggestions are limited to species with [ABA Checklist](https://www.aba.org/aba-checklist/) codes 1–3 (regular and rare US/Canada birds, 842 of the taxonomy's 2,065), plus any species already in your catalog. This keeps the model from picking look-alikes from other continents. `--americas` lifts the limit. Fuzzy search is never limited.
4. **The checklist stays local.** It's copyrighted, so setup downloads it to `scripts/birds/data/` (gitignored), and it's never published with the site.

### GPS to county
The photo's GPS position is matched offline against US county boundaries (`us_counties.geojson`, committed) with `shapely`. A ~10-mile fallback catches birds photographed off piers or shorelines, so they still match the adjacent county.

### Conversion, privacy and copyright
1. **ImageMagick:**
   - converts to sRGB first, so wide-gamut photos don't look washed out
   - resizes to 800px wide (Lanczos)
   - sharpens lightly and strips profiles
   - saves WebP at quality 84
2. **exiftool removes all metadata:** GPS, camera and original timestamps never reach the site.
3. **Copyright tags are written back** (`stamp_copyright`):
   - EXIF Artist and Copyright
   - XMP creator, rights, "copyrighted", and a link to `assets/img/birds/LICENSE.txt`
   - the year comes from when the photo was taken
   - compact XMP keeps this under 1 KB per photo

   `rake birds:copyright` re-stamps every existing photo.

---

## The catalog (`_data/birds.yml`)
One entry per species, sorted by `date_taken`. Most fields are written by the import; two are yours to edit.

| Field | Meaning |
|---|---|
| `species_common`, `species_scientific` | Names, from the taxonomy |
| `banding_code`, `ebird_code` | 4-letter banding code; eBird species code (drives the photo viewer's "View on eBird" link) |
| `slug`, `filename` | URL-safe name and the photo's file in `assets/img/birds/` |
| `family`, `sibley_category`, `sibley_category_order`, `taxonomic_order` | Grouping and order on the page (by Sibley category, then taxonomic order) |
| `date_taken`, `location` | When and where (county) the photo was taken. Safe to correct by hand |
| `source_filename`, `source_id` | The original file and its fingerprint (see "Recognising photos already imported") |
| `notes` | *Yours.* Shown on the card and in the photo viewer |
| `locked` | *Yours.* `true` stops any import from replacing the photo |

---

## The `/birds/` page
The page itself is built by Jekyll from the catalog:
- `_layouts/birds.html` (markup and scripts)
- `_sass/_birds.scss` (styles, loaded through `_includes/extra/birds.scss`)
- `_pages_standalone/birds.md` (intro text and settings)

What the page does:
- **Grid:** birds grouped by Sibley category, sorted taxonomically, so close relatives sit together.
- **"New" badges:** mark birds photographed in the last 60 days. The visitor's browser compares each photo date with its own current date on every view, so badges expire by themselves without a redeploy.
- **"New" button:** beside the find box, shows how many birds are new and, when pressed, narrows the grid to just those (it combines with the find box). It hides itself when nothing is new.
- **Stats under the title:** pills with the species count and the most recent photo, which links to its card. Like the copyright years (in the notice under the find box), they're fixed at build time and change when you deploy new photos.
- **Navigation:**
  - On desktop, a category index sits in the left margin, highlights the current section, and the section headings stick.
  - On phones, a floating bar shows the current category and opens a category picker, with a back-to-top button.
  - Each heading has a permalink, and "Updated on … with the X" links to that bird's card.
- **Find a bird:** filters the grid by common or scientific name as you type (ignoring hyphens, apostrophes and accents), and hides empty categories.
- **Photo viewer:**
  - Click a photo to open it. Use ← / → or the buttons on desktop, swipe on phones (swipe down to close).
  - The caption shows the species and location, the date and time, any note, and "View on eBird".
  - Closing it jumps the page to the last bird viewed.
- **Bandwidth:** a photo only downloads once scrolling settles near it, so jumping or flinging past birds doesn't download them. Each photo downloads at most once.
- **Discussion:** Disqus comments at the bottom, in production builds only. They load only when a reader gets near them or follows "Join the discussion below".
- **Copyright and crawlers:**
  - The page shows "All photographs © … All rights reserved."
  - The photos are all rights reserved (`assets/img/birds/LICENSE.txt`), separate from the repository's MIT-licensed code.
  - `robots.txt` keeps AI crawlers away from the photos, while allowing search engines and the Internet Archive.
- **Accessibility:**
  - Real buttons, alt text that names collages, spoken labels for the emoji, and a screen-reader-friendly photo viewer.
  - Without JavaScript, the page shows a note instead of photos, so the photo URLs aren't exposed to scrapers.

---

## Maintenance

### Adding a species that's missing from the taxonomy
`taxonomy_sibley.csv` covers North and Central America: 2,065 species, every bird on the ABA Checklist that can still be seen, and Central American species. If fuzzy search can't find a bird, add it by hand. Wrentit and 18 others were added this way in October 2026.

1. **Look up its eBird details.** Use the scientific name or eBird's species code:

       curl -s "https://api.ebird.org/v2/ref/taxonomy/ebird?cat=species&fmt=csv&species=wrenti" | cut -d, -f1-11

   You need `SCIENTIFIC_NAME`, `COMMON_NAME`, `SPECIES_CODE` (the `ebird_code`), `TAXON_ORDER` (the `taxonomic_order`, without the `.0`), `BANDING_CODES` and `FAMILY_SCI_NAME`.

2. **Pick its category.** Find the family in `sibley_family_map.json`, which gives its `sibley_category` and `sibley_category_order` (1–35).
   - If the family isn't there, choose the category where its closest relatives are, and add a line for the family so future rebuilds keep it:

         "Paradoxornithidae": { "sibley_category": "Kinglets, Old World Warblers, and Thrush Allies", "sibley_category_order": 25 },

3. **Banding code.** Use eBird's if it has one; otherwise make a 4-letter code that isn't already used in the file.
   - The convention (`generate_fallback_banding_code` in `setup_offline_assets.py`) is the first letters of each word, e.g. Hen Harrier → `HEHA`.
   - For a species with no official code, also add its scientific name to `SPECIES_WITHOUT_BANDING_CODES` in `setup_offline_assets.py`, so a future rebuild keeps it.

4. **Add the row** to `taxonomy_sibley.csv`, keeping the file sorted by `sibley_category_order`, then `taxonomic_order` (a spreadsheet works fine):

       common_name,scientific_name,banding_code,family,sibley_category,sibley_category_order,taxonomic_order,ebird_code
       Wrentit,Chamaea fasciata,WREN,Paradoxornithidae,"Kinglets, Old World Warblers, and Thrush Allies",25,25431,wrenti

5. **Rebuild the AI's embeddings (the `.pt` file).** The AI only knows species that have an embedding in `bioclip_species_embeddings.pt`.
   - The file records the exact species list and model revision it was built for. Whenever the CSV's species list changes, it's out of date and is rebuilt automatically.
   - To do it up front rather than at the start of your next import (takes about a minute), run:

         rake birds:setup

   - To force a rebuild, delete `scripts/birds/bioclip_species_embeddings.pt` and run `rake birds:setup`.

6. **Check it.** `rake birds:doctor` should report the new species count and "Species embeddings cached for this model and taxonomy".
   - If the bird is regular in the US or Canada (ABA code 1–3), the AI can now suggest it. Otherwise it's available through fuzzy search, or AI suggestions with `--americas`.

**Avoid `rake birds:setup -- --force` unless you mean it.** It rebuilds the whole taxonomy from eBird's current release, which can rename species and renumber `taxonomic_order`. Hand-added rows survive only if their family is in `sibley_family_map.json`, and, for species without a banding code, they're in `SPECIES_WITHOUT_BANDING_CODES`.

### Staying up to date (automatic)
You never edit package versions. `requirements.in` / `requirements-ai.in` list what's needed. `requirements.txt` / `requirements-ai.txt` are generated lock files with the exact versions that last passed the checks.

About once a month, at the start of an import, `update_deps.py`:
1. builds the newest versions in a scratch environment (`/tmp/venv-birds-candidate`),
2. runs the health check there and, if AI suggestions work today, a 30-photo accuracy test that must match today's result,
3. only if both pass, writes new lock files, installs them, and restarts the import on the new versions.

It prints what changed; commit the changed `requirements*.txt` when convenient.

If anything fails, nothing changes. You stay on the working versions, see one line saying why (details in `scripts/birds/.deps-update.log`), and it retries in a week. Without internet it simply tries next time.

- **Check now:** `rake birds:update_deps`.
- **Skip once:** `rake birds:import -- --no-update` (or set `BIRDS_NO_UPDATE=1`).
- **Add a package:** add its name to the right `.in` file and run `rake birds:update_deps`.

The container's Python comes from Debian `bookworm` (Python 3.11), set in `.devcontainer/devcontainer.json`, so it only changes when you change that. After moving to a newer release, run `rake birds:update_deps` to relock.

The AI model is deliberately *not* auto-updated, since a new model changes which birds get suggested. See the next section.

### Replacing the AI model (or when it disappears)
The model is pinned to `MODEL_REVISION` in `bird_model.py` and checked against `model-checksums.txt`. Once downloaded it never touches the network, so it keeps working even if it changes or vanishes from Hugging Face, **as long as you keep `scripts/birds/models/`**. Back that folder up with your photos.

To try a replacement:
1. **Find a candidate** that open_clip can load (a folder with `open_clip_config.json` plus weights). Biology or bird-focused CLIP models, such as BioCLIP's successors, are the best bet.
2. **Download it to its own folder:**

       /opt/venv-birds/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('ORG/MODEL', local_dir='scripts/birds/models/candidate')"

3. **Measure it against your photos:**

       rake birds:evaluate -- --model-dir scripts/birds/models/candidate

4. **Switch if it's as good or better.**
   - In `bird_model.py`, set `MODEL_REPO`, `MODEL_REVISION` (the Hugging Face commit) and `MODEL_FILES` (and `MODEL_DIR` if you like).
   - Delete `model-checksums.txt`, then run `rake birds:setup`. It downloads the pinned revision, records fresh checksums (commit them) and rebuilds the embeddings.
   - Run `rake birds:doctor`.

**Baseline** (BioCLIP `ce901ab3`, October 2026, 167 catalog photos; top-3 is what the import shows):

| Species considered | Top-1 | Top-3 | Singles (top-1 / top-3) | Collages (top-1 / top-3) |
|---|---|---|---|---|
| ABA codes 1–3, 842 species (default) | 76.6% | 89.2% | 75.6% / 89.1% | 79.2% / 89.6% |
| All 2,065 of North and Central America (`--americas`) | 72.5% | 87.4% | 71.4% / 87.4% | 75.0% / 87.5% |

About 0.12 s per photo. The remaining misses are hard pairs (Cooper's vs Sharp-shinned Hawk, Alder vs Willow Flycatcher) and gulls.

### Shrinking the repository (old photo versions in git history)
Every replaced photo leaves its old version in git history. If the repository ever gets too big:

    rake birds:compact_history                # Dry run: what would be removed and roughly how much it frees
    rake birds:compact_history -- --apply     # Rewrites history (asks you to type "compact" first)

**This rewrites history.** Every commit ID changes, so the result has to be force-pushed (`git push --force --all origin`, `git push --force --tags origin`), and other clones must be re-cloned.

`--apply` protects you:
- It refuses to run with uncommitted changes.
- It saves a backup bundle (`../website-history-backup-<date>.bundle`) first.
- It keeps any photo version that's current on some branch or tag.
- It never pushes.

**Try `git gc` first.** Near-identical versions (like a copyright re-stamp) are stored as tiny deltas once packed, so `git gc` alone often frees most of the space without rewriting anything. The dry run says when unpacked objects are inflating its estimate.

### Changing image size or format
In `import_birds.py`, `process_image_to_webp()` has `width: int = 800` and `quality: int = 84`. For a different format, also change `dest_filename = f"{slug}.webp"` in `main()`. Existing photos keep their old size until replaced.

### Changing the catalog's storage format
All catalog reading and writing is in `load_catalog()` / `save_catalog()` in `import_birds.py`. Jekyll reads `.yml`, `.json` or `.csv` from `_data/` the same way, so switching to `_data/birds.json` only means changing those two functions; the page doesn't change.

### Template notes (`_layouts/birds.html`)
- **Sorting.** Liquid can't sort by nested values, and Jekyll's `sort` isn't stable (chaining two sorts can scramble the inner order). So the layout sorts by category, groups, then sorts each group:

      {% assign birds_by_category = site.data.birds | sort: "sibley_category_order" %}
      {% assign grouped_categories = birds_by_category | group_by: "sibley_category" %}
      {% for category in grouped_categories %}
        {% assign category_birds = category.items | sort: "taxonomic_order" %}

- **Photo shapes.** Grid images use `object-fit: contain` in a 4:3 box, so other shapes are letterboxed on grey, never cropped.

---

## File map
Paths are relative to the repository root.

    .devcontainer/post-create.sh             # Installs system tools and the Python venv (/opt/venv-birds)
    _staging/                                # Put photos to import here (gitignored)
    _data/birds.yml                          # The catalog
    assets/img/birds/                        # 800px WebP photos + LICENSE.txt (all rights reserved)
    _layouts/birds.html, _sass/_birds.scss   # The /birds/ page
    _pages_standalone/birds.md               # Page intro and settings
    Rakefile                                 # rake birds:* tasks
    scripts/birds/
        import_birds.py                      # The import (rake birds:import / auto / reimport / copyright)
        bird_model.py                        # The pinned AI model: download, verify, load, species list, predict
        setup_offline_assets.py              # rake birds:setup
        doctor.py                            # rake birds:doctor
        evaluate_model.py                    # rake birds:evaluate
        update_deps.py                       # Automatic tested package updates (rake birds:update_deps)
        compact_history.py                   # rake birds:compact_history
        taxonomy_sibley.csv                  # 2,065 species with Sibley category, taxonomic order, eBird code
        sibley_family_map.json               # Bird family -> Sibley category
        us_counties.geojson                  # US county boundaries (committed)
        requirements.in, requirements-ai.in  # Python packages needed (names only)
        requirements.txt, requirements-ai.txt  # GENERATED locks: exact versions that last passed the checks
        model-checksums.txt                  # sha256 of the pinned model files
        models/bioclip/                      # (gitignored, ~600 MB) The AI model. Back it up!
        data/aba_checklist.csv               # (gitignored, copyrighted) ABA Checklist, local only
        bioclip_species_embeddings.pt        # (gitignored) Species embeddings, rebuilt automatically
        .deps-state.json, .deps-update.log   # (gitignored) Last automatic update check

---

## Container and dependencies
When the dev container is built, `.devcontainer/post-create.sh` installs:
1. **System tools (apt):**
   - `libimage-exiftool-perl` (reads capture time and GPS, strips metadata, writes copyright tags)
   - `imagemagick` (conversion)
   - `python3-venv`
2. **The Python venv at `/opt/venv-birds`.** It's kept outside the repository because Jekyll's file watcher crawls every folder in the repo, and torch's thousands of folders added ~45s to `rake serve`.
   - The **core** lock (`requirements.txt`) is required.
   - The **AI** lock (`requirements-ai.txt`) is optional: if it fails, the container still builds and imports use fuzzy search.

| Tier | Packages (in the `.in` files) | Used for |
|---|---|---|
| Core | pyyaml, natsort, shapely, prompt_toolkit, rich, pillow, git-filter-repo | Catalog, file order, GPS → county, prompts and fuzzy search, console output, image loading, history compaction |
| AI | torch, torchvision (CPU builds), open_clip_torch, huggingface_hub | Running BioCLIP and downloading it the first time |
