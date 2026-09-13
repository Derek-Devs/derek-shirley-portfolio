# Global airport modeling: cost sizing

**Scope superseded:** The user subsequently chose the United States and U.S. territories. This document preserves the earlier worldwide sizing research; see `airport-weather-aws.md` for the current U.S. scope and budget target.

Prepared September 11, 2026. USD, before tax; excludes existing portfolio hosting, development labor, and promotional credits. This is a planning estimate, not a vendor quote or authorization to spend. No subscriptions, AWS limits, or production models were changed.

**Airport-specific training is computationally affordable. Obtaining enough reliable historical outcomes for every airport is the unresolved expense.** Allow approximately **$10–$50/month for AWS** under the assumptions below, plus flight-data licensing and any weather-archive coverage gaps. A complete worldwide data contract cannot yet be priced from public information alone.

## Scope and evidence standard

The current catalog contains 5,077 airports: 1,171 classified as large and 3,906 as medium. This estimate uses all **1,171 large airports** as a broad sizing envelope. That classification is not an audited list of major passenger airports; the final scope should include major commercial airports regardless of catalog classification.

Assume 36 months of historical data, separate departure and arrival predictions at 6, 12, and 24 hours, hourly weather updates and scoring, and one monthly training/evaluation cycle. Six prediction slices per airport means 7,026 slices, with multiple outcome heads. These remain airport-level estimates for scheduled commercial flights; private-flight outcome modeling requires different labels.

The estimate allows separate models for each airport. A shared model could be an experimental comparator, but its aggregate performance would never establish accuracy at another airport. Each airport needs:

- Scheduled and actual gate times, cancellations and diversions, with missing outcomes distinguished from successful flights and duplicate codeshares removed.
- Forecasts actually issued and available at each prediction cutoff. Later observations or revised forecasts cannot replace missing historical forecasts.
- Chronological backtests across seasons; local time, traffic, and seasonality baselines; and calibration on data separate from the final evaluation period.
- Airport/horizon-specific Brier or log-loss skill, calibration, uncertainty coverage, event counts, and confidence intervals that account for correlated flights and days. Include multiple-comparison controls when selecting among many models.
- A publication gate that withholds unsupported estimates. A paid source cannot guarantee enough cancellation or severe-weather examples everywhere.

Thirty-six months is a planning target, not proof of adequate evidence. The current 32-month monthly recipe and short final holdout need broader seasonal evaluation. Forecast support must be assessed separately at each horizon, rather than discarding a valid T-6 example solely because T-24 is missing.

## Compute evidence and monthly assumptions

An offline benchmark used existing 2023–2024 DFW, JFK, and PHX records, two CPU threads, and the current boosted algorithm with probability calibration. One T-6 fit took:

| Airport | Departures | Arrivals |
|---|---:|---:|
| DFW | 0.70 seconds | 1.11 seconds |
| JFK | 0.80 seconds | 1.06 seconds |
| PHX | 0.56 seconds | 0.93 seconds |

These are desktop timings on about 2,800–3,900 training windows per fit. They exclude downloads, preparation, other horizons, comparison models, repeated backtests, interval estimation, and cloud overhead. No held-out 2026 outcomes or production weights were changed. They show inexpensive fitting, not a completed global performance test.

For sizing, allocate **30–300 seconds per airport** for a complete monthly modeling cycle at 3,008 MB, substantially more than the individual fits. This is an unmeasured workload allowance. Using the Ohio x86 Lambda rate of $0.0000166667/GB-second, `1,171 × 30–300 × (3,008/1,024) × rate` is **$1.72–$17.20/month**. Allocate another 240–600 aggregate GB-seconds per hourly collection/scoring run: 744 runs cost **$2.98–$7.44**. [AWS Lambda pricing](https://aws.amazon.com/lambda/pricing/), [Ohio rate reference](https://aws.amazon.com/about-aws/whats-new/2022/08/aws-lambda-tiered-pricing/).

| Component | Monthly planning allowance |
|---|---:|
| Training, calibration and backtesting | $1.72–$17.20 |
| Hourly collection and scoring | $2.98–$7.44 |
| 50–200 GB of retained compressed data/artifacts | $1.15–$4.60 |
| Object requests, incremental preparation, logs and control state | $3–$10 |
| Modest public delivery | $1–$3 |
| Rounded AWS planning range | **$10–$50** |

Storage uses $0.023/GB-month as a US East planning rate. The remaining rows are allowances, not measured service bills. This assumes compressed, partitioned history, compact cached public outputs, roughly 1–10 GB/month public delivery, and bounded retries. Larger archives, repeated full rebuilds, or heavy traffic increase costs. [AWS storage cost example](https://docs.aws.amazon.com/solutions/latest/live-streaming-on-aws-with-amazon-s3/cost-example-1.html), [S3 pricing components](https://aws.amazon.com/s3/pricing/).

Allow **$10–$100 one-time AWS processing** for the initial archive preparation and modeling experiment, excluding the data itself. This provisional envelope allows roughly 100–1,500 GB-hours of compute ($6–$90 at the same Lambda rate), plus requests. It needs an end-to-end pilot on representative airports before commitment.

This is a proposed partitioned batch design. The current 25-airport cap, single learner invocation, memory ceilings and publication bounds cannot simply be lifted to run this workload. A global pilot must measure memory, loading, preparation, and publication as well as fitting.

## Flight-data options

**Lower-cost candidate, incomplete coverage:** AeroDataBox Growth lists $99/month, 400,000 units and 24-hour airport queries. At two units/query, one daily pass costs `1,171 × 31 × 2 = 72,602` units; two passes for corrections use 145,204. Self-service history reaches only 365 days. The $499 Scale plan's 48-hour queries could retrieve one year within its quota: `1,171 × 183 × 2 = 428,586` units. Older datasets require a quote. Growth permits longer retention while subscribed; Starter's seven-day retention is unsuitable for this training archive. Confirm applicable model-training rights and plan availability. [AeroDataBox pricing](https://aerodatabox.com/pricing/), [endpoint specification](https://doc.aerodatabox.com/docs/openapi-direct-v1.json).

This gives an exploratory operating budget of **$109–$149/month**, not a complete global solution. The supplier explicitly documents geographic outcome gaps; schedules alone cannot label delays or cancellations. Its country percentages are approximate and are not airport-level historical completeness guarantees. [AeroDataBox coverage](https://aerodatabox.com/data-coverage).

**Retail historical API reference:** FlightAware charges $0.02 per 15-record historical airport result set. Assuming 3–6 million returned records/month gives $4,000–$8,000 before discounts and **$2,680–$4,080 after marginal volume discounts**, plus AWS. This is a usage scenario, not a quote or market minimum. Three million records is an illustrative volume; querying both airport boards can duplicate flights. Partially filled pages, corrections and retries add usage. The 500,000 history-result-set monthly cap makes a large backfill unsuitable for ordinary API purchase; obtain bulk pricing instead. [FlightAware pricing](https://www.flightaware.com/commercial/aeroapi/).

**Complete multi-year archive:** request airport/date-specific completeness and bulk licensing prices for 36 months, then ongoing outcome updates. Cirium advertises historical status data, but its public product page does not provide a price for this scope. No quote has been obtained from it or another supplier. [Cirium flight-status data](https://www.cirium.com/data/flight-tracking-status/).

## Weather and the unresolved total

The existing NOAA bulk weather feeds avoid one paid request per airport. Their data availability still varies. The IEM TAF archive is a historical source, but we have not verified three years of usable forecasts at every global airport or coverage at all three horizons. The estimate assumes public weather sources where adequate; paid forecast archives, radar, lightning, ensembles, and worldwide gridded-model processing are unpriced additions. [NOAA data API](https://aviationweather.gov/data/api/), [IEM TAF archive](https://mesonet.agron.iastate.edu/request/taf.php).

The complete project's startup cost is **historical data quote + approximately $10–$100 AWS processing**. Its monthly cost is **ongoing data license + approximately $10–$50 AWS**. The affordable API candidate does not satisfy verified all-airport coverage; the expensive API scenario is not evidence that a bulk contract must cost that much.

The next step is a coverage and licensing assessment against the airport list, followed by a representative end-to-end pilot. Free regional sources or a research/data partnership could reduce licensing costs, but no verified combination currently supports a promise of validated probabilities at every major airport within $20/month. Existing spending protections remain in effect.

## Follow-up: routes worth testing within $20/month

Public regional outcomes offer a credible expansion path without a subscription. U.S. BTS provides the detailed scheduled/actual times and disruption labels already used by this project, covering reporting carriers' domestic operations. Brazil's ANAC also publishes flight-history files; its official directory contains annual folders through 2026. Brazil is a candidate for a separate coverage/forecast audit, not a completed integration or validation. International routes in a national dataset do not establish coverage of all traffic at their foreign endpoint. [BTS fields](https://transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ), [ANAC VRA catalog](https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/voos-e-operacoes-aereas/voo-regular-ativo-vra), [ANAC archive](https://siros.anac.gov.br/siros/registros/diversos/vra/).

A smaller initial scope of approximately 50–100 supported airports can target $5–$15/month AWS with free data, bounded batch processing and modest traffic; this is an extrapolation needing end-to-end measurement. Initial preparation can run locally. It is a regional expansion budget, not a revision of the 1,171-airport estimate.

There is also a cheaper **global monitoring** lead: AeroDataBox's bulk `/airports/delays` endpoint returns qualified airports' arrival/departure statistics in one request. At six units per request, 744 hourly requests consume 4,464 units, within the advertised $7.50 API.Market plan's 5,000 units. This is quota arithmetic only; current plan access has not been tested. [Pricing](https://aerodatabox.com/pricing/), [API specification](https://doc.aerodatabox.com/docs/openapi-direct-v1.json).

These summaries contain median delays, an index, and flight counts; they do not supply the full distribution needed to calculate our exact 15-minute-delay target. Missing airports are not evidence of normal operations. Cheap-plan history and retention rights also remain unresolved: the default maximum retention is seven days unless response headers or plan terms permit longer. A cheap current-status feed therefore does not yet solve multi-year global training. [Data coverage](https://aerodatabox.com/data-coverage), [retention terms](https://aerodatabox.com/terms).

OpenSky tracking is not a replacement for the missing labels: it explicitly does not supply commercial schedules, delays or cancellations. [OpenSky FAQ](https://opensky-network.org/about/faq).
