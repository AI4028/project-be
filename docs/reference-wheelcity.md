# Reference: WheelCity (휠도시, 2025) / 참고 프로젝트

Last year's KAIST CS499 Tech for Impact project with a barrier-free map.
작년 KAIST CS499 테크포임팩트 수업의 배리어프리 지도 프로젝트입니다.

- Backend: https://github.com/kang022878/WheelCity_back_2025 (FastAPI, MongoDB, S3, YOLOv8 + Gemini)
- Frontend: https://github.com/lollipop719/WheelCity_front_2025 (HTML/JS, Kakao Maps)
- AI: https://github.com/AsyncNomad/WheelCity_AI_2025

> ⚠️ **No license on either repo.** All rights are reserved by default, so we
> can learn from their ideas and data model, but we must not copy their code.
> If we want to reuse code, ask the authors first; their contacts are in the
> backend README.
> **라이선스가 없습니다.** 아이디어와 구조는 참고하되 코드는 복사하지 않습니다.
> 코드가 필요하면 작성자에게 먼저 허락을 받습니다.

## What it does / 기능

A crowdsourced barrier-free map for **wheelchair users**. Users add places
and photos of entrances. An AI (YOLOv8, then Gemini) tags each entrance with
`ramp` and `curb` (step). Reviews ("could you enter?", "could you enter
alone?", "was it comfortable?", "was the AI right?") keep the data up to date.
When reviews disagree with the AI, the photos are re-analysed.

휠체어 사용자를 위한 사용자 참여형 배리어프리 지도입니다. 입구 사진을 AI가 분석해
경사로·턱 여부를 태그하고, 리뷰로 정보를 계속 갱신합니다.

## Worth adopting / 가져올 만한 것

| Idea | Theirs | For Galjido |
| --- | --- | --- |
| Map SDK | Kakao Maps JS SDK (`kakao.maps.Map`, markers, `Places` search), centred on KAIST | Kakao Maps has the best Korean POI data. Center on GIST; needs a Kakao developer app key with our domain registered. Leaflet + OpenStreetMap is a no-key fallback. 카카오맵 사용 (GIST 중심) |
| My location | `navigator.geolocation` plus a custom overlay that rotates with `heading` | The same idea for "you are here", and the basis for geofencing: compare the position with each store's `lat`/`lng` and `geofenceRadiusM`. 내 위치 + 지오펜싱 |
| Nearby stores | `GET /shops/nearby?lat&lng&radius=800` (MongoDB `$near`) | Add `GET /stores/nearby` to project-be. With few stores, distance can be computed in Python; no geo database needed. 주변 매장 API |
| Personal accessibility | The user profile stores `wheelchair_type` (manual/auto) and `max_height_cm` (highest step they can manage) | This fits our flow, where the user picks a disability type, saved in a cookie. The wheelchair map could also ask for the highest step they can manage and mark each store as "can enter / can't enter". 개인 맞춤 접근 가능 여부 |
| Entrance data | `ramp`, `curb` booleans | Extend our `accessibility` JSON with step height, ramp, entrance width, floor and elevator. 출입구 정보 확장 |
| Keeping data fresh | Review rates: `enter_success_rate`, `alone_entry_rate`, `comfort_rate` | Our midterm check-in says we still need a way to check and update entrance, step and floor data. A simple "Could you get in?" review after an order is cheap to add. 정보 갱신 방법 |

## Not adopting (for now) / 당분간 제외

- **The YOLOv8 + Gemini photo pipeline, S3 uploads and Kakao login.** It's a
  big stack (torch, a 6.5 MB model, a Gemini key) for our timeline. We have a
  few pilot stores, so the team can enter their data by hand.
  AI 사진 분석·S3·카카오 로그인: 일정 대비 너무 큼.
- **Polling endpoints** (`/accessibility/updates`, ETag): we already have WebSockets.
- **MongoDB:** we use SQLite/PostgreSQL. 기존 DB 유지.

## How we differ / 차별점

WheelCity covers **one user group (wheelchair users) and one stage (reaching
the place)**. Galjido covers blind, low-vision and physically disabled users,
with a different map for each, and continues **after arrival**: ordering
methods, and ordering from your own phone. This helps answer the midterm
feedback asking whether linking a map with ordering adds enough value.
휠도시는 휠체어 사용자·매장 접근 단계에 집중합니다. 갈지도는 여러 장애 유형별 지도와
도착 후 주문까지 이어지는 것이 차별점입니다 (중간 피드백에 대한 답변 근거).
