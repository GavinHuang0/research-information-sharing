# Current research progress

The current professor-facing document includes the original research question, completed work, first empirical findings, limitations, and next steps. It is a concise progress report, separate from the detailed experiment protocols.

- **[Read the Markdown report](progress.md)**: canonical content, directly readable on GitHub.
- **[Read the PDF](proposal.pdf)**: generated from the same Markdown for sharing.
- [Generated LaTeX](proposal.tex): retained for transparency; edit the Markdown rather than this file.
- [Synchronization record](progress_sync.json): fingerprints of the source, template, builder, and generated outputs.

## Build and verify

From the repository root, with Pandoc and TeX Live/PDFLaTeX installed:

```bash
python scripts/build_progress_report.py
python scripts/build_progress_report.py --check
```

On Windows use `.\.venv\Scripts\python.exe` in place of `python`. From this folder, `make -B` builds and `make check` verifies. The PDF is compiled twice with shell escape disabled; intermediate files remain in an ignored scratch directory. Markdown links stay repository-relative; generated PDF links point to GitHub.

After changing the Markdown, rebuild all outputs and visually inspect the PDF pages. The check refuses stale or modified outputs. Compiler/Pandoc versions are recorded; a different version can change PDF bytes without changing report content.

## Historical proposal

The [October 9, 2026 original proposal](archive/2026-10-09/proposal.pdf), [LaTeX](archive/2026-10-09/proposal.tex), [bibliography](archive/2026-10-09/references.bib), and original Makefile are preserved under [archive/2026-10-09](archive/2026-10-09/), with original-byte [checksums](archive/2026-10-09/SHA256.json). The current report retains its research rationale while updating status; its short selected references are part of the canonical Markdown. The historical proposal is not presented as the current project record.

## Detailed experimental records

- [Experiment 1: completed fixed S6 pilot](../experiments/01-fixed-s6-pilot/README.md).
- [Experiment 2: planned bootstrap and coefficient-history study](../experiments/02-bootstrap-history/README.md). It has not been executed.
