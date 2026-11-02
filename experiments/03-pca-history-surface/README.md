# Experiment 3: PCA dimension and estimation-history surfaces

**Status: planned November 2, 2026; not implemented or run.** No new forecasts, heatmaps, bootstrap draws, p-values, or empirical findings have been generated. The [detailed protocol](protocol.md) and [non-executable planning settings](../../configs/experiment_03_plan.toml) record the design separately from the concise progress report. Existing experiment runners do not implement this surface design.

Experiment 2 fixed two PCs and expanding predictor-only PCA while changing coefficient history. This follow-up asks how forecast accuracy varies jointly with the number of PCs and the history available to estimate the representation and forecasting coefficients. It compares three fixed slope rules rather than selecting a new favorable donor group.

| Part | PCA estimation | Supervised coefficient estimation | Purpose |
| --- | --- | --- | --- |
| A: matched histories | Recent L eligible pairs | The same recent L pairs | Describe joint dimension/history performance when both estimation stages have limited history |
| B: expanding PCA | All eligible historical predictor rows before the fitting cutoff | The same recent L pairs used in Part A | Separate the effect of longer predictor-only measurement history from coefficient history |

The proposed heatmap axes are **K = 1, ..., 8 PCs** and **L = 52, 78, ..., 520 eligible pairs**, with a shared expanding-coefficient control. **K=0 is the own-history reference**, not a fitted zero-component PCA. Targets remain `Food, Mach, Banks, Oil, Util, Hlth`; measurement membership is all 48 industries. Common and partially pooled slopes use all 48 outcomes; separate slopes retain target-specific relationships. Industry intercepts and own current/four-/twelve-week coefficients remain separate.

Separate, common, and partially pooled surfaces must use the same declared dates and fitted measurement representation within each K/history/part comparison. Partial pooling's penalty is selected using historical target validation only, following the protocol; the surface does not authorize choosing K, L, membership, or a final winner after inspecting evaluation losses. Full procedures, control treatment, timing, and reporting requirements belong in [protocol.md](protocol.md).

The previously used evaluation periods are **already seen**. Any resulting surfaces on those periods are exploratory, not a new holdout or a confirmatory search for a favorable cell. A dimension/history pattern is not by itself evidence that factors add population information, that a donor selector works, or that a trading strategy is profitable.

**Calibration and power work is deferred and remains pending.** Experiment 2's adverse synthetic rejection/coverage findings are not repaired by adding PCs, windows, or partial pooling. A saved-loss paired bootstrap is technically feasible for forecasts from historically tuned partial pooling, just as for the other fixed procedures. Such resampling would condition on the saved forecasts; it would neither refit the learning pipeline nor establish valid nominal p-values, coverage, or selection-adjusted inference. This plan produces no new statistical validation claim.
