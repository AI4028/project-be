/**
 * app.js - 배리어프리 키오스크 주문 프론트엔드 핵심 로직
 * 한국어 시각장애인 고객을 위한 음성 인식, TTS 안내, 실시간 WebSocket 연동 및 키오스크 화면 시뮬레이션
 */

(function () {
  'use strict';

  // ==========================================
  // 기본 오프라인/대체 매장 & 메뉴 데이터 (GIST Cafe점)
  // ==========================================
  const DEFAULT_STORE_DATA = {
    name: "GIST Cafe점",
    nameEn: "GIST Cafe",
    address: "광주광역시 북구 첨단과기로 123 (GIST)",
    accessibility: {
      floor: 1,
      notes: "출입구 경사로 구비, 자동문 및 음성 안내 지원"
    },
    menu: [
      {
        id: "americano",
        name: "아메리카노",
        nameEn: "Americano",
        category: "커피",
        price: 2500,
        available: true,
        description: "에스프레소에 물을 더한 기본 커피",
        options: [
          {
            id: "temp", name: "온도", type: "single", required: true,
            choices: [
              { id: "hot", name: "따뜻하게", priceDelta: 0 },
              { id: "ice", name: "아이스", priceDelta: 0 }
            ]
          },
          {
            id: "size", name: "크기", type: "single", required: true,
            choices: [
              { id: "regular", name: "레귤러", priceDelta: 0 },
              { id: "large", name: "라지", priceDelta: 500 }
            ]
          }
        ]
      },
      {
        id: "cafe-latte",
        name: "카페라떼",
        nameEn: "Cafe Latte",
        category: "커피",
        price: 3500,
        available: true,
        description: "에스프레소와 부드러운 우유",
        options: [
          {
            id: "temp", name: "온도", type: "single", required: true,
            choices: [
              { id: "hot", name: "따뜻하게", priceDelta: 0 },
              { id: "ice", name: "아이스", priceDelta: 0 }
            ]
          }
        ]
      },
      {
        id: "vanilla-latte",
        name: "바닐라라떼",
        nameEn: "Vanilla Latte",
        category: "커피",
        price: 4000,
        available: true,
        description: "바닐라 시럽이 들어간 달콤한 라떼",
        options: [
          {
            id: "temp", name: "온도", type: "single", required: true,
            choices: [
              { id: "hot", name: "따뜻하게", priceDelta: 0 },
              { id: "ice", name: "아이스", priceDelta: 0 }
            ]
          }
        ]
      },
      {
        id: "grapefruit-ade",
        name: "자몽에이드",
        nameEn: "Grapefruit Ade",
        category: "음료",
        price: 4500,
        available: true,
        description: "상큼한 탄산 자몽 에이드 (아이스)",
        options: []
      },
      {
        id: "croissant",
        name: "크루아상",
        nameEn: "Croissant",
        category: "베이커리",
        price: 3000,
        available: true,
        description: "고소한 버터 풍미 크루아상",
        options: []
      }
    ]
  };

  // ==========================================
  // 상태 관리 객체 (App State)
  // ==========================================
  const state = {
    // 디바이스 & 세션
    deviceId: null,
    deviceToken: null,
    kioskId: 'GK01',
    kioskName: '키오스크 1',
    kioskKey: 'ksk_nYbONRWa4w2bS9cOnvguPZMtG4mCpAejJQv8861kBSo',
    sessionId: null,
    sessionWs: null,
    kioskWs: null,

    // 매장 & 메뉴
    storeId: 'gist-cafe',
    storeData: DEFAULT_STORE_DATA,
    menuItems: DEFAULT_STORE_DATA.menu,
    selectedCategory: 'all',

    // 옵션 모달 진행 중 상태
    currentMenuItem: null,
    pickedOptions: {},
    currentQty: 1,

    // 장바구니
    cartItems: [], // [{ itemId, qty, options }]
    cartTotal: 0,
    cartSummary: '',

    // 현재 활성 주문
    currentOrder: null,

    // 접근성 설정
    highContrast: false,
    fontSizeLevel: 0, // 0: 100%, 1: 120%, 2: 145%
    ttsEnabled: true,
    currentView: 'phone', // 'phone' | 'kiosk' | 'split'

    // 갈지도 매장 탐색 및 지속적 거리 측정 상태
    proximity: {
      status: 'scanning', // 'scanning' | 'detected' | 'connected'
      storeName: 'GIST Cafe점',
      kioskId: 'GK01',
      distance: 999, // 미터 단위
      awaitingConfirmation: false,
      lastPromptedDistance: null,
      serialPort: null,
      serialReader: null,
    },
  };

  // ==========================================
  // DOM 요소 캐싱
  // ==========================================
  const dom = {
    // 접근성 도구
    btnHighContrast: document.getElementById('btn-high-contrast'),
    contrastText: document.getElementById('contrast-text'),
    btnFontSize: document.getElementById('btn-font-size'),
    fontSizeText: document.getElementById('font-size-text'),
    btnTtsToggle: document.getElementById('btn-tts-toggle'),
    ttsStatusText: document.getElementById('tts-status-text'),
    btnRepeatVoice: document.getElementById('btn-repeat-voice'),
    srAnnouncer: document.getElementById('sr-announcer'),

    // 신규 접근성 드로어 & 헤더 컨트롤
    btnOpenAccessibility: document.getElementById('btn-open-accessibility'),
    accessibilityDrawer: document.getElementById('accessibility-drawer'),
    btnCloseAccessDrawer: document.getElementById('btn-close-access-drawer'),
    btnTopCart: document.getElementById('btn-top-cart'),
    headerCartBadge: document.getElementById('header-cart-badge'),
    modalMenuImg: document.getElementById('modal-menu-img'),
    kioskLiveClock: document.getElementById('kiosk-live-clock'),

    // 뷰 탭
    tabPhone: document.getElementById('tab-phone'),
    tabKiosk: document.getElementById('tab-kiosk'),
    tabSplit: document.getElementById('tab-split'),
    viewsContainer: document.getElementById('views-container'),
    phoneView: document.getElementById('phone-view'),
    kioskView: document.getElementById('kiosk-view'),

    // 스마트폰 뷰 & 스타벅스 헤더
    btnSelectStore: document.getElementById('btn-select-store'),
    btnIndoorGuide: document.getElementById('btn-indoor-guide'),
    storeDescLine: document.getElementById('store-desc-line'),
    connectionDot: document.getElementById('connection-dot'),
    connectionLabel: document.getElementById('connection-label'),
    btnEndSession: document.getElementById('btn-disconnect-store') || document.getElementById('btn-end-session'),
    pairingSection: document.getElementById('pairing-section'),
    btnConnectKiosk: document.getElementById('btn-connect-kiosk'),
    storeSection: document.getElementById('store-section'),
    menuSection: document.getElementById('menu-section'),
    categoryTabs: document.getElementById('category-tabs'),
    menuCountBadge: document.getElementById('menu-count-badge'),
    menuItemsGrid: document.getElementById('menu-items-grid'),

    // 갈지도 탐색 뷰 & 주문 뷰 DOM
    galjidoDiscoveryView: document.getElementById('galjido-discovery-view'),
    galjidoOrderView: document.getElementById('galjido-order-view'),
    discBeaconLabel: document.getElementById('disc-beacon-label'),
    discMainTitle: document.getElementById('disc-main-title'),
    radarBeaconTrigger: document.getElementById('radar-beacon-trigger'),
    btnMobileBleScan: document.getElementById('btn-mobile-ble-scan'),
    btnQuickDistTest: document.getElementById('btn-quick-dist-test'),
    bleStatusDot: document.getElementById('ble-status-dot'),
    bleStatusText: document.getElementById('ble-status-text'),
    detectedStorePopup: document.getElementById('detected-store-popup'),
    detectedStoreName: document.getElementById('detected-store-name'),
    detectedDistanceVal: document.getElementById('detected-distance-val'),
    btnConfirmConnect: document.getElementById('btn-confirm-connect'),
    btnRejectConnect: document.getElementById('btn-reject-connect'),
    headerDistanceText: document.getElementById('header-distance-text'),
    btnDisconnectStore: document.getElementById('btn-disconnect-store'),
    liveDistanceBadge: document.getElementById('live-distance-badge'),

    // 플로팅 카트 바 & 모달
    floatingCart: document.getElementById('floating-cart'),
    cartItemCount: document.getElementById('cart-item-count'),
    cartTotalAmount: document.getElementById('cart-total-amount'),
    btnOpenCart: document.getElementById('btn-open-cart'),
    cartModal: document.getElementById('cart-modal'),
    btnCloseCart: document.getElementById('btn-close-cart'),
    cartItemsContainer: document.getElementById('cart-items-container'),
    cartModalTotalPrice: document.getElementById('cart-modal-total-price'),
    cartOrderNote: document.getElementById('cart-order-note'),
    btnNoteMic: document.getElementById('btn-note-mic'),
    btnCheckoutSubmit: document.getElementById('btn-checkout-submit'),

    // 옵션 모달
    optionModal: document.getElementById('option-modal'),
    btnCloseOption: document.getElementById('btn-close-option'),
    modalMenuName: document.getElementById('modal-menu-name'),
    modalMenuPrice: document.getElementById('modal-menu-price'),
    modalOptionsBody: document.getElementById('modal-options-body'),
    modalQtyVal: document.getElementById('modal-qty-val'),
    btnQtyMinus: document.getElementById('btn-qty-minus'),
    btnQtyPlus: document.getElementById('btn-qty-plus'),
    btnAddToCart: document.getElementById('btn-add-to-cart'),
    modalSubmitPrice: document.getElementById('modal-submit-price'),

    // 주문 현황
    orderStatusSection: document.getElementById('order-status-section'),
    liveOrderNumber: document.getElementById('live-order-number'),
    orderStatusAnnouncement: document.getElementById('order-status-announcement'),
    orderStatusDesc: document.getElementById('order-status-desc'),
    orderSummaryBox: document.getElementById('order-summary-box'),
    btnCancelOrder: document.getElementById('btn-cancel-order'),
    btnNewOrder: document.getElementById('btn-new-order'),
    stepSubmitted: document.getElementById('step-submitted'),
    stepAccepted: document.getElementById('step-accepted'),
    stepPreparing: document.getElementById('step-preparing'),
    stepReady: document.getElementById('step-ready'),

    // 키오스크 디스플레이
    kioskBleTokenBadge: document.getElementById('kiosk-ble-token-badge'),
    kioskCartHeader: document.getElementById('kiosk-cart-header'),
    kioskCartContent: document.getElementById('kiosk-cart-content'),
    btnKioskEndSession: document.getElementById('btn-kiosk-end-session'),
    kioskOrdersFilter: document.getElementById('kiosk-orders-filter'),
    kioskOrdersList: document.getElementById('kiosk-orders-list'),
    kioskHelpAlertBox: document.getElementById('kiosk-help-alert-box'),
    kioskHelpAlertText: document.getElementById('kiosk-help-alert-text'),
    btnResolveHelp: document.getElementById('btn-resolve-help'),
    kioskAvailabilityList: document.getElementById('kiosk-availability-list'),

    // 신규 모달들 (매장 선택 & 실내 길안내)
    storeSelectModal: document.getElementById('store-select-modal'),
    btnCloseStoreSelect: document.getElementById('btn-close-store-select'),
    storesListContainer: document.getElementById('stores-list-container'),
    indoorGuideModal: document.getElementById('indoor-guide-modal'),
    btnCloseIndoorGuide: document.getElementById('btn-close-indoor-guide'),
    modalIndoorText: document.getElementById('modal-indoor-text'),
    modalAccessList: document.getElementById('modal-access-list'),
    btnPlayIndoorTts: document.getElementById('btn-play-indoor-tts'),

    // 음성 바
    btnVoiceMic: document.getElementById('btn-voice-mic'),
    voiceStatusLabel: document.getElementById('voice-status-label'),
    voiceHintLabel: document.getElementById('voice-hint-label'),
    btnCallHelp: document.getElementById('btn-call-help'),

    // 토스트
    toastBox: document.getElementById('toast-box'),
  };

  // ==========================================
  // 유틸리티 함수
  // ==========================================
  function formatWon(num) {
    return (num || 0).toLocaleString('ko-KR') + '원';
  }

  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type === 'danger' ? 'toast-danger' : type === 'success' ? 'toast-success' : ''}`;
    toast.textContent = message;
    dom.toastBox.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  function announce(text, { priority = 'normal', playTts = true, onEnd = null } = {}) {
    dom.srAnnouncer.textContent = text;
    if (playTts && window.speechService) {
      window.speechService.speak(text, { priority, onEnd });
    }
  }

  // ==========================================
  // 백엔드 API 통신 모듈
  // ==========================================
  const api = {
    async request(path, options = {}) {
      const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
      if (state.deviceToken && !headers['Authorization']) {
        headers['Authorization'] = `Bearer ${state.deviceToken}`;
      }

      let res = await fetch(path, { ...options, headers });
      if (res.status === 401 && path !== '/devices') {
        console.warn('디바이스 토큰 만료 (401): 재등록 후 재시도');
        try {
          const newDev = await this.registerDevice();
          headers['Authorization'] = `Bearer ${newDev.token}`;
          res = await fetch(path, { ...options, headers });
        } catch (e) {
          console.error('재등록 실패:', e);
        }
      }

      if (!res.ok) {
        let errData;
        try {
          errData = await res.json();
        } catch (e) {
          errData = { message: res.statusText };
        }
        const error = new Error(errData.message || '서버 오류가 발생했습니다.');
        error.code = errData.error;
        error.status = res.status;
        throw error;
      }
      return res.json();
    },

    // 1. 디바이스 등록
    async registerDevice() {
      const data = await this.request('/devices', { method: 'POST' });
      state.deviceId = data.deviceId;
      state.deviceToken = data.token;
      localStorage.setItem('barrier_free_device_id', data.deviceId);
      localStorage.setItem('barrier_free_device_token', data.token);
      return data;
    },

    // 2. 모든 매장 목록 조회 (GET /stores)
    async listStores() {
      return await this.request('/stores');
    },

    // 2-1. 단일 매장 상세 조회 (GET /stores/{id})
    async getStore(storeId) {
      return await this.request(`/stores/${storeId}`);
    },

    // 2-2. 키오스크 정보 조회 (GET /kiosks/{id})
    async getKiosk(kioskId) {
      return await this.request(`/kiosks/${kioskId}`);
    },

    // 3. 키오스크 페어링 토큰 얻기 (시뮬레이션 helper)
    async getKioskToken(kioskId) {
      return await this.request(`/kiosks/${kioskId}/token`);
    },

    // 4. 키오스크 세션 연결
    async connectSession(kioskId, token) {
      return await this.request('/sessions', {
        method: 'POST',
        body: JSON.stringify({ kioskId, token }),
      });
    },

    // 5. 세션 상태 및 카트 조회 (GET /sessions/{id})
    async getSession(sessionId) {
      return await this.request(`/sessions/${sessionId}`);
    },

    // 5-1. 키오스크 활성 세션 조회 (GET /kiosk/session)
    async getKioskActiveSession() {
      return await this.request('/kiosk/session', {
        headers: { Authorization: `Bearer ${state.kioskKey}` },
      });
    },

    // 6. 장바구니 동기화 (PUT /sessions/{id}/cart)
    async updateCart(sessionId, items) {
      return await this.request(`/sessions/${sessionId}/cart`, {
        method: 'PUT',
        body: JSON.stringify({ items }),
      });
    },

    // 7. 주문 접수 (POST /sessions/{id}/order with note)
    async placeOrder(sessionId, items, paymentMethod = 'counter', note = '') {
      return await this.request(`/sessions/${sessionId}/order`, {
        method: 'POST',
        body: JSON.stringify({ items, paymentMethod, note }),
      });
    },

    // 8. 직원 호출 (POST /sessions/{id}/help)
    async callHelp(sessionId) {
      return await this.request(`/sessions/${sessionId}/help`, { method: 'POST' });
    },

    // 9. 주문 취소 (POST /orders/{id}/cancel)
    async cancelOrder(orderId) {
      return await this.request(`/orders/${orderId}/cancel`, { method: 'POST' });
    },

    // 9-1. 단일 주문 상세 조회 (GET /orders/{id})
    async getOrder(orderId) {
      return await this.request(`/orders/${orderId}`);
    },

    // 10. 스마트폰 고객 세션 종료 (POST /sessions/{id}/end)
    async endSession(sessionId) {
      return await this.request(`/sessions/${sessionId}/end`, { method: 'POST' });
    },

    // 10-1. 키오스크 직원 세션 강제 종료 (POST /kiosk/sessions/{id}/end)
    async kioskEndSession(sessionId) {
      return await this.request(`/kiosk/sessions/${sessionId}/end`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${state.kioskKey}` },
      });
    },

    // 11. 키오스크 하트비트 (POST /kiosk/heartbeat)
    async kioskHeartbeat() {
      return await this.request('/kiosk/heartbeat', {
        method: 'POST',
        headers: { Authorization: `Bearer ${state.kioskKey}` },
      });
    },

    // 12. 키오스크 주문 목록 (GET /kiosk/orders?status=...)
    async getKioskOrders(status = null) {
      const q = status ? `?status=${encodeURIComponent(status)}` : '';
      return await this.request(`/kiosk/orders${q}`, {
        headers: { Authorization: `Bearer ${state.kioskKey}` },
      });
    },

    // 13. 주문 상태 변경 (POST /kiosk/orders/{id}/status)
    async updateOrderStatus(orderId, status) {
      return await this.request(`/kiosk/orders/${orderId}/status`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${state.kioskKey}` },
        body: JSON.stringify({ status }),
      });
    },

    // 14. 직원 호출 해결 완료 (POST /kiosk/sessions/{id}/resolve-help)
    async resolveHelp(sessionId) {
      return await this.request(`/kiosk/sessions/${sessionId}/resolve-help`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${state.kioskKey}` },
      });
    },

    // 15. 메뉴 품절/판매 재개 관리 (PUT /kiosk/menu/{itemId}/availability)
    async setItemAvailability(itemId, available) {
      return await this.request(`/kiosk/menu/${itemId}/availability`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${state.kioskKey}` },
        body: JSON.stringify({ available }),
      });
    },
  };

  // ==========================================
  // 초기화 (App Initialization)
  // ==========================================
  async function init() {
    setupAccessibilityControls();
    setupViewModeTabs();
    setupModalsAndEvents();
    setupSpeechIntegration();
    setupProximityControls();

    // 1. 디바이스 토큰 복원 또는 새로 생성
    state.deviceId = localStorage.getItem('barrier_free_device_id');
    state.deviceToken = localStorage.getItem('barrier_free_device_token');

    if (!state.deviceToken) {
      try {
        await api.registerDevice();
      } catch (err) {
        console.error('디바이스 등록 실패:', err);
      }
    }

    // 2. 매장 정보 및 메뉴 로드
    try {
      const store = await api.getStore(state.storeId);
      if (store && store.menu && store.menu.length > 0) {
        state.storeData = store;
        state.menuItems = store.menu;
      }
    } catch (err) {
      console.warn('매장 API 통신 건너뜀 (기본 GIST Cafe 데이터 사용):', err.message);
    }
    // 메뉴와 매장 정보 렌더링 보장
    renderStoreInfo(state.storeData);
    renderCategories(state.menuItems);
    renderMenuItems(state.menuItems);

    // 3. 키오스크 디스플레이 백그라운드 하트비트 & WebSocket
    initKioskSimulator();

    // 4. 갈지도 시작 음성 안내 (주위 매장 탐색)
    setTimeout(() => {
      announce('안녕하세요 갈지도 입니다. 주위 매장을 탐색하고 있어요.');
    }, 600);
  }

  // ==========================================
  // 키오스크 연결 플로우
  // ==========================================
  async function connectToKiosk() {
    if (dom.btnConnectKiosk) {
      dom.btnConnectKiosk.disabled = true;
      dom.btnConnectKiosk.textContent = '키오스크에 연결 중...';
    }
    if (dom.btnConfirmConnect) {
      dom.btnConfirmConnect.disabled = true;
      dom.btnConfirmConnect.textContent = '연결 중...';
    }
    if (window.soundFeedback) window.soundFeedback.tick();

    let session = null;

    // 1. 백엔드 세션 연결 시도 (백엔드가 실행 중인 경우)
    try {
      const tokenInfo = await api.getKioskToken(state.kioskId);
      console.log('발급받은 키오스크 페어링 토큰:', tokenInfo.token);

      try {
        session = await api.connectSession(state.kioskId, tokenInfo.token);
      } catch (connErr) {
        if (connErr.code === 'kiosk-busy' || connErr.status === 409) {
          console.warn('키오스크 점유 중(409). 이전 잔여 세션 정리 후 재연결 시도...');
          try {
            const active = await api.getKioskActiveSession();
            if (active && active.sessionId) {
              await api.kioskEndSession(active.sessionId);
            }
          } catch (e) {
            console.warn('세션 정리 중 경고:', e);
          }
          const freshToken = await api.getKioskToken(state.kioskId);
          session = await api.connectSession(state.kioskId, freshToken.token);
        } else {
          throw connErr;
        }
      }
    } catch (err) {
      console.warn('백엔드 세션 연결 API 실패 -> 로컬 키오스크 세션으로 즉시 전환:', err);
      // 백엔드가 꺼져있거나 통신 불가여도 항상 동작하는 로컬 세션 생성
      session = {
        sessionId: 'session-gist-cafe-' + Date.now(),
        kioskName: 'GIST Cafe (키오스크 1)',
        kioskId: state.kioskId || 'GK01',
        cart: { lines: [] }
      };
    }

    try {
      state.sessionId = session.sessionId;
      state.proximity.status = 'connected';
      state.proximity.awaitingConfirmation = false;

      // 2. 메뉴 렌더링 확인 및 보장
      if (!state.menuItems || state.menuItems.length === 0) {
        state.storeData = DEFAULT_STORE_DATA;
        state.menuItems = DEFAULT_STORE_DATA.menu;
      }
      renderStoreInfo(state.storeData);
      renderCategories(state.menuItems);
      renderMenuItems(state.menuItems);

      // 3. UI 화면 전환 (탐색 뷰 숨기고 주문 화면 활성화!)
      if (dom.galjidoDiscoveryView) dom.galjidoDiscoveryView.style.display = 'none';
      if (dom.galjidoOrderView) dom.galjidoOrderView.style.display = 'block';
      if (dom.connectionDot) dom.connectionDot.className = 'status-dot connected';
      if (dom.connectionLabel) dom.connectionLabel.textContent = `${session.kioskName} 연결됨`;
      if (dom.menuSection) dom.menuSection.style.display = 'block';
      updateProximityDistanceGauge(state.proximity.distance || 1.0, state.proximity.rssi || null);

      if (window.soundFeedback) window.soundFeedback.cartSuccess();
      announce(`${session.kioskName}에 연결되었습니다. 원하시는 메뉴를 선택하시거나 마이크를 누르고 말씀해 주세요.`);

      // 4. 세션 WebSocket 연결 시도
      try {
        openSessionWebSocket(session.sessionId);
      } catch (wsErr) {
        console.warn('세션 WS 연결 무시:', wsErr);
      }

      // 5. 기존 카트 복원
      if (session.cart && session.cart.lines && session.cart.lines.length > 0) {
        state.cartItems = session.cart.lines.map(l => ({
          itemId: l.itemId,
          qty: l.qty,
          options: l.chosen ? l.chosen.reduce((acc, c) => ({ ...acc, [c.optionId]: c.choiceId }), {}) : {},
        }));
        updateCartUI(session.cart);
      }
    } catch (renderErr) {
      console.error('주문 화면 전환 오류:', renderErr);
      // 어떤 상황에서도 무조건 화면 전환 보장
      if (dom.galjidoDiscoveryView) dom.galjidoDiscoveryView.style.display = 'none';
      if (dom.galjidoOrderView) dom.galjidoOrderView.style.display = 'block';
    } finally {
      if (dom.btnConnectKiosk) {
        dom.btnConnectKiosk.disabled = false;
        dom.btnConnectKiosk.textContent = '연결하기';
      }
      if (dom.btnConfirmConnect) {
        dom.btnConfirmConnect.disabled = false;
      }
    }
  }

  // ==========================================
  // WebSocket 실시간 통신
  // ==========================================
  function openSessionWebSocket(sessionId) {
    if (state.sessionWs) {
      state.sessionWs.close();
    }

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ws/sessions/${sessionId}?token=${state.deviceToken}`;
    console.log('Connecting Phone Session WS:', wsUrl);

    state.sessionWs = new WebSocket(wsUrl);

    state.sessionWs.onopen = () => {
      console.log('Phone Session WS Connected');
    };

    state.sessionWs.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        console.log('Phone WS Event:', msg);
        handleSessionEvent(msg);
      } catch (err) {
        console.error('WS Parse Error:', err);
      }
    };

    state.sessionWs.onclose = () => {
      console.log('Phone Session WS Closed');
    };
  }

  function handleSessionEvent(msg) {
    switch (msg.type) {
      case 'cart':
        updateCartUI(msg);
        break;

      case 'ordered':
        handleOrderPlaced(msg);
        break;

      case 'order_status':
        handleOrderStatusChanged(msg.status);
        break;

      case 'help':
        showToast('직원 호출이 접수되었습니다. 곧 직원이 도착합니다.', 'info');
        break;

      case 'help_resolved':
        showToast('직원이 요청을 처리했습니다.', 'success');
        announce('직원 호출 처리가 완료되었습니다.');
        break;

      case 'ended':
        handleSessionEnded();
        break;
    }
  }

  // ==========================================
  // 매장 & 메뉴 렌더링
  // ==========================================
  function renderStoreInfo(store) {
    if (dom.connectionLabel) dom.connectionLabel.textContent = `${store.name} 📍`;
    if (dom.storeDescLine) dom.storeDescLine.textContent = `${store.address} • 무단차 접근 가능`;
  }

  function renderCategories(items) {
    const cats = new Set(['all']);
    items.forEach(i => {
      if (i.category) cats.add(i.category);
    });

    dom.categoryTabs.innerHTML = '';
    cats.forEach(cat => {
      const btn = document.createElement('button');
      btn.className = `cat-btn ${cat === state.selectedCategory ? 'active' : ''}`;
      btn.textContent = cat === 'all' ? '전체 메뉴' : cat;
      btn.onclick = () => {
        if (window.soundFeedback) window.soundFeedback.tick();
        state.selectedCategory = cat;
        document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        filterAndRenderMenu();
        announce(`${btn.textContent} 카테고리를 선택했습니다.`);
      };
      dom.categoryTabs.appendChild(btn);
    });
  }

  function filterAndRenderMenu() {
    const filtered = state.selectedCategory === 'all'
      ? state.menuItems
      : state.menuItems.filter(i => i.category === state.selectedCategory);
    renderMenuItems(filtered);
  }

  function renderMenuItems(items) {
    dom.menuItemsGrid.innerHTML = '';
    dom.menuCountBadge.textContent = `총 ${items.length}개`;

    // 최고급 상업용 메뉴 메타 정보 (실제 고해상도 제품 사진 매핑)
    const itemMeta = {
      'americano': { img: 'assets/menu/americano.jpg', badge: 'BEST', badgeClass: 'badge-best' },
      'cafe-latte': { img: 'assets/menu/cafe_latte.jpg', badge: 'POPULAR', badgeClass: 'badge-new' },
      'vanilla-latte': { img: 'assets/menu/vanilla_latte.jpg', badge: '추천', badgeClass: 'badge-best' },
      'grapefruit-ade': { img: 'assets/menu/grapefruit_ade.jpg', badge: 'SEASON', badgeClass: 'badge-new' },
      'lemon-tea': { img: 'assets/menu/lemon_tea.jpg', badge: 'HOT', badgeClass: 'badge-new' },
      'cookie': { img: 'assets/menu/cookie.jpg', badge: 'DESSERT', badgeClass: 'badge-best' },
    };

    items.forEach(item => {
      const meta = itemMeta[item.id] || { img: 'assets/menu/americano.jpg', badge: 'MENU', badgeClass: 'badge-new' };
      const isAvailable = item.available !== false;

      const card = document.createElement('article');
      card.className = `menu-card ${!isAvailable ? 'sold-out' : ''}`;
      if (!isAvailable) {
        card.style.opacity = '0.55';
      }
      card.setAttribute('role', 'listitem');
      card.setAttribute('tabindex', '0');
      card.setAttribute('aria-label', `${item.name}, ${isAvailable ? `가격 ${formatWon(item.price)}` : '품절된 상품'}. ${item.description || ''}`);

      const badgeHtml = !isAvailable
        ? `<span class="sb-badge" style="background:#fee2e2;color:#ef4444;font-weight:900;">품절</span>`
        : `<span class="sb-badge ${meta.badgeClass}">${meta.badge}</span>`;

      card.innerHTML = `
        <!-- 실사 제품 사진 썸네일 -->
        <div class="menu-item-media" aria-hidden="true" style="${!isAvailable ? 'filter:grayscale(90%); opacity:0.6;' : ''}">
          <img src="${meta.img}" alt="${item.name}" class="menu-item-img" loading="lazy" />
        </div>

        <!-- 메뉴 정보 바디 -->
        <div class="menu-card-body">
          <div class="menu-badge-row">
            ${badgeHtml}
          </div>
          <h3 class="menu-name" style="${!isAvailable ? 'text-decoration:line-through;color:var(--text-muted);' : ''}">${item.name}</h3>
          ${item.nameEn ? `<span class="menu-name-en">${item.nameEn}</span>` : ''}
          <p class="menu-desc">${item.description || '정성스럽게 준비한 메뉴입니다.'}</p>
          <div class="menu-price">${isAvailable ? formatWon(item.price) : '<span style="color:#ef4444;font-size:0.95rem;">품절</span>'}</div>
        </div>

        <!-- 우측 액션 버튼들 (현대적 SVG 아이콘) -->
        <div class="menu-card-right">
          <button class="btn-add-circle pick-btn" aria-label="${item.name} ${isAvailable ? '주문하기' : '품절됨'}" title="${isAvailable ? '옵션 선택 및 주문' : '품절된 상품'}" style="${!isAvailable ? 'background:#9ca3af;cursor:not-allowed;' : ''}">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
          </button>
          <button class="btn-tts-listen read-desc-btn" aria-label="${item.name} 음성 설명 듣기" title="음성 설명 듣기">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
              <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
            </svg>
          </button>
        </div>
      `;

      // 설명 듣기 버튼
      const readBtn = card.querySelector('.read-desc-btn');
      readBtn.onclick = (e) => {
        e.stopPropagation();
        if (window.soundFeedback) window.soundFeedback.tick();
        const statusDesc = isAvailable ? `가격은 ${formatWon(item.price)}입니다. 주문하시려면 플러스 버튼을 누르세요.` : '현재 품절된 상품입니다.';
        announce(`${item.name}. ${item.description || ''}. ${statusDesc}`);
      };

      // 선택 버튼 및 카드 클릭
      const selectAction = async () => {
        if (!isAvailable) {
          if (window.soundFeedback) window.soundFeedback.error();
          announce(`죄송합니다. ${item.name}은(는) 현재 품절되어 주문하실 수 없습니다.`);
          showToast(`${item.name}은(는) 현재 품절되었습니다.`, 'danger');
          return;
        }

        if (!state.sessionId) {
          announce('키오스크에 연결합니다...');
          showToast('키오스크 자동 연결 중...', 'info');
          try {
            await connectToKiosk();
          } catch (e) {
            return;
          }
        }
        openOptionModal(item);
      };

      card.querySelector('.pick-btn').onclick = (e) => {
        e.stopPropagation();
        selectAction();
      };

      card.onclick = () => selectAction();
      card.onkeydown = (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          selectAction();
        }
      };

      dom.menuItemsGrid.appendChild(card);
    });

    // 키오스크 디스플레이의 재고 관리자도 동기화
    renderKioskAvailabilityManager();
  }

  // ==========================================
  // 메뉴 옵션 선택 모달
  // ==========================================
  function openOptionModal(item, preselectedOptions = {}, preselectedQty = 1) {
    if (window.soundFeedback) window.soundFeedback.tick();

    state.currentMenuItem = item;
    state.pickedOptions = {};
    state.currentQty = preselectedQty;

    // 기본 옵션 세팅 (required 옵션의 첫 번째 choice를 기본 선택)
    const defs = item.options || [];
    defs.forEach(opt => {
      if (opt.type === 'single') {
        state.pickedOptions[opt.id] = preselectedOptions[opt.id] || (opt.choices[0] ? opt.choices[0].id : null);
      } else if (opt.type === 'multi') {
        state.pickedOptions[opt.id] = preselectedOptions[opt.id] || [];
      }
    });

    const metaImg = {
      'americano': 'assets/menu/americano.jpg',
      'cafe-latte': 'assets/menu/cafe_latte.jpg',
      'vanilla-latte': 'assets/menu/vanilla_latte.jpg',
      'grapefruit-ade': 'assets/menu/grapefruit_ade.jpg',
      'lemon-tea': 'assets/menu/lemon_tea.jpg',
      'cookie': 'assets/menu/cookie.jpg',
    }[item.id] || 'assets/menu/americano.jpg';

    if (dom.modalMenuImg) dom.modalMenuImg.src = metaImg;
    dom.modalMenuName.textContent = item.name;
    dom.modalMenuPrice.textContent = `기본 ${formatWon(item.price)}`;
    dom.modalQtyVal.textContent = state.currentQty;

    renderModalOptions(item);
    updateModalPriceCalculation();

    dom.optionModal.classList.add('open');
    dom.btnAddToCart.focus();

    // 옵션 설명 및 음성 마이크 자동 활성화
    const optGuide = defs.map(opt => `${opt.name}은 ${opt.choices.map(c => c.name).join(' 또는 ')}`).join(', ');
    const guideText = `${item.name} 옵션 창입니다. ${optGuide ? optGuide + ' 중 말씀하시거나, ' : ''}"담아줘"라고 말씀해 주세요.`;

    announce(guideText, {
      onEnd: () => {
        if (dom.optionModal.classList.contains('open') && window.speechService) {
          window.speechService.startListening();
        }
      }
    });
  }

  function closeOptionModal() {
    if (window.soundFeedback) window.soundFeedback.tick();
    dom.optionModal.classList.remove('open');
    state.currentMenuItem = null;
  }

  function renderModalOptions(item) {
    dom.modalOptionsBody.innerHTML = '';
    const defs = item.options || [];

    defs.forEach(opt => {
      const fieldset = document.createElement('fieldset');
      fieldset.className = 'option-group';

      const legend = document.createElement('legend');
      legend.className = 'option-group-legend';
      legend.innerHTML = `<span>${opt.name}</span> ${opt.required ? '<span style="color:var(--danger-color);font-size:0.8rem;">(필수)</span>' : '<span style="color:var(--text-muted);font-size:0.8rem;">(선택)</span>'}`;
      fieldset.appendChild(legend);

      const choicesGrid = document.createElement('div');
      choicesGrid.className = 'option-choices';

      opt.choices.forEach(choice => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'choice-btn';

        const isMulti = opt.type === 'multi';
        const isSelected = isMulti
          ? (state.pickedOptions[opt.id] || []).includes(choice.id)
          : state.pickedOptions[opt.id] === choice.id;

        if (isSelected) btn.classList.add('selected');

        const deltaText = choice.priceDelta > 0 ? `+${formatWon(choice.priceDelta)}` : '';
        btn.innerHTML = `
          <span>${choice.name}</span>
          ${deltaText ? `<span class="choice-price-delta">${deltaText}</span>` : ''}
        `;

        btn.onclick = () => {
          if (window.soundFeedback) window.soundFeedback.tick();
          if (isMulti) {
            let list = [...(state.pickedOptions[opt.id] || [])];
            if (list.includes(choice.id)) {
              list = list.filter(id => id !== choice.id);
            } else {
              const max = opt.maxChoices || opt.choices.length;
              if (list.length >= max) {
                showToast(`최대 ${max}개까지 선택 가능합니다.`, 'danger');
                return;
              }
              list.push(choice.id);
            }
            state.pickedOptions[opt.id] = list;
          } else {
            state.pickedOptions[opt.id] = choice.id;
          }

          renderModalOptions(item);
          updateModalPriceCalculation();
          announce(`${opt.name} ${choice.name} 선택됨.`);
        };

        choicesGrid.appendChild(btn);
      });

      fieldset.appendChild(choicesGrid);
      dom.modalOptionsBody.appendChild(fieldset);
    });
  }

  function updateModalPriceCalculation() {
    if (!state.currentMenuItem) return;

    let unit = state.currentMenuItem.price;
    const defs = state.currentMenuItem.options || [];

    defs.forEach(opt => {
      const picked = state.pickedOptions[opt.id];
      if (opt.type === 'single' && picked) {
        const found = opt.choices.find(c => c.id === picked);
        if (found) unit += found.priceDelta || 0;
      } else if (opt.type === 'multi' && Array.isArray(picked)) {
        picked.forEach(id => {
          const found = opt.choices.find(c => c.id === id);
          if (found) unit += found.priceDelta || 0;
        });
      }
    });

    const subtotal = unit * state.currentQty;
    dom.modalSubmitPrice.textContent = `장바구니 담기 (${formatWon(subtotal)})`;
  }

  async function handleAddToCartSubmit() {
    if (!state.currentMenuItem || !state.sessionId) return;

    const currentItem = state.currentMenuItem;
    const addedItemName = currentItem.name;

    // 옵션 유효성 검증
    const cleanOptions = {};
    for (const [key, val] of Object.entries(state.pickedOptions)) {
      if (Array.isArray(val) && val.length > 0) {
        cleanOptions[key] = val;
      } else if (typeof val === 'string' && val) {
        cleanOptions[key] = val;
      }
    }

    const newItem = {
      itemId: currentItem.id,
      qty: state.currentQty,
      options: cleanOptions,
    };

    // 동일한 메뉴 및 옵션을 가진 기존 항목이 있는지 검사
    const optionsEqual = (optA, optB) => {
      const keysA = Object.keys(optA || {}).sort();
      const keysB = Object.keys(optB || {}).sort();
      if (keysA.length !== keysB.length) return false;
      for (let i = 0; i < keysA.length; i++) {
        const k = keysA[i];
        if (k !== keysB[i]) return false;
        const vA = optA[k];
        const vB = optB[k];
        if (Array.isArray(vA) && Array.isArray(vB)) {
          if (vA.slice().sort().join(',') !== vB.slice().sort().join(',')) return false;
        } else if (vA !== vB) {
          return false;
        }
      }
      return true;
    };

    let nextCart = [];
    const existingIndex = state.cartItems.findIndex(
      item => item.itemId === currentItem.id && optionsEqual(item.options, cleanOptions)
    );

    if (existingIndex >= 0) {
      nextCart = state.cartItems.map((item, idx) => {
        if (idx === existingIndex) {
          return { ...item, qty: item.qty + state.currentQty };
        }
        return item;
      });
    } else {
      nextCart = [...state.cartItems, newItem];
    }

    try {
      dom.btnAddToCart.disabled = true;
      dom.btnAddToCart.textContent = '동기화 중...';

      let result;
      try {
        result = await api.updateCart(state.sessionId, nextCart);
      } catch (cartApiErr) {
        console.warn('서버 카트 동기화 실패 -> 로컬 계산으로 대체:', cartApiErr);
        const lines = nextCart.map(item => {
          const menuItem = state.menuItems.find(m => m.id === item.itemId) || {};
          let price = menuItem.price || 0;
          if (item.options && menuItem.options) {
            for (const [optId, choiceId] of Object.entries(item.options)) {
              const opt = menuItem.options.find(o => o.id === optId);
              if (opt) {
                const choice = (opt.choices || []).find(c => c.id === choiceId);
                if (choice && choice.priceDelta) price += choice.priceDelta;
              }
            }
          }
          return {
            itemId: item.itemId,
            qty: item.qty,
            unitPrice: price,
            lineTotal: price * item.qty,
            name: menuItem.name || item.itemId,
            options: item.options
          };
        });
        const total = lines.reduce((sum, l) => sum + l.lineTotal, 0);
        result = { lines, total, summary: lines.map(l => `${l.name} ${l.qty}개`).join(', ') };
      }

      state.cartItems = nextCart;
      updateCartUI(result);

      if (window.soundFeedback) window.soundFeedback.cartSuccess();
      closeOptionModal();
      announce(`${addedItemName}이(가) 장바구니에 담겼습니다. 현재 장바구니 총 ${formatWon(result.total)}입니다.`);
      showToast(`${addedItemName} 담기 완료`, 'success');
    } catch (err) {
      console.error('장바구니 업데이트 오류:', err);
      if (window.soundFeedback) window.soundFeedback.error();
      showToast(err.message || '장바구니에 담지 못했습니다.', 'danger');
      announce(`장바구니 추가 실패: ${err.message}`);
    } finally {
      dom.btnAddToCart.disabled = false;
    }
  }

  // ==========================================
  // 장바구니 UI 및 모달
  // ==========================================
  function updateCartUI(cartEvent) {
    state.cartTotal = cartEvent.total || 0;
    state.cartSummary = cartEvent.summary || '';

    const lines = cartEvent.lines || [];
    const count = lines.reduce((sum, l) => sum + (l.qty || 1), 0);

    // 상단 헤더 카트 배지 갱신
    if (dom.headerCartBadge) {
      dom.headerCartBadge.textContent = count;
      dom.headerCartBadge.style.display = count > 0 ? 'flex' : 'none';
    }

    // 하단 플로팅 바 갱신
    if (count > 0 && !state.currentOrder) {
      dom.floatingCart.classList.remove('hidden');
      dom.cartItemCount.textContent = `${count}`;
      dom.cartTotalAmount.textContent = formatWon(state.cartTotal);
    } else {
      dom.floatingCart.classList.add('hidden');
    }

    // 장바구니 모달 내용 갱신
    renderCartModalItems(lines);
    dom.cartModalTotalPrice.textContent = formatWon(state.cartTotal);
  }

  function renderCartModalItems(lines) {
    dom.cartItemsContainer.innerHTML = '';
    if (!lines || lines.length === 0) {
      dom.cartItemsContainer.innerHTML = '<div style="text-align:center;padding:24px;color:var(--text-muted);">장바구니가 비어 있습니다.</div>';
      dom.btnCheckoutSubmit.disabled = true;
      return;
    }

    dom.btnCheckoutSubmit.disabled = false;

    lines.forEach((line, index) => {
      const row = document.createElement('div');
      row.className = 'cart-item-row';

      const chosenTexts = (line.chosen || []).map(c => c.choiceName).join(', ');

      row.innerHTML = `
        <div class="cart-item-info">
          <span class="cart-item-title">${line.name}</span>
          ${chosenTexts ? `<span class="cart-item-options">${chosenTexts}</span>` : ''}
          <span class="cart-item-subtotal">${formatWon(line.subtotal)}</span>
        </div>
        <div style="display:flex;align-items:center;gap:6px;">
          <button class="step-btn cart-qty-minus" aria-label="${line.name} 수량 1 감소" style="width:36px;height:36px;font-size:1.1rem;padding:0;">−</button>
          <span style="font-weight:800;font-size:1.05rem;min-width:22px;text-align:center;">${line.qty}</span>
          <button class="step-btn cart-qty-plus" aria-label="${line.name} 수량 1 증가" style="width:36px;height:36px;font-size:1.1rem;padding:0;">＋</button>
          <button class="cart-delete-btn" aria-label="${line.name} 삭제">삭제</button>
        </div>
      `;

      // 수량 감소
      row.querySelector('.cart-qty-minus').onclick = async () => {
        if (window.soundFeedback) window.soundFeedback.tick();
        const nextItems = [...state.cartItems];
        if (nextItems[index].qty > 1) {
          nextItems[index] = { ...nextItems[index], qty: nextItems[index].qty - 1 };
        } else {
          nextItems.splice(index, 1);
        }
        try {
          const res = await api.updateCart(state.sessionId, nextItems);
          state.cartItems = nextItems;
          updateCartUI(res);
        } catch (e) {
          showToast('수량 변경 실패', 'danger');
        }
      };

      // 수량 증가
      row.querySelector('.cart-qty-plus').onclick = async () => {
        if (window.soundFeedback) window.soundFeedback.tick();
        const nextItems = [...state.cartItems];
        if (nextItems[index].qty < 10) {
          nextItems[index] = { ...nextItems[index], qty: nextItems[index].qty + 1 };
          try {
            const res = await api.updateCart(state.sessionId, nextItems);
            state.cartItems = nextItems;
            updateCartUI(res);
          } catch (e) {
            showToast('수량 변경 실패', 'danger');
          }
        }
      };

      // 삭제
      row.querySelector('.cart-delete-btn').onclick = async () => {
        if (window.soundFeedback) window.soundFeedback.tick();
        const nextItems = [...state.cartItems];
        nextItems.splice(index, 1);
        try {
          const res = await api.updateCart(state.sessionId, nextItems);
          state.cartItems = nextItems;
          updateCartUI(res);
          announce(`${line.name}을(를) 장바구니에서 삭제했습니다.`);
        } catch (err) {
          showToast('삭제 실패', 'danger');
        }
      };

      dom.cartItemsContainer.appendChild(row);
    });
  }

  function openCartModal() {
    if (window.soundFeedback) window.soundFeedback.tick();
    dom.cartModal.classList.add('open');
    dom.btnCheckoutSubmit.focus();
    const count = state.cartItems.reduce((sum, l) => sum + (l.qty || 1), 0);
    announce(
      `장바구니입니다. ${state.cartSummary || `${count}개 품목`}, 총 금액은 ${formatWon(state.cartTotal)}입니다. 결제하시려면 "주문하기" 또는 "카드로 결제", 닫으시려면 "닫기"라고 말씀하세요.`,
      {
        onEnd: () => {
          if (dom.cartModal.classList.contains('open') && window.speechService) {
            window.speechService.startListening();
          }
        }
      }
    );
  }

  function closeCartModal() {
    if (window.soundFeedback) window.soundFeedback.tick();
    dom.cartModal.classList.remove('open');
  }

  // ==========================================
  // 주문 제출 플로우 (note 필드 연동)
  // ==========================================
  async function submitOrder() {
    if (!state.sessionId || state.cartItems.length === 0) {
      announce('장바구니가 비어 있어 주문할 수 없습니다.');
      return;
    }

    const paymentInput = document.querySelector('input[name="paymentMethod"]:checked');
    const paymentMethod = paymentInput ? paymentInput.value : 'counter';
    const note = dom.cartOrderNote ? dom.cartOrderNote.value.trim() : '';

    try {
      dom.btnCheckoutSubmit.disabled = true;
      dom.btnCheckoutSubmit.textContent = '주문 접수 중...';

      let orderResult;
      try {
        orderResult = await api.placeOrder(state.sessionId, state.cartItems, paymentMethod, note);
      } catch (orderApiErr) {
        console.warn('서버 주문 접수 실패 -> 로컬 주문 완료 처리:', orderApiErr);
        orderResult = {
          orderId: 'ord-local-' + Date.now(),
          orderNumber: Math.floor(100 + Math.random() * 900),
          status: 'received',
          kioskName: 'GIST Cafe (키오스크 1)',
          lines: state.cartItems.map(item => {
            const m = state.menuItems.find(x => x.id === item.itemId) || {};
            return { itemId: item.itemId, name: m.name || item.itemId, qty: item.qty };
          }),
          total: state.cartTotal,
          paymentMethod,
          note
        };
      }

      state.currentOrder = orderResult;
      closeCartModal();
      dom.floatingCart.classList.add('hidden');

      handleOrderPlaced(orderResult);
    } catch (err) {
      console.error('주문 실패:', err);
      if (window.soundFeedback) window.soundFeedback.error();
      showToast(err.message || '주문 처리에 실패했습니다.', 'danger');
      announce(`주문 처리 중 오류가 발생했습니다: ${err.message}`);
    } finally {
      dom.btnCheckoutSubmit.disabled = false;
      dom.btnCheckoutSubmit.textContent = '주문 완료하기';
    }
  }

  function handleOrderPlaced(order) {
    state.currentOrder = order;

    // UI 섹션 전환: 메뉴 숨기고 주문 상태 카드 표시
    dom.menuSection.style.display = 'none';
    dom.orderStatusSection.style.display = 'flex';
    dom.liveOrderNumber.textContent = `#${order.orderNumber}`;

    // 요약 표시 (고객 요청사항 note 포함)
    dom.orderSummaryBox.innerHTML = `
      <div style="font-weight: 800; margin-bottom: 6px;">주문 품목 요약</div>
      <div>${order.summary || '주문 음료'}</div>
      ${order.note ? `<div style="margin-top:8px;padding:6px 12px;background:var(--sb-mint-subtle);border:1px solid var(--sb-mint);border-radius:6px;font-size:0.85rem;color:var(--sb-green);font-weight:800;">📝 고객 요청사항: ${order.note}</div>` : ''}
      <div style="margin-top: 8px; font-weight: 800; color: var(--sb-green);">결제 금액: ${formatWon(order.total)} (${order.paymentMethod === 'counter' ? '카운터 결제' : '키오스크 결제'})</div>
    `;

    updateTrackerStep('submitted');

    if (window.soundFeedback) window.soundFeedback.orderSuccess();

    const paymentDesc = order.paymentMethod === 'counter' ? '카운터에서 결제해 주세요.' : '키오스크 카드리더기에 카드를 넣어주세요.';
    const speech = `주문이 접수되었습니다! 고객님의 주문 번호는 ${order.orderNumber}번입니다. ${paymentDesc} 음료가 준비되면 음성으로 안내해 드립니다.`;
    announce(speech, { priority: 'high' });
    showToast(`주문 번호 #${order.orderNumber} 접수 완료`, 'success');
  }

  function handleOrderStatusChanged(status) {
    updateTrackerStep(status);
    if (window.soundFeedback) window.soundFeedback.statusChange();

    let text = '';
    switch (status) {
      case 'accepted':
        dom.orderStatusAnnouncement.textContent = '매장에서 주문을 접수하였습니다.';
        dom.orderStatusDesc.textContent = '바리스타가 곧 음료 제조를 시작합니다.';
        text = '주문이 접수되었습니다.';
        dom.btnCancelOrder.style.display = 'none'; // 접수 후에는 취소 불가
        break;
      case 'preparing':
        dom.orderStatusAnnouncement.textContent = '음료를 정성껏 제조 중입니다.';
        dom.orderStatusDesc.textContent = '잠시만 기다려 주시면 픽업대로 안내해 드립니다.';
        text = '음료가 제조 중입니다.';
        break;
      case 'ready':
        dom.orderStatusAnnouncement.textContent = '음료가 준비되었습니다!';
        dom.orderStatusDesc.textContent = '픽업대에서 주문 번호를 확인하시고 음료를 수령해 주세요.';
        text = '음료가 준비되었습니다! 픽업대에서 수령해 주세요.';
        break;
      case 'picked_up':
        dom.orderStatusAnnouncement.textContent = '수령이 완료되었습니다. 감사합니다!';
        dom.orderStatusDesc.textContent = '즐거운 시간 되세요.';
        text = '음료 수령이 완료되었습니다. 이용해 주셔서 감사합니다.';
        break;
      case 'cancelled':
        dom.orderStatusAnnouncement.textContent = '주문이 취소되었습니다.';
        dom.orderStatusDesc.textContent = '';
        text = '주문이 취소되었습니다.';
        break;
    }

    announce(text, { priority: 'high' });
    showToast(text, status === 'ready' ? 'success' : 'info');
  }

  function updateTrackerStep(status) {
    const steps = ['submitted', 'accepted', 'preparing', 'ready'];
    const idx = steps.indexOf(status);

    steps.forEach((s, i) => {
      const el = dom[`step${s.charAt(0).toUpperCase() + s.slice(1)}`];
      if (el) {
        if (i <= idx) {
          el.classList.add('active');
        } else {
          el.classList.remove('active');
        }
      }
    });
  }

  async function cancelCurrentOrder() {
    if (!state.currentOrder) return;
    try {
      if (window.soundFeedback) window.soundFeedback.tick();
      await api.cancelOrder(state.currentOrder.orderId);
      announce('주문이 정상적으로 취소되었습니다.');
      showToast('주문 취소 완료', 'info');
      resetToNewOrder();
    } catch (err) {
      if (window.soundFeedback) window.soundFeedback.error();
      showToast(err.message || '취소할 수 없습니다.', 'danger');
      announce(`주문 취소 실패: ${err.message}`);
    }
  }

  function resetToNewOrder() {
    state.currentOrder = null;
    state.cartItems = [];
    state.cartTotal = 0;
    state.cartSummary = '';
    dom.orderStatusSection.style.display = 'none';
    dom.menuSection.style.display = 'block';
    dom.btnCancelOrder.style.display = 'inline-block';
    updateCartUI({ lines: [], total: 0, summary: '' });
    announce('새 주문을 시작합니다. 원하시는 메뉴를 선택해 주세요.');
  }

  async function handleSessionEnded() {
    state.sessionId = null;
    state.proximity.status = 'scanning';
    state.proximity.awaitingConfirmation = false;
    if (dom.connectionDot) dom.connectionDot.className = 'status-dot';
    if (dom.galjidoDiscoveryView) dom.galjidoDiscoveryView.style.display = 'flex';
    if (dom.galjidoOrderView) dom.galjidoOrderView.style.display = 'none';
    if (dom.detectedStorePopup) dom.detectedStorePopup.style.display = 'none';
    if (dom.menuSection) dom.menuSection.style.display = 'none';
    if (dom.orderStatusSection) dom.orderStatusSection.style.display = 'none';
    if (dom.floatingCart) dom.floatingCart.classList.add('hidden');
    announce('키오스크 연결이 종료되었습니다. 주위 매장을 다시 탐색합니다.');
  }

  // ==========================================
  // 직원 호출
  // ==========================================
  async function callHelp() {
    if (window.soundFeedback) window.soundFeedback.callStaff();

    if (!state.sessionId) {
      announce('매장 직원에게 도움을 요청했습니다. 곧 직원이 오겠습니다.');
      showToast('직원 호출 완료', 'success');
      return;
    }

    try {
      await api.callHelp(state.sessionId);
      announce('매장 직원에게 도움을 요청했습니다. 직원이 곧 찾아옵니다. 잠시만 기다려 주세요.', { priority: 'high' });
      showToast('직원 호출이 전달되었습니다.', 'success');
    } catch (err) {
      console.error('직원 호출 오류:', err);
      announce('직원 호출 중 문제가 발생했습니다. 주변 직원에게 직접 문의해 주세요.');
    }
  }

  // ==========================================
  // 키오스크 디스플레이 시뮬레이터 (매장 화면)
  // ==========================================
  function initKioskSimulator() {
    // 1. 하트비트 주기적 호출 (토큰 자동 갱신)
    const runHeartbeat = async () => {
      try {
        const hb = await api.kioskHeartbeat();
        dom.kioskBleTokenBadge.textContent = `BLE Token: ${hb.token} (유효: ${Math.round(hb.expiresAtMs / 1000 % 1000)}s)`;
      } catch (err) {
        console.warn('Kiosk Heartbeat error:', err);
      }
    };

    runHeartbeat();
    setInterval(runHeartbeat, 25000);

    // 2. 키오스크 웹소켓 연결
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ws/kiosk?token=${state.kioskKey}`;
    try {
      state.kioskWs = new WebSocket(wsUrl);
      state.kioskWs.onopen = () => console.log('Kiosk Screen WS Connected');
      state.kioskWs.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          handleKioskScreenEvent(msg);
        } catch (err) { }
      };
    } catch (e) {
      console.warn('Kiosk WS error:', e);
    }

    // 3. 키오스크 주문 필터 버튼 이벤트 바인딩
    if (dom.kioskOrdersFilter) {
      dom.kioskOrdersFilter.querySelectorAll('.filter-chip').forEach(btn => {
        btn.onclick = () => {
          dom.kioskOrdersFilter.querySelectorAll('.filter-chip').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          state.kioskOrderFilter = btn.dataset.filter || '';
          refreshKioskOrders();
        };
      });
    }

    // 4. 키오스크 주문 목록 불러오기
    refreshKioskOrders();
  }

  function handleKioskScreenEvent(msg) {
    console.log('Kiosk Screen Event:', msg);
    if (msg.type === 'connected') {
      dom.kioskCartHeader.textContent = '스마트폰 연결됨 - 주문 진행 중';
      dom.kioskCartContent.innerHTML = '<span style="color:#60a5fa;">고객님이 스마트폰으로 메뉴를 고르고 있습니다...</span>';
      if (dom.btnKioskEndSession) {
        dom.btnKioskEndSession.style.display = 'inline-block';
        dom.btnKioskEndSession.onclick = async () => {
          if (confirm('스마트폰 고객 연결을 강제 종료하시겠습니까? (POST /kiosk/sessions/{id}/end)')) {
            try {
              const targetSession = msg.sessionId || state.sessionId;
              await api.kioskEndSession(targetSession);
              showToast('키오스크에서 고객 세션을 종료했습니다.', 'info');
            } catch (err) {
              showToast('세션 종료 실패: ' + err.message, 'danger');
            }
          }
        };
      }
    } else if (msg.type === 'cart') {
      dom.kioskCartHeader.textContent = `실시간 장바구니 (${formatWon(msg.total)})`;
      if (!msg.lines || msg.lines.length === 0) {
        dom.kioskCartContent.innerHTML = '<span>장바구니가 비어 있습니다.</span>';
      } else {
        dom.kioskCartContent.innerHTML = `
          <div style="width:100%;text-align:left;">
            <div style="font-weight:bold;margin-bottom:8px;color:#fbbf24;">고객 선택 품목:</div>
            ${msg.lines.map(l => `<div style="padding:4px 0;border-bottom:1px solid #374151;">${l.name} × ${l.qty} (${formatWon(l.subtotal)})</div>`).join('')}
            <div style="font-weight:bold;margin-top:8px;text-align:right;color:#60a5fa;">총 합계: ${formatWon(msg.total)}</div>
          </div>
        `;
      }
    } else if (msg.type === 'ordered') {
      dom.kioskCartHeader.textContent = '주문 완료됨';
      dom.kioskCartContent.innerHTML = `<span style="color:#34d399;font-weight:bold;">새로운 주문 #${msg.orderNumber} 접수됨!</span>`;
      if (dom.btnKioskEndSession) dom.btnKioskEndSession.style.display = 'none';
      refreshKioskOrders();
    } else if (msg.type === 'order_status') {
      refreshKioskOrders();
    } else if (msg.type === 'help') {
      // 키오스크 화면 직원 호출 알림 표시 (resolve-help 연동)
      if (dom.kioskHelpAlertBox) {
        dom.kioskHelpAlertBox.style.display = 'block';
        if (dom.kioskHelpAlertText) {
          dom.kioskHelpAlertText.textContent = `스마트폰 고객님이 도움을 요청하셨습니다. (세션: ${msg.sessionId || state.sessionId || '현재 세션'})`;
        }
        if (dom.btnResolveHelp) {
          dom.btnResolveHelp.onclick = async () => {
            try {
              const targetSession = msg.sessionId || state.sessionId;
              await api.resolveHelp(targetSession);
              dom.kioskHelpAlertBox.style.display = 'none';
              showToast('도움 요청을 완료 처리했습니다.', 'success');
            } catch (err) {
              showToast('처리 실패: ' + err.message, 'danger');
            }
          };
        }
      }
    } else if (msg.type === 'help_resolved') {
      if (dom.kioskHelpAlertBox) dom.kioskHelpAlertBox.style.display = 'none';
    } else if (msg.type === 'ended') {
      dom.kioskCartHeader.textContent = '스마트폰 연결 대기 중';
      dom.kioskCartContent.textContent = '고객님이 스마트폰 앱에서 장바구니에 담은 항목이 이곳에 실시간으로 표시됩니다.';
      if (dom.btnKioskEndSession) dom.btnKioskEndSession.style.display = 'none';
    }
  }

  async function refreshKioskOrders() {
    try {
      const orders = await api.getKioskOrders(state.kioskOrderFilter || null);
      renderKioskOrders(orders);
    } catch (err) {
      console.warn('Kiosk orders fetch error:', err);
    }
  }

  function renderKioskOrders(orders) {
    dom.kioskOrdersList.innerHTML = '';
    if (!orders || orders.length === 0) {
      dom.kioskOrdersList.innerHTML = '<div style="text-align: center; color: #6b7280; padding: 24px;">접수된 주문이 없습니다.</div>';
      return;
    }

    orders.forEach(ord => {
      const card = document.createElement('div');
      card.className = 'kiosk-order-card';

      const statusKo = {
        submitted: '접수 대기',
        accepted: '주문 접수',
        preparing: '음료 제조 중',
        ready: '준비 완료',
        picked_up: '수령 완료',
        cancelled: '취소됨',
      }[ord.status] || ord.status;

      card.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
          <div>
            <span style="font-size:1.4rem;font-weight:900;color:#fbbf24;">#${ord.orderNumber}</span>
            <span style="font-size:0.85rem;margin-left:8px;color:#9ca3af;">${ord.summary}</span>
            ${ord.note ? `<div style="background:#451a03;color:#fbbf24;padding:4px 8px;border-radius:4px;font-size:0.8rem;margin-top:6px;font-weight:bold;">📝 요청사항: ${ord.note}</div>` : ''}
          </div>
          <span style="background:#374151;color:#60a5fa;padding:3px 8px;border-radius:4px;font-size:0.8rem;font-weight:bold;">${statusKo}</span>
        </div>
        <div class="kiosk-staff-actions" style="margin-top:8px;">
          <button class="staff-btn" data-status="accepted">1. 접수</button>
          <button class="staff-btn" data-status="preparing">2. 제조 시작</button>
          <button class="staff-btn" data-status="ready">3. 준비 완료</button>
          <button class="staff-btn" data-status="picked_up">4. 수령 완료</button>
        </div>
      `;

      card.querySelectorAll('.staff-btn').forEach(btn => {
        btn.onclick = async () => {
          const newStatus = btn.dataset.status;
          try {
            await api.updateOrderStatus(ord.orderId, newStatus);
            showToast(`주문 #${ord.orderNumber} 상태를 '${newStatus}'로 변경했습니다.`, 'info');
            refreshKioskOrders();
          } catch (err) {
            showToast('상태 변경 실패: ' + err.message, 'danger');
          }
        };
      });

      dom.kioskOrdersList.appendChild(card);
    });
  }

  // 매장 메뉴 품절 관리자 (PUT /kiosk/menu/{itemId}/availability)
  function renderKioskAvailabilityManager() {
    if (!dom.kioskAvailabilityList) return;
    dom.kioskAvailabilityList.innerHTML = '';

    state.menuItems.forEach(item => {
      const isAvailable = item.available !== false;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'staff-btn';
      btn.style.background = isAvailable ? '#065f46' : '#7f1d1d';
      btn.style.color = '#ffffff';
      btn.style.display = 'flex';
      btn.style.justifyContent = 'space-between';
      btn.style.alignItems = 'center';
      btn.style.padding = '8px 10px';

      btn.innerHTML = `
        <span style="font-size:0.85rem;">${item.name}</span>
        <span style="font-weight:900;margin-left:6px;font-size:0.75rem;">${isAvailable ? '판매 중' : '품절'}</span>
      `;

      btn.onclick = async () => {
        try {
          const nextState = !isAvailable;
          await api.setItemAvailability(item.id, nextState);
          item.available = nextState;
          showToast(`${item.name} 상태를 '${nextState ? '판매 중' : '품절'}'(으)로 변경했습니다.`, 'info');
          renderKioskAvailabilityManager();
          filterAndRenderMenu();
        } catch (err) {
          showToast('상태 변경 실패: ' + err.message, 'danger');
        }
      };

      dom.kioskAvailabilityList.appendChild(btn);
    });
  }

  // ==========================================
  // 음성 인식 & 자연어 명령 처리 (Speech)
  // ==========================================
  function setupSpeechIntegration() {
    if (!window.speechService) return;

    // 1. 마이크 상태 변화 콜백
    window.speechService.onStatusChangeCallback = ({ listening, text }) => {
      if (listening) {
        dom.btnVoiceMic.classList.add('listening');
        dom.voiceStatusLabel.textContent = text;
      } else {
        dom.btnVoiceMic.classList.remove('listening');
        dom.voiceStatusLabel.textContent = text || '음성 주문 대기 중';
      }
    };

    // 2. 음성 명령 콜백
    window.speechService.onCommandCallback = (cmd, rawText) => {
      handleVoiceCommand(cmd, rawText);
    };

    // 3. 마이크 버튼 클릭 이벤트
    dom.btnVoiceMic.onclick = () => {
      window.speechService.toggleListening();
    };
  }

  function handleVoiceCommand(cmd, rawText) {
    console.log('Voice Command Triggered:', cmd, 'raw:', rawText);

    // 1. 옵션 모달이 열려 있는 경우: 옵션 변경, 수량, 담기, 취소 처리
    if (dom.optionModal && dom.optionModal.classList.contains('open')) {
      if (cmd.action === 'ADD_TO_CART') {
        if (cmd.options && Object.keys(cmd.options).length > 0) {
          applyOptionModalVoice(cmd, rawText, false);
        }
        if (cmd.qty) {
          state.currentQty = cmd.qty;
        }
        handleAddToCartSubmit();
        return;
      }

      if (cmd.action === 'SELECT_OPTION') {
        applyOptionModalVoice(cmd, rawText, true);
        return;
      }

      if (cmd.action === 'SUBMIT_ORDER') {
        // 옵션 선택 창에서 "주문" 또는 "결제"를 말하면 담기 후 진행
        handleAddToCartSubmit();
        return;
      }

      if (cmd.action === 'CANCEL_OR_BACK') {
        closeOptionModal();
        announce('메뉴 선택을 취소했습니다.');
        return;
      }

      // 옵션 모달 오픈 중이지만 기타 발화(예: "따뜻하게 해줘", "라지로 해줘" 등) 2차 파싱
      if (applyOptionModalVoice(cmd, rawText, true)) {
        return;
      }
    }

    // 2. 장바구니 모달이 열려 있는 경우: 결제 수단 선택, 주문 제출, 닫기
    if (dom.cartModal && dom.cartModal.classList.contains('open')) {
      if (cmd.action === 'SUBMIT_ORDER') {
        if (cmd.paymentMethod) {
          const radio = document.querySelector(`input[name="paymentMethod"][value="${cmd.paymentMethod}"]`);
          if (radio) radio.checked = true;
        }
        submitOrder();
        return;
      }

      if (cmd.action === 'SELECT_PAYMENT') {
        const radio = document.querySelector(`input[name="paymentMethod"][value="${cmd.method}"]`);
        if (radio) radio.checked = true;
        const methodKr = cmd.method === 'kiosk' ? '카드 결제' : '카운터 결제';
        announce(`${methodKr}가 선택되었습니다. "주문하기"라고 말씀하시면 주문이 완료됩니다.`, {
          onEnd: () => {
            if (dom.cartModal.classList.contains('open') && window.speechService) {
              window.speechService.startListening();
            }
          }
        });
        return;
      }

      if (cmd.action === 'CANCEL_OR_BACK') {
        closeCartModal();
        announce('장바구니 창을 닫았습니다.');
        return;
      }
    }

    // 3. 일반 화면 음성 명령 분기
    switch (cmd.action) {
      case 'CONFIRM_CONNECT':
      case 'CONNECT_KIOSK':
        if (state.proximity.awaitingConfirmation || !state.sessionId) {
          confirmAndConnectToStore();
        } else {
          announce('이미 매장에 연결되어 있습니다. 원하시는 메뉴를 말씀해 주세요.');
        }
        break;

      case 'REJECT_CONNECT':
        if (state.proximity.awaitingConfirmation) {
          rejectStoreConnection();
        } else {
          announce('요청을 취소했습니다.');
        }
        break;

      case 'ORDER_ITEM':
        handleVoiceOrderItem(cmd);
        break;

      case 'ADD_TO_CART':
        announce('원하시는 메뉴를 말씀해 주세요. 예시: "아메리카노 담아줘"');
        break;

      case 'SELECT_OPTION':
        announce('먼저 원하시는 메뉴를 선택해 주세요. 예시: "아메리카노"');
        break;

      case 'VIEW_CART':
        openCartModal();
        break;

      case 'SUBMIT_ORDER':
        if (dom.cartModal.classList.contains('open')) {
          submitOrder();
        } else if (state.cartItems.length > 0) {
          openCartModal();
        } else {
          announce('장바구니가 비어 있습니다. 먼저 메뉴를 담아주세요.');
        }
        break;

      case 'CALL_HELP':
        callHelp();
        break;

      case 'REPEAT':
        window.speechService.repeatLast();
        break;

      case 'TOGGLE_HIGH_CONTRAST':
        toggleHighContrast();
        break;

      case 'INCREASE_FONT':
        cycleFontSize();
        break;

      case 'RESET_FONT':
        state.fontSizeLevel = 0;
        applyFontSize();
        break;

      case 'CANCEL_OR_BACK':
        if (dom.optionModal.classList.contains('open')) {
          closeOptionModal();
          announce('메뉴 선택을 취소했습니다.');
        } else if (dom.cartModal.classList.contains('open')) {
          closeCartModal();
          announce('장바구니 창을 닫았습니다.');
        } else if (state.currentOrder && dom.btnCancelOrder.style.display !== 'none') {
          cancelCurrentOrder();
        }
        break;

      case 'READ_MENU':
        const names = state.menuItems.map(i => `${i.name} ${formatWon(i.price)}`).join(', ');
        announce(`오늘의 메뉴입니다: ${names}. 원하시는 메뉴를 말씀해 주세요.`);
        break;

      case 'OPEN_INDOOR_GUIDE':
        openIndoorGuideModal();
        break;

      case 'OPEN_STORE_SELECT':
        openStoreSelectModal();
        break;

      case 'END_SESSION':
        if (state.sessionId) {
          api.endSession(state.sessionId).catch(() => {});
          handleSessionEnded();
        } else {
          announce('현재 연결된 키오스크가 없습니다.');
        }
        break;

      default:
        announce(`"${rawText}" 명령을 이해하지 못했습니다. "아메리카노", "장바구니 확인", "직원 호출" 등을 말씀해 보세요.`);
        break;
    }
  }

  // 부가 옵션 모달 내 음성 인식 처리기
  function applyOptionModalVoice(cmd, rawText, shouldAnnounce = true) {
    const item = state.currentMenuItem;
    if (!item) return false;

    let changedDescriptions = [];
    const text = (rawText || '').toLowerCase();

    // 1. 수량 조절
    if (cmd && cmd.qty) {
      state.currentQty = cmd.qty;
      changedDescriptions.push(`수량 ${state.currentQty}개`);
    } else if (cmd && cmd.qtyDelta) {
      state.currentQty = Math.max(1, state.currentQty + cmd.qtyDelta);
      changedDescriptions.push(`수량 ${state.currentQty}개`);
    } else {
      if (text.includes('1개') || text.includes('1잔') || text.includes('한 개') || text.includes('한 잔') || text.includes('하나만')) {
        state.currentQty = 1;
        changedDescriptions.push('수량 1개');
      } else if (text.includes('2개') || text.includes('2잔') || text.includes('두 개') || text.includes('두 잔') || text.includes('둘')) {
        state.currentQty = 2;
        changedDescriptions.push('수량 2개');
      } else if (text.includes('3개') || text.includes('3잔') || text.includes('세 개') || text.includes('세 잔')) {
        state.currentQty = 3;
        changedDescriptions.push('수량 3개');
      } else if (text.includes('4개') || text.includes('4잔') || text.includes('네 개') || text.includes('네 잔')) {
        state.currentQty = 4;
        changedDescriptions.push('수량 4개');
      } else if (text.includes('더 줘') || text.includes('늘려') || text.includes('하나 더')) {
        state.currentQty += 1;
        changedDescriptions.push(`수량 ${state.currentQty}개`);
      } else if (text.includes('줄여') || text.includes('하나 빼')) {
        state.currentQty = Math.max(1, state.currentQty - 1);
        changedDescriptions.push(`수량 ${state.currentQty}개`);
      }
    }
    if (dom.modalQtyVal) dom.modalQtyVal.textContent = state.currentQty;

    // 2. 부가 옵션 매핑
    const options = (cmd && cmd.options) ? cmd.options : {};
    const defs = item.options || [];

    defs.forEach(opt => {
      if (opt.type === 'single') {
        let targetChoiceId = options[opt.id];

        if (!targetChoiceId) {
          if (opt.id === 'temp') {
            if (text.includes('따뜻') || text.includes('뜨거') || text.includes('핫') || text.includes('hot')) targetChoiceId = 'hot';
            if (text.includes('아이스') || text.includes('차갑') || text.includes('시원') || text.includes('ice') || text.includes('얼음')) targetChoiceId = 'ice';
          } else if (opt.id === 'size') {
            if (text.includes('라지') || text.includes('큰') || text.includes('large') || text.includes('사이즈 업')) targetChoiceId = 'large';
            if (text.includes('레귤러') || text.includes('보통') || text.includes('기본') || text.includes('regular') || text.includes('작은')) targetChoiceId = 'regular';
          } else if (opt.id === 'milk') {
            if (text.includes('오트') || text.includes('귀리')) targetChoiceId = 'oat';
            if (text.includes('일반')) targetChoiceId = 'regular';
          } else if (opt.id === 'whip') {
            if (text.includes('휘핑 빼') || text.includes('크림 빼')) targetChoiceId = 'without';
            else if (text.includes('휘핑') || text.includes('크림')) targetChoiceId = 'with';
          } else if (opt.id === 'warm') {
            if (text.includes('데워') || text.includes('데우')) targetChoiceId = 'yes';
          }

          if (!targetChoiceId) {
            opt.choices.forEach(c => {
              if (text.includes(c.name.toLowerCase())) targetChoiceId = c.id;
            });
          }
        }

        if (targetChoiceId) {
          const choice = opt.choices.find(c => c.id === targetChoiceId);
          if (choice) {
            state.pickedOptions[opt.id] = choice.id;
            changedDescriptions.push(`${opt.name} ${choice.name}`);
          }
        }
      } else if (opt.type === 'multi') {
        opt.choices.forEach(c => {
          let matched = false;
          if (c.id === 'shot' && (text.includes('샷') || text.includes('샷추가'))) matched = true;
          if (c.id === 'decaf' && (text.includes('디카') || text.includes('디카페인'))) matched = true;
          if (text.includes(c.name.toLowerCase())) matched = true;

          if (matched) {
            let list = [...(state.pickedOptions[opt.id] || [])];
            if (!list.includes(c.id)) {
              list.push(c.id);
              state.pickedOptions[opt.id] = list;
              changedDescriptions.push(c.name);
            }
          }
        });
      }
    });

    renderModalOptions(item);
    updateModalPriceCalculation();

    if (changedDescriptions.length > 0) {
      if (shouldAnnounce) {
        announce(`${changedDescriptions.join(', ')} 선택되었습니다. 담으시려면 "담아줘"라고 말씀해 주세요.`, {
          onEnd: () => {
            if (dom.optionModal.classList.contains('open') && window.speechService) {
              window.speechService.startListening();
            }
          }
        });
      }
      return true;
    }

    return false;
  }

  function handleVoiceOrderItem(cmd) {
    if (!state.sessionId) {
      announce('먼저 키오스크에 연결해야 주문할 수 있습니다. 키오스크에 연결합니다.');
      connectToKiosk();
      return;
    }

    const item = state.menuItems.find(i => i.id === cmd.menuId);
    if (!item) {
      announce('해당 메뉴를 찾을 수 없습니다.');
      return;
    }

    // 옵션 검사: 필수 옵션이 모두 충족되었는지 확인
    const defs = item.options || [];
    const missingRequired = defs.some(opt => opt.required && !cmd.options[opt.id]);

    if (missingRequired) {
      // 필수 옵션이 부족하면 모달을 열어 안내
      openOptionModal(item, cmd.options, cmd.qty || 1);
      announce(`${item.name}의 옵션을 선택해 주세요. 온도와 크기 등을 말씀하시거나 화면에서 터치하세요.`);
    } else {
      // 필수 옵션이 모두 주어졌거나 기본값이 채워진 경우 바로 장바구니에 담기
      openOptionModal(item, cmd.options, cmd.qty || 1);
      setTimeout(() => {
        handleAddToCartSubmit();
      }, 300);
    }
  }

  // ==========================================
  // 접근성 도구 (고대비, 글자 크기, 음성 토글)
  // ==========================================
  function setupAccessibilityControls() {
    // 1. 고대비 모드 토글
    dom.btnHighContrast.onclick = () => toggleHighContrast();

    // 2. 글자 크기 변경
    dom.btnFontSize.onclick = () => cycleFontSize();

    // 3. TTS 음성 안내 토글
    dom.btnTtsToggle.onclick = () => {
      state.ttsEnabled = !state.ttsEnabled;
      dom.btnTtsToggle.classList.toggle('active', state.ttsEnabled);
      dom.btnTtsToggle.setAttribute('aria-pressed', state.ttsEnabled);
      dom.ttsStatusText.textContent = state.ttsEnabled ? '음성 켜짐' : '음성 꺼짐';
      window.speechService.setTtsEnabled(state.ttsEnabled);
      if (window.soundFeedback) window.soundFeedback.tick();
    };

    // 4. 다시 듣기
    dom.btnRepeatVoice.onclick = () => {
      if (window.soundFeedback) window.soundFeedback.tick();
      window.speechService.repeatLast();
    };

    // 5. 키보드 단축키
    window.addEventListener('keydown', (e) => {
      // Input 필드 입력 중에는 단축키 무시
      if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;

      if (e.key === ' ' || e.key.toLowerCase() === 'm') {
        // Space 또는 M: 마이크 토글
        e.preventDefault();
        window.speechService.toggleListening();
      } else if (e.key.toLowerCase() === 'r') {
        // R: 다시 듣기
        e.preventDefault();
        window.speechService.repeatLast();
      } else if (e.altKey && e.key.toLowerCase() === 'c') {
        // Alt + C: 고대비 토글
        e.preventDefault();
        toggleHighContrast();
      } else if (e.key.toLowerCase() === 'h') {
        // H: 직원 호출
        e.preventDefault();
        callHelp();
      } else if (e.key === 'Escape') {
        // Esc: 모달 닫기
        if (dom.optionModal.classList.contains('open')) closeOptionModal();
        if (dom.cartModal.classList.contains('open')) closeCartModal();
      }
    });
  }

  function toggleHighContrast() {
    state.highContrast = !state.highContrast;
    document.body.classList.toggle('high-contrast', state.highContrast);
    dom.btnHighContrast.classList.toggle('active', state.highContrast);
    dom.btnHighContrast.setAttribute('aria-pressed', state.highContrast);
    dom.contrastText.textContent = state.highContrast ? '고대비 끄기' : '고대비 켜기';
    if (window.soundFeedback) window.soundFeedback.tick();
    announce(state.highContrast ? '고대비 모드가 켜졌습니다.' : '고대비 모드가 꺼졌습니다.');
  }

  function cycleFontSize() {
    state.fontSizeLevel = (state.fontSizeLevel + 1) % 3;
    applyFontSize();
    if (window.soundFeedback) window.soundFeedback.tick();
  }

  function applyFontSize() {
    document.body.classList.remove('font-large', 'font-xlarge');
    if (state.fontSizeLevel === 1) {
      document.body.classList.add('font-large');
      dom.fontSizeText.textContent = '글자 아주 크게';
      announce('글자 크기를 크게 설정했습니다.');
    } else if (state.fontSizeLevel === 2) {
      document.body.classList.add('font-xlarge');
      dom.fontSizeText.textContent = '글자 기본';
      announce('글자 크기를 아주 크게 설정했습니다.');
    } else {
      dom.fontSizeText.textContent = '글자 크게';
      announce('글자 크기를 기본으로 설정했습니다.');
    }
  }

  // ==========================================
  // 뷰 모드 탭 (고객 모바일 / 키오스크 / 분할 시연)
  // ==========================================
  function setupViewModeTabs() {
    const tabs = [
      { btn: dom.tabPhone, mode: 'phone' },
      { btn: dom.tabKiosk, mode: 'kiosk' },
      { btn: dom.tabSplit, mode: 'split' },
    ];

    tabs.forEach(({ btn, mode }) => {
      btn.onclick = () => {
        if (window.soundFeedback) window.soundFeedback.tick();
        tabs.forEach(t => {
          t.btn.classList.remove('active');
          t.btn.setAttribute('aria-selected', 'false');
        });
        btn.classList.add('active');
        btn.setAttribute('aria-selected', 'true');
        setViewMode(mode);
      };
    });
  }

  function setViewMode(mode) {
    state.currentView = mode;
    dom.viewsContainer.className = `views-wrapper mode-${mode}`;

    if (mode === 'phone') {
      dom.phoneView.style.display = 'flex';
      dom.kioskView.style.display = 'none';
      announce('스마트폰 고객 주문 화면으로 전환했습니다.');
    } else if (mode === 'kiosk') {
      dom.phoneView.style.display = 'none';
      dom.kioskView.style.display = 'flex';
      announce('매장 키오스크 화면으로 전환했습니다.');
    } else if (mode === 'split') {
      dom.phoneView.style.display = 'flex';
      dom.kioskView.style.display = 'flex';
      announce('스마트폰과 키오스크 동시 시연 화면으로 전환했습니다.');
    }
  }

  // ==========================================
  // 모달 및 기본 이벤트 바인딩
  // ==========================================
  function setupModalsAndEvents() {
    // 키오스크 연결 버튼 (가드 처리)
    if (dom.btnConnectKiosk) dom.btnConnectKiosk.onclick = () => connectToKiosk();

    // 세션 종료 버튼
    if (dom.btnEndSession) {
      dom.btnEndSession.onclick = async () => {
        if (confirm('키오스크 연결을 종료하시겠습니까?')) {
          try {
            await api.endSession(state.sessionId);
            handleSessionEnded();
          } catch (e) { }
        }
      };
    }

    // 옵션 모달 수량 조절
    if (dom.btnQtyMinus) {
      dom.btnQtyMinus.onclick = () => {
        if (state.currentQty > 1) {
          state.currentQty--;
          if (dom.modalQtyVal) dom.modalQtyVal.textContent = state.currentQty;
          updateModalPriceCalculation();
          if (window.soundFeedback) window.soundFeedback.tick();
        }
      };
    }

    if (dom.btnQtyPlus) {
      dom.btnQtyPlus.onclick = () => {
        if (state.currentQty < 10) {
          state.currentQty++;
          if (dom.modalQtyVal) dom.modalQtyVal.textContent = state.currentQty;
          updateModalPriceCalculation();
          if (window.soundFeedback) window.soundFeedback.tick();
        }
      };
    }

    // 옵션 모달 담기 버튼
    if (dom.btnAddToCart) dom.btnAddToCart.onclick = () => handleAddToCartSubmit();
    if (dom.btnCloseOption) dom.btnCloseOption.onclick = () => closeOptionModal();

    // 장바구니 열기/닫기
    if (dom.btnOpenCart) dom.btnOpenCart.onclick = () => openCartModal();
    if (dom.btnCloseCart) dom.btnCloseCart.onclick = () => closeCartModal();
    if (dom.btnCheckoutSubmit) dom.btnCheckoutSubmit.onclick = () => submitOrder();

    // 상단 접근성 설정 드로어 열기/닫기
    if (dom.btnOpenAccessibility) {
      dom.btnOpenAccessibility.onclick = () => {
        if (window.soundFeedback) window.soundFeedback.tick();
        if (dom.accessibilityDrawer) dom.accessibilityDrawer.classList.add('open');
        announce('접근성 설정 창이 열렸습니다.');
      };
    }
    if (dom.btnCloseAccessDrawer) {
      dom.btnCloseAccessDrawer.onclick = () => {
        if (window.soundFeedback) window.soundFeedback.tick();
        if (dom.accessibilityDrawer) dom.accessibilityDrawer.classList.remove('open');
      };
    }

    // 상단 헤더 장바구니 버튼
    if (dom.btnTopCart) {
      dom.btnTopCart.onclick = () => openCartModal();
    }

    // 키오스크 실시간 디지털 시계
    if (dom.kioskLiveClock) {
      const updateKioskClock = () => {
        const now = new Date();
        dom.kioskLiveClock.textContent = now.toLocaleTimeString('ko-KR', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
      };
      updateKioskClock();
      setInterval(updateKioskClock, 1000);
    }

    // 모달 배경(Backdrop) 터치 시 닫기
    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) {
          if (window.soundFeedback) window.soundFeedback.tick();
          backdrop.classList.remove('open');
        }
      });
    });

    // 주문 취소 & 새 주문
    if (dom.btnCancelOrder) dom.btnCancelOrder.onclick = () => cancelCurrentOrder();
    if (dom.btnNewOrder) dom.btnNewOrder.onclick = () => resetToNewOrder();

    // 직원 호출
    if (dom.btnCallHelp) dom.btnCallHelp.onclick = () => callHelp();

    // 모바일 QR 모달 열기/닫기
    const btnShowQr = document.getElementById('btn-show-qr');
    const btnCloseQrModal = document.getElementById('btn-close-qr-modal');
    const mobileQrModal = document.getElementById('mobile-qr-modal');

    if (btnShowQr && mobileQrModal) {
      btnShowQr.onclick = () => {
        if (window.soundFeedback) window.soundFeedback.tick();
        mobileQrModal.classList.add('open');
      };
    }
    if (btnCloseQrModal && mobileQrModal) {
      btnCloseQrModal.onclick = () => {
        if (window.soundFeedback) window.soundFeedback.tick();
        mobileQrModal.classList.remove('open');
      };
    }

    // 스타벅스 메인 탭 이벤트 (전체 메뉴 / 추천 메뉴 / 음성 가이드)
    const tabAll = document.getElementById('sb-tab-all');
    const tabRec = document.getElementById('sb-tab-recommend');
    const tabVoice = document.getElementById('sb-tab-voice');

    if (tabAll && tabRec && tabVoice) {
      const switchSbTab = (activeTab) => {
        if (window.soundFeedback) window.soundFeedback.tick();
        [tabAll, tabRec, tabVoice].forEach(t => t.classList.remove('active'));
        activeTab.classList.add('active');
      };

      tabAll.onclick = () => {
        switchSbTab(tabAll);
        state.selectedCategory = 'all';
        filterAndRenderMenu();
        announce('전체 메뉴를 표시합니다.');
      };

      tabRec.onclick = () => {
        switchSbTab(tabRec);
        const recList = state.menuItems.filter(i => ['americano', 'vanilla-latte', 'grapefruit-ade'].includes(i.id));
        renderMenuItems(recList);
        announce('인기 추천 메뉴를 표시합니다.');
      };

      tabVoice.onclick = () => {
        switchSbTab(tabVoice);
        announce('음성 주문 안내입니다. 하단의 마이크 버튼을 누르고 "아이스 아메리카노 한 잔 담아줘", "장바구니 확인", "주문해줘", "직원 호출" 등을 자연스럽게 말씀해 주세요.');
        showToast('마이크를 누르고 "아이스 아메리카노 담아줘"라고 말해보세요!', 'info');
      };
    }

    // 1. 매장 선택 모달 이벤트 (GET /stores)
    if (dom.btnSelectStore) dom.btnSelectStore.onclick = () => openStoreSelectModal();
    if (dom.btnCloseStoreSelect) dom.btnCloseStoreSelect.onclick = () => closeStoreSelectModal();

    // 2. 매장 실내 길안내 모달 이벤트 (indoorDirections)
    if (dom.btnIndoorGuide) dom.btnIndoorGuide.onclick = () => openIndoorGuideModal();
    if (dom.btnCloseIndoorGuide) dom.btnCloseIndoorGuide.onclick = () => closeIndoorGuideModal();
    if (dom.btnPlayIndoorTts) {
      dom.btnPlayIndoorTts.onclick = () => {
        const text = dom.modalIndoorText ? dom.modalIndoorText.textContent.trim() : '입구로 들어오시면 키오스크 1은 오른쪽 약 2m 거리에 위치해 있습니다.';
        announce(text, { priority: 'high' });
      };
    }

    // 3. 주문 요청사항 메모 (note) 마이크 입력 & 퀵 칩
    if (dom.btnNoteMic) {
      dom.btnNoteMic.onclick = () => {
        if (!window.speechService) return;
        announce('요청사항을 말씀해 주세요.');
        window.speechService.startListening();
        // 인식된 텍스트를 note에 반영
        const prevStatusCallback = window.speechService.onStatusChangeCallback;
        window.speechService.onStatusChangeCallback = ({ listening, text }) => {
          if (prevStatusCallback) prevStatusCallback({ listening, text });
          if (!listening && text.startsWith('인식 완료: "')) {
            const recognized = text.replace('인식 완료: "', '').replace('"', '').trim();
            if (dom.cartOrderNote && recognized) {
              dom.cartOrderNote.value = recognized;
              announce(`요청사항에 "${recognized}"가 입력되었습니다.`);
            }
          }
        };
      };
    }

    // 요청사항 퀵 칩 버튼들
    document.querySelectorAll('.note-chip').forEach(chip => {
      chip.onclick = () => {
        if (window.soundFeedback) window.soundFeedback.tick();
        const clean = chip.textContent.trim();
        if (dom.cartOrderNote) {
          dom.cartOrderNote.value = dom.cartOrderNote.value ? `${dom.cartOrderNote.value}, ${clean}` : clean;
          announce(`요청사항에 ${clean} 추가됨`);
        }
      };
    });
  }

  // ==========================================
  // 매장 선택 탐색기 (GET /stores)
  // ==========================================
  async function openStoreSelectModal() {
    if (window.soundFeedback) window.soundFeedback.tick();
    try {
      const stores = await api.listStores();
      dom.storesListContainer.innerHTML = '';

      stores.forEach(st => {
        const card = document.createElement('div');
        card.className = 'menu-card';
        card.style.cursor = 'pointer';
        const isCurrent = st.storeId === state.storeId;

        card.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:center;width:100%;">
            <div>
              <div style="font-weight:900;font-size:1.15rem;color:var(--sb-green);">${st.name}</div>
              <div style="font-size:0.85rem;color:var(--text-secondary);margin-top:2px;">${st.address}</div>
              <div style="display:flex;gap:4px;margin-top:6px;">
                <span class="tag" style="font-size:0.75rem;">♿ 1층 무단차</span>
                <span class="tag" style="font-size:0.75rem;">🖥️ 키오스크 주문</span>
              </div>
            </div>
            <button class="tool-btn ${isCurrent ? 'active' : ''}" style="min-height:36px;white-space:nowrap;">
              ${isCurrent ? '현재 매장' : '선택'}
            </button>
          </div>
        `;

        card.onclick = async () => {
          if (st.storeId === state.storeId) {
            closeStoreSelectModal();
            return;
          }
          await switchStore(st.storeId);
          closeStoreSelectModal();
        };

        dom.storesListContainer.appendChild(card);
      });

      dom.storeSelectModal.classList.add('open');
      announce('매장 선택 창입니다. 방문하실 매장을 선택하세요.');
    } catch (err) {
      showToast('매장 목록 로드 실패: ' + err.message, 'danger');
    }
  }

  function closeStoreSelectModal() {
    if (window.soundFeedback) window.soundFeedback.tick();
    dom.storeSelectModal.classList.remove('open');
  }

  async function switchStore(storeId) {
    try {
      state.storeId = storeId;
      const store = await api.getStore(storeId);
      state.storeData = store;
      state.menuItems = store.menu || [];
      if (dom.connectionLabel) dom.connectionLabel.textContent = `${store.name} 📍`;
      if (dom.storeDescLine) dom.storeDescLine.textContent = `${store.address} • 무단차 접근 가능`;

      renderCategories(state.menuItems);
      renderMenuItems(state.menuItems);
      showToast(`${store.name} 매장으로 변경되었습니다.`, 'success');
      announce(`${store.name} 매장으로 변경되었습니다. 원하시는 메뉴를 골라주세요.`);
    } catch (err) {
      showToast('매장 변경 실패: ' + err.message, 'danger');
    }
  }

  // ==========================================
  // 매장 실내 음성 길안내 (indoorDirections)
  // ==========================================
  function openIndoorGuideModal() {
    if (window.soundFeedback) window.soundFeedback.tick();
    const store = state.storeData || {};
    const text = store.indoorDirections || '입구로 들어오시면 키오스크 1은 오른쪽 약 2m 거리에 위치해 있습니다. 카운터와 음료 픽업대는 정면 5m 앞입니다.';
    if (dom.modalIndoorText) dom.modalIndoorText.textContent = text;
    dom.indoorGuideModal.classList.add('open');
    announce(`매장 실내 길안내입니다. ${text}`);
  }

  function closeIndoorGuideModal() {
    if (window.soundFeedback) window.soundFeedback.tick();
    dom.indoorGuideModal.classList.remove('open');
  }

  // ==========================================
  // 갈지도(Galjido) 근접 감지 & 아두이노 블루투스 연동
  // ==========================================
  function setupProximityControls() {
    // 1. 매장 감지 카드 내 버튼
    if (dom.btnConfirmConnect) {
      dom.btnConfirmConnect.onclick = () => confirmAndConnectToStore();
    }
    if (dom.btnRejectConnect) {
      dom.btnRejectConnect.onclick = () => rejectStoreConnection();
    }
    if (dom.btnDisconnectStore) {
      dom.btnDisconnectStore.onclick = () => handleSessionEnded();
    }

    // 2. 모바일 블루투스 스캔 버튼 (Web Bluetooth API)
    if (dom.btnMobileBleScan) {
      dom.btnMobileBleScan.onclick = () => startMobileBluetoothScan();
    }

    // 3. 모바일 원터치 가상 감지 테스트 버튼 (근접)
    if (dom.btnQuickDistTest) {
      dom.btnQuickDistTest.onclick = () => {
        if (window.soundFeedback) window.soundFeedback.tick();
        showToast('블루투스 신호 감지 (근접)', 'info');
        handleProximityUpdate(1.0, 'GIST Cafe점', -58);
      };
    }

    // 4. 중앙 펄스 비콘 터치 시 동작
    if (dom.radarBeaconTrigger) {
      dom.radarBeaconTrigger.onclick = () => {
        if (navigator.bluetooth) {
          startMobileBluetoothScan();
        } else {
          handleProximityUpdate(1.0, 'GIST Cafe점', -58);
        }
      };
      dom.radarBeaconTrigger.ondblclick = () => {
        handleProximityUpdate(1.0, 'GIST Cafe점', -58);
      };
    }

    // 5. 백엔드 실시간 근접 WebSocket 자동 연결 (아두이노 브리지와 실시간 연동)
    initProximityWebSocket();

    // 6. 키보드 단축키 'D'로도 테스트 가능
    window.addEventListener('keydown', (e) => {
      if ((e.key === 'd' || e.key === 'D') && !e.target.matches('input, textarea')) {
        handleProximityUpdate(1.0, 'GIST Cafe점', -58);
      }
    });

    // 7. 모바일 브라우저 오디오/음성 언락 (최초 터치 시 활성화)
    const unlockMobileAudio = () => {
      if (window.soundFeedback) window.soundFeedback._initContext();
      if (window.speechSynthesis && window.speechSynthesis.resume) {
        window.speechSynthesis.resume();
      }
      window.removeEventListener('touchstart', unlockMobileAudio);
      window.removeEventListener('click', unlockMobileAudio);
    };
    window.addEventListener('touchstart', unlockMobileAudio, { passive: true });
    window.addEventListener('click', unlockMobileAudio, { passive: true });
  }

  // 모바일 Web Bluetooth 스캔 (스마트폰 크롬에서 아두이노 블루투스 직접 검색 및 페어링)
  async function startMobileBluetoothScan() {
    if (window.soundFeedback) window.soundFeedback.tick();

    if (!navigator.bluetooth) {
      showToast('블루투스 감지: GIST Cafe점 주문창으로 바로 연결합니다.', 'success');
      state.proximity.distance = 1.0;
      state.proximity.rssi = -58;
      state.proximity.storeName = 'GIST Cafe점';
      confirmAndConnectToStore();
      return;
    }

    try {
      showToast('주변 아두이노 블루투스 장치를 검색합니다...', 'info');
      announce('주변 아두이노 블루투스를 검색합니다. 연결할 기기를 선택해 주세요.');

      // Android Chrome의 네이티브 블루투스 장치 선택창 호출
      const device = await navigator.bluetooth.requestDevice({
        acceptAllDevices: true,
        optionalServices: [
          '0000ffe0-0000-1000-8000-00805f9b34fb', // HM-10 / ZS-040 BLE 표준 서비스
          'generic_access',
          'device_information'
        ]
      });

      console.log('선택된 블루투스 장치:', device.name, device.id);
      showToast(`블루투스 장치 [${device.name || '아두이노'}] 감지 완료!`, 'success');

      if (dom.bleStatusText) {
        dom.bleStatusText.textContent = `연동됨: ${device.name || '아두이노'}`;
      }
      const badge = dom.bleStatusText ? dom.bleStatusText.closest('.ble-status-badge') : null;
      if (badge) badge.classList.add('connected');

      // 아두이노 블루투스 장치 선택 즉시 지스트 카페 주문창 오픈!
      confirmAndConnectToStore();

      // 1. 블루투스 신호 세기(RSSI) 기반 거리 자동 측정 시작!
      startRssiDistanceTracking(device);

      // 2. 아두이노 BLE 실시간 데이터 스트리밍 수신 시작 (GATT)
      if (device.gatt) {
        connectBleGattStreaming(device);
      }

      // 연결 해제 이벤트 리스너
      device.addEventListener('gattserverdisconnected', () => {
        console.log('Bluetooth device disconnected');
        if (dom.bleStatusText) {
          dom.bleStatusText.textContent = '신호 대기 중';
        }
        if (badge) badge.classList.remove('connected');
        showToast('블루투스 연결이 해제되었습니다.', 'info');
      });

    } catch (err) {
      if (err.name === 'NotFoundError') {
        console.log('사용자가 블루투스 선택창을 닫았습니다.');
      } else {
        console.warn('Bluetooth scan note:', err);
        showToast('블루투스 검색 안내: ' + (err.message || '장치를 찾을 수 없습니다.'), 'info');
      }
    }
  }

  // ==========================================
  // 블루투스 신호 세기(RSSI) 기반 근접 단계 분류 & 실내 거리 보정
  // 사용자 요구 반영:
  // - 최대로 강할 때: "매우 근접" (바로 앞)
  // - 보통/중간일 때: "근접 (접근 중)"
  // - 멀리 있을 때:   "멀리 위치"
  // ==========================================
  let smoothedRssiDistance = null;

  function getProximityLevel(rssi, distMeter = null) {
    // 1. 블루투스 RSSI(dBm) 기준 판별 (최우선)
    if (typeof rssi === 'number' && rssi < 0) {
      if (rssi >= -63) {
        // [최대 강함] 키오스크 바로 앞 (0.3m ~ 0.8m)
        const m = Math.min(0.8, Math.max(0.3, Math.round((0.3 + ((-50 - Math.min(-50, rssi)) * 0.03)) * 10) / 10));
        return {
          level: 'very_close',
          badgeText: '매우 근접',
          desc: `키오스크 매우 근접 (신호 ${rssi}dBm)`,
          meters: m,
          className: 'proximity-very-close'
        };
      } else if (rssi >= -76) {
        // [중간/보통] 접근 중 (1.0m ~ 2.2m)
        const ratio = (-63 - rssi) / 13; // 0 ~ 1
        const m = Math.round((1.0 + ratio * 1.2) * 10) / 10;
        return {
          level: 'approaching',
          badgeText: '근접 (접근 중)',
          desc: `키오스크 접근 중 (신호 ${rssi}dBm)`,
          meters: m,
          className: 'proximity-approaching'
        };
      } else {
        // [약함/멀리] 멀리 위치 (2.5m ~ 4.5m)
        const ratio = Math.min(1.0, (-76 - rssi) / 14);
        const m = Math.round((2.5 + ratio * 2.0) * 10) / 10;
        return {
          level: 'far',
          badgeText: '멀리 위치',
          desc: `키오스크 멀리 위치 (신호 ${rssi}dBm)`,
          meters: m,
          className: 'proximity-far'
        };
      }
    }

    // 2. RSSI 없이 미터수만 있는 경우 보정
    const num = parseFloat(distMeter);
    if (!isNaN(num)) {
      if (num <= 1.0) {
        return {
          level: 'very_close',
          badgeText: '매우 근접',
          desc: `키오스크 매우 근접 (${num.toFixed(1)}m)`,
          meters: num,
          className: 'proximity-very-close'
        };
      } else if (num <= 2.5) {
        return {
          level: 'approaching',
          badgeText: '근접 (접근 중)',
          desc: `키오스크 접근 중 (${num.toFixed(1)}m)`,
          meters: num,
          className: 'proximity-approaching'
        };
      } else {
        return {
          level: 'far',
          badgeText: '멀리 위치',
          desc: `키오스크 멀리 위치 (${Math.min(5.0, num).toFixed(1)}m)`,
          meters: Math.min(5.0, num),
          className: 'proximity-far'
        };
      }
    }

    return {
      level: 'unknown',
      badgeText: '신호 대기 중',
      desc: '키오스크 신호 연동됨',
      meters: 1.5,
      className: 'proximity-approaching'
    };
  }

  function rssiToDistance(rssi) {
    const p = getProximityLevel(rssi);
    return p.meters;
  }

  function getSmoothedDistance(rawDist, alpha = 0.35) {
    if (smoothedRssiDistance === null) {
      smoothedRssiDistance = rawDist;
    } else {
      smoothedRssiDistance = alpha * rawDist + (1 - alpha) * smoothedRssiDistance;
    }
    return Math.round(smoothedRssiDistance * 10) / 10;
  }

  async function startRssiDistanceTracking(device) {
    if (!device.watchAdvertisements) {
      console.warn('이 브라우저는 device.watchAdvertisements()를 지원하지 않습니다.');
      return;
    }

    try {
      await device.watchAdvertisements();
      console.log('블루투스 RSSI 신호 세기 실시간 측정 활성화 완료!');
      showToast('블루투스 신호 세기(RSSI) 기반 거리 자동 측정 활성화!', 'success');

      device.addEventListener('advertisementreceived', (event) => {
        const rssi = event.rssi;
        if (typeof rssi === 'number' && rssi < 0) {
          const rawMeters = rssiToDistance(rssi, event.txPower || -59);
          const smoothedMeters = getSmoothedDistance(rawMeters);
          console.log(`[RSSI 수신] ${rssi} dBm -> 실시간 계산 거리: ${smoothedMeters}m`);
          
          handleProximityUpdate(smoothedMeters, 'GIST Cafe점', rssi);
        }
      });
    } catch (err) {
      console.warn('RSSI 감시 활성화 오류:', err);
    }
  }

  // 아두이노 BLE GATT 알림(Notification)으로 실시간 거리 데이터 스트리밍 수신
  async function connectBleGattStreaming(device) {
    try {
      console.log('BLE GATT 서버 연결 시도 중...');
      const server = await device.gatt.connect();
      console.log('BLE GATT 서버 연결 성공!');

      // ZS-040 / HM-10 / AT-09 표준 UART BLE 서비스 및 캐릭터리스틱
      const serviceUuids = ['0000ffe0-0000-1000-8000-00805f9b34fb', 'ffe0'];
      let service = null;
      for (const u of serviceUuids) {
        try {
          service = await server.getPrimaryService(u);
          if (service) break;
        } catch (e) {}
      }

      if (!service) {
        console.warn('BLE UART 서비스를 찾을 수 없습니다.');
        return;
      }

      const charUuids = ['0000ffe1-0000-1000-8000-00805f9b34fb', 'ffe1'];
      let characteristic = null;
      for (const u of charUuids) {
        try {
          characteristic = await service.getCharacteristic(u);
          if (characteristic) break;
        } catch (e) {}
      }

      if (!characteristic) {
        console.warn('BLE UART 특성을 찾을 수 없습니다.');
        return;
      }

      await characteristic.startNotifications();
      console.log('실시간 거리 Notification 구독 성공!');

      let rxBuffer = '';
      const decoder = new TextDecoder('utf-8');

      characteristic.addEventListener('characteristicvaluechanged', (e) => {
        const text = decoder.decode(e.target.value);
        rxBuffer += text;

        const lines = rxBuffer.split('\n');
        rxBuffer = lines.pop();

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.includes('DIST:')) {
            const valStr = trimmed.split('DIST:')[1].split(',')[0].trim();
            const realDist = parseFloat(valStr);
            if (!isNaN(realDist)) {
              handleProximityUpdate(realDist, 'GIST Cafe점');
            }
          }
        }
      });
    } catch (err) {
      console.warn('GATT 실시간 거리 구독 오류:', err);
    }
  }

  // 실시간 근접 WebSocket 연결 (scripts/arduino_bt_bridge.py -> FastAPI -> 브라우저)
  function initProximityWebSocket() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${proto}//${location.host}/ws/proximity`;

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('Proximity WS connected to', wsUrl);
        if (dom.bleStatusText) {
          dom.bleStatusText.textContent = '실시간 브릿지 연동됨 (Wi-Fi)';
        }
        const badge = dom.bleStatusText ? dom.bleStatusText.closest('.ble-status-badge') : null;
        if (badge) badge.classList.add('connected');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'proximity' && data.distance !== undefined) {
            handleProximityUpdate(parseFloat(data.distance), data.storeName || 'GIST Cafe점', data.rssi || null);
          }
        } catch (e) {
          console.error('Proximity WS parse error:', e);
        }
      };

      ws.onclose = () => {
        if (dom.bleStatusText && !dom.bleStatusText.textContent.includes('연동됨')) {
          dom.bleStatusText.textContent = '신호 대기 중';
          const badge = dom.bleStatusText.closest('.ble-status-badge');
          if (badge) badge.classList.remove('connected');
        }
        // 백그라운드 재연결 (3초 후)
        setTimeout(initProximityWebSocket, 3000);
      };
    } catch (err) {
      console.warn('Proximity WS connect error:', err);
    }
  }

  function handleProximityUpdate(distMeter, storeName = 'GIST Cafe점', rssi = null) {
    const p = state.proximity;
    p.distance = distMeter;
    p.storeName = storeName;
    if (rssi) p.rssi = rssi;

    // [상태 1] 이미 키오스크 세션에 연결되어 주문 중인 상태:
    if (state.sessionId || p.status === 'connected') {
      updateProximityDistanceGauge(distMeter, rssi);
      return;
    }

    // [상태 2] 100m 이내로 들어온 경우 (블루투스 감지 -> 즉시 지스트 카페 주문창 오픈!)
    if (distMeter <= 100) {
      p.status = 'connected';
      p.awaitingConfirmation = false;
      if (dom.detectedStorePopup) dom.detectedStorePopup.style.display = 'none';
      confirmAndConnectToStore();
    } else {
      // 100m 밖인 경우: 다시 탐색 상태로 복귀
      p.status = 'scanning';
      p.awaitingConfirmation = false;
      if (dom.detectedStorePopup) dom.detectedStorePopup.style.display = 'none';
    }
  }

  function updateProximityDistanceGauge(distMeter, rssi = null) {
    const prox = getProximityLevel(rssi, distMeter);
    state.proximity.distance = prox.meters;
    if (rssi) state.proximity.rssi = rssi;

    const bar = dom.headerDistanceText ? dom.headerDistanceText.closest('.live-kiosk-distance-bar') : null;
    if (bar) {
      bar.classList.remove('proximity-very-close', 'proximity-approaching', 'proximity-far');
      bar.classList.add(prox.className);
    }

    if (dom.headerDistanceText) {
      dom.headerDistanceText.textContent = prox.desc;
    }
    if (dom.liveDistanceBadge) {
      dom.liveDistanceBadge.textContent = prox.badgeText;
    }

    if (prox.level === 'very_close' && !state.proximity.arrivedAnnounced) {
      state.proximity.arrivedAnnounced = true;
      if (window.soundFeedback) window.soundFeedback.chime();
      announce(`키오스크 매우 근접했습니다. 바로 앞에서 주문하실 수 있습니다.`);
    } else if (prox.level === 'far') {
      state.proximity.arrivedAnnounced = false;
    }
  }

  function confirmAndConnectToStore() {
    const p = state.proximity;
    p.awaitingConfirmation = false;
    p.status = 'connected';

    if (dom.detectedStorePopup) dom.detectedStorePopup.style.display = 'none';

    announce(`${p.storeName}에 연결합니다. 원격 주문을 시작합니다.`);
    connectToKiosk();
  }

  function rejectStoreConnection() {
    const p = state.proximity;
    p.awaitingConfirmation = false;
    p.status = 'scanning';

    if (dom.detectedStorePopup) dom.detectedStorePopup.style.display = 'none';

    announce('매장 연결을 취소했습니다. 계속해서 주변 매장을 탐색합니다.');
  }

  // 앱 시작
  window.addEventListener('DOMContentLoaded', init);
})();
