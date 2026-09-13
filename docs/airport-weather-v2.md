# Airport weather experiment v2

Historical version. [Version 3](airport-weather-v3.md) is current; it retains these 25 models while adding independently fitted airport models.

This local experiment expands the original nine-airport project to 25 major US airports. It retains free NOAA weather collection, static visitor snapshots, the worldwide weather map, and private-aviation weather context. No paid providers, hosted jobs, deployments, or subscriptions are added. Global outcome transfer remains unsupported.

## Frozen experiment

The specification is `research/airport-protocol-v2.json`. Airport selection reflects major hubs and contrasting climates, not observed test performance. All 25 currently issue long enough TAFs to make T−24 comparisons possible, but historical missingness still excludes some windows.

Three chronological development folds cover winter, summer, and autumn 2024. Fixed linear and gradient-boosted candidates are evaluated in every direction/horizon slice. Selection uses mean flight-weighted disruption Brier over the 18 fold/direction/horizon results per candidate. Boosting must improve by at least 0.5% relative to replace the simpler linear candidate. No 2025 or 2026 outcome file is opened by the selection loader. The fold interval-calibration blocks are reserved/unused during learner selection, preserving long outcome-release gaps; only the final model receives the interval calibration described below.

Final feature-model fit: January 2023–June 2024. Probability calibration: July–December 2024. Interval calibration: January–September 2025. New holdout: January–February 2026, which was not collected or evaluated for v1. Previously inspected March–June 2026 is a separate, clearly labeled stress re-evaluation. July 2026 was absent from the public BTS archive when the protocol was fixed. The new winter test is therefore not a claim of independent all-season performance.

Model selection validation overlaps the final probability-calibration period. Final interval calibration and the new holdout remain outside selection. The final matched calendar baseline uses the same chosen learner and probability-calibration procedure as the weather model, so weather skill is not confused with changing algorithms.

## What changed scientifically

- The original weather feature extractor and outcome definitions stay fixed. Boosted trees can learn nonlinear weather thresholds and interactions using those same features. Additional raw data providers are not needed to test that improvement.
- Calibration learns a sigmoid on model log odds plus regularized airport offsets over six months, instead of a single pooled month. Cancellation, diversion, and delay heads remain conditional, with mutually exclusive unconditional published probabilities.
- Nine months of interval residuals cover multiple seasons. Separate signed lower and upper residual quantiles allow asymmetric bands. Predicted-risk bins (<25%, 25–50%, ≥50%) receive their own airport bands only with at least 100 calibration windows; otherwise the airport-wide band is used. Coverage, width, and the proper interval score are reported together. Wide bands alone do not establish improvement.
- Skill intervals resample calendar blocks of up to three days, retaining correlated flights and adjacent windows. Approximate centered-bootstrap p-values receive Benjamini–Hochberg adjustment across 150 airport/direction/horizon comparisons within each evaluation period. These remain exploratory approximations under serial/cross-airport dependence.
- A moderate evidence label requires at least 45 test days, 5,000 flights, positive lower 95% skill bound, adjusted q≤0.1, calibration error below 5 percentage points, and interval coverage ≥75%. These thresholds were frozen before fitting. They are not operational safety thresholds or a 95% assurance of an individual flight outcome.
- Horizon comparisons keep the same eligible windows. Per-airport/direction/horizon forecast gaps and low-volume/unknown-outcome exclusions are recorded in preparation metadata. A 60-minute weather-delivery sensitivity check retains the original fitted model and reports its overlap with the main 10-minute assumption.
- V1 comparisons use exactly the same events and features for the original nine airports. V1 had later training/calibration periods, so these are whole-version retrospective comparisons, not isolated algorithm experiments or necessarily deployable winter baselines.

## Completed results · September 11, 2026

The selected learner is gradient boosting. Mean development Brier was 0.16676 versus 0.17208 for the linear candidate (3.1% lower). Selection was fixed before reading the fresh holdout. Final training contains 174,949 airport-direction windows and 8,091,340 flight events; probability calibration 58,244 windows; interval calibration 87,496 windows. The new winter test contains 17,031 windows / 811,821 events; spring re-evaluation 39,609 windows / 1,912,395 events. Events can count both endpoints of the same flight; they are not unique flight totals.

Across 150 winter airport/direction/horizon slices, mean Brier is 0.17091 versus 0.17936 for the matched calendar baseline. Mean interval coverage is 70.6%, below the 80% target. Only 23 slices meet the stricter moderate-evidence rule. For the original nine airports on the same fresh winter events, mean Brier improves modestly from 0.17242 in v1 to 0.17136 in v2. This does not mean every airport improved.

DFW departures at T−6 illustrate both progress and limitations:

| Metric | Fresh winter v1 | Fresh winter v2 | Previously seen spring v1 | Spring v2 |
|---|---:|---:|---:|---:|
| Disruption Brier ↓ | 0.19596 | 0.19723 | 0.21053 | 0.20931 |
| Window MAE ↓ | 11.4 pp | 12.2 pp | 14.3 pp | 13.2 pp |
| 80% target band coverage | 80.9% | 82.5% | 61.3% | 79.6% |
| Mean band width | 29.9 pp | 35.9 pp | 30.1 pp | 40.9 pp |
| Interval score ↓ | 0.682 | 0.636 | 0.698 | 0.598 |
| Cancellation predicted | 1.5% | 2.5% | 1.3% | 2.6% |
| Cancellation observed | 6.5% | 6.5% | 3.4% | 3.4% |

Winter probability accuracy regresses slightly at DFW even though aggregate original-airport accuracy improves. Winter cancellation remains materially underestimated. Spring interval coverage improves partly through wider bands; the lower interval score and window error provide additional evidence of improvement there. Those spring outcomes were already seen in v1 and are not promoted as a new independent discovery. The interface preserves these comparisons and uses winter results for live confidence labels.

Promotion checks passed for 25 airports, 150 fresh test slices, 150 stress slices, and 1,200 portable parity vectors. The full model, evaluation, validation, and experiment code hashes are archived locally in `public/data/airport-weather/versions/v2`.

## Local reproduction commands

Use the existing model venv and pinned `research/requirements.txt`:

```powershell
.\.airport-data\model-env\Scripts\python.exe tools/airport_prepare_v2.py
.\.airport-data\model-env\Scripts\python.exe tools/airport_train_v2.py select
.\.airport-data\model-env\Scripts\python.exe tools/airport_train_v2.py evaluate
.\.airport-data\model-env\Scripts\python.exe -m unittest discover -s tests -p 'test_airport*.py'
.\.airport-data\model-env\Scripts\python.exe tools/airport_promote_v2.py
```

Preparation fixes 39 source months, refuses more than 40, and uses at most two month workers. TAF archives are batched to eight airports per request to avoid silent truncation at 9,999 products. The compressed/expanded byte limits from v1 remain. Derived aggregates, original TAF ZIPs, and source hashes are cached in `.airport-data/model-v2`; each raw BTS ZIP is removed only after its derivation is durable. This is an explicit local research run outside the live monthly request quota. It is not scheduled.

Selection requires all 24 months of 2023–2024 and can run while later months finish preparation. Evaluation requires all 39 months and a completed selection record matching the protocol hash. It refuses to overwrite a completed candidate evaluation. Model/feature changes require a new versioned experiment and rebuilt derived features, not reuse of old caches under the same name. Cached development records assume the frozen code/protocol; archive or version the experiment before changing either.

Candidate artifacts go to `.airport-data/model-v2/candidate`. Promotion validates hashes, date/version agreement, 36 unique development slices, common horizon denominators, multiplicity adjustments, and 1,200 portable-serving parity vectors. It scores the actual downloaded weather before changing the current local model. No web deployment occurs. Immutable version snapshots live under `public/data/airport-weather/versions/v1` and `versions/v2`; the original published numbers remain available.

Histogram models are exported as numeric tree nodes and sigmoid parameters, not pickle or executable serialized objects. Every fitted tree ensemble is checked against native sklearn decision scores. Threshold-edge and serving/batch parity tests cover the exported format. Live scoring still uses only the Python standard library; sklearn is needed only for local research. Visitors read shared static scores and never invoke provider requests or fit a model.

## Remaining limitations

Final-vintage BTS records are used without release-vintage reconstruction. Scheduled-flight outcomes include cancellations already known at a cutoff because cancellation announcement timestamps are unavailable. TAF delivery is approximated historically by issue/product time plus a lag. Endpoint weather cannot explain all crew, maintenance, capacity, network, or route effects. Airport clock blocks with fewer than 30 eligible training windows are withheld live; overnight data are not extrapolated. Fixed historical windows and rolling live windows differ. Forecast-error, upstream-weather, airport-transfer, and prospective monitoring experiments remain future work, requiring another untouched evaluation set.

## Sources

- [BTS public source archives](https://transtats.bts.gov/PREZIP/)
- [IEM original forecast product archive](https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py?help)
- [scikit-learn histogram gradient boosting](https://scikit-learn.org/stable/modules/ensemble.html#histogram-based-gradient-boosting)
- [scikit-learn probability calibration](https://scikit-learn.org/stable/modules/calibration.html)

Source URLs and content hashes for every downloaded month are in the evaluation artifact. Exact package versions are pinned; v2 introduces no new package dependencies.
