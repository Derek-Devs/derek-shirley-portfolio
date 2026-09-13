# Airport weather and disruption

Local portfolio on `codex/portfolio-leadership-content`, connected to the existing AWS weather service. Airport and weather scope is the United States and U.S. territories.

**AWS operation:** [account setup, cost controls, hourly updates, and monthly candidate learning](airport-weather-aws.md). The shared service is active under the protected AWS Free account plan; see the runbook for the operating lease and cost controls.

**Current model: v3, assessing all 100 major U.S. airports, with tested models for 97.** See [the v3 experiment and runbook](airport-weather-v3.md) for current reproduction, evaluation periods, and coverage. This document retains the original nine-airport experiment for historical context; its collector, budget, and replay instructions still apply. Running the original `airport_train.py` command reproduces v1 and replaces the current model, so use the v3 workflow for current work.

## What works

- `/work/airport-weather`: U.S. airport search, current observations, forecast groups for a selected UTC time, departures/arrivals, and an origin/destination private aviation view.
- A stdlib Python collector downloads NOAA METAR and TAF bulk files hourly while running. It publishes small station-prefix JSON files for the static Astro site. The browser never calls NOAA or any paid API.
- A descriptive May 2025 DFW replay joins scheduled flight outcomes to the archived forecast issues available at approximate T−24, T−12, and T−6 cutoffs. Original bulletins establish forecast validity boundaries omitted from parsed archive rows.
- Airport selection, direction, and horizon changes populate results automatically. A self-hosted Leaflet/Natural Earth map supports contiguous U.S., Alaska, Hawaii, and territory views, panning, zooming, and selecting airports. Colors represent airport probabilities, not interpolated weather or risk between airports. Gray indicates no estimate. Dashed rings indicate limited evidence for weather or interval undercoverage.
- Fixed logistic models for DFW, ORD, ATL, DEN, SEA, LAX, JFK, SFO, and MIA estimate cancellation, delay, and (arrivals only) diversion shares. Portable scoring runs with the hourly collector, without sklearn or network calls. Private aviation and other airports keep weather context only.
- The selected airport's scorecard reports real held-out Brier skill, day-bootstrap intervals, window MAE, calibration, sample counts, component metrics, and empirical interval coverage. Unfavorable results remain visible.
- Portfolio homepage and Work collection link to the project, marked in development.

## Run locally

Use Python 3.10+ with the IANA `tzdata` package available on Windows for historical timezone conversion. Live collection uses only the standard library.

```sh
python tools/airport_weather.py catalog
python tools/airport_weather.py refresh
python tools/airport_weather.py watch
```

`watch` is a foreground local process. It does not install a login task, schedule an OS job, or run while the computer sleeps. Stop it with Ctrl+C. Run the normal Astro development server in another terminal. The supplied public snapshot remains usable when collection is stopped, with timestamps and a stale-data indication.

When `model.json` and `evaluation.json` are present, collection also writes `risk.json`. To rescore already-downloaded weather without any provider request: `python tools/airport_predict.py`. Restart a running collector after changing its Python code. The browser requires matching weather/risk generations and model/evaluation versions, and withholds stale (>90-minute) probabilities. Missing, unsupported, superseded, or incomplete TAFs never become low-risk estimates. Preset horizons use the snapshot's as-of time; custom times show weather only. Backtests use fixed local two-hour windows; live predictions use rolling two-hour windows, an explicit deployment limitation.

## Reproduce the model experiment

```sh
python -m venv .airport-data/model-env
.airport-data/model-env/Scripts/python.exe -m pip install -r research/requirements.txt
.airport-data/model-env/Scripts/python.exe tools/airport_prepare.py
.airport-data/model-env/Scripts/python.exe tools/airport_train.py
python tools/airport_predict.py
```

Use the equivalent `bin/python` venv path on Unix. The checked-in protocol was fixed before fitting. Preparation downloads 27 BTS monthly archives and 27 IEM bulk TAF ZIPs plus the airport timezone catalog. It caches derived monthly aggregates and source hashes locally, removing each raw BTS ZIP only after its derivation is durable. No historical jobs run unattended. The raw TAF ZIPs remain available for parser audits. Reruns resume completed months. Changing a feature parser or cohort definition requires explicitly rebuilding derived caches and versioning the experiment; do not mix old prepared features with new serving code.

Public artifacts: `model.json` (portable coefficients, standardization, sigmoid calibration, interval radii, feature ranges, and protocol), `evaluation.json` (all results, source URLs/hashes, exclusions, and cohort counts), `risk.json` (shared current scores). No raw flight-level records or serialized executable models are published. Scoring uses the exact same raw-US-TAF feature extractor as training.

Serving also requires at least 30 training windows in each local two-hour clock block touched by a rolling prediction window. This prevents extrapolating a daytime model to sparse overnight operations. The rule uses training support only, was added after the first backtest for serving, and does not modify the published evaluation. It is recorded separately under `servingPolicy`; gray dotted markers show low data. Forecast skill and interval coverage continue to use the unchanged frozen test cohort.

The fit uses weighted binomial logistic heads with fixed C=1, lbfgs, tolerance 1e-7, and 1,500 maximum iterations. Each aggregated airport window supplies success/failure weights rather than duplicating flights. Features are standardized on training only. Sigmoid calibrators use disjoint October data and the same fixed optimizer. Cancellation is estimated among scheduled flights, diversion among uncancelled arrivals, then delay among operated/nondiverted flights. Products of these conditional probabilities yield mutually exclusive unconditional outcomes summing to one. No class balancing or test-set hyperparameter selection occurs.

Training: January 2024–September 2025 (76,230 airport-direction windows; 4,787,862 flight events). Probability calibration: October 2025 (3,274 windows). Interval calibration: November 2025 (3,338 windows). Final test: March–June 2026 (14,328 windows; 936,948 flight events). Exact dates and gaps are in the protocol. A flight can appear once at each studied endpoint; event totals are not unique flight totals. All three horizons use the same eligible test windows.

First-run DFW departure results: 62,215 flights, 714 windows, 104 test days. Brier improvement over calendar baseline: T−24 0.6% (95% interval −1.7% to 2.6%), T−12 2.0% (−0.1% to 4.2%), T−6 2.3% (0.1% to 4.6%). T−6 window MAE is 14.3 percentage points, versus 14.7 for the baseline. The target-80% interval covers only 61.3% of test windows; cancellation averages 1.3% predicted versus 3.4% observed. These are meaningful deficiencies, displayed beside live probabilities, not corrected by fitting to the final test. Results vary by airport; for example LAX does not improve on the baseline. The model remains experimental.

“Moderate evidence” is evidence for adding weather, not overall forecast reliability: the protocol requires at least 60 test days, 5,000 flights, a positive lower bound on the nominal Brier skill interval, and bin calibration error below five percentage points. Interval undercoverage is separately flagged even when weather signal is moderate. Nominal 95% intervals use 300 day-block bootstrap resamples, are not adjusted for 54 comparisons, and do not fully capture multiday storm dependence. The 80% target bands use November absolute window residuals and a finite-sample conformal quantile; temporal dependence and distribution shift mean coverage is empirical, not guaranteed.

The collector reserves an hourly attempt before network I/O and allows only one attempt per UTC hour. Restarting it does not cause more requests in that hour. If a crashed process leaves `.airport-data/collector.lock`, inspect its PID and only remove that exact lock once the process is confirmed stopped. Corrupt state fails closed. A failed source retains its last successful download time and sets an error flag.

To reproduce the historical sample:

```sh
python tools/airport_history.py --year 2025 --month 5
```

The first run downloads one approximately 31 MB BTS ZIP, a parsed IEM TAF month, and at most 500 small original bulletins (335 in this sample). Subsequent runs use local cached inputs. The archive has separate download-size limits and three bounded workers, with no automatic retries. A different month replaces the public replay artifact; update the fixed month/date controls and copy before publishing a different sample.

## Budget safeguards

- There are no paid providers, API credentials, LLM calls, paid fallbacks, purchase paths, or automatic upgrades in the implementation. External data subscription spend is therefore $0 in this version.
- Live network requests are limited to a fixed allowlist of free public files. Redirects are refused. Maximum 1,600 requests per UTC calendar month, reserved before I/O, with a cross-process lock. Normal hourly collection is at most 1,488 weather requests in a 31-day month.
- Maximum 16 MiB downloaded per live source and 32 MiB expanded XML; no XML DTD/entity declarations. The local weather archive keeps at most 14 days and 128 MiB, whichever is reached first. Catalog and latest state are additional small files.
- Research downloads are explicit local commands, outside the live collector quota. The model preparation fixes 27 months (refuses more than 30), caps each BTS archive at 96 MiB compressed / 768 MiB expanded, and each bulk TAF archive at 16 MiB compressed / 32 MiB expanded / fewer than 9,999 products. The separate replay caps individual bulletins at 128 KiB and 500 bulletins per run. There is no unattended historical backfill.
- Browser traffic reads static shared files. A typical DFW weather bucket is around 74 KB uncompressed, versus roughly 5 MB for all airports. The airport catalog is approximately 0.8 MB, self-hosted geography is 260 KB, and the replay is loaded on request. Map interactions have no tile-provider charges. Model weights are downloaded only on explicit request; the browser reads scores and evaluation summaries.
- These are application limits, not a guarantee about the existing hosting bill. No hosted hourly collector is configured. Before deployment, measure compute/storage/egress, determine the existing hosting plan's included allowance, and choose a scheduler/storage plan with a provider-enforced hard limit. Any future paid dependency must fit within the user's $20/month cap including tax and have no overage path. Alerts alone are not a hard cap.
- Do not run a full site build on every visitor request or forecast refresh. A hosted deployment will need an explicit path for updating the static snapshots; a normal static deploy alone will not update hourly.

## Data and scientific boundaries

Current catalog selection: OurAirports large and medium airports with four-character identifiers; it includes airports useful for private aviation and is not a passenger-volume ranking. Weather availability is measured per snapshot. Nine airports have an experimental, retrospectively backtested outcome model. Global and private-flight probabilities are unsupported. The UI never manufactures probabilities from weather rules.

Live source times distinguish observation time, forecast issue time, first local retrieval, and dataset download. Forecasts may describe a future validity interval. Forecast selection uses issue and retrieval times and checks validity. Conditional groups remain separate; blank values are never converted to zero wind or clear weather. The live +6/+12/+24 panels show forecast **valid times from now**, not historical model evaluation snapshots.

Replay outcome categories are mutually exclusive: cancelled first; for arrivals, diverted next; then delayed ≥15 minutes, less than 15 minutes late (including early), or outcome missing. Denominators include all represented scheduled flights. Severe delay ≥60 minutes or cancellation is an additional overlapping measure, not another component of the outcome distribution. Missing arrival delay on a diversion is not dropped as an unknown delay.

Replay windows span two hours in DFW local time. Cutoffs are relative to the start of an airport arrival/departure window. This differs from predicting an individual arriving flight before its origin departure. The source FlightDate is the departure date: arrivals are placed using scheduled elapsed time, origin timezone, and the DFW arrival clock. Ambiguous/nonexistent DST times and unresolved timezones fail the join and are counted, not silently guessed. Adjacent source months are needed to complete arrival coverage at month boundaries. Retain this limitation until those boundary inputs are included.

IEM's initial TAF group is named `Observation` in the CSV, but it is part of a forecast, not an observed METAR. The importer labels it Prevailing and gets the real validity start/end from the original bulletin. Missing prevailing end times are bounded by the next prevailing group or bulletin validity end. Conditional groups must have explicit endpoints. Historical issue time +10 minutes is a documented availability proxy, not verified delivery time. Partial target-window coverage is labeled. Source URLs and content hashes are stored in the public replay metadata; the original input files remain private in `.airport-data`.

BTS reporting-carrier domestic records do not cover all international operations, global airports, or private flights. Final cancellation records do not say when cancellations were announced. All displayed replay rates are descriptive; no weather causality or prediction accuracy is inferred.

## Next experiments (not implemented)

1. Investigate seasonal calibration drift and cancellation underprediction using new development data, reserving a fresh final test. Add rolling-origin development folds and more representative interval calibration; do not optimize against the published final holdout.
2. Prospectively archive predictions and forecast arrival times, evaluate additional seasons, and use multiday storm blocks for sensitivity. The existing 14-day live weather archive is not a permanent prediction registry.
3. Separately ablate forecast revisions, earlier observed forecast errors, upstream weather, capacity, and airline/network effects. More data must improve a held-out metric to earn its cost. No causal attribution from coefficient magnitude alone.
4. Add airports only after obtaining comparable outcomes and geographic holdout evidence. A worldwide airport map does not establish global model accuracy.

## Checks

```sh
python -m unittest discover -s tests -p "test_*.py"
node --test tests/airport-weather.test.mjs
npm run check
npm run build
```

Use the model venv for the full Python suite (portable-serving parity also imports numpy/sklearn). Node 22.18+ supports the test runner's direct TypeScript imports. Tests cover time leakage, forecast validity, conditional weather, feature order/local time, missing data, probability conservation, serving/training math parity, common horizon denominators, chronological split order, output escaping, quotas, locks, DST/midnight conversion, and replay reconciliation. UI checks include automatic search, map selection, horizons, private mode, unsupported airports, responsive layout, and theme contrast.

## Sources

- [NOAA AWC API and bulk cache documentation](https://aviationweather.gov/data/api/)
- [NOAA report semantics](https://aviationweather.gov/help/data/)
- [OurAirports public-domain data](https://ourairports.com/data/)
- [BTS source archives](https://transtats.bts.gov/PREZIP/)
- [BTS on-time reporting](https://transtats.bts.gov/ONTIME/)
- [IEM TAF archive documentation](https://mesonet.agron.iastate.edu/cgi-bin/request/taf.py?help)
- [IEM original bulletin API](https://mesonet.agron.iastate.edu/api/1/docs)
- [IEM bulk original-product retrieval](https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py?help)
- [scikit-learn probability calibration](https://scikit-learn.org/stable/modules/calibration.html)
- [Natural Earth public-domain geography](https://www.naturalearthdata.com/about/terms-of-use/)
- [Leaflet](https://leafletjs.com/reference.html)
