# Airport operations outlook — proposed next model

September 12, 2026. Product proposal with an authorized local six-airport research
pilot. The frozen experiment specification is
[airport-operations-pilot-v1.json](../research/airport-operations-pilot-v1.json).
The pilot does not change live predictions, scheduled jobs, subscriptions, or AWS
settings. Product changes below remain proposed.

## Product and intended user

The private view is for a **single-owner private jet already at the departure
airport**, expecting to depart within the next 24 hours. Fleet assignment,
positioning flights, and advance itinerary planning are outside the default
scenario. The question is: **What could hold up this departure or disrupt the
arrival, given the conditions and restrictions we know now?**

The owner supplies origin, destination, intended departure, and expected arrival.
The default assumes the aircraft is positioned at origin. This does not assume
that an IFR flight plan has been filed or a departure clearance obtained.
Propose “Private jet outlook” as the tab name, with IFR operations explicit.
Prioritize +1, +3, and +6 hours, retaining +12 and +24 as early warning. These
new horizons need their own validation; the current +6 model cannot simply be
relabeled as a +1 model. Shared data updates remain hourly.

Ceiling/visibility categories remain a secondary weather layer. They describe
weather, not the aircraft's capability or probability of being delayed.
[NOAA category definitions](https://aviationweather.gov/gfa/help/).
An IFR-capable jet is still exposed to airport flow restrictions. FAA programs
can hold aircraft at their origin to meter arrivals at the destination; scope,
exemptions, and revisions matter.
[FAA ground-delay procedures](https://www.faa.gov/air_traffic/publications/atpubs/foa_html/chap18_section_10.html).

## What the predictions would mean

| Output | Target and evidence |
| --- | --- |
| Airline departure/arrival disruption | Retain scheduled reporting-carrier outcomes, including delay, cancellation, and arrival diversion. Test whether operations inputs improve these probabilities. |
| Private jet airport outlook | Show current restrictions, forecast conditions, and locally validated probabilities of clearly defined airport events where possible. Do not label an airline delay percentage as the owner's chance of delay. |
| Private jet actual delay/diversion probability | Requires representative private-flight intended departure/arrival times captured before the cutoff, actual movements, changes, cancellations, and diversion outcomes. This dataset is not currently available in the project. |

The BTS reporting population is scheduled domestic airline operations; its
on-time rules exclude nonscheduled and charter flights. Changing predictors
cannot change that target population.
[BTS reporting scope](https://www.bts.gov/explore-topics-and-geography/modes/aviation/number-40-technical-directive-reporting-time).

A feasible separate research target is whether a **new FAA airport ground stop
or ground-delay program is reported during the selected airport window**.
Predict continuation of an already-active program separately and compare against
a persistence baseline. Standing access restrictions, such as prior-permission
requirements, remain explicit conditions rather than repeated new disruption
events. A reported-event probability is not a flight-delay probability. Eligibility
depends on an audit of reporting coverage; missing feed intervals are not negatives.

Do not generate a private-jet cancellation rate from missing aircraft tracks:
the absence of a flight does not identify a cancelled previously intended trip.
Private schedule changes also need a definition of delay anchored to the plan
known at the prediction time, rather than a plan revised after a disruption.

## Candidate inputs and constraints

1. **FAA state available at the cutoff.** Program type, issue/availability time,
   age, announced future start/end, reported average/maximum delay, reason,
   scope, exemptions, and recent amendments. Apply departure and destination
   information at their respective event times. A destination restriction must
   not automatically be treated as applying to every flight departing origin.
   Announced end times are expectations, not confirmed future clearance.
2. **Runway geometry interacting with forecast weather.** Compute wind and gust
   components relative to documented runway orientations, and summarize the
   range of alignment across available inventory. Keep true/magnetic direction
   conventions consistent and variable/missing winds unknown. Count and length
   alone are constant in an airport-local model and cannot explain changing
   disruption risk. Geometry-by-weather interactions can vary with time.
3. **Capacity-related context only where established.** Instrument approach
   availability, documented operational runway configuration, and dated capacity
   benchmarks are later candidates requiring source/coverage audits. Current
   inventory is not live runway configuration or a measured arrival rate. Do not
   treat all listed runways as simultaneously usable or turn a generic jet size
   into certified runway, wind, or approach limits.
4. **Lagged IFR/business-jet volume.** Audit FAA TFMSC as a better-matched demand
   proxy for the private view. It groups traffic by business-jet equipment and
   user class, but these are not a clean single-owner population. Its monthly
   history is delayed and some IFR movements are missing. Use released historical
   profiles, not realized future counts. The earlier BTS traffic-proxy experiment
   failed to demonstrate a general benefit, so volume must earn its inclusion.
   [TFMSC definitions and limitations](https://aspmhelp.faa.gov/index/TFMSC.html).

The resulting project is an **airport operations disruption model**, with weather
as one input family. It still does not observe every operational cause, such as
crew availability, maintenance, or flight-specific clearance. No single numeric
“readiness” or safety score is proposed.

## Historical data must precede model fitting

- Audit archived [FAA advisories](https://www.fly.faa.gov/adv/advAdvisoryForm)
  for originals, amendments, cancellations, applicability, and timestamps. The
  current XML summary omits information needed for detailed program scope. Its
  content hashes are not stable program identifiers: a changed average delay
  must not be counted as a newly started program.
- Obtain runway metadata versions available in the historical period, or
  explicitly verify stable geometry. Never apply today's closed flag or newly
  opened runway retroactively. Preserve source version and identifier history.
- For prospective records, retain actual download/first-seen timestamps. For
  historical records without delivery timestamps, publish a conservative latency
  assumption and replay the hourly collection cadence. Audit short events that
  could begin and end between snapshots; our hourly archive cannot establish
  their absence. Feed outages and unmapped airport identifiers remain unknown.
- At T−24/12/6, use only information available by that cutoff. A ground stop
  announced two hours before departure cannot enter a T−6 or T−24 prediction.
  FAA reported delay statistics are permissible only when already available;
  statistics published after the target window are outcomes, not inputs.
- Operations are interventions as well as signals: a ground stop can indicate
  pressure while reducing later airborne congestion. Predictive improvement
  does not prove a causal effect of weather or the restriction.

## Scientific experiment and release gates

Start with **DFW, DAL, ORD, SFO, MIA, and JFK**, all present in the modeled catalog.
Audit **TEB, VNY, HPN, and APA** separately for the private-jet use case; they are
already selectable but do not inherit the major-airport airline evidence.
Expand testing to the remaining major airports after the data pipeline passes.

Compare, on identical eligible airport/time windows and using the same learner:
calendar baseline; calendar + weather; weather + FAA; weather + runway
interactions; and weather + both. Benchmark the existing deployed version too.
Test TFMSC volume separately so its effect is identifiable. Keep airport-local
fits, or require an explicit locally validated alternative; no blind transfer
to airports without their own outcome evidence.

Before fitting, freeze features, eligible populations, splits, thresholds, and
the promotion rule. Separate training, probability calibration, uncertainty
calibration, and final evaluation chronologically. Select a genuinely unused
final period after auditing availability. Existing inspected winter/spring tests
are retrospective development evidence, not newly unseen validation. Add a
prospective shadow period and score it when matching outcomes are released.

Report Brier score and log loss, calibration curves/gaps, error in the airport
disruption share, and interval coverage/width. For rare FAA events, also report
precision-recall performance, false-alert rate, event recall, and useful warning
time, splitting new-onset from continuing events. Include no-event, persistence,
calendar, and weather baselines as appropriate. Resample days/storm episodes,
adjust for multiple airport/horizon comparisons, and publish missing-data rates.
Do not promote based on aggregate “accuracy” or an AUC alone.

Each airport/horizon must meet the frozen practical-improvement and calibration
criteria. Keep the existing model or show insufficient evidence where the
candidate fails. Comparing both endpoints does not justify multiplying their
probabilities into a trip risk: dependence requires route-level validation.

## Owner-facing presentation

Lead with separate departure and destination outlooks, the selected times, when
information was last checked, and the dominant reported or forecast factors.
Distinguish a restriction already reported now from a model forecast of a future
event. Prioritize flow restrictions, thunderstorms, wind, and low-visibility
implications; keep runway details expandable. Present the population and evidence
beside any probability. “Insufficient evidence” remains a valid result.

The map can switch among reported restrictions, forecast weather, and validated
modeled outcomes. Never relabel the existing VFR/IFR colors as operational risk.
Keep the intended airports fixed unless the owner changes them; this is a
near-term execution outlook, not an itinerary planner or fleet optimizer.

## Sequence and budget

1. Correct private-jet positioning and define the private target and +1/+3-hour
   evaluation windows. These are proposed UI changes, not made in this plan.
2. Run a bounded local archive/coverage audit and produce an as-of feature sample.
   Decide whether FAA history supports retrospective testing or requires more
   prospective collection before any claimed gain.
3. Freeze and run the six-airport experiment locally. Measure runtime, memory,
   data volume, and accuracy; expand the evaluation only after it passes.
4. Shadow qualifying models, then promote validated airport/horizon combinations
   through the existing reviewed deployment process. Keep prior artifacts.

Reuse the hourly collector, static CDN, and existing provider feeds. Last measured
collection was 9.8 seconds / 248 MB, with a 1,024 MB / 120-second allocation.
This is headroom evidence, not a benchmark for an unbuilt model. No new paid API
is assumed. Keep the $20 monthly maximum, $8 early stop, free-account checks,
744 hourly-run ceiling, one capped monthly training run, storage limits, and
no automatic promotion. Local experiments avoid an unbounded cloud sweep.
Benchmark a full 100-airport retrain before assigning it to the monthly job;
if it exceeds the existing runtime, narrow the candidate workload rather than
silently raising limits. Historical outcome access, particularly for single-owner
jets, is the main unresolved feasibility question.
