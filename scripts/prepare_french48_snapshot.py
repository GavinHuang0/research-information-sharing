"""Prepare both return panels and labels from a preserved French ZIP snapshot.

Run from the repository root after installing the project dependencies:
    python scripts/prepare_french48_snapshot.py --snapshot-date YYYY-MM-DD

Input archives and acquisition.json must already exist under data/raw/kenneth-french/
48-industry-daily/YYYY-MM-DD/. This script never downloads or overwrites data.
"""

import argparse
import csv
from datetime import date, datetime, timezone
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factorcast.retrieval import _parse_archive_bytes


def sha256(contents):
    return hashlib.sha256(contents).hexdigest()


def csv_bytes(rows):
    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator="\n").writerows(rows)
    return buffer.getvalue().encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-date", required=True, type=date.fromisoformat)
    parser.add_argument("--verify", action="store_true", help="Reproduce and check the committed files without writing")
    args = parser.parse_args()
    relative = Path("kenneth-french/48-industry-daily") / args.snapshot_date.isoformat()
    raw_dir = ROOT / "data/raw" / relative
    output_dir = ROOT / "data/processed" / relative
    if output_dir.exists() and not args.verify:
        parser.error(f"Refusing to overwrite existing snapshot: {output_dir}")

    archive_path = raw_dir / "48_Industry_Portfolios_Daily_CSV.zip"
    definitions_path = raw_dir / "Siccodes48.zip"
    acquisition_path = raw_dir / "acquisition.json"
    acquisition_bytes = acquisition_path.read_bytes()
    acquisition = json.loads(acquisition_bytes)
    assert acquisition["snapshot_date"] == args.snapshot_date.isoformat()
    archive_bytes = archive_path.read_bytes()
    definitions_bytes = definitions_path.read_bytes()
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None, "Corrupt source archive"
    with zipfile.ZipFile(definitions_path) as archive:
        assert archive.testzip() is None, "Corrupt definitions archive"
        definitions = archive.read("Siccodes48.txt").decode("utf-8-sig")
    labels = [
        (int(match[1]), match[2], match[3].strip())
        for line in definitions.splitlines()
        if (match := re.fullmatch(r"\s*(\d{1,2})\s+(\S+)\s+(.+)", line))
    ]
    assert [row[0] for row in labels] == list(range(1, 49)), "Expected 48 industry definitions"

    outputs = {}
    panels = {}
    missingness = [["weighting", "industry_code", "missing_daily_returns", "observed_daily_returns",
                    "first_observed_date", "last_observed_date"]]
    for weighting in ("value", "equal"):
        panel, metadata = _parse_archive_bytes(archive_bytes, weighting=weighting)
        assert list(panel.columns) == [row[1] for row in labels], "Definition order differs from return columns"
        filename = f"{weighting}_weighted_returns_decimal.csv"
        contents = panel.to_csv(date_format="%Y-%m-%d", na_rep="", float_format="%.12g",
                                lineterminator="\n").encode("utf-8")
        outputs[filename] = contents
        panels[weighting] = dict(metadata, path=(output_dir / filename).relative_to(ROOT).as_posix(),
                                 sha256=sha256(contents), bytes=len(contents))
        for code in panel.columns:
            observed = panel[code].dropna()
            missingness.append([weighting, code, int(panel[code].isna().sum()), len(observed),
                                observed.index.min().date().isoformat(),
                                observed.index.max().date().isoformat()])

    outputs["industry_labels.csv"] = csv_bytes([["industry_number", "industry_code", "industry_name"], *labels])
    outputs["missingness.csv"] = csv_bytes(missingness)
    sources = acquisition["sources"]
    for path, contents in (
        (archive_path, archive_bytes),
        (definitions_path, definitions_bytes),
    ):
        source = next(item for item in sources if item["path"] == path.relative_to(ROOT).as_posix())
        assert source["sha256"] == sha256(contents) and source["bytes"] == len(contents), "Acquisition hash mismatch"
    provenance = dict(
        schema_version=1,
        dataset_id="kenneth-french/48-industry-daily",
        snapshot_date=args.snapshot_date.isoformat(),
        snapshot_date_timezone="America/New_York",
        provider="Kenneth R. French Data Library",
        source_details_url="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_48_ind_port.html",
        provider_attribution="Copyright Eugene F. Fama and Kenneth R. French; original notices retained in raw archives.",
        retrieval_mode=acquisition["retrieval_mode"],
        acquisition_metadata=dict(path=acquisition_path.relative_to(ROOT).as_posix(),
                                  sha256=sha256(acquisition_bytes), bytes=len(acquisition_bytes)),
        prepared_at_utc=datetime.now(timezone.utc).isoformat(),
        sources=sources,
        panels=panels,
        auxiliary_files=[dict(path=(output_dir / name).relative_to(ROOT).as_posix(),
                              sha256=sha256(contents), bytes=len(contents))
                         for name, contents in outputs.items() if not name.endswith("returns_decimal.csv")],
        preparation=dict(script="scripts/prepare_french48_snapshot.py",
                         script_sha256=sha256(Path(__file__).read_bytes()),
                         adapter="src/factorcast/retrieval.py",
                         adapter_sha256=sha256((ROOT / "src/factorcast/retrieval.py").read_bytes()),
                         command=f"python scripts/prepare_french48_snapshot.py --snapshot-date {args.snapshot_date}",
                         csv_line_ending="LF", row_order="original_provider_order",
                         calendar_filter="none", imputation="none", weekly_aggregation="none",
                         python=sys.version.split()[0],
                         packages={name: importlib.metadata.version(name) for name in ("numpy", "pandas")}),
        interpretation="Daily industry portfolio returns, not observed volatility. Use the value-weighted panel as the initial default.",
        methodology_note="Provider rebuilds historical files. Current US research returns use CRSP CIZ, adopted starting with the January 2025 release; this is a fixed retrospective snapshot, not point-in-time vintages.",
    )
    if args.verify:
        existing = json.loads((output_dir / "provenance.json").read_bytes())
        provenance["prepared_at_utc"] = existing["prepared_at_utc"]
        if provenance != existing:
            parser.error("Provenance differs from current acquisition records, inputs, code, or dependency versions")
        for name, contents in outputs.items():
            if (output_dir / name).read_bytes() != contents:
                parser.error(f"Reproduction differs: {name}")
        print("Verified original archive checksums, both return panels, labels, missingness, and provenance.")
        return
    outputs["provenance.json"] = (json.dumps(provenance, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output_dir.mkdir(parents=True, exist_ok=False)
    for name, contents in outputs.items():
        with (output_dir / name).open("xb") as handle:
            handle.write(contents)
    print(json.dumps(dict(paths={name: (output_dir / name).relative_to(ROOT).as_posix() for name in outputs},
                          coverage={key: {field: value[field] for field in ("first_date", "last_date", "daily_rows", "asset_count")}
                                    for key, value in panels.items()},
                          total_bytes=sum(map(len, outputs.values())) + len(archive_bytes) + len(definitions_bytes) + len(acquisition_bytes)), indent=2))


if __name__ == "__main__":
    main()
