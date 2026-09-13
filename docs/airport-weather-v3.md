# Major U.S. airport expansion

Version 3 assesses all 100 airports classified as large in the reviewed U.S. and territories catalog. The remaining 833 medium airports stay searchable for weather and private-aviation context. Catalog inclusion is not a claim that BTS covers all traffic at an airport.

## Scientific design

The original 25 airport-aware boosted models, their weights, and their local clock-support rules are retained. Each additional airport receives independently fitted regularized logistic models, with its own probability calibration and uncertainty calibration. No new airport falls back to the pooled incumbent model. Settings are fixed in `research/airport-protocol-v3.json`; no choice of learner or hyperparameters uses the 2026 backtest results.

Training is January 2023–June 2024, probability calibration July–December 2024, and uncertainty calibration January–September 2025, with purged boundaries. Winter testing uses January–February 2026; spring stress testing uses March–June 2026. These dates and some connected flight outcomes were inspected in earlier experiments. Both evaluations are explicitly retrospective, not a new independent prospective holdout.

The January 2023 training-volume audit showed that a ten-flight minimum removed almost all windows at some smaller major airports. Before fitting or inspecting new airport test outcomes, the added-airport protocol was changed to retain nonempty windows with known outcomes. Flight counts weight the binomial model loss. Small populations can produce wide uncertainty bands; achieved coverage and band width remain visible. The incumbent models keep their original cohorts.

The fit gate requires 300 local training windows, 100 probability-calibration windows, 100 uncertainty-calibration windows, and 50 winter test windows for each direction and horizon. Live windows must also have at least 30 eligible training examples at both local clock blocks they touch. Unmet gates produce a reason, never a borrowed probability.

Forecast eligibility is separate at T−24, T−12, and T−6 for new airports. A missing 24-hour forecast no longer removes a valid six-hour example. Primary scores therefore have different denominators across horizons. The evidence page also reports Brier scores on identical windows across all three horizons where such a cohort exists. An ordinary 24-hour TAF usually cannot cover an entire two-hour window starting 24 hours after the information cutoff; adding an airport cannot manufacture that forecast history.

The published metrics retain flight-weighted Brier and log loss, window MAE, reliability bins, cancellation and diversion calibration, weather-versus-calendar skill, three-day block bootstrap intervals, and empirical 80% band coverage, width, and interval score. Approximate significance is adjusted across every actually tested airport/direction/horizon combination within each evaluation period. Moderate evidence requires the prespecified support, calibration, skill, and coverage gates; a larger map is not evidence of improved accuracy.

## Data and identifiers

Thirty-nine source months use the free [BTS reporting-carrier archive](https://www.transtats.bts.gov/ontime/) and [IEM original TAF archive](https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py?help). Two local month workers, eight airports per new forecast request, and compressed/expanded byte caps bound preparation. Original source hashes, exclusion counts, and per-horizon cohort counts accompany the evaluation. Exact incumbent source ZIPs are reused; derived features are rebuilt for the changed eligibility rule.

Explicit ICAO mappings support Alaska, Hawaii, Puerto Rico, the U.S. Virgin Islands, Guam, the Northern Mariana Islands, and American Samoa. A forecast product must match its reviewed station. Airport identifiers are not assumed to begin with K. Palm Beach historical PBI/KPBI outcomes and weather map to current DJT/KDJT; the July 2026 weather transition queries both identifiers. The [airport's official change record](https://flydjt.org/about/name-change-faqs/) documents the ICAO and IATA transition dates.

## Reproduction and publication

```powershell
.\.airport-data\model-env\Scripts\python.exe tools/airport_prepare_v3.py
.\.airport-data\model-env\Scripts\python.exe tools/airport_train_v3.py
.\.airport-data\model-env\Scripts\python.exe -m unittest discover -s tests -p 'test_airport*.py'
.\.airport-data\model-env\Scripts\python.exe tools/airport_promote_v3.py
```

Candidate results are cached separately for each additional airport. Frozen protocol and experiment-source hashes prevent silent reuse after scientific changes. Promotion checks incumbent weight preservation, local feature isolation, portable serving parity, complete catalog accounting, calibration denominators, adjusted significance, and matched-horizon denominators. Versioned v1 and v2 artifacts remain available.

## AWS operation

The collector's model-capacity guard increases from 25 to 100 audited airports. Its 120-second runtime, 1 GB allocation, hourly slot reservation, 744-run monthly ceiling, and two provider requests remain unchanged. The monthly worker retains one 900-second invocation, a 3,008 MB allocation, at most two new source months, and review-only candidate publication. Expanded history is sharded through compressed temporary files so it is never loaded entirely into memory. The learner has a 30-request cap for the two months, a 48 MB expanded-month cap, a 1.6 million-row training cap, and a 384 MB temporary-file cap. Hitting a cap stops the attempt; it does not buy more compute or promote an incomplete model.

The existing Free account requirement, early budget stop, IAM protections, and operating lease are preserved. No paid API subscription, paid-plan upgrade, new schedule, or quota reset is introduced. The initial historical preparation and model fitting run locally. Two short bounded image builds updated the existing Lambda runtime, the second incorporating the observed archive-quality fix; its temporary build resources are removed afterward.

Monthly learning needs delayed BTS outcomes and a complete rolling history. The original 39-month research selection omits October–December 2025. Those three months were prepared separately by `infra/aws/prepare_history_v3.py` and seeded for future rolling candidates only. They were not read by the current model fitting, calibration, or evaluation, and the untouched-future evaluation frontier remains June 2026. It will not claim to be learning merely because weather updates hourly. Candidates never replace live models automatically.

Airport-wide domestic reporting-carrier statistics do not cover every international, private, cargo, or charter flight. Endpoint weather cannot account for all crew, maintenance, capacity, or network effects. Historical delivery is approximated by archive/issue time plus ten minutes, with a sixty-minute sensitivity check. The model does not establish aviation safety or causally attribute disruptions to weather.

## Completed results · September 12, 2026

All 100 target airports were assessed. Seventy-two additional airports passed the local sample-support gates, giving 97 airports with tested departure and arrival models at T−6 and T−12. Forty-five also have tested T−24 models. There are 478 supported airport/direction/horizon combinations in each evaluation period, including 328 new combinations. Missing long-horizon forecasts are not extrapolated.

Pago Pago (PPG) has too few covered events: its T−6 departure slice contains 158 training windows, 56 probability-calibration windows, 96 uncertainty-calibration windows, and 24 winter test windows. Rota (ROP) and San Bernardino (SBD) have no reporting-carrier departure records in the 39 selected source months. All three remain weather-only; this is not a claim they have no flights.

The winter mean across supported slices is Brier 0.16715 versus calendar-only 0.17255. Mean band coverage is 74.4%, below the 80% target; only 22 slices satisfy the moderate-evidence rule, including eight new-airport slices. Spring mean Brier is 0.17364 versus baseline 0.17583, with 78.2% mean band coverage and 60 moderate-evidence slices. These are unweighted means across different airport/horizon populations, not an aggregate v2-to-v3 improvement claim. Most added-airport weather-effect evidence remains limited, and unfavorable metrics remain visible.

The additional-airport fit and evaluation took 167.52 seconds locally, including data loading and both retrospective periods but excluding source preparation. A genuine snapshot containing all 100 airport entries scored in 0.135 seconds locally. Promotion passed 20,992 additional portable parity vectors and preserved incumbent weights. The combined model is 5.00 MiB and evaluation 4.61 MiB.

AWS published version `airport-v3-us-local-expansion` at 04:07:47 UTC with 300 currently available direction/horizon outlooks. That real collector invocation took 15.48 seconds and used 234 MB of its unchanged 1,024 MB allocation. It remains well within the 120-second ceiling. Full monthly rolling challenger performance still depends on new data and is subject to its existing fixed stop limits; local timings are not an AWS bill guarantee.

The operating lease and early budget protections were verified unchanged, and the Free account remains active. The expanded 42-month historical upload was 51,952,464 bytes. Cloud model/evaluation hashes match the reviewed local artifacts. Deployment and runtime evidence are recorded privately under `.airport-data/aws-package/v3-*.json`; the full public experiment is archived under `public/data/airport-weather/versions/v3/`.
