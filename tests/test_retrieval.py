"""Synthetic parser fixtures and mocked transport; no live provider requests."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error
import zipfile

import numpy as np

from factorcast.data import load_daily_returns
from factorcast import retrieval

ASSETS = (
    "Agric Food Soda Beer Smoke Toys Fun Books Hshld Clths Hlth MedEq Drugs Chems "
    "Rubbr Txtls BldMt Cnstr Steel FabPr Mach ElcEq Autos Aero Ships Guns Gold Mines "
    "Coal Oil Util Telcm PerSv BusSv Comps Chips LabEq Paper Boxes Trans Whlsl Rtail "
    "Meals Banks Insur RlEst Fin Other"
).split()


def fixture_text() -> str:
    """Provider-shaped test values, not downloaded or empirical observations."""
    header = "," + ",".join(ASSETS)
    value_first = ["1.00", "-99.99", "-999"] + ["0.50"] * 45
    equal_first = ["2.00", "0.75", "-0.25"] + ["0.25"] * 45
    return "\n".join([
        "This file was created by using a synthetic TEST database.",
        "Missing data are indicated by -99.99 or -999.",
        "",
        "  Average Value Weighted Returns -- Daily",
        header,
        "20200102," + ",".join(value_first),
        "20200103," + ",".join(["-0.10"] * 48),
        "",
        "  Average Equal Weighted Returns -- Daily",
        header,
        "20200102," + ",".join(equal_first),
        "20200103," + ",".join(["0.10"] * 48),
        "",
        "  Number of Firms -- Daily",
        header,
        "20200102," + ",".join(["10"] * 48),
        "",
    ])


def zip_fixture(text: str | None = None, member: str = "48_Industry_Portfolios_Daily.csv") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member, fixture_text() if text is None else text)
    return buffer.getvalue()


class Response(io.BytesIO):
    def __init__(self, data: bytes, *, declared_length: str | None = None) -> None:
        super().__init__(data)
        self.headers = {} if declared_length is None else {"Content-Length": declared_length}


class FrenchRetrievalTests(unittest.TestCase):
    def test_exact_section_selection_units_and_sentinel_conversion(self) -> None:
        archive = zip_fixture()
        value, metadata = retrieval._parse_archive_bytes(archive, weighting="value")
        equal, equal_metadata = retrieval._parse_archive_bytes(archive, weighting="equal")
        self.assertEqual(list(value.columns), ASSETS)
        self.assertEqual(value.shape, (2, 48))
        self.assertAlmostEqual(value.iloc[0, 0], 0.01)
        self.assertAlmostEqual(equal.iloc[0, 0], 0.02)
        self.assertTrue(np.isnan(value.iloc[0, 1]))
        self.assertTrue(np.isnan(value.iloc[0, 2]))
        self.assertAlmostEqual(value.iloc[1, 0], -0.001)
        self.assertEqual(metadata["converted_sentinel_cells"], {"-99.99": 1, "-999": 1})
        self.assertEqual(equal_metadata["converted_sentinel_cells"], {"-99.99": 0, "-999": 0})
        self.assertEqual(metadata["processed_units"], "decimal")
        self.assertIn("synthetic TEST", metadata["provider_notes"][0])

    def test_local_archive_creates_hashed_snapshot_without_network(self) -> None:
        archive = zip_fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local_archive = root / "manual.zip"
            local_archive.write_bytes(archive)
            with patch.object(retrieval, "_download_bytes", side_effect=AssertionError("Network contacted")):
                result = retrieval.download_french48(root / "raw", root / "processed", archive_path=local_archive)
            self.assertEqual(result.raw_archive_path.read_bytes(), archive)
            self.assertEqual(result.metadata["archive_sha256"], hashlib.sha256(archive).hexdigest())
            self.assertEqual(result.metadata["processed_csv_sha256"], hashlib.sha256(result.processed_csv_path.read_bytes()).hexdigest())
            self.assertEqual(json.loads(result.provenance_path.read_text()), result.metadata)
            self.assertEqual(result.metadata["retrieval_mode"], "local_archive")
            self.assertFalse(result.metadata["local_archive_origin_verified"])
            loaded = load_daily_returns(result.processed_csv_path, units="decimal")
            self.assertEqual(loaded.shape, (2, 48))
            self.assertAlmostEqual(loaded.iloc[0, 0], 0.01)
            self.assertTrue(np.isnan(loaded.iloc[0, 1]))
            repeated = retrieval.download_french48(root / "raw", root / "processed", archive_path=local_archive)
            self.assertNotEqual(repeated.raw_archive_path.parent, result.raw_archive_path.parent)
            self.assertEqual(result.raw_archive_path.read_bytes(), archive)

    def test_mocked_official_download_has_fixed_url_timeout_and_preserved_opener(self) -> None:
        archive = zip_fixture()
        opener = Mock()
        opener.open.return_value = Response(archive, declared_length=str(len(archive)))
        with patch.object(retrieval.urllib.request, "build_opener", return_value=opener) as build:
            with tempfile.TemporaryDirectory() as directory:
                result = retrieval.download_french48(Path(directory) / "raw", Path(directory) / "processed", weighting="equal")
                self.assertEqual(result.metadata["retrieval_mode"], "official_url_download")
                self.assertEqual(result.metadata["weighting"], "equal")
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, retrieval.FRENCH48_URL)
        self.assertTrue(request.full_url.startswith("https://mba.tuck.dartmouth.edu/"))
        self.assertEqual(opener.open.call_args.kwargs["timeout"], 30.0)
        self.assertIsInstance(build.call_args.args[0], retrieval._OfficialRedirectHandler)

    def test_size_bounds_include_unknown_content_length_and_uncompressed_member(self) -> None:
        for declared_length in (None, "11"):
            opener = Mock()
            opener.open.return_value = Response(b"a" * 11, declared_length=declared_length)
            with self.subTest(declared_length=declared_length):
                with patch.object(retrieval, "_MAX_ARCHIVE_BYTES", 10), patch.object(retrieval.urllib.request, "build_opener", return_value=opener):
                    with self.assertRaisesRegex(ValueError, "download size"):
                        retrieval._download_bytes()
        with patch.object(retrieval, "_MAX_MEMBER_BYTES", 10):
            with self.assertRaisesRegex(ValueError, "uncompressed"):
                retrieval._parse_archive_bytes(zip_fixture(), weighting="value")

    def test_network_failure_explains_manual_archive_fallback(self) -> None:
        opener = Mock()
        opener.open.side_effect = urllib.error.URLError("source blocked")
        with patch.object(retrieval.urllib.request, "build_opener", return_value=opener):
            with self.assertRaisesRegex(RuntimeError, "--archive.*source blocked"):
                retrieval._download_bytes()

    def test_malformed_rows_headers_dates_and_values_are_rejected(self) -> None:
        text = fixture_text()
        first_row = "20200102,1.00,-99.99,-999," + ",".join(["0.50"] * 45)
        bad_texts = [
            text.replace(",Agric,Food", ",Agric,Agric", 1),
            text.replace(first_row, first_row.rsplit(",", 1)[0], 1),
            text.replace("20200102,1.00", "malformed,1.00", 1),
            text.replace("20200102,1.00", "20201302,1.00", 1),
            text.replace("20200103,-0.10", "20200102,-0.10", 1),
            text.replace("20200103,-0.10", "20200101,-0.10", 1),
            text.replace("20200102,1.00", "20200102,inf", 1),
            text.replace("20200102,1.00", "20200102,nan", 1),
            text.replace("20200102,1.00", "20200102,not-numeric", 1),
        ]
        for bad_text in bad_texts:
            with self.subTest(source=bad_text):
                with self.assertRaises(ValueError):
                    retrieval._parse_archive_bytes(zip_fixture(bad_text), weighting="value")

    def test_section_boundary_without_blank_is_accepted(self) -> None:
        text = fixture_text().replace("\n\n  Average Equal", "\n  Average Equal")
        panel, _ = retrieval._parse_archive_bytes(zip_fixture(text), weighting="value")
        self.assertEqual(len(panel), 2)

    def test_internal_blank_cannot_silently_truncate_daily_observations(self) -> None:
        text = fixture_text().replace("20200103,-0.10", "\n20200103,-0.10", 1)
        with self.assertRaisesRegex(ValueError, "Unexpected internal blank"):
            retrieval._parse_archive_bytes(zip_fixture(text), weighting="value")

    def test_blanks_before_eof_or_copyright_footer_are_accepted(self) -> None:
        selected_section = fixture_text().split("\n\n  Average Equal")[0]
        for ending in ("\n\n", "\n\nCopyright 2026 Kenneth R. French\n"):
            with self.subTest(ending=ending):
                panel, _ = retrieval._parse_archive_bytes(zip_fixture(selected_section + ending), weighting="value")
                self.assertEqual(len(panel), 2)

    def test_archive_paths_members_and_weighting_are_validated(self) -> None:
        for member in ("wrong.csv", "../48_Industry_Portfolios_Daily.csv", "/48_Industry_Portfolios_Daily.csv"):
            with self.subTest(member=member):
                with self.assertRaises(ValueError):
                    retrieval._parse_archive_bytes(zip_fixture(member=member), weighting="value")
        with self.assertRaisesRegex(ValueError, "valid French ZIP"):
            retrieval._parse_archive_bytes(b"not a ZIP", weighting="value")
        with self.assertRaises(ValueError):
            retrieval.download_french48(weighting="unknown")


if __name__ == "__main__":
    unittest.main()
