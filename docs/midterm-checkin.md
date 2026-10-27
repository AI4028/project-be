# Midterm Check-in / 중간 체크인 (26-2학기)

Our team page on the Kakao Impact Tech for Impact program, as written at the
midterm check-in. The original Korean text is kept below.
카카오임팩트 테크포임팩트 팀 페이지의 중간 체크인 내용입니다. 아래에 원문을 그대로 옮겼습니다.

## English summary

- **Service:** Galjido (갈지도). It connects the accessibility information that
  blind, low-vision and physically disabled users need, from reaching a store
  to ordering.
- **Problem:** On the field trip, a blind user who was used to kiosks needed
  about 5 minutes to add a menu item. Kiosk voice guidance cut out or skipped
  options, and the magnifier froze the kiosk. Contrast, entrance conditions and
  kiosk height also matter. Having accessibility features is not the same as
  being able to use them comfortably.
- **Feedback received:** Is linking an accessibility map with ordering enough
  value, or should we focus on ordering? Plan: narrow the target users and
  problem, and define the impact compared with existing ways.
- **Approach:** Three stages: store access, ordering method, menu and order.
  The user orders on their own phone (touch and voice). The current web
  prototype only checks the flow; design and brand identity come later, with
  screen readers and magnification in mind.
- **Tech:** FastAPI, SQLAlchemy, SQLite, WebSocket, HTML/CSS/JS, Web Speech
  API, Web Bluetooth, Arduino. Planned: GPS and geofencing using stored store
  coordinates and radius, then Bluetooth on arrival. Entrance, step and floor
  information still needs a way to be checked and updated at real stores.
- **Risks:** Bluetooth support differs by device and browser, indoor proximity
  is inaccurate, and store noise affects voice ordering. Handle the failure
  cases.
- **Roles:** PM (planning, schedule, budget), Frontend (UI/UX, interaction),
  Backend (features, server, data).
- **Next:** Define the core users, MVP scope, architecture and data sources.
  Then a UI/UX overhaul with the brand identity, connecting frontend and
  backend, and a field test (QA) at a real cafe at GIST.

## Team / 팀

- 소속 · 팀: GIST · 1등
- 팀원: 김진우 · 유선재 · Stalbekov Baiastan · Tsoy Mikhail · Yessenbay Yestay
- 사회혁신가: 이호경 책임 · 링키지랩
- 카카오멘토: 최지원 (jerrie) · 이창용 (yong) · 김진옥 (jade)
- 태그: #접근성 #배리어프리 #매장 이용 #주문 보조 #위치 기반 서비스 #Bluetooth #음성 인터페이스

## Links / 링크

- Notion: https://app.notion.com/p/Linkage-Lab-Galjido-3d5e09a12c8880d68cb4c96184f94678?source=copy_link
- Drive (중간 발표 PPT 자료): https://drive.google.com/drive/folders/1fda341ZXUt6bY5uICxrteDatdVntslxA?usp=sharing

## 원문 / Original (Korean)

**갈지도:** 매장 접근부터 주문까지 장애인에게 필요한 접근성 정보를 세밀하게 연결하는 서비스

### 01 돕는 기술 소개

저희 팀이 개발 중인 ‘갈지도’는 시각장애인, 지체장애인 및 저시력 사용자를 비롯하여, 이동과 공간 접근에 어려움이 있는 사용자의 매장 접근 및 이용을 돕는 서비스입니다. 매장에 들어갈 수 있는지 확인하는 단계부터 주문 방법을 파악하고 메뉴를 선택하는 단계까지, 각 상황에 필요한 접근성 정보를 연결해 제공하고자 합니다.

방문 전에는 출입구와 엘리베이터 등 매장 접근에 필요한 정보를, 매장에 도착한 뒤에는 이용 가능한 주문 방식과 메뉴, 가격, 옵션을 확인할 수 있도록 하며, 개인 스마트폰으로 메뉴와 옵션을 선택하는 주문 보조 기능도 함께 구상하고 있습니다. 이를 통해 사용자가 자신의 상황에 맞는 이용 방법을 선택하고, 현장에서 정보를 다시 확인하거나 주문 기기를 직접 조작해야 하는 부담을 줄이는 것이 목표입니다.

### 02 문제 정의

저희가 해결하고자 하는 문제는 시각장애인, 저시력 사용자, 지체장애인 등이 매장에 접근하고 주문하는 과정에서 필요한 정보를 얻거나 주문 기기를 조작하는 데 어려움을 겪는다는 것입니다. 매장에 접근할 수 있는지에 대한 정보뿐만 아니라, 도착한 뒤 어떤 방식으로 주문할 수 있는지 파악하고 메뉴와 옵션을 선택하는 과정에도 장벽이 있다는 것을 깨달았습니다.

필드트립 과정에서, 키오스크 사용에 익숙한 전맹 시각장애인 사용자분도 메뉴를 담는 데 약 5분이 걸린 것을 발견했습니다. 또한, 키오스크의 음성 안내가 중간에 끊기거나 선택 옵션의 안내가 누락되기도 했으며, 저시력자를 위한 확대 기능을 사용하던 중 기기가 멈추는 상황도 발생했습니다. 뿐만 아니라 저시력 사용자에게는 대비 비율, 지체장애인에게는 매장 진입 조건과 키오스크 높이 역시 이용에 영향을 주는 문제임을 알게 되었습니다.

이러한 문제는 접근성이 있는 것과 접근성 기능을 편리하게 사용할 수 있는 것은 엄연히 다르다는 점에서 시작된다고 생각합니다. 즉, 앞선 실제 사례에서 살펴본 바와 같이 아무리 접근성과 관련된 기능이 있더라도, 그것이 실사용자에게 맞지 않으면 결국 그것 또한 불편함이 될 수 있다는 것입니다.

따라서, 저희는 이들이 매장 접근부터 주문까지 필요한 정보를 하나의 서비스 내에서 확인하고, 자신의 상황에 맞는 방법으로 주문할 수 있도록 돕는 데 집중하고자 합니다.

다만, 기존 접근성 지도와 주문 서비스를 하나로 연결하는 것만으로 사용자에게 충분한 편의를 줄 수 있는지, 주문 과정 쪽에 서비스를 집중하는 편이 나은 것이 아닐지 등 몇몇 피드백을 받기도 했습니다. 이에 따라, 우선 대상 사용자와 문제 상황을 조금 더 뾰족하게 정하고, 기존 방식과 비교했을 때 서비스가 가지는 임팩트(impact)가 무엇일지 추후 세밀하게 생각해보고자 합니다.

### 03 기획·디자인 접근

서비스 이용 과정을 크게 매장 접근, 주문 방법 확인, 메뉴 선택 및 주문의 3단계 순서로 세분화하여, 단계별로 접근하고 발전시키는 방향으로 진행하였습니다.

우선 주문 방식으로는 개인 스마트폰을 활용하는 방안을 검토했습니다. 사용자가 자신이 익숙한 기기 내에서 보조 기능을 활용함으로써, 공용 키오스크의 높이나 조작 방식에서 발생할 수 있는 부담을 줄여줄 수 있을 것으로 판단했습니다. 이에 화면 조작과 음성 인식을 함께 활용하는 주문 방식을 구상하고, 초기 웹 시제품을 통해 매장 연결부터 메뉴 선택까지의 이용 흐름과 기능 간 연계 방식을 구체화하고 있습니다.

구현 측면에서는 HTML, CSS, JavaScript를 기반으로 우선적으로 웹 시제품을 개발하고 있습니다. 화면을 통한 메뉴 및 옵션 선택을 기본으로 하되, 브라우저에서 제공하는 음성 인식 및 음성 합성 기능을 활용하여 음성으로도 주문 과정을 진행할 수 있는 방안을 검토하고 있습니다. 또한 매장과의 연결 및 근접 정보 제공을 위해 Web Bluetooth와 아두이노 기반 장치 등을 활용하는 방식을 시험하고 있습니다. 각 기술의 실제 구현 가능성과 사용성을 확인하면서 핵심 이용 흐름을 우선 검증하고, 이를 바탕으로 서비스의 구체적인 기능과 디자인을 발전시키고자 합니다.

다만 현재 제작해보고 있는 웹 시제품은 기능과 작동 순서를 확인하기 위한 초기 시제품이며, 구체적인 디자인 작업과 브랜드 아이덴티티(BI) 반영은 아직 진행하지 않았습니다. 추후 이용 흐름을 점검한 뒤 정보 배치와 화면 구성을 설계하고, 스크린 리더와 확대 기능을 사용하는 경우도 고려해 UI/UX를 개편할 계획입니다.

### 04 핵심 기술 구현 계획

Python과 FastAPI로 주문 백엔드 구현을 먼저 시작해 보았습니다. 매장과 주문 데이터는 SQLAlchemy와 SQLite를 활용해 관리하고, 서버가 주문금액을 계산한 뒤 WebSocket으로 장바구니와 주문 상태를 전달하도록 구성하고 있습니다. 현재는 초기 코드를 바탕으로 스마트폰과 매장 측 화면 사이에서 주문이 저장되고 전달되는 과정을 확인하고 보완하는 단계로 보입니다.

이후 주문 흐름에 매장 접근 정보를 연결하기 위해 지도와 위치 기반 기능을 추가할 계획입니다. 아직 구현에 착수하지는 않았지만, 매장 좌표와 반경을 저장하는 구조를 바탕으로 GPS와 Geofencing을 활용해 매장 근처에 도착했는지 파악하고자 합니다. 도착 후에는 블루투스로 매장을 연결하는 시제품과 연계하는 방식을 검토하고 있으며, 이때 함께 제공할 출입구, 단차, 층수 등의 정보는 실제 매장에서 확인하고 갱신할 방법을 마련할 예정입니다.

또한, 실제 환경에서 이 흐름을 연결하려면 기기와 브라우저에 따라 블루투스 기능이 달라지는 문제와 실내에서 근접 정보에 오차가 생기는 문제가 어느 정도인지 확인해봐야 할 것으로 보입니다. 음성 주문 역시 매장 소음의 영향을 받을 수 있으므로, 연결이나 음성 인식에 실패했을 때 등의 엣지 케이스를 고려하여 보완할 예정입니다.

### 05 현재 서비스 단계

현재 저희 팀은 프로젝트 매니징(PM), 프론트엔드(Front-end), 백엔드(Backend)의 세 그룹으로 역할을 나누어 작업하고 있습니다. PM에서는 기획과 일정, 예산을 맡고, 프론트엔드(Front-end)에서는 화면(UI/UX)과 사용자 인터랙션을, 백엔드(Backend)에서는 전반적인 기능 개발과 각 정보 및 데이터를 처리하는 서버 기능 구현 등을 담당하고 있습니다.

현재까지는 팀 구성과 현장 조사를 마치고, 문제 정의 초안과 기본 MVP 방향을 정리했습니다. 지금은 이를 구체화하면서 주문 중심의 초기 웹 시제품으로 화면과 서버의 연결을 점검하고 있습니다. 기존 계획보다 주문 기능의 탐색을 일부 먼저 진행했지만, 지도와 위치 기반 기능, 실제 매장 데이터 연계 등는 앞으로 구현해야 할 사항들이 꽤 남아 있습니다.

이후 핵심 사용자와 MVP 범위, 시스템 구조와 데이터 확보 방식을 정리하고, BI를 반영한 UI/UX 개편 및 프론트엔드-백엔드 연결 등의 과정들을 거친 뒤, 지스트 내 실제 카페에서 현장 테스트(QA)를 진행해볼 계획입니다.

### 06 기대 효과

저희 ‘갈지도’ 서비스를 통해, 사용자가 매장에 가기 전에 자신에게 필요한 접근성 정보를 확인하고, 현장에서는 이용 가능한 주문 방법과 메뉴를 한번에 파악할 수 있기를 기대하고 있습니다. 개인 스마트폰에서 메뉴와 옵션을 선택할 수 있다면, 공용 키오스크의 높이나 조작 방식 때문에 겪는 어려움을 줄이는 데도 도움이 될 수 있을 것으로 보입니다. 서비스를 통해 궁극적으로 사용자가 자신의 상황에 맞는 매장과 이용 방식을 선택할 수 있도록 돕는 것이 목표입니다.

### 활용 도구 · 기술 스택

- 기획·디자인 도구: Notion, ChatGPT, Claude, Gemini, Figma (예정)
- 개발 도구: Codex, Claude Code, VS Code
- 기술 스택: Python, FastAPI, SQLAlchemy, SQLite, HTML, CSS, JavaScript, WebSocket, Web Speech API, Web Bluetooth API, Arduino, GPS (예정), Geofencing (예정)
