import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from factorcast.cli import main
from factorcast.data import load_daily_returns
from test_retrieval import zip_fixture


class DownloadCLITests(unittest.TestCase):
    def test_offline_command_outputs_loadable_decimal_data_and_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "input.zip"
            archive.write_bytes(zip_fixture())
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                main(["download-data", "--archive", str(archive), "--raw-dir", str(root / "raw"),
                      "--processed-dir", str(root / "processed"), "--json"])
            output = json.loads(stream.getvalue())
            self.assertTrue(Path(output["raw_archive"]).is_file())
            self.assertTrue(Path(output["provenance"]).is_file())
            daily = load_daily_returns(output["returns_csv"], units="decimal")
            self.assertAlmostEqual(daily.iloc[0, 0], 0.01)
            self.assertEqual(output["metadata"]["processed_units"], "decimal")

    def test_network_failure_produces_actionable_error_without_traceback(self):
        stream = io.StringIO()
        with patch("factorcast.cli.download_french48", side_effect=RuntimeError("Use --archive when source is blocked")):
            with contextlib.redirect_stderr(stream), self.assertRaises(SystemExit) as error:
                main(["download-data"])
        self.assertEqual(error.exception.code, 2)
        self.assertIn("--archive", stream.getvalue())
        self.assertIn("docs/data.md", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
