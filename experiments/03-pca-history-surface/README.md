# Experiment 3: PCA dimension and estimation-history surfaces

**Status: completed November 3, 2026.** Both forecast stages and every saved-loss interval/anchor calculation passed independent audits. **No prespecified anchor passes the primary block-13 Holm rule in either weighting.** See the [execution/reproduction record](executed.md) and [complete results, all 60 primary anchor rows, and all 19 figure pairs](results.md).

Point-estimate maps show that extra PCs can hurt sharply at short histories, especially with separate slopes; common/partial pooling often cushions that deterioration without a uniform best rule. History and PCA-mode patterns change across the two already-seen periods. At block 26 only, two equal-weighted sensitivity anchors cross the adjusted threshold; they do not replace the primary non-rejections. No new K/L/mode/rule winner was selected.

The November 2 [protocol](protocol.md) and [planning settings](../../configs/experiment_03_plan.toml) retain their original documentation-only wording as frozen design records. The [executable configuration](../../configs/experiment_03.toml) and [dedicated runner](../../scripts/run_experiment_03.py) implement the completed computation. The [source freeze](../../results/experiment-03-2026-11-03/source_freeze.json) precedes empirical execution. Calibration and power work remains deferred.

Experiment 2 fixed two PCs and expanding predictor-only PCA while changing coefficient history. This follow-up evaluated how forecast accuracy varies jointly with the number of PCs and the history available to estimate the representation and forecasting coefficients. It compared three fixed slope rules without selecting a new donor group.

| Part | PCA estimation | Supervised coefficient estimation | Purpose |
| --- | --- | --- | --- |
| A: matched histories | Recent L eligible pairs | The same recent L pairs | Describe joint dimension/history performance when both estimation stages have limited history |
| B: expanding PCA | All eligible historical predictor rows before the fitting cutoff | The same recent L pairs used in Part A | Separate the effect of longer predictor-only measurement history from coefficient history |

The frozen heatmap axes are **K = 1, ..., 8 PCs** and **L = 52, 78, ..., 520 eligible pairs**, with a shared expanding-coefficient control. **K=0 is the own-history reference**, not a fitted zero-component PCA. Targets remain `Food, Mach, Banks, Oil, Util, Hlth`; measurement membership is all 48 industries. Common and partially pooled slopes use all 48 outcomes; separate slopes retain target-specific relationships. Industry intercepts and own current/four-/twelve-week coefficients remain separate.

Separate, common, and partially pooled surfaces use the same declared dates and fitted measurement representation within each K/history/part comparison. Partial pooling's penalty was selected using historical target validation only. The full record contains 936 distinct factor cells plus 20 own references per weighting/period, every target, all marginal interval rows, and all fixed anchor/sensitivity results. Full procedures, control treatment, and timing are recorded in [executed.md](executed.md) and the unchanged [protocol](protocol.md).

Both evaluation periods were **already seen**. These surfaces are exploratory, not a new holdout or a confirmatory search for a favorable cell. A dimension/history pattern is not by itself evidence that factors add population information, that a donor selector works, or that a trading strategy is profitable.

**Calibration and power work is deferred and remains pending.** Experiment 2's adverse synthetic rejection/coverage findings are not repaired by adding PCs, windows, or partial pooling. The saved-loss bootstrap conditioned on forecasts from historically tuned procedures; it did not refit PCA, coefficients, or penalty selection. All marginal intervals remain approximate. Only the 30 prespecified later-seen anchors received p-values, with one Holm family per weighting/block setting; the rest of the surface received no p-value stars. Numerical audit success is not a new calibration or full-pipeline validity result.
