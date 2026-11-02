# Multi-week AIS holdout: blocked external dependency

The proposed C7 study is specified in `configs/research/ais_multiweek_holdout.yaml`
and preregistered in `docs/preregistration.md`. It has not been run.

The [Danish Maritime Authority](https://www.dma.dk/safety-at-sea/navigational-information/ais-data)
publishes historical AIS archives. Its documented [routing change](https://www.dma.dk/safety-at-sea/navigational-information/new-shipping-routes-in-kattegat-and-skagerrak)
and [follow-up traffic analysis](https://www.dma.dk/news/2020/september/new-routeing-systems-provide-visible-traffic-changes)
provide an external event suitable for a future holdout.

The archive catalogue at `https://aisdata.ais.dk/` returned HTTP 503 from
this execution environment. No new raw data has been acquired, no checksum
has been invented, and no multi-week performance or calibration result is
claimed. The missing checksum is deliberate. Acquisition, provenance and
licensing checks must succeed before analysis. This study specification is
not a runnable ExperimentConfig for the current synthetic CLI.

The later access recheck is preserved in
`validation/part_c/data_access_recheck.json`; it did not acquire a raw archive.
