# Do operations inputs improve airport forecasts?

Completed September 12, 2026. **FAA advisory history is a promising input at six
hours. This pilot does not justify replacing the live model yet.** The combined
inputs improve spring probability scores, but winter evidence is weaker,
uncertainty bands are under-calibrated, and DAL does not improve consistently.
The experiment validates airline outcomes, not private-jet delay probabilities.

## What we tested

DFW, DAL, ORD, SFO, MIA, and JFK provide a small geographic and operating contrast,
including two nearby airports with different traffic patterns. They are not a
representative sample of all U.S. airports.

At each airport we fit separate arrival and departure models for T−24, T−12,
and T−6. Six variants share the same eligible rows, learner, time splits, and
calibration procedure:

1. Local calendar patterns.
2. Calendar plus the existing weather features.
3. Weather plus forecast wind direction.
4. Weather, wind direction, and runway geometry interacting with forecast winds.
5. Weather plus recent FAA ground-stop/GDP advisory activity.
6. All those inputs together.

The direction-only control is essential: improvement from adding a runway/wind
feature could simply reflect previously omitted wind direction. Static runway
counts cannot vary within an airport-local model. We tested changing weather
interactions with a frozen layout, not measured runway capacity.

There are **34 tested airport/direction/horizon slices per evaluation period**,
covering six airports at 6/12 hours and five at 24 hours. DAL has only 34 eligible
24-hour windows across all five periods combined, so neither DAL 24-hour model
passes support gates. Missing forecasts remain unavailable.

## Main findings

The table shows flight-event-weighted **relative reduction in Brier error** for
the combined model versus the matched weather baseline. Higher is better. These
numbers are neither increases in percent accuracy nor changes in flight delay
probability. Brackets show paired 95% bootstrap intervals.

| Six-hour outcome | Winter: January–February 2026 | Spring: March–June 2026 |
| --- | ---: | ---: |
| Departure disruption | +2.27% [−0.06%, +5.52%] | +2.53% [+1.35%, +3.80%] |
| Arrival disruption | +3.14% [+0.20%, +7.06%] | +4.62% [+3.19%, +6.13%] |

The six-hour winter comparison contains 135,019 departure events and 135,029
arrival events; spring contains 290,261 and 290,202 respectively. These are
airport events, not distinct journeys: a flight may contribute at both endpoints.

- **FAA history carries the clearest additional signal.** At six hours, FAA
  features alone reduce aggregate Brier error by 2.34%/3.22% for winter
  departures/arrivals and 2.05%/3.74% in spring. These are signals about recent
  operating conditions, not evidence that notices caused the later disruption.
- **Runway geometry is not yet a clear general improvement beyond direction.**
  All 12 aggregate geometry-versus-direction confidence intervals cross zero.
  Some local spring comparisons improve, but wind direction accounts for much
  of the aggregate weather/runway gain. The experiment does not establish that
  runway inventory itself improves predictions everywhere.
- **The gain varies by airport.** Spring combined six-hour departure/arrival
  improvements are 5.25%/9.63% at DFW, 1.73%/3.08% at ORD, 0.96%/2.95% at SFO,
  2.63%/3.69% at MIA, and 0.72%/1.45% at JFK. DAL worsens by 0.63%/0.36%.
  These point estimates have different uncertainty; see every interval and
  adjusted comparison in the tables below.
- **Shorter-horizon FAA inputs look more useful.** The 24-hour FAA-only departure
  gain is small and uncertain in both periods. Different horizons have different
  eligible windows, so this is not a controlled estimate of the value of waiting.

[All horizons, airports, calibration metrics, and uncertainty](airport-operations-pilot-v1-tables.md).

## Confidence is the remaining problem

Across the 34 slices, the combined model's mean calibration gap falls from
6.15 to 5.50 percentage points in winter, and from 4.40 to 3.38 points in spring.
However, nominal 80% outcome-rate bands cover only **73.3%** of winter windows
and **75.4%** of spring windows. The corresponding weather baselines cover
74.7% and 74.7%. Better average probability scores do not guarantee useful
uncertainty estimates. For example, SFO's spring six-hour arrival band covers
only 60.6% of windows even though its Brier score improves.

After the approximate multiple-comparison adjustment, 17 of 34 combined-model
spring slices retain positive improvement; 10 also satisfy the prespecified
sample, calibration, and band-coverage gates. Winter has **zero** combined-model
slices passing the adjusted improvement test or the full evidence gates.

The correction covers four experimental contrasts across all 34 slices, or
136 comparisons per period. Aggregate intervals in the headline table are
descriptive and are not adjusted for multiple aggregate comparisons. Calendar
blocks are resampled together across airports to preserve some common-day
dependence. This does not remove all dependence or selection uncertainty.

Both 2026 periods were inspected in earlier experiments. The protocol was frozen
before fitting these variants, but these are **retrospective results**, not a
fresh confirmatory holdout. The final training months, independent probability
calibration, and independent band calibration are listed in the
[frozen protocol](../research/airport-operations-pilot-v1.json).

## What the extra inputs actually represent

**FAA:** We downloaded daily public advisory listings and accepted 903 of 933
requested dates. Thirty dates failed strict validation because of duplicate
advisory numbers or conflicting dates. Windows needing those dates were removed
from every variant. The exclusion is conservative and could be nonrandom.
Among weather-eligible windows, roughly 7% are excluded for FAA history coverage.
No missing day is interpreted as a quiet airport.

The features count exact-airport ground-stop/GDP messages over the previous
6/24 hours, count cancellations separately, and measure message recency. Counts
include updates to the same program. They are **advisory activity**, not unique
disruptions, active program duration, NOTAM coverage, or a restriction on every
flight. They use publication time and an assumed hourly fetch with a 10-minute
publication lag; we also score the same models with an additional hour of FAA
lag. Full sensitivity results are downloadable. The replay assumes an
hour-aligned collection phase; actual historical delivery was not observed.
[FAA advisory archive](https://www.fly.faa.gov/adv/advAdvisoryForm).

An audited DFW notice on January 24, 2026 applied only to American Airlines and
was labeled carrier-requested. That is useful evidence of airport activity for
an airline outcome experiment, but it would be wrong to show it as a universal
restriction on an owner's private jet.
[Audited FAA advisory](https://www.fly.faa.gov/adv/adv_otherdis?adv_date=01242026&advn=47).

**Runways:** We use true headings from the December 31, 2022 OurAirports commit,
before training starts: 7 paved/open-listed runways at DFW, 2 at DAL, 8 at ORD,
and 4 each at SFO, MIA, and JFK. Geometry stays fixed for the experiment. No
present-day closed flag is backfilled into historical windows. Best available
alignment in that inventory does not tell us the actual assigned runway,
temporary availability, approach configuration, aircraft limits, or airport
throughput. Variable wind has an explicit unknown-direction feature and an
upper crosswind bound rather than a calm assumption.
[Frozen runway source](https://github.com/davidmegginson/ourairports-data/blob/7930aceb52abf2a476e293d598505c41412f97f3/runways.csv).

**Weather and outcomes:** Wind direction was reconstructed from cached IEM TAF
archives, and every retained vector matched the existing as-of weather features.
The latest unavailable or unsupported TAF cannot be replaced by an older valid
one. No observed future weather, realized flight volume, or later flight outcome
enters the feature matrix. BTS labels are final-vintage scheduled airline
records; historical revisions are not replayed.

## What this means for the private-jet view

The intended user remains the owner of an IFR-capable jet already at origin.
This pilot supports investigating near-term airport operating conditions; it
does **not** validate a private jet's delay or cancellation probability. BTS
reporting excludes nonscheduled/charter flights, and an observed aircraft track
cannot tell us every trip that was planned and cancelled.
[BTS reporting population](https://www.bts.gov/explore-topics-and-geography/modes/aviation/number-40-technical-directive-reporting-time).

Private-jet notices need carrier/flight applicability, origin-versus-destination
scope, effective times, amendments, and cancellations. Until that is resolved,
the useful product is a timestamped operational outlook with source evidence
and explicit gaps. Fleet positioning and airline rotation assumptions do not
belong in the default single-owner scenario.

## Decision and next bounded experiment

Keep the production model. Five pilot airports retain their original pooled
production models and DAL retains its local model; this experiment uses local
comparators at all six and is not a direct before/after production test.

The next research priority is a separately frozen 1/3/6-hour FAA experiment,
with scoped notices and an explicit active-program/persistence baseline, while
retaining a direction-only comparator. Recalibration should be developed on
older folds and checked on future data, not tuned against these 2026 outcomes.
DAL should remain in the pilot as a difficult counterexample. A prospective
shadow period must demonstrate local gains and uncertainty quality before
promotion, and private-jet claims require a target and labels appropriate to
private operations.

The live FAA XML feed currently supplies active context; it does not supply the
same historical advisory-message counts. Matching the live and training feature
definitions, timestamp/scope parsing, missingness, and collection cadence is a
deployment prerequisite. Adding another hourly request would also need to fit
the existing request caps. No additional collector or AWS job was enabled.

## Cost, reproducibility, and verification

- **Incremental AWS/API charge: $0.** All work ran locally against free public
  sources and cached flight/weather data; existing AWS safeguards are unchanged.
- The bounded FAA pass used 933 requests, 34,093,329 bytes, and 292.61 seconds.
  Four earlier FAA source probes, one GitHub metadata probe, and a 3.82 MB runway
  download are recorded separately in the published source audit. The frozen
  budget prose said three earlier FAA probes; the audited file count is four.
- Successful feature preparation took 36.42 seconds. Fitting and evaluating
  **204 candidate models** across 34 slices took 34.69 seconds locally, with
  two configured compute threads. This is measured local wall time, not an AWS
  cost estimate or a guarantee for larger experiments.
- Nine new leakage, availability, geometry, and weighting tests passed; the
  complete airport Python suite passed 79 tests. A separate validation pass
  reproduced all **408 saved-model evaluation scores** to within `1e-12`.
- Production model and evaluation hashes match their pre-experiment values.
  The report contains protocol, code, input, and fitted-model hashes, runtime
  versions, coverage exclusions, calibration tables, and paired block losses.

Reproduce locally from the repository root, using the existing scientific Python
environment. The downloader reuses valid cached days, never retries failed dates,
and enforces persisted request/byte limits. Do not regenerate prepared inputs
after fitting an existing frozen run; its fingerprint will reject changes.

```powershell
./.airport-data/model-env/Scripts/python.exe tools/airport_operations_history.py
./.airport-data/model-env/Scripts/python.exe tools/airport_operations_pilot_features.py
./.airport-data/model-env/Scripts/python.exe tools/airport_operations_pilot.py
./.airport-data/model-env/Scripts/python.exe tools/airport_operations_pilot_report.py
```

For an already completed run, rerun only the report validator. A fresh checkout
also needs the existing v3 data preparation and the pinned runway CSV before
these commands; the source manifests identify the required files. Rerunning
preparation updates its manifest timestamp and intentionally invalidates the
frozen fit fingerprint.

Downloads: [Protocol and airport results](../public/data/airport-weather/experiments/operations-pilot-v1.json)
and [full reproducibility report](../public/data/airport-weather/experiments/operations-pilot-v1-full.json.gz).
