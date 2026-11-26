#!/usr/bin/env python3
"""
Unit tests for the bird portfolio pipeline.

Designed to run both in a bare Python 3 standard-library environment (e.g. GitHub
Actions CI) and inside /opt/venv-birds or a macOS dev environment with ImageMagick,
exiftool, Pillow, PyYAML, Shapely, and Rich installed. Tests requiring optional
system tools or third-party packages are skipped cleanly via @unittest.skipUnless.

Run with:
    python3 -m unittest discover -s scripts/birds -p 'test_*.py' -v
"""

import datetime
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import bird_common
import bird_model
import doctor
import setup_offline_assets
import update_deps

HAS_MAGICK = bool(shutil.which("magick") or shutil.which("convert"))
HAS_EXIFTOOL = bool(shutil.which("exiftool"))
HAS_PIL = importlib.util.find_spec("PIL") is not None
HAS_YAML = importlib.util.find_spec("yaml") is not None
HAS_SHAPELY = importlib.util.find_spec("shapely") is not None
HAS_RICH = importlib.util.find_spec("rich") is not None
HAS_IMPORT_BIRDS_DEPS = all(
    importlib.util.find_spec(mod) is not None
    for mod in ("yaml", "natsort", "prompt_toolkit", "rich")
)

MACOS_DISPLAY_P3_ICC = Path("/System/Library/ColorSync/Profiles/Display P3.icc")


def _exiftool_json(path: Path) -> dict:
    res = subprocess.run(["exiftool", "-j", str(path)], capture_output=True, text=True, check=True)
    data = json.loads(res.stdout)
    return data[0] if data else {}


class TestBirdCommon(unittest.TestCase):
    def test_slugify(self) -> None:
        self.assertEqual(bird_common.slugify("American Robin"), "american-robin")
        self.assertEqual(bird_common.slugify("Woodhouse's Scrub-Jay"), "woodhouses-scrub-jay")
        self.assertEqual(bird_common.slugify("Cooper’s Hawk"), "coopers-hawk")
        self.assertEqual(bird_common.slugify("  Black-legged Kittiwake!  "), "black-legged-kittiwake")
        self.assertEqual(bird_common.slugify("Great   Blue---Heron"), "great-blue-heron")

    def test_is_collage(self) -> None:
        self.assertTrue(bird_common.is_collage("20261023_142445-COLLAGE.jpg"))
        self.assertTrue(bird_common.is_collage("photo-collage.jpeg"))
        self.assertTrue(bird_common.is_collage(Path("/tmp/20260714-Collage.PNG")))
        self.assertTrue(bird_common.is_collage("2026-COLLAGE-2.jpg"))
        self.assertFalse(bird_common.is_collage("american-robin.jpg"))
        self.assertFalse(bird_common.is_collage("mycollage.jpg"))
        self.assertFalse(bird_common.is_collage("collage-photo.jpg"))
        self.assertFalse(bird_common.is_collage(""))

    def test_parse_user_timestamp_valid(self) -> None:
        cases = [
            # 24-hour formats
            ("2025-04-12 09:09", "2025-04-12T09:09:00"),
            ("2025-04-12T21:09:30", "2025-04-12T21:09:30"),
            ("2025-04-12 0:05", "2025-04-12T00:05:00"),
            ("  2025-4-2   14:07:09  ", "2025-04-02T14:07:09"),
            # am/pm and 12am/12pm edge cases
            ("2025-04-12 9:09 am", "2025-04-12T09:09:00"),
            ("2025-04-12 9:09 p.m.", "2025-04-12T21:09:00"),
            ("2025-04-12 12:00 am", "2025-04-12T00:00:00"),
            ("2025-04-12 12:15 a.m.", "2025-04-12T00:15:00"),
            ("2025-04-12 12:00 pm", "2025-04-12T12:00:00"),
            ("2025-04-12 12:45 PM", "2025-04-12T12:45:00"),
            # Google Photos written formats (@, at, comma, bullet, hyphen, abbreviations)
            ("October 23, 2026 @ 1:16 PM", "2026-10-23T13:16:00"),
            ("April 12, 2025 at 9:09 AM", "2025-04-12T09:09:00"),
            ("Sept 5, 2025, 11:45 pm", "2025-09-05T23:45:00"),
            ("Oct. 3, 2024 • 7:05:12 am", "2024-10-03T07:05:12"),
            ("Mar 1 2024 - 12:00 pm", "2024-03-01T12:00:00"),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(bird_common.parse_user_timestamp(raw), expected)

    def test_parse_user_timestamp_invalid(self) -> None:
        invalid = [
            "",
            "not a date",
            "2025-04-12",  # missing time
            "2025-02-30 10:00",  # invalid calendar date
            "Feb 30, 2025 @ 10:00 AM",
            "2025-04-12 13:00 pm",  # hour > 12 with meridiem
            "2025-04-12 0:30 am",  # hour 0 with meridiem
            "2025-04-12 24:00",  # hour 24 invalid
            "2025-04-12 10:60",  # minute 60 invalid
            "Oc 12, 2025 9:00 AM",  # abbreviation < 3 letters
            "Foo 12, 2025 9:00 AM",  # unknown month
        ]
        for raw in invalid:
            with self.subTest(raw=raw):
                self.assertIsNone(bird_common.parse_user_timestamp(raw))

    def test_extract_and_normalize_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            photo = Path(tmp) / "bird.jpg"
            photo.write_bytes(b"fake")
            fixed_dt = datetime.datetime(2024, 6, 15, 8, 30, 45)
            ts = fixed_dt.timestamp()
            os.utime(photo, (ts, ts))

            # Priority: DateTimeOriginal > CreateDate > ModifyDate
            exif_all = {
                "DateTimeOriginal": "2025:05:01 07:15:22",
                "CreateDate": "2025:05:02 08:00:00",
                "ModifyDate": "2025:05:03 09:00:00",
            }
            self.assertEqual(bird_common.extract_timestamp(exif_all, photo), ("2025-05-01T07:15:22", True))
            self.assertEqual(bird_common.normalize_timestamp(exif_all, photo), "2025-05-01T07:15:22")

            exif_create = {
                "CreateDate": "2025-05-02 08:00:00-04:00",
                "ModifyDate": "2025:05:03 09:00:00",
            }
            self.assertEqual(bird_common.extract_timestamp(exif_create, photo), ("2025-05-02T08:00:00", True))

            exif_modify = {"ModifyDate": "2025:05:03 09:10:11"}
            self.assertEqual(bird_common.extract_timestamp(exif_modify, photo), ("2025-05-03T09:10:11", True))

            # Missing / unparseable EXIF falls back to file mtime with from_exif=False
            self.assertEqual(bird_common.extract_timestamp({}, photo), ("2024-06-15T08:30:45", False))
            self.assertEqual(bird_common.normalize_timestamp({}, photo), "2024-06-15T08:30:45")
            self.assertEqual(
                bird_common.extract_timestamp({"DateTimeOriginal": "not-a-date"}, photo),
                ("2024-06-15T08:30:45", False),
            )

    def test_sanitize_staged_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            # Unchanged when no brackets
            plain = root / "robin.jpg"
            plain.write_bytes(b"a")
            self.assertEqual(bird_common.sanitize_staged_filename(plain), plain)

            # Strips brackets cleanly
            bracketed = root / "hawk[0].jpg"
            bracketed.write_bytes(b"b")
            cleaned = bird_common.sanitize_staged_filename(bracketed)
            self.assertEqual(cleaned, root / "hawk0.jpg")
            self.assertTrue(cleaned.is_file())
            self.assertFalse(bracketed.exists())

            # Collision adds _1 suffix without clobbering existing file
            colliding = root / "hawk[0].jpg"
            colliding.write_bytes(b"c")
            renamed = bird_common.sanitize_staged_filename(colliding)
            self.assertEqual(renamed, root / "hawk0_1.jpg")
            self.assertEqual(cleaned.read_bytes(), b"b")
            self.assertEqual(renamed.read_bytes(), b"c")

    def test_parse_requirements_pins_and_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock = root / "requirements.txt"
            lock.write_text(
                "# header comment\n"
                "--extra-index-url https://download.pytorch.org/whl/cpu\n"
                "PyYAML==6.0.2  # inline comment\n"
                "prompt_toolkit==3.0.50\n"
                "open-clip-torch==2.32.0\n"
                "  Pillow==11.1.0\n",
                encoding="utf-8",
            )
            self.assertEqual(
                bird_common.parse_requirements_pins(lock),
                {
                    "pyyaml": "6.0.2",
                    "prompt-toolkit": "3.0.50",
                    "open-clip-torch": "2.32.0",
                    "pillow": "11.1.0",
                },
            )

            req_in = root / "requirements.in"
            req_in.write_text(
                "# direct deps\n"
                "--extra-index-url https://example.com/simple\n"
                "PyYAML>=6.0  # yaml parser\n"
                "prompt_toolkit\n"
                "shapely[vectorized]>=2.0\n"
                "  \n",
                encoding="utf-8",
            )
            self.assertEqual(
                bird_common.parse_requirements_in(req_in, normalize=True),
                ["pyyaml", "prompt-toolkit", "shapely"],
            )
            self.assertEqual(
                bird_common.parse_requirements_in(req_in, normalize=False),
                ["PyYAML", "prompt_toolkit", "shapely"],
            )

    def test_build_source_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            photo = Path(tmp) / "PXL_20250721_192936013.jpg"
            payload = b"sample-bird-photo-bytes"
            photo.write_bytes(payload)
            expected_hash = hashlib.sha256(payload).hexdigest()[:8]
            self.assertEqual(
                bird_common.build_source_id(photo, "2025-07-21T11:29:36"),
                f"PXL_20250721_192936013.jpg_20250721T112936_{expected_hash}",
            )


@unittest.skipUnless(HAS_MAGICK and HAS_EXIFTOOL and HAS_PIL, "requires ImageMagick, exiftool, and Pillow")
class TestImageProcessing(unittest.TestCase):
    def test_resize_large_and_preserve_small(self) -> None:
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            # Large 1200x900 image -> resized to 800x600
            large_src = root / "large.png"
            large_dest = root / "large.webp"
            Image.new("RGB", (1200, 900), (40, 120, 200)).save(large_src)
            bird_common.process_image_to_webp(large_src, large_dest, year="2026")
            with Image.open(large_dest) as out:
                self.assertEqual(out.size, (800, 600))

            # Small 400x300 crop -> NOT upscaled
            small_src = root / "small.png"
            small_dest = root / "small.webp"
            Image.new("RGB", (400, 300), (80, 160, 60)).save(small_src)
            bird_common.process_image_to_webp(small_src, small_dest, year="2026")
            with Image.open(small_dest) as out:
                self.assertEqual(out.size, (400, 300))

    def test_exif_orientation_rotated_upright(self) -> None:
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "sideways.jpg"
            dest = root / "upright.webp"

            # Raw 400x200: top half red, bottom half blue.
            # Orientation=6 means rotate 90 deg CW -> 200x400 with right half red, left half blue.
            img = Image.new("RGB", (400, 200), (20, 40, 220))
            img.paste((220, 30, 20), (0, 0, 400, 100))
            exif = Image.Exif()
            exif[274] = 6  # Orientation = Rotate 90 CW
            img.save(src, format="JPEG", quality=95, exif=exif.tobytes())

            bird_common.process_image_to_webp(src, dest, year="2026")
            with Image.open(dest) as out:
                self.assertEqual(out.size, (200, 400))
                left_px = out.getpixel((40, 200))
                right_px = out.getpixel((160, 200))
                self.assertGreater(left_px[2], 150, f"expected blue on left, got {left_px}")
                self.assertGreater(right_px[0], 150, f"expected red on right, got {right_px}")

    def test_display_p3_converted_to_srgb_and_icc_stripped(self) -> None:
        from PIL import Image, ImageCms

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "wide_gamut.png"
            dest = root / "srgb.webp"

            if MACOS_DISPLAY_P3_ICC.is_file():
                p3_bytes = MACOS_DISPLAY_P3_ICC.read_bytes()
                raw_rgb = (220, 60, 40)
                img = Image.new("RGB", (200, 200), raw_rgb)
                img.save(src, format="PNG", icc_profile=p3_bytes)

                # Reference conversion via Pillow ImageCms
                p3_prof = ImageCms.ImageCmsProfile(io.BytesIO(p3_bytes))
                srgb_prof = ImageCms.createProfile("sRGB")
                expected_rgb = ImageCms.profileToProfile(img, p3_prof, srgb_prof).getpixel((100, 100))

                bird_common.process_image_to_webp(src, dest, year="2026")
                with Image.open(dest) as out:
                    self.assertIsNone(out.info.get("icc_profile"))
                    actual_rgb = out.getpixel((100, 100))
                    # Must genuinely convert away from raw P3 values toward sRGB
                    shift_from_raw = sum(abs(a - r) for a, r in zip(actual_rgb, raw_rgb))
                    diff_from_expected = max(abs(a - e) for a, e in zip(actual_rgb, expected_rgb))
                    self.assertGreater(shift_from_raw, 20, f"expected P3->sRGB shift, got {actual_rgb} vs raw {raw_rgb}")
                    self.assertLessEqual(diff_from_expected, 12, f"got {actual_rgb}, expected near {expected_rgb}")
            else:
                # Fallback when Display P3 profile isn't installed on the host: verify ICC stripping
                srgb_bytes = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
                Image.new("RGB", (200, 200), (120, 180, 90)).save(src, format="PNG", icc_profile=srgb_bytes)
                bird_common.process_image_to_webp(src, dest, year="2026")
                with Image.open(dest) as out:
                    self.assertIsNone(out.info.get("icc_profile"))

    def test_multiframe_tiff_exports_first_frame(self) -> None:
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "multipage.tiff"
            dest = root / "single.webp"

            frame0 = Image.new("RGB", (300, 200), (220, 30, 30))  # red
            frame1 = Image.new("RGB", (300, 200), (30, 30, 220))  # blue
            frame0.save(src, format="TIFF", save_all=True, append_images=[frame1])

            bird_common.process_image_to_webp(src, dest, year="2026")
            with Image.open(dest) as out:
                self.assertEqual(getattr(out, "n_frames", 1), 1)
                self.assertEqual(out.size, (300, 200))
                r, g, b = out.getpixel((150, 100))
                self.assertGreater(r, 170)
                self.assertLess(b, 80)

    def test_gps_and_camera_stripped_and_copyright_stamped(self) -> None:
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "tagged.jpg"
            dest = root / "clean.webp"

            Image.new("RGB", (320, 240), (100, 140, 90)).save(src, format="JPEG", quality=92)
            subprocess.run(
                [
                    "exiftool",
                    "-overwrite_original",
                    "-GPSLatitude=42.9634",
                    "-GPSLatitudeRef=N",
                    "-GPSLongitude=85.6681",
                    "-GPSLongitudeRef=W",
                    "-Make=TestCam",
                    "-Model=BirdMaster 5000",
                    "-DateTimeOriginal=2024:05:10 08:22:11",
                    str(src),
                ],
                capture_output=True,
                check=True,
            )

            bird_common.process_image_to_webp(src, dest, year="2024")
            meta = _exiftool_json(dest)

            for forbidden in ("GPSLatitude", "GPSLongitude", "Make", "Model", "DateTimeOriginal"):
                self.assertNotIn(forbidden, meta, f"unexpected {forbidden} in exported WebP")

            expected_notice = f"© 2024 {bird_common.COPYRIGHT_HOLDER}. All rights reserved."
            self.assertEqual(meta.get("Artist"), bird_common.COPYRIGHT_HOLDER)
            self.assertEqual(meta.get("Copyright"), expected_notice)
            self.assertEqual(meta.get("Creator"), bird_common.COPYRIGHT_HOLDER)
            self.assertEqual(meta.get("Rights"), expected_notice)
            self.assertEqual(meta.get("Marked"), True)
            self.assertEqual(meta.get("WebStatement"), bird_common.COPYRIGHT_LICENSE_URL)

    def test_batched_stamp_copyright(self) -> None:
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p1 = root / "one.webp"
            p2 = root / "two.webp"
            Image.new("RGB", (120, 120), (10, 20, 30)).save(p1, format="WEBP")
            Image.new("RGB", (120, 120), (30, 20, 10)).save(p2, format="WEBP")

            bird_common.stamp_copyright([p1, p2], "2026")

            expected_notice = f"© 2026 {bird_common.COPYRIGHT_HOLDER}. All rights reserved."
            for p in (p1, p2):
                meta = _exiftool_json(p)
                self.assertEqual(meta.get("Copyright"), expected_notice)
                self.assertEqual(meta.get("Rights"), expected_notice)


class TestBirdModel(unittest.TestCase):
    def test_name_variants(self) -> None:
        self.assertEqual(bird_model._name_variants(""), [])
        self.assertEqual(bird_model._name_variants("American Robin"), ["american robin"])
        self.assertEqual(bird_model._name_variants("Woodhouse’s Scrub-Jay"), ["woodhouse's scrub-jay"])

        sci_variants = set(bird_model._name_variants("Setophaga aestiva (petechia)"))
        self.assertEqual(sci_variants, {"setophaga aestiva", "setophaga petechia"})

        common_variants = set(bird_model._name_variants("Northern Yellow (Yellow) Warbler"))
        self.assertIn("northern yellow warbler", common_variants)
        self.assertIn("yellow warbler", common_variants)

    def test_allowed_species(self) -> None:
        rows = [
            {"common_name": "American Robin", "scientific_name": "Turdus migratorius"},
            {"common_name": "Snowy Owl", "scientific_name": "Bubo scandiacus"},
            {"common_name": "Blue Mockingbird", "scientific_name": "Melanotis caerulescens"},
            {"common_name": "Resplendent Quetzal", "scientific_name": "Pharomachrus mocinno"},
        ]
        fake_aba = {
            "turdus migratorius": 1,
            "bubo scandiacus": 3,
            "melanotis caerulescens": 4,  # above ABA_MAX_CODE (3)
        }

        with mock.patch.object(bird_model, "aba_codes", return_value=fake_aba):
            allowed, desc = bird_model.allowed_species(rows)
            self.assertEqual(allowed, [0, 1])
            self.assertIn("2 species", desc)

            allowed_inc, _ = bird_model.allowed_species(rows, always_include=["Resplendent Quetzal"])
            self.assertEqual(allowed_inc, [0, 1, 3])

            allowed_americas, desc_americas = bird_model.allowed_species(rows, americas=True)
            self.assertIsNone(allowed_americas)
            self.assertIn("--americas", desc_americas)

        with mock.patch.object(bird_model, "aba_codes", return_value={}):
            allowed_missing, desc_missing = bird_model.allowed_species(rows)
            self.assertIsNone(allowed_missing)
            self.assertIn("ABA checklist missing", desc_missing)

    def test_prompts_hash_changes_with_taxonomy_fields(self) -> None:
        base = [
            {"common_name": "American Robin", "scientific_name": "Turdus migratorius", "family": "Turdidae"},
        ]
        h_base = bird_model.prompts_hash(base)
        self.assertEqual(h_base, bird_model.prompts_hash(base))

        diff_sci = [
            {"common_name": "American Robin", "scientific_name": "Turdus confinis", "family": "Turdidae"},
        ]
        diff_fam = [
            {"common_name": "American Robin", "scientific_name": "Turdus migratorius", "family": "Muscicapidae"},
        ]
        self.assertNotEqual(h_base, bird_model.prompts_hash(diff_sci))
        self.assertNotEqual(h_base, bird_model.prompts_hash(diff_fam))

    def test_cache_matches_legacy_and_prompt_hash(self) -> None:
        names = ["American Robin"]
        self.assertTrue(
            bird_model._cache_matches({"model_revision": "rev1", "common_names": names}, "rev1", names, "hashA")
        )
        self.assertTrue(
            bird_model._cache_matches(
                {"model_revision": "rev1", "common_names": names, "prompt_hash": "hashA"}, "rev1", names, "hashA"
            )
        )
        self.assertFalse(
            bird_model._cache_matches(
                {"model_revision": "rev1", "common_names": names, "prompt_hash": "hashB"}, "rev1", names, "hashA"
            )
        )
        self.assertFalse(
            bird_model._cache_matches(
                {"model_revision": "rev2", "common_names": names, "prompt_hash": "hashA"}, "rev1", names, "hashA"
            )
        )

    @unittest.skipUnless(HAS_PIL, "requires Pillow")
    def test_open_rgb_image_applies_exif_orientation(self) -> None:
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rotated.jpg"
            img = Image.new("RGB", (400, 200), (50, 100, 150))
            exif = Image.Exif()
            exif[274] = 6  # Rotate 90 CW
            img.save(path, format="JPEG", exif=exif.tobytes())

            rgb = bird_model._open_rgb_image(path)
            self.assertEqual(rgb.mode, "RGB")
            self.assertEqual(rgb.size, (200, 400))


class TestDoctor(unittest.TestCase):
    def _sample_entry(self, **overrides) -> dict:
        entry = {
            "species_common": "American Robin",
            "species_scientific": "Turdus migratorius",
            "banding_code": "AMRO",
            "slug": "american-robin",
            "filename": "american-robin.webp",
            "family": "Turdidae",
            "sibley_category": "Kinglets, Old World Warblers, and Thrush Allies",
            "sibley_category_order": 25,
            "taxonomic_order": 27400,
            "ebird_code": "amerob",
            "date_taken": "2025-04-12T09:09:00",
            "location": "Ottawa County, MI",
            "notes": "",
            "source_filename": "IMG_0001.JPG",
            "source_id": "IMG_0001.JPG_20250412T090900_12345678",
        }
        entry.update(overrides)
        return entry

    def test_audit_catalog_integrity_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            photos = Path(tmp)
            (photos / "american-robin.webp").write_bytes(b"RIFF")
            (photos / "LICENSE.txt").write_text("All rights reserved", encoding="utf-8")

            result = doctor.audit_catalog_integrity([self._sample_entry()], photos)
            self.assertEqual(
                result,
                {
                    "missing_photos": [],
                    "orphan_photos": [],
                    "duplicates": [],
                    "invalid_dates": [],
                    "missing_locations": [],
                    "slug_mismatches": [],
                },
            )

    def test_audit_catalog_integrity_catches_all_issues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            photos = Path(tmp)
            (photos / "american-robin.webp").write_bytes(b"RIFF")
            (photos / "orphan-bird.webp").write_bytes(b"RIFF")

            catalog = [
                self._sample_entry(),
                # Duplicate slug, filename, source_id, species_common
                self._sample_entry(),
                # Missing photo, future date, missing location, slug mismatch
                self._sample_entry(
                    species_common="Snowy Owl",
                    slug="wrong-owl-slug",
                    filename="snowy-owl.webp",
                    source_id="IMG_0002.JPG_20990101T000000_abcdef01",
                    date_taken="2099-01-01T00:00:00",
                    location="   ",
                ),
                # Invalid calendar date
                self._sample_entry(
                    species_common="Bald Eagle",
                    slug="bald-eagle",
                    filename="bald-eagle.webp",
                    source_id="IMG_0003.JPG_20250230T100000_abcdef02",
                    date_taken="2025-02-30T10:00:00",
                    location="Kent County, MI",
                ),
            ]
            (photos / "bald-eagle.webp").write_bytes(b"RIFF")

            result = doctor.audit_catalog_integrity(catalog, photos)
            self.assertEqual(result["missing_photos"], ["snowy-owl.webp"])
            self.assertEqual(result["orphan_photos"], ["orphan-bird.webp"])
            self.assertIn("slug: american-robin", result["duplicates"])
            self.assertIn("filename: american-robin.webp", result["duplicates"])
            self.assertIn("source_id: IMG_0001.JPG_20250412T090900_12345678", result["duplicates"])
            self.assertIn("species_common: American Robin", result["duplicates"])
            self.assertEqual(len(result["invalid_dates"]), 2)
            self.assertTrue(any("Snowy Owl" in s and "future" in s for s in result["invalid_dates"]))
            self.assertTrue(any("Bald Eagle" in s for s in result["invalid_dates"]))
            self.assertEqual(result["missing_locations"], ["Snowy Owl"])
            self.assertEqual(len(result["slug_mismatches"]), 1)
            self.assertIn("Snowy Owl", result["slug_mismatches"][0])

    @unittest.skipUnless(HAS_MAGICK and HAS_EXIFTOOL and HAS_PIL, "requires ImageMagick, exiftool, and Pillow")
    def test_audit_photo_metadata(self) -> None:
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            photos = Path(tmp)
            # Empty folder -> ([], [])
            self.assertEqual(doctor.audit_photo_metadata(photos), ([], []))

            # Clean copyright-stamped WebP
            src = photos / "source.png"
            Image.new("RGB", (120, 120), (40, 80, 120)).save(src)
            clean_webp = photos / "clean.webp"
            bird_common.process_image_to_webp(src, clean_webp, year="2026")
            src.unlink()

            # Unstamped WebP
            unstamped = photos / "unstamped.webp"
            Image.new("RGB", (120, 120), (80, 40, 120)).save(unstamped, format="WEBP")

            # GPS-leaking WebP (stamped with copyright, but has GPS coordinates)
            gps_leak = photos / "gps-leak.webp"
            shutil.copyfile(clean_webp, gps_leak)
            subprocess.run(
                [
                    "exiftool",
                    "-overwrite_original",
                    "-GPSLatitude=42.9634",
                    "-GPSLatitudeRef=N",
                    "-GPSLongitude=85.6681",
                    "-GPSLongitudeRef=W",
                    str(gps_leak),
                ],
                capture_output=True,
                check=True,
            )

            gps_leaks, missing_copyright = doctor.audit_photo_metadata(photos)
            self.assertEqual(gps_leaks, ["gps-leak.webp"])
            self.assertEqual(missing_copyright, ["unstamped.webp"])


class TestSetupOfflineAssets(unittest.TestCase):
    def test_generate_fallback_banding_code(self) -> None:
        self.assertEqual(setup_offline_assets.generate_fallback_banding_code("Mallard"), "MALL")
        self.assertEqual(setup_offline_assets.generate_fallback_banding_code("Hen Harrier"), "HEHA")
        self.assertEqual(setup_offline_assets.generate_fallback_banding_code("Oriental Honey-buzzard"), "OHBU")
        self.assertEqual(setup_offline_assets.generate_fallback_banding_code("Black-crowned Night-Heron"), "BCNH")
        self.assertEqual(setup_offline_assets.generate_fallback_banding_code("Cooper's Hawk"), "COHA")
        self.assertEqual(setup_offline_assets.generate_fallback_banding_code(""), "BIRD")

    def test_sibley_family_map_viduidae(self) -> None:
        family_map = json.loads((SCRIPT_DIR / "sibley_family_map.json").read_text(encoding="utf-8"))
        self.assertIn("Viduidae", family_map)
        self.assertNotIn("Vidua", family_map)
        for family, info in family_map.items():
            self.assertIsInstance(info["sibley_category"], str, family)
            self.assertIsInstance(info["sibley_category_order"], int, family)


class TestUpdateDeps(unittest.TestCase):
    def test_in_names_and_lock_pins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            req_in = root / "requirements.in"
            req_in.write_text("# comment\nPyYAML>=6.0\nrich\n", encoding="utf-8")
            self.assertEqual(update_deps.in_names(req_in), ["PyYAML", "rich"])

            lock = root / "requirements.txt"
            lock.write_text("# generated\nPyYAML==6.0.2\nrich==14.0.0\n", encoding="utf-8")
            self.assertEqual(update_deps.lock_pins(lock), {"pyyaml": "6.0.2", "rich": "14.0.0"})

    def test_write_locks_with_and_without_extra_index_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            core_in = root / "requirements.in"
            ai_in = root / "requirements-ai.in"
            core_lock = root / "requirements.txt"
            ai_lock = root / "requirements-ai.txt"

            core_in.write_text("PyYAML\n", encoding="utf-8")
            ai_in.write_text("--extra-index-url https://download.pytorch.org/whl/cpu\ntorch\n", encoding="utf-8")

            with mock.patch.multiple(
                update_deps,
                CORE_IN=core_in,
                AI_IN=ai_in,
                CORE_LOCK=core_lock,
                AI_LOCK=ai_lock,
            ):
                update_deps.write_locks(["PyYAML==6.0.2"], ["torch==2.6.0+cpu"])
                self.assertIn("PyYAML==6.0.2", core_lock.read_text(encoding="utf-8"))
                ai_text = ai_lock.read_text(encoding="utf-8")
                self.assertIn("--extra-index-url https://download.pytorch.org/whl/cpu\ntorch==2.6.0+cpu\n", ai_text)

                # Without --extra-index-url in AI_IN, write_locks must still succeed
                ai_in.write_text("torch\n", encoding="utf-8")
                update_deps.write_locks(["PyYAML==6.0.2"], ["torch==2.6.0"])
                ai_text_no_idx = ai_lock.read_text(encoding="utf-8")
                self.assertNotIn("--extra-index-url", ai_text_no_idx)
                self.assertIn("torch==2.6.0\n", ai_text_no_idx)


@unittest.skipUnless(HAS_IMPORT_BIRDS_DEPS, "requires import_birds dependencies (PyYAML, natsort, prompt_toolkit, rich)")
class TestMigrateTaxonomy(unittest.TestCase):
    def setUp(self) -> None:
        import migrate_taxonomy

        self.mt = migrate_taxonomy

    def test_field_changes(self) -> None:
        row = {
            "common_name": "American Robin",
            "scientific_name": "Turdus migratorius",
            "banding_code": "AMRO",
            "family": "Turdidae",
            "sibley_category": "Thrushes",
            "sibley_category_order": 25,
            "taxonomic_order": 27400,
            "ebird_code": "amerob",
        }
        entry = {
            "species_common": "American Robin",
            "species_scientific": "Turdus migratorius",
            "banding_code": "AMRO",
            "family": "Turdidae",
            "sibley_category": "Thrushes",
            "sibley_category_order": 25,
            "taxonomic_order": 27400,
            "ebird_code": "amerob",
        }
        self.assertEqual(self.mt.field_changes(entry, row), {})

        entry["taxonomic_order"] = 27000
        entry["banding_code"] = "OLD1"
        self.assertEqual(
            self.mt.field_changes(entry, row),
            {"taxonomic_order": (27000, 27400), "banding_code": ("OLD1", "AMRO")},
        )

    def test_find_match_priority(self) -> None:
        r_code = {"common_name": "By Code", "scientific_name": "Genus a", "ebird_code": "code1"}
        r_sci = {"common_name": "By Sci", "scientific_name": "Genus b", "ebird_code": "code2"}
        r_com = {"common_name": "By Common", "scientific_name": "Genus c", "ebird_code": "code3"}
        by_code = {"code1": r_code}
        by_sci = {"Genus b": r_sci}
        by_common = {"By Common": r_com}

        self.assertEqual(
            self.mt.find_match({"ebird_code": "code1", "species_scientific": "Genus b", "species_common": "By Common"}, by_code, by_sci, by_common),
            (r_code, "code"),
        )
        self.assertEqual(
            self.mt.find_match({"ebird_code": "gone", "species_scientific": "Genus b", "species_common": "By Common"}, by_code, by_sci, by_common),
            (r_sci, "scientific"),
        )
        self.assertEqual(
            self.mt.find_match({"ebird_code": "gone", "species_scientific": "Other x", "species_common": "By Common"}, by_code, by_sci, by_common),
            (r_com, "common"),
        )
        self.assertEqual(
            self.mt.find_match({"ebird_code": "gone", "species_scientific": "Other x", "species_common": "Missing"}, by_code, by_sci, by_common),
            (None, None),
        )

    def test_successor_candidates(self) -> None:
        taxonomy = [
            {"common_name": "Eastern Marsh Wren", "scientific_name": "Cistothorus palustris", "ebird_code": "emarwr"},
            {"common_name": "Western Marsh Wren", "scientific_name": "Cistothorus plesius", "ebird_code": "wmarwr"},
            {"common_name": "Sedge Wren", "scientific_name": "Cistothorus stellaris", "ebird_code": "sedwre"},
            {"common_name": "House Wren", "scientific_name": "Troglodytes aedon", "ebird_code": "houwre"},
        ]
        entry = {
            "species_common": "Marsh Wren",
            "species_scientific": "Cistothorus palustris",
            "ebird_code": "marwre",
        }
        cands = self.mt.successor_candidates(entry, taxonomy)
        self.assertEqual(
            [c["ebird_code"] for c in cands],
            ["emarwr", "wmarwr", "sedwre"],
        )

    def test_same_slug_rename_does_not_collide(self) -> None:
        from rich.console import Console

        with tempfile.TemporaryDirectory() as tmp:
            photos = Path(tmp)
            (photos / "coopers-hawk.webp").write_bytes(b"RIFF")

            catalog = [
                {
                    "species_common": "Cooper's Hawk",
                    "species_scientific": "Astur cooperii",
                    "banding_code": "COHA",
                    "slug": "coopers-hawk",
                    "filename": "coopers-hawk.webp",
                    "family": "Accipitridae",
                    "sibley_category": "Diurnal Raptors",
                    "sibley_category_order": 7,
                    "taxonomic_order": 8000,
                    "ebird_code": "coohaw",
                }
            ]
            # Punctuation-only common name change keeping the exact same slug
            taxonomy = [
                {
                    "common_name": "Coopers Hawk",
                    "scientific_name": "Astur cooperii",
                    "banding_code": "COHA",
                    "family": "Accipitridae",
                    "sibley_category": "Diurnal Raptors",
                    "sibley_category_order": 7,
                    "taxonomic_order": 8000,
                    "ebird_code": "coohaw",
                }
            ]
            with mock.patch.object(self.mt, "console", Console(file=io.StringIO())):
                changed = self.mt.migrate(catalog, taxonomy, photos, dry_run=False, assume_yes=True)

            self.assertEqual(changed, 1)
            self.assertEqual(catalog[0]["species_common"], "Coopers Hawk")
            self.assertEqual(catalog[0]["slug"], "coopers-hawk")
            self.assertEqual(catalog[0]["filename"], "coopers-hawk.webp")
            self.assertTrue((photos / "coopers-hawk.webp").is_file())


@unittest.skipUnless(HAS_IMPORT_BIRDS_DEPS and HAS_SHAPELY, "requires import_birds dependencies and shapely")
class TestCountyLocator(unittest.TestCase):
    def test_strtree_interior_boundary_coastal_and_outside(self) -> None:
        import import_birds

        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"county_state": "Test County, MI"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [-86.0, 42.0],
                            [-85.0, 42.0],
                            [-85.0, 43.0],
                            [-86.0, 43.0],
                            [-86.0, 42.0],
                        ]],
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            geo_path = Path(tmp) / "counties.geojson"
            geo_path.write_text(json.dumps(geojson), encoding="utf-8")

            locator = import_birds.CountyLocator(geo_path)
            # Interior
            self.assertEqual(locator.resolve(42.5, -85.5), "Test County, MI")
            # Exact boundary
            self.assertEqual(locator.resolve(42.0, -85.5), "Test County, MI")
            # Coastal / near shoreline (within 0.15 deg fallback)
            self.assertEqual(locator.resolve(42.5, -86.05), "Test County, MI")
            # Far outside
            self.assertIsNone(locator.resolve(10.0, 10.0))
            # Missing coordinates
            self.assertIsNone(locator.resolve(None, -85.5))
            self.assertIsNone(locator.resolve(42.5, None))


if __name__ == "__main__":
    unittest.main()
