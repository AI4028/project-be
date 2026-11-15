# Accessibility data sources

The original files are distributed separately, unmodified. `manifest.json`
records the upstream revision, download URLs and SHA-256 digests. Run
`python -m scripts.import_accessibility` to reproduce this snapshot.

| File | Original source | Terms | Dataset snapshot |
| --- | --- | --- | --- |
| audio-signals.json | Seoul Open Data, OA-15543 | Korea Open Government License Type 1 (attribution) | Base date 2026-05-28 |
| voice-guides.json | Seoul Metro, OA-22526 | Korea Open Government License Type 1 (attribution) | 2025-08 |
| crosswalks.json | Korean local authorities, data.go.kr 15028201 | Public dataset; unrestricted use according to source notice | Retrieved upstream 2026-08-23 |
| subway-stations.json | Korea National Railway, data.go.kr 15013205 | Source-specific public-data terms, see upstream notice | Upstream notice checked 2026-08-17 |
| osm-walk-nodes.json | © OpenStreetMap contributors | ODbL 1.0, derived database | OSM timestamp 2026-08-16 |

- Snapshot distribution: https://github.com/Engccer/gildongmu
- Upstream source and terms inventory: https://github.com/Engccer/gildongmu/blob/c4a0be3250d9bb7c1df34f3e8c42c8652f9404b9/NOTICE.md
- OpenStreetMap attribution: https://www.openstreetmap.org/copyright
- ODbL license: https://opendatacommons.org/licenses/odbl/1-0/
- KOGL Type 1: https://www.kogl.or.kr/info/licenseType1.do

The OSM derived database remains a separate ODbL file. Do not merge it into
the public-data source files or relabel it as MIT. Runtime query results carry
source and license metadata. Source dates are not live operational verification.
Voice-guide locations are mapped to station coordinates, not device/entrance
coordinates. Recorded infrastructure does not establish route accessibility.
