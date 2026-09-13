# Private aviation and model inputs — September 12, 2026

The airline model uses airport identity/local fits, local hour, day of week,
season, and the archived airport forecast available at each cutoff. Arrival and
departure models are separate. Historical flight counts weight fitting,
calibration, and evaluation and establish sample support. They are not a demand
or congestion feature. There is no live schedule volume, runway capacity,
aircraft rotation, staffing, or upstream delay input. The optional operations
model adds recent FAA advisory-message activity to the airline model; it does
not provide private-jet outcome validation.

The completed traffic-proxy experiment compares calendar, calendar + weather,
and calendar + weather + lagged historical traffic on identical chronological
windows. It did not establish a reliable general benefit; the live model remains
unchanged. See [the experiment and free-data assessment](airport-operations-data.md).
Actual future schedules still need their own as-of archive at each cutoff.

## Private view

Private aviation uses terminal weather context independently of the airline
models and their evidence gates. It does not publish private-flight delay
probabilities, confidence bands, or a safety score.

- The map now colors prevailing ceiling/visibility categories using the
  [NOAA AWC definitions](https://aviationweather.gov/gfa/help/). Temporary and
  probability groups remain separate and receive a dashed map ring. VFR does
  not summarize wind, storms, en-route conditions, operating minima, or safety.
- The private and airline tabs both use one airport, an arrivals/departures
  selector, and one airport time. Airport selection populates the page
  automatically; no destination, route, or trip duration is required.
- All map points and the airport panel use the selected airport time. The
  coverage table labels the selected arrival/departure context and shows that
  airport at each horizon. Private +6/+12/+24 are measured from now;
  airline horizons remain aligned to the published model snapshot.
- Both views share NOAA weather reports, FAA airport notices, and OurAirports
  runway inventory. Switching arrival/departure context does not change the
  underlying airport weather or create direction-specific private probabilities.
  The airline models additionally use historical scheduled-airline outcomes;
  the private view does not reuse that population's probability estimates.
- The coverage table explains the airport's availability at every look-ahead. Airport
  panels include the exact forecast expiry for times beyond available coverage.
  Missing forecasts, missing fields, stale snapshots, and download failures are
  distinct states. Observations never fill future forecast gaps; older forecasts
  never override a superseding issue with shorter coverage.
- Medium airports appear when zoomed in and are always searchable if listed.
- The browser reuses existing static station-prefix files, cached per snapshot,
  with four background downloads at a time. No new AWS jobs, paid weather APIs,
  model weights, or budget settings are involved. Static delivery bytes can
  increase for private-map users; there is no per-selection compute invocation.

Regression checks cover category thresholds, censored/missing data, forecast
amendments and time availability, conditional groups, airport timing, and all
933 bundled airports at each of three horizons (2,799 selections). This is a
functional coverage check, not a claim of private-flight predictive accuracy.

## FAA notices and runway inventory

The selected airport shows timestamped FAA airport notices and monthly cached
OurAirports runway records. Closure exceptions and restrictions limited to
general aviation remain visible. FAA ground stops/delay programs concern flights
bound for the named airport, so a destination restriction can hold departures
elsewhere. No notice is not an all-clear, and the displayed current status is
not a prediction for the planned future trip time. Static runway geometry does
not identify active runway configuration, current capacity, aircraft suitability,
or operating minima. These additions do not create private-flight probabilities.
