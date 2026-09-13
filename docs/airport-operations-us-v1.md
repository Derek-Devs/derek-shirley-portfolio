# FAA + weather: nationwide operations model

The operations model is an **optional experiment** in the airport tool. Weather
remains the default: the new model slightly improves on a matched, independently
fitted local weather baseline, but does not improve on the actual currently
served weather model overall. No existing weather weights were replaced.

## What was tested

All 100 major U.S. and territory airports in the existing protocol were assessed.
97 support local models; PPG, ROP, and SBD lack sufficient outcome support.
There are 478 airport/direction/horizon comparisons in each evaluation period:
97 airports at 6 and 12 hours and 45 at 24 hours, for both departures and arrivals.
Forecast availability and supported local hours still govern live coverage.
The broader 933-airport catalog receives weather and operational context, not
probabilities transferred from other airports.

Each airport's fixed regularized logistic models were fitted using its own BTS
reporting-carrier domestic outcomes. Calendar, weather, and weather + FAA variants
use identical eligible rows. The added inputs count airport-specific ground-stop
and ground-delay-program messages over the preceding 6/24 hours, cancellation
messages over 24 hours, and recent-advisory decay. Revisions count as activity;
these are not counts of simultaneously active restrictions. Carrier-specific
advisories do not necessarily affect every flight.

903 previously cached national daily listings passed validation; 30 dates remain
missing or ambiguous. No additional historical downloads or paid API were needed.
Historical and live scoring share the same feature extractor. Only messages
published before the preceding hourly collection at :35, less a 10-minute
publication allowance, enter a prediction. A 70-minute sensitivity case tests
slower delivery. Missing archive dates remain unknown, never zero activity.

Training used September 4, 2023–June 27, 2024; probability calibration used
July 4–December 27, 2024; outcome-rate band calibration used January 4–September
27, 2025. Winter evaluation covers January 3–February 26, 2026, and spring covers
March 4–June 27, 2026. Both periods were previously inspected: this is a
retrospective expansion following the pilot, not a new confirmatory holdout.
No model tuning followed the national results.

## Results and release decision

These are equal-weight means across the 478 airport/direction/horizon slices.
Lower Brier error and log loss are better; neither is a classification accuracy
percentage.

| Period / metric | Currently served weather | Matched local weather | Operations |
|---|---:|---:|---:|
| Winter Brier error | 0.16790781 | 0.16775849 | 0.16746066 |
| Spring Brier error | 0.17313192 | 0.17458027 | 0.17421248 |
| Winter log loss | 0.51712222 | 0.51695792 | 0.51587732 |
| Spring log loss | 0.52550320 | 0.52923851 | 0.52844464 |

Against matched local weather, FAA improves average Brier error by 0.18% in
winter and 0.21% in spring. Against the actual incumbent, winter improves but
spring regresses; averaging the two period means gives approximately **0.19%
worse Brier error**. These comparisons answer different questions: the matched
ablation isolates the added inputs, while the incumbent comparison determines
whether replacing the current product helps.

The release rule requires lower mean Brier error and log loss against both
comparators in both periods. The incumbent check was added after seeing the
ablation results but before scoring the incumbent; this timing is recorded in
the release specification. Operations did not qualify as the default. Airport
results include regressions rather than selecting only winners.

Paired uncertainty uses 1,000 three-day calendar-block bootstrap draws, with BH
adjustment across all 478 comparisons separately in each period. Winter has 161
positive comparisons, five positive after adjustment, and one meeting the full
moderate-evidence criteria. Spring has 158 positive comparisons, 27 after
adjustment, and seven meeting those criteria. The criteria also consider sample
support, calibration, and interval coverage. National flight-weighted summaries
use shared calendar blocks across airports; their intervals are descriptive and
not multiplicity-adjusted. Horizon cohorts differ, so differences between
horizons are not themselves a paired horizon-improvement experiment.

Operations' nominal 80% outcome-rate bands cover only 75.49% of winter windows
and 78.30% of spring windows on average. Average calibration gaps are 4.43 and
3.90 percentage points. The UI exposes these limitations alongside Brier error,
log loss, calibration, band width, and local samples.

### Evidence correction before release

186 slices have no FAA activity in training. The added features cannot learn a
local FAA effect there. Independent optimization of otherwise equivalent models
produced tiny numerical differences that the bootstrap could misleadingly label
significant. Before serving, their interpreted skill and interval were set to
zero and p-values to one; BH adjustment was then recomputed for every slice.
Raw numerical comparisons are retained in the full report. Predictions, raw
Brier/log-loss values, and model weights were not changed. These airports remain
explicitly labeled as having no learned FAA effect, not evidence of improvement.

## Hourly serving and cost controls

The existing hourly worker collects the current national FAA listing and
finalizes the previous UTC day once per day. A normal run makes four external
requests: two weather feeds, current FAA status, and FAA history. Finalizing a
day adds one; monthly runway refresh can add one more. Each run is capped at
six provider requests. The local collector's monthly request ceiling is 3,100;
AWS separately limits persistent collection reservations to 744 per month.

The initial end-to-end local runtime check took 5.2 seconds, produced operations
probabilities at 94 airports, and used 13.9 MB of public files plus a 0.45 MB
compressed archive. Live coverage changes with source freshness and horizon.
It fits the existing 120-second/1-GB collector, 16-MiB publication, and 2-MiB
compressed archive limits. No extra scheduled worker or paid data service was
added. The single image build is limited to ten minutes and its temporary
infrastructure is removed afterward.

Deployment verification on September 13, 2026 at 02:28 UTC confirmed 94 airports
with live operations probabilities. The real AWS invocation took 9.576 seconds
and used 279 MB of its 1,024 MB allocation. CloudFront returned the matching risk,
evaluation, and release files; unlisted model-weight paths returned 404. The
temporary builder reached `DELETE_COMPLETE`. The deployed template and
parameters were verified to differ only in the reviewed image and public path
allowlist; budget, compute, control state, and lease were preserved.

The $20 user ceiling, $8 reported-spend early stop, active AWS Free-plan check,
operating lease, and invocation limits remain unchanged. Budget notifications
can lag; they are not an absolute billing cap on a paid account. The runtime
continues to reject paid plans and cannot upgrade the account. See
[the AWS runbook](airport-weather-aws.md) for the existing protections.

FAA history must be complete, fresh, and compatible with the fitted features.
If unavailable, the operations probability is withheld; the interface offers
weather separately. The model weights are fixed at this national fit. Inputs
refresh hourly and are archived for future evaluation; the existing monthly
weather challenger does not automatically retrain or promote FAA models.

Current FAA notices and runway inventory remain additional context. This model
does not yet measure complete congestion, runway capacity, aircraft rotations,
or private-jet outcomes. Private-jet users receive airport context, with no claim
that scheduled-airline probabilities have been validated for their aircraft.

## Reproducibility

- Frozen specifications: `research/airport-operations-us-v1.json` and
  `research/airport-operations-us-v1-release.json`.
- Fit: `tools/airport_operations_us.py`; validate and export:
  `tools/airport_operations_us_report.py`.
- Shared FAA features: `tools/airport_faa_history.py`; live collection and scoring:
  `tools/airport_faa_collect.py` and `tools/airport_operations_score.py`.
- Public summary: `public/data/airport-weather/experiments/operations-us-v1.json`;
  full report: `operations-us-v1-full.json.gz` in the same directory.
- Local inputs, fitted candidates, checksums, and deployment receipts:
  `.airport-data/operations-us-v1/`.

All 2,868 saved variant scores were reproduced to a tolerance of 1e-12. The
incumbent was separately scored on the same 956 evaluation slices. The complete
national fit took about 327 seconds locally using two CPU threads, with no AWS
training job and no paid historical API.

Primary source: [FAA ATCSCC advisory database](https://www.fly.faa.gov/adv/advAdvisoryForm).
