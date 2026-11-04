# Current research progress

The current professor-facing document reconciles the original proposal with current progress: project purpose and hypotheses, summaries of related research, each experiment's purpose/brief procedure/results, and planned next steps including calibration. It is separate from the detailed experiment protocols.

The PDF has three pages of proposal, progress, and references, followed by two landscape pages with the existing earlier- and later-period Experiment 3 gain maps. Markdown displays the archived PNGs; the PDF embeds the corresponding vector figures without changing the experimental results.

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

After changing the Markdown, rebuild all outputs and visually inspect the PDF pages. The check refuses stale or modified outputs and verifies the four PNG/PDF figure-input hashes. Compiler/Pandoc versions are recorded; a different version can change PDF bytes without changing report content.

## Historical proposal

The [October 9, 2026 original proposal](archive/2026-10-09/proposal.pdf), [LaTeX](archive/2026-10-09/proposal.tex), [bibliography](archive/2026-10-09/references.bib), and original Makefile are preserved under [archive/2026-10-09](archive/2026-10-09/), with original-byte [checksums](archive/2026-10-09/SHA256.json). The current report retains its research rationale while updating status; its short selected references are part of the canonical Markdown. The historical proposal is not presented as the current project record.

## Detailed experimental records

- [Experiment 1: completed fixed S6 pilot](../experiments/01-fixed-s6-pilot/README.md).
- [Experiment 2: completed bootstrap and coefficient-history study](../experiments/02-bootstrap-history/README.md), including the new-period findings and unresolved calibration limits.
- [Experiment 3: completed PCA-dimension/history surfaces](../experiments/03-pca-history-surface/README.md), including [all primary anchor results and surface interpretations](../experiments/03-pca-history-surface/results.md), [execution/reproduction record](../experiments/03-pca-history-surface/executed.md), and the unchanged [scientific protocol](../experiments/03-pca-history-surface/protocol.md). All primary anchor decisions are non-rejections; both periods were already seen, and calibration/power research remains deferred.
