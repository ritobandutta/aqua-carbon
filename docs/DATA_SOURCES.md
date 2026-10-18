# Data Sources: Audit Tracker

Candidates only. **None are verified yet.** Phase 0 task: for each row confirm access, licence, resolution and a stable URL, then mirror the result into `data/sources.yaml` (id, URL, licence, resolution, accessed date). Do not pick community-ledger indicators until this is done.

Status values: `candidate`, `verified`, `rejected`.

| Need | Candidate source | Expected resolution | Used for | Status | Licence / notes |
|---|---|---|---|---|---|
| Hourly weather | Open-Meteo or ERA5 historical, or a TMY file for Bengaluru | hourly, point | cooling energy and water in the sim | candidate | check licence and attribution |
| Basin water stress | WRI Aqueduct | basin or sub-basin | regional water-stress context | candidate | confirm licence terms |
| Groundwater stage | CGWB dynamic groundwater resources assessment | block or taluk | groundwater context | candidate | check release year and format |
| Water supply and tariff | BWSSB published capacity and tariff | city | headroom share, water cost | candidate | capacity may not be published. If so show `unavailable` |
| Electricity tariff | BESCOM and KERC HT tariff order | utility | operating cost | candidate | pick the tariff year deliberately |
| Peak demand | BESCOM or Karnataka SLDC peak demand | utility or state | share of peak | candidate | confirm availability and granularity |
| Grid emission factor | CEA CO2 Baseline Database for the Indian grid | national or regional | carbon | candidate | annual factor first. Hourly is a stretch goal |
| Generation mix | Grid-India or POSOCO reports | state or regional, hourly | hourly carbon (stretch) | candidate | check access and format |
| Reliability or outages | utility reliability indices | utility | grid reliability context | candidate | likely sparse. Expect `unavailable` |
| Built-up footprint | GHSL or WorldPop | 10 m to 100 m | coverage check (stretch) | candidate | open licence to confirm |
| Official population | Census of India, ward-level where available | ward | coverage check (stretch) | candidate | census vintage is old, so say so |
| Vulnerability context | public vulnerability indices | varies | community context | candidate | reuse existing layers, do not invent |
| Cooling coefficients | Karimi et al. 2022, ASHRAE, vendor datasheets | n/a | engine coefficients as low, central and high | candidate | record the page or table for every number |

## Rules for adding a source

1. Record the licence and whether redistribution inside this repo is allowed. If not allowed, store a download script, not the data.
2. Record the geographic resolution. The UI shows it on every indicator.
3. Record the access date and dataset version.
4. Mark every value derived from synthetic or assumed inputs as "Illustrative".
5. A source we cannot access is a finding. Record it and show `unavailable` in the product.

## Synthetic facility inputs

There is no real data-center access. Facility inputs (IT load, setpoints, equipment efficiencies) are illustrative and must be labelled. Document each assumption and its basis here as it is chosen.

| Input | Illustrative value | Basis |
|---|---|---|
| | | |
