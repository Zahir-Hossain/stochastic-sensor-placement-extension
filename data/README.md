# Data

## AIS sample (case study)

| | |
|---|---|
| Content | AIS position reports, 5 July 2017, near the port of Gothenburg (84,702 reports, 100 vessels) |
| Publisher | Danish Maritime Authority, https://dma.dk/safety-at-sea/navigational-information/ais-data |
| Redistributed as | `data/ais.gpkg` in https://github.com/anitagraser/movingpandas-examples |
| SHA-256 | `038c98af738e29cdac5d91a1829eb88a4b7cf94fedbf6f6cf8e04982bd65e4e3` |

The raw file is **not** committed. Fetch it with

```bash
python scripts/fetch_ais_sample.py      # writes data/raw/ais.gpkg and checks the hash
stochplace ais                          # runs the case study into results/ais_gothenburg/
```

`results/ais_gothenburg/lines.csv` holds only the derived straight
trajectory pieces (representation, endpoints in local km, ship type,
time). Vessel MMSI numbers are replaced by an anonymous index.

Please credit the Danish Maritime Authority when using the data.

## Synthetic data

All other experiments generate their data on the fly from
`stochplace.scenarios`; configs and seeds in `configs/` fully determine
them.
