# Derek Shirley | Marketing Analytics & Growth Measurement

**[View the live site](https://www.derekdevs.com)**

Static professional portfolio for attribution, forecasting, commercial decision support, and analytics leadership.

## Stack

- Astro
- MDX content collections
- TypeScript
- Plain CSS

Pages are static. Case studies, work listings, and experience live in content collections.

The airport project at `/work/airport-weather` reads static snapshots from a bounded hourly AWS collector. It includes U.S. weather, FAA notices, runway inventory, airport-local disruption models, and a DFW historical replay. Weather remains the default; an optional FAA + weather operations model was assessed across 100 major airports, with sufficient outcome support at 97. See [the nationwide operations evaluation](docs/airport-operations-us-v1.md), [AWS runbook](docs/airport-weather-aws.md), and [project runbook](docs/airport-weather.md) for evidence, source limits, and budget controls. The website stays on its existing host; a static deployment alone does not run collection or training.

## Content

- `src/content/cases/`: full case studies, including attribution and partner enrollment forecasting.
- `src/content/work/`: summaries and display order for the full work catalog.
- `src/content/experience/`: role history, contributions, and leadership scope.
- `src/lib/site.ts`: shared metadata, contact details, and résumé URL.
- `public/Derek_Shirley_Resume_2026.pdf`: the one-page résumé download. Update the PDF and shared URL together when replacing it; preserve redirects for old public URLs in `netlify.toml`.

Forecast validation summaries are dated. Update them when new evidence is available, keeping the monthly, per-partner scope explicit. Work in design or prototype remains labeled as such.

## Visual design

The homepage is an editorial selection in `src/pages/index.astro`, with its layout in `src/styles/home.css`. `DecisionGraphic.astro` contains three distinct, static figures for attribution, proposed budgets, and the forecasting workflow. Keep figure values and qualifications consistent with the corresponding case studies when updating them.

Write copy in plain first-person language about Derek’s actual responsibilities, methods, and results. Use descriptive headings. Avoid slogans, stacked sentence fragments, generic claims about growth or decisions, and repeated summaries that add no information. Keep the distinction between attribution and causal lift, proposed and realized spend, and shipped work and prototypes clear.

Shared colors and typography live in `src/styles/global.css`. The default theme is warm off-white; an explicitly saved light or dark preference is honored across pages. Theme colors for browser chrome also live in `src/lib/site.ts`. Headlines use the system Georgia font; IBM Plex body and figure-label fonts are served locally. No third-party font requests or animation libraries are needed.

## Getting started

Node.js 22+ is recommended.

```sh
npm install
npm run dev
```

Open [http://localhost:4321](http://localhost:4321).

```sh
npm run build
npm run preview
```

## Contact

- Derek Shirley, [derek@derekdevs.com](mailto:derek@derekdevs.com)
- LinkedIn, [linkedin.com/in/derekdevs](https://www.linkedin.com/in/derekdevs/)
