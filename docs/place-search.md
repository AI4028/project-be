# Public place search and accessibility records

`GET /places/search?q=Seoul&kind=stations` works without private provider keys.
Supported kinds: `all`, `stations`, `audio_signals`, `voice_guides`, `tactile`,
`crossings`. Optional `lat` and `lng` must be supplied together. Feature queries
need a position or a station-name match; no artificial user position is used.

Set server-only `KAKAO_REST_API_KEY` to enable general venue search. No key is
bundled in Expo or the browser. The server reads the environment at request time;
launch with `uvicorn --env-file` if using a private local environment file. The
JavaScript map key is not a substitute for a Kakao REST key. Search also matches
registered store names, addresses, and menu names. Registered stores and public
records are still returned during provider failures. A provider failure without
any fallback matches returns 503. For a text query with no matches in the available sources, `status` is
`empty`. When the external directory is unconfigured, `generalSearch` is
`not-configured` so clients can describe which sources were searched.

`GET /accessibility/nearby?lat=37.55&lng=126.97&radiusM=300` returns up to five
nearby records per type, source dates, terms and distances. States distinguish
records, no recorded data, and outside dataset coverage. These are historical
records, not real-time functionality checks or accessible route guidance.

Data attribution and provenance are in `app/data/accessibility/NOTICE.md`.
No database migration or new runtime package is required.
