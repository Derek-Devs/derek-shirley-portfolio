# Operations pilot: all aggregate results

Relative Brier-error reduction versus the matched calendar + weather model. Positive values mean lower probability error, not percentage points of flight delay or percent accuracy. Brackets are paired 95% bootstrap intervals, not adjusted aggregate significance tests.

Each direction/horizon pools eligible flight events across airports. Windows differ across horizons. Arrivals and departures can count the same flight; do not add these counts as distinct journeys.

## Winter: January–February 2026

| Direction / horizon | Airports | Airport flight events | + direction / runways | + FAA activity | Combined |
| --- | ---: | ---: | ---: | ---: | ---: |
| Departures / 24h | 5 | 115,740 | +0.03% [-0.69, +0.61] | +0.54% [-0.74, +2.05] | +0.35% [-0.99, +1.59] |
| Departures / 12h | 6 | 135,049 | +0.13% [-0.45, +0.68] | +1.20% [-0.61, +3.56] | +0.99% [-0.85, +3.11] |
| Departures / 6h | 6 | 135,019 | +0.15% [-0.51, +0.70] | +2.34% [+0.06, +5.65] | +2.27% [-0.06, +5.52] |
| Arrivals / 24h | 5 | 118,248 | +0.17% [-0.62, +0.85] | +0.89% [-0.48, +2.48] | +0.84% [-0.77, +2.42] |
| Arrivals / 12h | 6 | 135,034 | +0.21% [-0.37, +0.79] | +1.62% [-0.66, +4.60] | +1.51% [-0.78, +4.14] |
| Arrivals / 6h | 6 | 135,029 | +0.16% [-0.53, +0.72] | +3.22% [+0.28, +7.28] | +3.14% [+0.20, +7.06] |

### Calibration and uncertainty

Equal-weight means across the 34 tested airport/direction/horizon slices. Calibration gap is the flight-weighted absolute gap within 10 probability bins, then averaged across slices. Outcome-rate bands target 80% coverage; these are not confidence intervals on an individual flight.

| Input variant | Brier error ↓ | Calibration gap ↓ | 80% band coverage | Mean band width | Log loss ↓ |
| --- | ---: | ---: | ---: | ---: | ---: |
| calendar | 0.19461 | 6.25 pp | 76.0% | 38.9 pp | 0.58127 |
| weather | 0.18327 | 6.15 pp | 74.7% | 35.4 pp | 0.55360 |
| weatherDirection | 0.18254 | 5.89 pp | 74.3% | 34.5 pp | 0.55172 |
| weatherRunway | 0.18269 | 5.77 pp | 74.3% | 34.6 pp | 0.55192 |
| weatherFaa | 0.18116 | 5.78 pp | 73.7% | 34.7 pp | 0.54746 |
| weatherRunwayFaa | 0.18093 | 5.50 pp | 73.3% | 34.1 pp | 0.54683 |

### Six-hour airport results: combined inputs versus weather

| Airport | Departure error reduction [95% interval] | Departure adjusted q | Arrival error reduction [95% interval] | Arrival adjusted q |
| --- | ---: | ---: | ---: | ---: |
| DFW | +5.44% [-2.02, +15.28] | 0.501 | +7.60% [-2.51, +20.30] | 0.501 |
| DAL | -0.32% [-2.43, +1.45] | 1.000 | -1.72% [-4.50, +0.32] | 1.000 |
| ORD | +0.94% [+0.34, +1.65] | 0.151 | +0.73% [-0.25, +2.07] | 0.422 |
| SFO | +1.59% [-0.11, +3.67] | 0.422 | +4.29% [+1.30, +7.79] | 0.217 |
| MIA | +0.90% [-1.81, +3.00] | 0.501 | +1.35% [-1.20, +3.48] | 0.448 |
| JFK | +1.09% [-3.33, +4.47] | 0.665 | +2.57% [-2.25, +6.46] | 0.489 |

The approximate BH adjustment includes all four experimental contrasts across the 34 airport/direction/horizon slices (136 tests) within this period. It does not remove retrospective selection, dependence, or delivery uncertainty.

## Spring: March–June 2026

| Direction / horizon | Airports | Airport flight events | + direction / runways | + FAA activity | Combined |
| --- | ---: | ---: | ---: | ---: | ---: |
| Departures / 24h | 5 | 197,190 | +0.71% [+0.07, +1.34] | -0.03% [-0.64, +0.68] | +0.58% [-0.29, +1.53] |
| Departures / 12h | 6 | 289,857 | +0.97% [+0.30, +1.62] | +0.50% [-0.16, +1.23] | +1.30% [+0.42, +2.30] |
| Departures / 6h | 6 | 290,261 | +0.93% [+0.38, +1.48] | +2.05% [+0.95, +3.18] | +2.53% [+1.35, +3.80] |
| Arrivals / 24h | 5 | 197,804 | +1.23% [+0.41, +2.08] | +0.41% [-0.26, +1.23] | +1.51% [+0.40, +2.78] |
| Arrivals / 12h | 6 | 289,842 | +1.78% [+0.91, +2.59] | +1.05% [+0.19, +1.95] | +2.53% [+1.35, +3.76] |
| Arrivals / 6h | 6 | 290,202 | +1.81% [+1.04, +2.51] | +3.74% [+2.41, +5.09] | +4.62% [+3.19, +6.13] |

### Calibration and uncertainty

Equal-weight means across the 34 tested airport/direction/horizon slices. Calibration gap is the flight-weighted absolute gap within 10 probability bins, then averaged across slices. Outcome-rate bands target 80% coverage; these are not confidence intervals on an individual flight.

| Input variant | Brier error ↓ | Calibration gap ↓ | 80% band coverage | Mean band width | Log loss ↓ |
| --- | ---: | ---: | ---: | ---: | ---: |
| calendar | 0.19655 | 4.91 pp | 75.1% | 43.5 pp | 0.57844 |
| weather | 0.19138 | 4.40 pp | 74.7% | 40.4 pp | 0.56650 |
| weatherDirection | 0.18953 | 3.64 pp | 75.0% | 39.3 pp | 0.56215 |
| weatherRunway | 0.18926 | 3.44 pp | 75.1% | 39.1 pp | 0.56158 |
| weatherFaa | 0.18941 | 4.20 pp | 75.3% | 39.5 pp | 0.56186 |
| weatherRunwayFaa | 0.18780 | 3.38 pp | 75.4% | 38.4 pp | 0.55808 |

### Six-hour airport results: combined inputs versus weather

| Airport | Departure error reduction [95% interval] | Departure adjusted q | Arrival error reduction [95% interval] | Arrival adjusted q |
| --- | ---: | ---: | ---: | ---: |
| DFW | +5.25% [+3.13, +7.59] | 0.008 | +9.63% [+6.29, +13.09] | 0.008 |
| DAL | -0.63% [-2.33, +1.12] | 1.000 | -0.36% [-2.18, +1.78] | 1.000 |
| ORD | +1.73% [-0.79, +4.38] | 0.226 | +3.08% [+0.34, +5.84] | 0.096 |
| SFO | +0.96% [+0.15, +1.90] | 0.092 | +2.95% [+1.68, +4.46] | 0.008 |
| MIA | +2.63% [+0.85, +4.76] | 0.050 | +3.69% [+1.17, +6.90] | 0.070 |
| JFK | +0.72% [-0.18, +1.56] | 0.119 | +1.45% [+0.05, +2.78] | 0.084 |

The approximate BH adjustment includes all four experimental contrasts across the 34 airport/direction/horizon slices (136 tests) within this period. It does not remove retrospective selection, dependence, or delivery uncertainty.
