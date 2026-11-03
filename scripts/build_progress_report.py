"""Synchronize the professor-facing Markdown, generated LaTeX, and PDF.

progress.md is the sole content source. Build with Pandoc and PDFLaTeX; --check
verifies the recorded input/output fingerprints without rebuilding the PDF.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / "proposal"
INPUTS = ("proposal/progress.md", "proposal/report-template.tex", "proposal/repo-links.lua",
          "scripts/build_progress_report.py")
OUTPUTS = ("proposal/proposal.tex", "proposal/proposal.pdf")
FIGURE_INPUTS = tuple(
    f"results/experiment-03-2026-11-03/reports/{period}_value_gain.{extension}"
    for period in ("earlier_seen", "later_seen")
    for extension in ("png", "pdf")
)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def normalized(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def fingerprints() -> dict:
    return {name: digest(normalized(ROOT / name)) for name in INPUTS}


def figure_fingerprints() -> dict:
    return {name: digest((ROOT / name).read_bytes()) for name in FIGURE_INPUTS}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    manifest_path = PROPOSAL / "progress_sync.json"
    source_hash = digest(normalized(PROPOSAL / "progress.md"))
    if args.check:
        manifest = json.loads(manifest_path.read_bytes())
        if manifest["inputs_sha256_lf"] != fingerprints():
            parser.error("Progress source/template/build inputs changed; rebuild the report")
        if manifest.get("figure_inputs_sha256") != figure_fingerprints():
            parser.error("Progress figure inputs changed; rebuild the report")
        for name, expected in manifest["outputs_sha256"].items():
            contents = (ROOT / name).read_bytes()
            if name.endswith(".tex"):
                contents = contents.replace(b"\r\n", b"\n")
            if digest(contents) != expected:
                parser.error(f"Generated output changed or is stale: {name}")
        if f"% Source SHA-256 (LF): {source_hash}" not in (PROPOSAL / "proposal.tex").read_text(encoding="utf-8"):
            parser.error("Generated LaTeX is not labeled with the canonical Markdown fingerprint")
        print("Progress Markdown, generated LaTeX, and PDF fingerprints are synchronized.")
        return

    pandoc, pdflatex = shutil.which("pandoc"), shutil.which("pdflatex")
    if not pandoc or not pdflatex:
        parser.error("Install Pandoc and PDFLaTeX (TeX Live), or use --check to verify existing outputs")
    command = [pandoc, "--from=markdown-implicit_figures", "--to=latex", "--standalone", "--wrap=none", "--eol=lf",
               "--shift-heading-level-by=-1", f"--template={PROPOSAL / 'report-template.tex'}",
               f"--lua-filter={PROPOSAL / 'repo-links.lua'}", f"--metadata=source_hash:{source_hash}"]
    body = subprocess.run(command, input=normalized(PROPOSAL / "progress.md"), cwd=ROOT,
                          capture_output=True, check=True).stdout
    generated = ("% GENERATED from proposal/progress.md; do not edit manually.\n"
                 f"% Source SHA-256 (LF): {source_hash}\n").encode() + body
    scratch = ROOT / ".venv/progress-build"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="report-", dir=scratch) as directory:
        staging = Path(directory).resolve()
        if not staging.is_relative_to(scratch.resolve()):
            raise ValueError("Build directory must stay within the repository's scratch directory")
        # Mirror repository paths so the generated LaTeX stays portable from proposal/.
        build = staging / "proposal"
        build.mkdir()
        for name in FIGURE_INPUTS:
            if name.endswith(".pdf"):
                target = staging / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)
        (build / "proposal.tex").write_bytes(generated)
        for _ in range(2):
            result = subprocess.run([pdflatex, "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", "proposal.tex"],
                                    cwd=build, capture_output=True)
            if result.returncode:
                raise RuntimeError(result.stdout.decode(errors="replace")[-12000:])
        log = (build / "proposal.log").read_text(encoding="utf-8", errors="replace")
        if "Overfull \\hbox" in log or "Overfull \\vbox" in log:
            raise RuntimeError("Report contains an overfull box; inspect and fix the layout before delivery")
        pdf = (build / "proposal.pdf").read_bytes()
        (PROPOSAL / "proposal.tex").write_bytes(generated)
        (PROPOSAL / "proposal.pdf").write_bytes(pdf)
    manifest = dict(schema_version=2, canonical_source="proposal/progress.md", source_sha256_lf=source_hash,
                    inputs_sha256_lf=fingerprints(),
                    figure_inputs_sha256=figure_fingerprints(),
                    outputs_sha256={name: digest(normalized(ROOT / name) if name.endswith(".tex") else (ROOT / name).read_bytes()) for name in OUTPUTS},
                    tools={"pandoc": subprocess.check_output([pandoc, "--version"]).decode().splitlines()[0],
                           "pdflatex": subprocess.check_output([pdflatex, "--version"]).decode().splitlines()[0]},
                    build_command="python scripts/build_progress_report.py", check_command="python scripts/build_progress_report.py --check")
    manifest_path.write_bytes((json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode())
    print("Built proposal/proposal.pdf and generated LaTeX from proposal/progress.md.")


if __name__ == "__main__":
    main()
