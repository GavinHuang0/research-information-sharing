# Experiment 3: execution record

**Completed November 3, 2026.** Earlier/later forecasts, joint saved-loss inference, tables, figures, and independent output audits have completed. This mutable account records what ran separately from the unchanged [November 2 protocol](protocol.md). Interpretation belongs in [results.md](results.md). Both periods were already seen; calibration and power research remains deferred.

## Source freeze before empirical execution

The implementation and validation were committed as `a1db310f1f15dd08c545a72165c04d2f992a0030` at **11:59:15 EST on November 3, 2026**. The [source freeze](../../results/experiment-03-2026-11-03/source_freeze.json), created at **11:59:19.071477 EST**, was committed as `358636450c282ec902d95827cf333f68aa047599` at **11:59:36 EST**, before earlier-seen forecasts began at **11:59:40.102526 EST**. Precise UTC timestamps and normalized file hashes remain in the saved artifacts.

The run is stored under `results/experiment-03-2026-11-03/`, including the [executable configuration copy](../../results/experiment-03-2026-11-03/config.toml), [protocol copy](../../results/experiment-03-2026-11-03/protocol.md), [calendar](../../results/experiment-03-2026-11-03/calendar.json), [canonical cell inventory](../../results/experiment-03-2026-11-03/cells.csv), and [environment/input metadata](../../results/experiment-03-2026-11-03/metadata.json). The original planning document's proposed-status text is preserved; it does not describe the current execution state.

## Exact computation executed

The inherited French snapshot, six target industries, weekly log-return-variation features, own-history controls, and all-48/both-weightings complete-case dates are unchanged. Both evaluation periods have **already been inspected** in earlier experiments: `earlier_seen` ends December 2024, and `later_seen` covers January 2025–August 2026. The freeze prevents undisclosed computational redesign, not retrospective use of those dates or restoration of a fresh holdout.

Finite coefficient windows are 52, 78, ..., 520 retained pairs. The grid uses K=1–8, separate/common/partial slopes, and matched versus expanding PCA. Common/partial slopes use all 48 outcomes; separate slopes use the target outcome. Industry intercepts and local coefficients remain unpenalized and separate. There are 912 finite factor cells, 24 deduplicated expanding-coefficient factor controls, and 20 own-history references: **956 canonical cells per weighting and period**. K=0 denotes the own reference, not a factor estimator.

At scheduled anchor `a=572+13*k`, let `b=a-52`. Inner coefficient fits use `[b-L:b)` and outer fits `[a-L:a)`; expanding controls start at zero. Matched PCA and both its column/score scalers use those same pair-row windows. Expanding PCA/scalers use `[0:b)` and `[0:a)`. Each unique representation computes eight deterministic PCs once; explicit first-K score adapters are used at fitting and prediction, shared across targets, slope rules, and penalties. Local-control residualization still uses the designated coefficient window.

The normalized partial-pooling objective and ascending lambda grid `(0.01, 0.1, 1, 10, 100)` are preserved, including no penalty division by K. Each target/mode/L/K chooses lambda by its own historical 52-pair validation MSE, using the first declared penalty on ties. K and L remain fixed surface axes, with no whole-surface winner selection. The refit schedule must replay the crossing block rather than restart at the period boundary.

Every candidate, tuning score, prediction, and actual is retained in deterministic compressed shards, with row/byte/hash inventories and the frozen file-size checks. Canonical NPY prediction arrays are read through memory maps for reporting; complete arrays are not copied into a single in-memory forecast table. Expanding-coefficient controls are stored once and displayed separately from finite L coordinates.

## Validation gates and expected inventories

The saved [preflight](../../results/experiment-03-2026-11-03/preflight.md), [validation log](../../results/experiment-03-2026-11-03/validation.txt), and [successful validation status](../../results/experiment-03-2026-11-03/validation_status.json) record 118 software tests and a focused six-test orchestration recheck. Numerical tests cover K-prefix dimensions, PCA/scaler and coefficient windows, normalized pooling solutions, historical tuning, joint bootstrap algebra, anchor membership, streaming integrity, and bounded reporting. A synthetic technical benchmark checked feasibility only. None of these was a calibration or power study.

The freeze verified exact bytes for 107 manifest-listed files from Experiments 1 and 2, alongside the archived daily data/provenance. The inherited calendar has 1,377 eligible pairs, with expected evaluated counts 718 earlier-seen and 87 later-seen dates. First later pair 1290 must replay anchor 1287. These are source/calendar gates, not accuracy results.

Declared output counts were verified against the completed artifacts:

| Item | Declared inventory |
| --- | ---: |
| Earlier-seen raw forecasts, both weightings and six targets | 8,236,896 |
| Later-seen raw forecasts, both weightings and six targets | 998,064 |
| Complete per-target summary cells, both periods/weights | 22,944 |
| Aggregate summary cells, both periods/weights | 3,824 |
| Own gains / finite PCA-mode differences / pooling differences per weighting-period | 936 / 456 / 624 |
| Marginal bootstrap rows, both periods/weights and three block settings | 24,192 |
| Later-seen anchor rows, both weights and three block settings | 180 |

The bootstrap uses saved scalar losses and one shared stationary-date index matrix per period/block setting. It recomputes candidate and matching-own MSEs in every draw without refitting PCA, coefficients, or lambda. Own gains and common-denominator mode/pooling differences are distinct statistics. All 936 factor own-gain cells and all mode/pooling contrasts receive nominal basic marginal intervals; only the 30 fixed later-seen anchors receive one-sided p-values and one joint Holm adjustment per weighting/block. No nonanchor p-values, simultaneous surface bands, or significance stars are authorized.

## Completed stages and interpretation limits

| Stage | Current record |
| --- | --- |
| Implementation/source/calendar gates | Completed before empirical forecasts |
| Source/configuration/input freeze | Committed before empirical execution |
| Earlier-seen forecasts | Completed; [full saved-output audit passed](../../results/experiment-03-2026-11-03/audit_earlier_seen.json) |
| Later-seen forecasts | Completed; [full saved-output audit passed](../../results/experiment-03-2026-11-03/audit_later_seen.json) |
| Joint bootstrap and 30-anchor families | Completed; [all intervals/tails/families independently audited](../../results/experiment-03-2026-11-03/audit_inference.json) |
| Complete tables/figures | [Report manifest](../../results/experiment-03-2026-11-03/reports/report_manifest.json) and [exact report-file checksums](../../results/experiment-03-2026-11-03/reports/stage_manifest.json) saved |

**Calibration and power studies remain deferred and were not run.** The [inherited diagnostic](../../results/experiment-03-2026-11-03/inherited_calibration_diagnostics.json) retains Experiment 2's adverse null rejection/coverage evidence. Software correctness and an independently reproducible bootstrap do not establish nominal coverage, calibrated p-values, full-pipeline inference, or selection-adjusted surface claims. This limitation remains even if an anchor's adjusted p-value is small.

Saved-output verification establishes consistency with the declared computation, not statistical calibration or a new untouched evaluation. The [results account](results.md) retains all primary anchors, adverse cells, target heterogeneity, and sensitivity settings without selecting a new policy.

## Completed earlier-seen audit and preservation

The [earlier-seen audit](../../results/experiment-03-2026-11-03/audit_earlier_seen.json) verified **8,236,896 raw forecasts**, **1,481,088 tuning records**, 718 dates per cell, all memberships, every historical window/scaler, partial-penalty candidate and target argmin, daily-derived actuals, and agreement between streamed records and canonical NPY predictions. The [timing record](../../results/experiment-03-2026-11-03/earlier_seen/timing.json) reports 112 weighting/refit blocks, 4,478 PCA fits, and 290.806 seconds overall: 137.178 seconds for value weighting and 152.230 for equal, plus shared overhead.

Overlapping Experiment 2 forecasts agree on 137,856 records with maximum absolute difference **8.8818e-14**. This is estimator/reproduction consistency, not independent economic replication. A separate [original-estimator oracle audit](../../results/experiment-03-2026-11-03/audit_original_estimator_oracles.json) checked 12 weighting/specification groups using the original PCA/FactorForecaster and an independent K-prefix adapter, without the optimized surface solver. It passed its recorded numerical tolerances, including all candidate validation losses and selected penalties in those groups. That audit also hashed 245 earlier-stage files and checked 236 raw gzip shards; the largest gzip shard was 3,925,120 bytes and all stage files were below the frozen 80-MiB threshold. These checks are neither calibration nor power research.

The audited earlier outputs were preserved in commit `583894a97f43c1c147e92ff0263904ab6b68cae3` at **12:06:32 EST**. The later-stage guard recorded its [replay freeze](../../results/experiment-03-2026-11-03/later_freeze.json), and later-seen forecasts began at **12:06:36.355152 EST**. Both periods remain seen-period exploration; this intermediate preservation is not a new holdout selection or a change to the frozen grid.

## Completed later-stage, inference, and report audits

Earlier-seen forecasting finished at **12:04:31.895475 EST**, before its audits and preservation commit. Later-seen forecasting finished at **12:07:14.939357 EST**. The [later timing record](../../results/experiment-03-2026-11-03/later_seen/timing.json) reports **998,064 predictions**, **185,136 tuning records**, 14 weighting/refit blocks, 560 fitted eight-component PCA representations, and **38.145 seconds** overall. Value/equal weighting took 18.443/18.636 seconds respectively, plus shared overhead.

The [later audit](../../results/experiment-03-2026-11-03/audit_later_seen.json) verified every streamed prediction, all dates/memberships, daily-derived actuals, PCA/scaler and supervised windows, and partial-penalty candidate losses/argmins. Its 16,704 overlapping Experiment 2 forecasts agree with maximum absolute difference **7.1054e-14**. The first later pair remained 1290 with scheduled anchor 1287; the subsequent anchors remained 1300, 1313, 1326, 1339, 1352, and 1365. No extra boundary fit was introduced.

Saved inference completed at **12:08:57.238858 EST**. The [independent inference audit](../../results/experiment-03-2026-11-03/audit_inference.json) reconstructed six exact joint index matrices, checked all 24,192 effect/interval rows, reproduced 180 anchor tail counts and six Holm-30 families, and found maximum effect/interval discrepancy **1.1103e-16**. The report stage completed at **12:10:09.332579 EST**, and the independent inference audit was recorded at **12:10:13.713230 EST**. The interpretation record was finalized only after those checks passed.

The [complete target table](../../results/experiment-03-2026-11-03/reports/target_summary.csv), [aggregate table](../../results/experiment-03-2026-11-03/reports/aggregate_summary.csv), [all marginal intervals](../../results/experiment-03-2026-11-03/reports/bootstrap_summary.csv), and [all anchor results](../../results/experiment-03-2026-11-03/reports/anchor_table.csv) are saved with **19 PNG/PDF figure pairs**. The [report manifest](../../results/experiment-03-2026-11-03/reports/report_manifest.json) lists each file and its interpretation labels. Prediction/tuning records are indexed by the [earlier](../../results/experiment-03-2026-11-03/earlier_seen/stage_manifest.json) and [later](../../results/experiment-03-2026-11-03/later_seen/stage_manifest.json) manifests. Per-period inference and the [combined inference manifest](../../results/experiment-03-2026-11-03/inference/stage_manifest.json) retain exact index/loss/output fingerprints. No old experiment source, protocol, or archived result was changed.

## Reproduction without overwriting the archive

Use the pinned [analysis environment](../../requirements-analysis-lock.txt) and byte-identical frozen implementation/configuration. A new checkout must record a successful test log and its matching status/hash before the freeze guard will proceed. The following PowerShell block regenerates those two prerequisite records from the test result; it does not run calibration or power simulations:

```powershell
$env:PYTHONPATH = 'src'
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
New-Item -ItemType Directory -Force .venv/tmp | Out-Null
$env:TEMP = (Resolve-Path .venv/tmp).Path
$env:TMP = $env:TEMP
@'
import hashlib, io, json, unittest
from pathlib import Path
stream = io.StringIO()
suite = unittest.defaultTestLoader.discover('tests')
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
raw = stream.getvalue().encode('utf-8')
Path('.venv/experiment_03_validation.txt').write_bytes(raw)
status = {
    'status': 'passed' if result.wasSuccessful() else 'failed',
    'tests_run': result.testsRun,
    'validation_log_sha256_lf': hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest(),
}
Path('.venv/experiment_03_validation_status.json').write_text(
    json.dumps(status, indent=2) + '\n', encoding='utf-8')
raise SystemExit(not result.wasSuccessful())
'@ | .\.venv\Scripts\python.exe -
```

Choose a new run directory, then execute the guarded stages in order:

```powershell
.\.venv\Scripts\python.exe scripts/run_experiment_03.py --config configs/experiment_03.toml --output results/reproduction-03 --stage freeze
.\.venv\Scripts\python.exe scripts/run_experiment_03.py --config configs/experiment_03.toml --output results/reproduction-03 --stage earlier_seen
.\.venv\Scripts\python.exe scripts/run_experiment_03.py --config configs/experiment_03.toml --output results/reproduction-03 --stage audit-earlier
.\.venv\Scripts\python.exe scripts/run_experiment_03.py --config configs/experiment_03.toml --output results/reproduction-03 --stage later_seen
.\.venv\Scripts\python.exe scripts/run_experiment_03.py --config configs/experiment_03.toml --output results/reproduction-03 --stage audit-later
.\.venv\Scripts\python.exe scripts/run_experiment_03.py --config configs/experiment_03.toml --output results/reproduction-03 --stage inference
.\.venv\Scripts\python.exe scripts/run_experiment_03.py --config configs/experiment_03.toml --output results/reproduction-03 --stage audit-inference
.\.venv\Scripts\python.exe scripts/run_experiment_03.py --config configs/experiment_03.toml --output results/reproduction-03 --stage report
.\.venv\Scripts\python.exe scripts/run_experiment_03.py --config configs/experiment_03.toml --output results/reproduction-03 --stage finalize
```

Freeze refuses an existing experiment directory, and stage guards verify source/configuration/input fingerprints and saved-output hashes. New stage directories are not silently replaced. Preserve independent original-estimator checks alongside the complete output audits when reproducing numerical optimizations. On macOS/Linux, use the environment's `python` command and equivalent environment/temporary-directory setup. Do not reuse the completed archive as an output directory or alter frozen settings after viewing its surfaces.
