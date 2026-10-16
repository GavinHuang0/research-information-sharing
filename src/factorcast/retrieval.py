"""Bounded retrieval and local adaptation of official French daily industries.

The source URL is fixed. urllib's default certificate validation and configured
proxy handling are preserved; no network-policy exceptions are attempted here.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any
import urllib.error
import urllib.parse
import urllib.request
import zipfile

import numpy as np
import pandas as pd

from .data import validate_daily_returns

FRENCH48_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "48_Industry_Portfolios_Daily_CSV.zip"
)
_ARCHIVE_NAME = "48_Industry_Portfolios_Daily_CSV.zip"
_MEMBER_NAME = "48_Industry_Portfolios_Daily.csv"
_MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
_MAX_MEMBER_BYTES = 128 * 1024 * 1024
_DOWNLOAD_TIMEOUT = 30.0
_DAILY_SECTION = re.compile(
    r"^Average\s+(Value|Equal)\s+Weighted\s+Returns\s*--\s*Daily$", re.IGNORECASE
)
_SECTION_BOUNDARY = re.compile(
    r"^(?:Average\s+(?:Value|Equal)\s+Weighted\s+Returns|Number\s+of\s+Firms|"
    r"Average\s+Firm\s+Size)(?:\s*--\s*(?:Daily|Monthly|Annual))?$",
    re.IGNORECASE,
)
_COPYRIGHT_FOOTER = re.compile(r"^(?:Copyright\b|©|\(c\)).*", re.IGNORECASE)


@dataclass(frozen=True)
class French48Snapshot:
    raw_archive_path: Path
    processed_csv_path: Path
    provenance_path: Path
    metadata: dict[str, Any]


class _OfficialRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Allow redirects only within the official HTTPS origin."""

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        destination = urllib.parse.urlparse(newurl)
        official = urllib.parse.urlparse(FRENCH48_URL)
        if destination.scheme != "https" or destination.netloc != official.netloc:
            raise urllib.error.URLError("The official source redirected outside its HTTPS origin.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _download_bytes() -> bytes:
    request = urllib.request.Request(
        FRENCH48_URL,
        headers={"User-Agent": "factorcast-research/0.1", "Accept": "application/zip"},
    )
    # build_opener supplies standard ProxyHandler and certificate-validating
    # HTTPSHandler; only redirect handling changes.
    opener = urllib.request.build_opener(_OfficialRedirectHandler())
    try:
        with opener.open(request, timeout=_DOWNLOAD_TIMEOUT) as response:
            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                try:
                    declared_length = int(content_length)
                except ValueError as exc:
                    raise ValueError("The source returned an invalid Content-Length.") from exc
                if declared_length < 0 or declared_length > _MAX_ARCHIVE_BYTES:
                    raise ValueError("The source archive exceeds the permitted download size.")
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = response.read(min(64 * 1024, _MAX_ARCHIVE_BYTES - total + 1))
                if not chunk:
                    break
                total += len(chunk)
                if total > _MAX_ARCHIVE_BYTES:
                    raise ValueError("The source archive exceeds the permitted download size.")
                chunks.append(chunk)
            if content_length is not None and total != declared_length:
                raise ValueError("The source response is incomplete or has an inconsistent Content-Length.")
            return b"".join(chunks)
    except (urllib.error.URLError, TimeoutError) as exc:
        reason = getattr(exc, "reason", str(exc))
        raise RuntimeError(
            "Could not retrieve the official French archive. Download the official ZIP "
            "on a machine with access and supply its path through --archive "
            f"(archive_path for the Python API). Source error: {reason}"
        ) from exc


def _parse_archive_bytes(archive_bytes: bytes, *, weighting: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    if weighting not in {"value", "equal"}:
        raise ValueError("weighting must be 'value' or 'equal'.")
    if len(archive_bytes) > _MAX_ARCHIVE_BYTES:
        raise ValueError("The source archive exceeds the permitted archive size.")
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            members = [
                member for member in archive.infolist()
                if PurePosixPath(member.filename).name.casefold() == _MEMBER_NAME.casefold()
            ]
            if len(members) != 1:
                raise ValueError("The ZIP must contain exactly one official daily 48-industry CSV member.")
            member = members[0]
            member_path = PurePosixPath(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts or "\\" in member.filename or ":" in member_path.parts[0]:
                raise ValueError("The ZIP CSV member has an unsafe path.")
            if member.file_size > _MAX_MEMBER_BYTES:
                raise ValueError("The uncompressed daily CSV exceeds the permitted size.")
            # Read the selected member in memory; never extract ZIP paths.
            with archive.open(member) as handle:
                member_bytes = handle.read(_MAX_MEMBER_BYTES + 1)
            if len(member_bytes) > _MAX_MEMBER_BYTES:
                raise ValueError("The uncompressed daily CSV exceeds the permitted size.")
            member_name = member.filename
    except zipfile.BadZipFile as exc:
        raise ValueError("The source is not a valid French ZIP archive.") from exc
    try:
        text = member_bytes.decode("utf-8-sig")
        encoding = "utf-8-sig"
    except UnicodeDecodeError:
        text = member_bytes.decode("cp1252")
        encoding = "cp1252"
    # Some official exports use CRCRLF. csv.reader treats the extra CR as
    # a blank record, so normalize only that sequence in the decoded copy.
    # Real blank lines remain intact, and the source archive stays unchanged.
    crcrlf_count = text.count("\r\r\n")
    text = text.replace("\r\r\n", "\r\n")
    requested = "Value" if weighting == "value" else "Equal"
    sections: list[tuple[int, str]] = []
    provider_notes: list[str] = []
    first_daily_found = False
    # Scan without retaining every field from all other provider tables.
    for index, row in enumerate(csv.reader(io.StringIO(text, newline=""))):
        match = _DAILY_SECTION.fullmatch(row[0].strip()) if row else None
        if match:
            first_daily_found = True
            if match.group(1).casefold() == requested.casefold():
                sections.append((index, row[0].strip()))
        elif not first_daily_found and any(row):
            provider_notes.append(",".join(row).strip())
    if len(sections) != 1:
        raise ValueError(f"Expected exactly one average {requested.lower()} weighted daily-return section.")
    section_index, section_title = sections[0]
    reader = csv.reader(io.StringIO(text, newline=""))
    for _ in range(section_index + 1):
        next(reader)
    cursor = section_index + 1
    header_row = next(reader, None)
    while header_row is not None and not any(cell.strip() for cell in header_row):
        cursor += 1
        header_row = next(reader, None)
    if header_row is None:
        raise ValueError("The selected daily-return section has no asset header.")
    header = [cell.strip() for cell in header_row]
    if len(header) != 49 or header[0].casefold() not in {"", "date"}:
        raise ValueError("The daily-return header must contain a date plus exactly 48 assets.")
    asset_names = header[1:]
    if len(set(asset_names)) != 48 or any(not name for name in asset_names):
        raise ValueError("The 48 daily asset names must be unique and nonempty.")
    dates: list[datetime] = []
    values: list[list[float]] = []
    sentinel_counts = {"-99.99": 0, "-999": 0}
    blank_count = 0
    section_gap = False
    for row_number, raw_row in enumerate(reader, start=cursor + 1):
        row = [cell.strip() for cell in raw_row]
        if not any(row):
            if dates:
                section_gap = True
            continue
        if _SECTION_BOUNDARY.fullmatch(row[0]) or _COPYRIGHT_FOOTER.fullmatch(row[0]):
            break
        if section_gap:
            raise ValueError(
                f"Unexpected internal blank in the daily-return section before source line {row_number + 1}."
            )
        if len(row) != 49 or not re.fullmatch(r"\d{8}", row[0]):
            raise ValueError(f"Malformed daily-return row at source line {row_number + 1}.")
        try:
            date = datetime.strptime(row[0], "%Y%m%d")
        except ValueError as exc:
            raise ValueError(f"Invalid daily calendar date at source line {row_number + 1}.") from exc
        if dates and date <= dates[-1]:
            raise ValueError("Source daily dates must be unique and strictly chronological.")
        parsed_row: list[float] = []
        for token in row[1:]:
            if not token:
                parsed_row.append(np.nan)
                blank_count += 1
                continue
            try:
                value = float(token)
            except ValueError as exc:
                raise ValueError(f"Nonnumeric daily return at source line {row_number + 1}.") from exc
            if not np.isfinite(value):
                raise ValueError(f"Nonfinite daily return at source line {row_number + 1}.")
            if value == -99.99:
                parsed_row.append(np.nan)
                sentinel_counts["-99.99"] += 1
            elif value == -999.0:
                parsed_row.append(np.nan)
                sentinel_counts["-999"] += 1
            else:
                parsed_row.append(value / 100.0)
        dates.append(date)
        values.append(parsed_row)
    if not dates:
        raise ValueError("The selected daily-return section has no daily observations.")
    panel = pd.DataFrame(values, index=pd.DatetimeIndex(dates, name="date"), columns=asset_names)
    validate_daily_returns(panel)
    parsed_metadata = {
        "zip_member_name": member_name,
        "zip_member_bytes": len(member_bytes),
        "source_text_encoding": encoding,
        "source_line_ending_normalization": {
            "action": "CRCRLF_to_CRLF_in_decoded_text",
            "replacements": crcrlf_count,
        },
        "source_section": section_title,
        "weighting": weighting,
        "source_units": "percent",
        "processed_units": "decimal",
        "unit_conversion": "nonmissing_return_divided_by_100",
        "missing_conversion": "-99.99_and_-999_to_empty_CSV_cells; preserve_existing_empty_cells",
        "converted_sentinel_cells": sentinel_counts,
        "source_blank_cells": blank_count,
        "daily_missing_by_asset": {name: int(count) for name, count in panel.isna().sum().items()},
        "daily_rows": len(panel),
        "asset_count": 48,
        "asset_names": asset_names,
        "first_date": dates[0].date().isoformat(),
        "last_date": dates[-1].date().isoformat(),
        "provider_notes": provider_notes,
    }
    return panel, parsed_metadata


def download_french48(
    raw_dir: str | Path = "data/raw",
    processed_dir: str | Path = "data/processed",
    weighting: str = "value",
    archive_path: str | Path | None = None,
) -> French48Snapshot:
    """Retrieve or locally adapt the official ZIP into a new auditable snapshot.

    Set ``archive_path`` to use a manually downloaded archive without contacting
    the network. Outputs never overwrite existing snapshots. The selected
    value/equal daily section is converted from percent to decimal returns;
    no weekly proxies or actual empirical results are produced here.
    """
    if weighting not in {"value", "equal"}:
        raise ValueError("weighting must be 'value' or 'equal'.")
    source_path = None if archive_path is None else Path(archive_path).expanduser().resolve()
    if source_path is None:
        archive_bytes = _download_bytes()
    else:
        if source_path.stat().st_size > _MAX_ARCHIVE_BYTES:
            raise ValueError("The source archive exceeds the permitted archive size.")
        with source_path.open("rb") as handle:
            archive_bytes = handle.read(_MAX_ARCHIVE_BYTES + 1)
    panel, parsed_metadata = _parse_archive_bytes(archive_bytes, weighting=weighting)
    csv_bytes = panel.to_csv(index=True, date_format="%Y-%m-%d", na_rep="", float_format="%.12g").encode("utf-8")
    archive_hash = hashlib.sha256(archive_bytes).hexdigest()
    snapshot_time = datetime.now(timezone.utc)
    snapshot_name = f"french48-{weighting}-{snapshot_time.strftime('%Y%m%dT%H%M%S%fZ')}-{archive_hash[:12]}"
    raw_root = Path(raw_dir).expanduser().resolve()
    processed_root = Path(processed_dir).expanduser().resolve()
    raw_snapshot = raw_root / snapshot_name
    processed_snapshot = processed_root / snapshot_name
    raw_archive_path = raw_snapshot / _ARCHIVE_NAME
    processed_csv_path = processed_snapshot / "daily48.csv"
    provenance_path = processed_snapshot / "provenance.json"
    metadata: dict[str, Any] = {
        "provider": "Kenneth R. French Data Library",
        "official_source_url": FRENCH48_URL,
        "retrieval_mode": "official_url_download" if source_path is None else "local_archive",
        "local_archive_path": None if source_path is None else str(source_path),
        "local_archive_origin_verified": False if source_path is not None else None,
        "snapshot_at_utc": snapshot_time.isoformat(),
        "archive_sha256": archive_hash,
        "archive_bytes": len(archive_bytes),
        "processed_csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
        "raw_archive_path": str(raw_archive_path),
        "processed_csv_path": str(processed_csv_path),
        **parsed_metadata,
    }
    provenance_bytes = (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8")
    created_dirs: list[Path] = []
    created_files: list[Path] = []
    try:
        raw_root.mkdir(parents=True, exist_ok=True)
        processed_root.mkdir(parents=True, exist_ok=True)
        raw_snapshot.mkdir(exist_ok=False)
        created_dirs.append(raw_snapshot)
        if processed_snapshot != raw_snapshot:
            processed_snapshot.mkdir(exist_ok=False)
            created_dirs.append(processed_snapshot)
        for path, contents in (
            (raw_archive_path, archive_bytes),
            (processed_csv_path, csv_bytes),
            (provenance_path, provenance_bytes),
        ):
            with path.open("xb") as handle:
                created_files.append(path)
                handle.write(contents)
    except Exception:
        # Remove only files created by this call; never remove preexisting files.
        for path in reversed(created_files):
            path.unlink(missing_ok=True)
        for directory in reversed(created_dirs):
            try:
                directory.rmdir()
            except OSError:
                pass
        raise
    return French48Snapshot(raw_archive_path, processed_csv_path, provenance_path, metadata)
