# Airport operations data: free sources and a completed traffic test

Update: FAA history has now been evaluated across all 100 major airports and
added as an optional operations predictor at 97 supported airports. Weather
remains the default. See [the nationwide evaluation](airport-operations-us-v1.md)
for the actual incumbent comparison, coverage, confidence, and hourly serving.
The context implementation described below preceded that model expansion.

Research checked September 12, 2026. The existing $20/month operating constraint
remains in place. The initial traffic experiment used local computation. The
FAA and runway context implementation below extends the existing AWS collector;
it does not add a scheduled job, paid data subscription, or production predictor.

## What we can obtain

| Factor | Source and data fee | What it adds | Main limitation |
| --- | --- | --- | --- |
| Typical arrival/departure demand | Existing BTS aggregates, $0 | Airport-local traffic profiles by weekday and two-hour period, including cancelled scheduled flights | Historical reporting-carrier domestic schedules; not current demand or a live queue |
| Ground stops, delay programs, airport restrictions | [FAA airport-status XML](https://www.fly.faa.gov/fly/FAQ/faq), public access, $0 | Current reported event type, airport, reason, start/end or reopening, reported delay fields where supplied | Airport-level events; no individual-flight probabilities and no guarantee that every local restriction is represented |
| Historical ATC interventions | [ATCSCC advisory database](https://www.fly.faa.gov/adv/advAdvisoryForm), public access, $0 | Dated ground-stop, ground-delay, route, and flow advisories | Needs archive coverage audit, issue/amendment/cancellation parsing, and as-of reconstruction before modeling |
| Runway geometry and characteristics | [OurAirports public-domain downloads](https://ourairports.com/data/), $0; [FAA NASR](https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/) for official reference | Runway count, length, headings, surface, lighted/closed flags; useful for weather/runway interactions | Static geometry is not current runway configuration, temporary closure status, or throughput capacity |
| Capacity benchmarks | [FAA airport capacity profiles](https://www.faa.gov/airports/planning_capacity/profiles), public PDFs, $0 | Modeled/called throughput under specified runway and weather configurations | Limited airport coverage and old revisions, mostly 2014–2019; not today's live AAR/ADR |
| Broader historical traffic mix | [FAA TFMSC](https://aspmhelp.faa.gov/index/TFMSC.html), public reports, $0 | Hourly traffic, aircraft/user categories, IFR general aviation, freight, and commercial activity | Most VFR and some non-enroute IFR traffic are missing; public monthly data arrive about a month later |
| Total operations context | [FAA OPSNET](https://www.aspm.faa.gov/aspmhelp/index/Operations_Network_%28OPSNET%29.html), public finalized reports, $0 | Broader airport operations and ATC delay history | Public data are delayed until the 20th of the following month; raw daily totals do not independently measure hourly arrival/departure demand |
| Aircraft rotations and taxi congestion history | [BTS flight-level fields](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ), public downloads, $0 | Tail numbers, scheduled/actual times, taxi times, and late-aircraft delay fields enable retrospective connection and propagation analysis | Our retained aggregates omit these fields. Final flown tail assignments and later arrivals cannot be presented as known at T−24/12/6 |
| More detailed live operations | [FAA SWIM/SWIFT](https://www.faa.gov/air_traffic/technology/swim/products/get_connected) | Potential flight/flow and terminal messages beyond the public status summary | Access onboarding, Service Access Agreement, stream processing, service-specific coverage; CDM elements are limited and not all services are on the self-service portal |

FAA states there is currently no charge for SWIM data, while consumers pay their
own interface costs. This makes a filtered feasibility trial worth considering,
but does not establish that a complete national streaming service fits our
runtime budget. Public access also does not establish complete advance airline
tail assignments. [FAA SWIM questions and answers](https://www.faa.gov/air_traffic/technology/swim/questions_answers),
[SWIFT access requirements](https://support.swim.faa.gov/hc/en-us).

OpenSky can offer aircraft observations, but its free REST service does not
provide commercial schedules, delay/cancellation status, or a complete live
flight database. Historical institutional access is not generally available
free to individual portfolio projects. It therefore does not close the advance
rotation gap by itself. [OpenSky FAQ](https://opensky-network.org/about/faq).

## Access and coverage verified locally

- The FAA endpoint linked by its developer FAQ returned a valid 1,943-byte XML
  response without authentication on September 12 at 18:02:41 UTC. Its own update
  time was 18:02:01 UTC. The sample included ground-delay and airport-closure
  groups. This verifies access, not service completeness or a refresh guarantee.
- The 3,964,061-byte OurAirports runway file directly matched 927 of the 933
  listed airports, including 99 of 100 major airports. The remaining major
  airport uses the documented KDJT/KPBI rename: matching its old code and runway
  endpoint coordinates brings major-airport coverage to 100/100. There are
  2,001 directly matched runway records before applying that alias.
- Receipts and hashes are saved under `.airport-data/operations-research/`.
- FAA's current NASR page notes format changes beginning with the September 3,
  2026 cycle. Any NASR parser should use the current dictionary and validate
  schema changes rather than silently accepting an old layout.

## Implementation sequence

1. Add FAA status as a clearly timestamped **reported operational context**
   layer, initially independent of probability estimates. Archive each fetched
   snapshot with an availability timestamp. One national hourly fetch is at
   most 744 requests in a 31-day month, rather than one request per airport.
2. Add versioned runway metadata and test weather/runway interactions. Preserve
   source dates and aliases. Do not infer active runways solely from wind or
   label runway count as measured capacity.
3. Audit historical FAA advisories and TFMSC coverage. Backtest restriction and
   broader demand features using the information available at each cutoff.
   An intervention can both indicate a problem and reduce its downstream
   consequences; its association is not a simple causal effect.
4. Re-download a bounded BTS pilot sample with tail numbers and taxi fields for
   retrospective network/turnaround analysis. Build only lagged historical
   propagation features until advance flight/aircraft assignments are available.
5. Evaluate a tightly filtered SWIM feed if the simpler sources demonstrate a
   material gap. Data are free, but onboarding and processing remain separate
   feasibility questions. No account creation or access agreement was submitted.

The context portions of steps 1 and 2 are implemented. Testing runway/weather
interactions and historical restriction features remains future modeling work.

## FAA and runway context implementation

`tools/airport_operations.py` parses the FAA's documented airport-status XML
and OurAirports runway inventory. `airport_weather.py` collects them alongside
weather. Both airline and private airport panels show context automatically;
the private view shows it separately for departure and destination.

- FAA: one national fetch per collector run, with feed-update, download, and
  event-first-seen timestamps. Ground stops, ground-delay programs, closure/access
  restrictions, and arrival/departure delay reports preserve their original
  reasons, exceptions, directions, and supplied time/delay fields. No year is
  invented for FAA time strings that omit it. Regional airspace/CTOP programs
  are counted as unassigned context; they are not mapped blindly to airports.
- Runways: the first attempted download in a calendar month is retained in the
  successfully published durable snapshot. Later runs reuse that inventory and
  its original download time, including after a failed refresh. A failed overall
  publication can repeat the monthly attempt; hourly quotas still bound it.
  Runway ends count as one physical record. Known closed runways do not enter
  the listed-open count or longest-listed-open metric. Missing flags/dimensions
  stay unknown. The KDJT/KPBI rename requires agreeing coordinates.
- The real September 12 collection matched **929/933 airports** to runway
  records, including **100/100 major airports**; 2,004 records were retained.
  Matching is not an accuracy audit of the inventory. The data vendor provides
  neither an effective date for every row nor a guarantee of current capacity.
- FAA status becomes stale after 90 minutes from either feed time or download,
  or immediately after a failed/deferred refresh. Old notices remain labeled
  historical; absence of notices never implies normal operations. Runway data
  display their date, monthly cadence, and a failed/overdue indicator after
  45 days. Current notices are not forecasts for the selected +6/+12/+24h time.
- Context fields are stored inside the existing station-prefix files and
  compressed hourly archives. There are no new public compute endpoints or
  per-airport provider calls. Archives retain availability evidence for future
  prospective tests. No historical FAA feature reconstruction is claimed yet.
- Local verification took 3.24 seconds for the complete four-source collection
  plus a second scoring pass. The compressed archive was 340,038 bytes, below
  the unchanged 2 MiB cap. Removing all context fields produced **identical
  prediction bytes**. Model and evaluation hashes remain unchanged.

The collector retains its 1,024 MB / 120-second limit and 744-run monthly cap.
Ordinary collection makes three free-provider requests; the monthly inventory
run makes at most four. FAA downloads are capped at 1 MiB and runways at 8 MiB,
with 12-second socket timeouts and no retries or redirects. Context collection
is deferred when less than 30 seconds remain for processing/publication. Local
collection has a 2,300-request monthly ceiling. Snapshot/archive/storage limits,
early budget stop, Free-account-plan checks, and the operating lease remain in
place. No paid provider fallback was introduced.

Deployment and verification receipts are saved under
`.airport-data/aws-package/operations-*.json`. The temporary image build allows
one run with a ten-minute cap; its resources are removed after completion.

Live verification passed at **2026-09-12T19:00:38Z**. All four source statuses
were `ok`; FAA's feed time was 19:00:06Z, downloaded at 19:00:40Z. Cloud runway
coverage matched the local audit. The deployment retained all non-image stack
parameters, the existing operating control item, and the exact model/evaluation
bytes. The browser loaded this generation from CloudFront and displayed Miami's
reported ground-delay program and runway inventory. The manual verification
used the normal 19:00 UTC quota slot; the scheduled 19:35 invocation cannot
collect again in that hour, so ordinary scheduled collection resumes at 20:35.

## Completed historical traffic experiment

The protocol was fixed before fitting in `research/airport-traffic-proxy-v1.json`.
All 100 major airports were assessed independently; 97 supported testing and
478 airport/direction/horizon comparisons were evaluated in each period. The
entire run took 266.76 seconds locally and used no new source downloads.

The profile averages arrivals and departures by local weekday and two-hour
block from up to 12 historical source months. It freezes the available profile
at the beginning of each target month after a conservative 120-day publication
lag. Zero-traffic blocks count toward exposure; missing source months do not.
Actual counts in the predicted window never become predictors. A release-lag
assumption is not a reconstruction of original BTS release vintages.

Three fixed airport-local logistic variants compare calendar alone, calendar
plus weather, and calendar plus weather plus traffic. Traffic includes expected
arrival/departure demand, demand relative to its historical 95th-percentile
profile, adjacent-period demand, and interactions with storms, low ceilings,
and gusts. Historical peak demand is not runway capacity.

All variants use identical rows within each comparison. Training is September
2023–June 2024, probability calibration July–December 2024, and interval
calibration January–September 2025. Winter and spring 2026 are retrospective
evaluations already touched by prior research. Original production models,
training dates, and pooled comparators differ, so these are controlled
experimental comparisons rather than a production before/after.

| Mean across 478 comparisons | Weather | Weather + traffic |
| --- | ---: | ---: |
| Winter Brier error ↓ | 0.166599 | 0.166751 |
| Spring Brier error ↓ | 0.175234 | 0.175140 |
| Winter calibration error ↓ | 4.362 pp | 4.524 pp |
| Spring calibration error ↓ | 3.915 pp | 3.995 pp |
| Winter interval coverage, 80% target | 75.90% | 75.49% |
| Spring interval coverage, 80% target | 78.23% | 78.01% |

Winter Brier error improves in 250/478 comparisons, and spring in 266/478.
After approximate multiple-comparison correction, 38 winter and 114 spring
comparisons retain positive evidence. Those local results do not establish a
national benefit. All six winter flight-weighted direction/horizon confidence
intervals cross zero. Five spring intervals cross zero; the remaining one
indicates worse arrival predictions at T−24. Aggregate intervals share sampled
three-day calendar blocks across airports.

At DFW, winter departure improvements are small and inconclusive. Spring
arrival Brier error worsens about 2.1–2.3% relatively across horizons. The result
does not justify promoting this traffic feature set. It also does not show that
actual congestion is irrelevant: this proxy is historical, coarse, and partly
redundant with calendar features, and omits non-reporting traffic.

Decision: keep the current live model. The website includes the experiment and
downloadable per-airport results and full report. This is evidence from a test
that could fail, not a reason to keep adding predictors without validation.
