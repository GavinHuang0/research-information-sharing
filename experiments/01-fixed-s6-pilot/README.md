# Experiment 1: fixed S6 industry forecasting pilot

**Status: completed.** Executed October 27, 2026; this experiment record was organized October 31, 2026. This folder records the completed experiment independently of the professor-facing progress document. It introduces no new forecast run, model, or statistical test. Experiment 2 is a separate planned experiment and has not been run.

The question was whether measuring two common components from more industries and sharing their predictive slopes across more outcomes improve next-week industry log-variance forecasts. The six fixed targets and small panel were `S = (Food, Mach, Banks, Oil, Util, Hlth)`. The procedure chosen on primary development forecasts used all 48 measurement industries and common factor slopes across all 48 outcomes. Its final equal-target mean MSE ratio to own-history regression was **0.957267**, a **4.2733% improvement**; the equal-weighted robustness improvement was **1.6562%**, including an unfavorable Banks result.

| Record | Location or value |
| --- | --- |
| Exact executed procedures | [Protocol account](protocol.md), with links to the original executed specification |
| Findings and limitations | [Results and interpretation](results.md) |
| Original completed run | [Archived run README](../../results/fixed-pilot-2026-10-27/README.md) |
| Authoritative executed specification | [Archived protocol](../../results/fixed-pilot-2026-10-27/protocol.md), [configuration](../../results/fixed-pilot-2026-10-27/config.toml), [18-policy inventory](../../results/fixed-pilot-2026-10-27/policies.json) |
| Inputs | October 16, 2026 French 48-industry daily snapshot; [data catalog](../../data/README.md) and [input/code/environment fingerprints](../../results/fixed-pilot-2026-10-27/metadata.json) |
| Sample | 1,290 aligned pairs; 260 initial-history pairs, 874 development forecast dates, 156 final forecast dates per target/policy/weighting |
| Implementation commit | `07edc7696bcd4a41dee0f80c94929c54f6ef93b6` |
| Development freeze commit | `b2161f6b5e5293de48e461b8a1b56bb7e693ffc7`; [frozen procedure and development scores](../../results/fixed-pilot-2026-10-27/frozen_procedure.json) |
| Completed archive commit | `cccf6dd029723e19e2d422433dc686fc5b7e8cbe` |
| Verification | [Development audit](../../results/fixed-pilot-2026-10-27/development_audit.json), [final audit](../../results/fixed-pilot-2026-10-27/final_audit.json), [58-test validation](../../results/fixed-pilot-2026-10-27/validation.txt), [artifact manifest](../../results/fixed-pilot-2026-10-27/artifact_manifest.json) |

Development ran first, and the frozen procedure was committed at **00:14:47 EDT on October 27, 2026**, before the logged final-stage start at **00:14:51.672943 EDT**. Exact UTC timestamps and the commit-order audit are in the [final audit](../../results/fixed-pilot-2026-10-27/final_audit.json). The implementation metadata records a dirty working tree at development start; the detailed normalized source/configuration hashes in the frozen manifest identify the executed files.

The files in this folder are a readable account of the existing record. The archived run files and their fingerprints remain the authority for what was executed; future changes belong to another experiment rather than a revision of Experiment 1's frozen procedure. Full-precision predictions, candidate validation scores, explicit memberships, figures, and all 18 policy comparisons remain in the [original artifact archive](../../results/fixed-pilot-2026-10-27/README.md#tables-predictions-tuning-and-figures).
