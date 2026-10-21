# World population pyramids

Move the pointer over a country to see its population pyramid. Click to pin a country, or pick one from the Country list. A Year slider (with Play) runs from 1950 to 2100; countries on the map are shaded by median age.

Live app: https://jsawle.github.io/population-pyramids/

Created by Jason Sawle.

## Versions

| Part | Version | What it covers |
|---|---|---|
| App | 1.0.0 | Whole app (map, panel, controls) |
| Pyramid data | 1.0 | UN WPP 2024 single-year ages for 1 July (mean of the 1 January values either side), grouped into 5-year bands; people per band kept to 3 significant figures; bars show share of total population |
| Median age | 1.0 | Interpolated from single-year ages; matches the UN's published median age |
| Map shading | 1.0 | Countries shaded by median age in 7 fixed classes, the same for every year |

## Data

- **Population by age and sex:** United Nations, Department of Economic and Social Affairs, Population Division (2024). [World Population Prospects 2024](https://population.un.org/wpp/), via the [wpp2024](https://github.com/PPgp/wpp2024) data package. Licensed [CC BY 3.0 IGO](https://creativecommons.org/licenses/by/3.0/igo/). Adapted: mid-year figures grouped into 5-year age bands. The UN has not reviewed or endorsed this app.
- **Country boundaries:** Esri Living Atlas, World Countries (Generalized). Sources: Esri; Garmin International, Inc.; U.S. Central Intelligence Agency (The World Factbook); National Geographic Society.
- **Map:** ArcGIS Maps SDK for JavaScript 5.1, Equal Earth projection, no basemap. Add `?sr=3857` to the URL to force Web Mercator.

Checks: mid-year totals match the UN's published figures (for example, world population 2025 = 8,231,613,070). The standard median-age interpolation from the UN's single-year data comes out exactly 1.0 year above the UN's published median ages; the app follows the published figures.

## Link to a country and year

`?country=JP&year=2050` opens Japan in 2050, pinned. Country codes are ISO two-letter codes.

## Rebuilding the data

The app is one file: `index.html`, with the data embedded. To rebuild it:

1. Get the `data/` folder of [PPgp/wpp2024](https://github.com/PPgp/wpp2024) (`UNlocations.txt`, `popAge1dt.rda`, `popprojAge1dt.rda`).
2. `pip install pyreadr pycountry pandas numpy`
3. `python tools/build_data.py <wpp2024>/data pyramids.json tools/esri_features.txt`
4. `python tools/assemble.py tools/app.template.html pyramids.json index.html`

Bump the version of any part whose maths or data handling changes, and the app version on every release (`APP_VERSION` and `MODELS` near the top of the script in `tools/app.template.html`).
