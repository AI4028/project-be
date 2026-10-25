/**
 * speech.js - 음성 인식(STT) 및 음성 합성(TTS) 관리자
 * 한국어 시각장애인 사용자를 위한 실시간 음성 가이드 및 자연어 명령 파서
 */

class SpeechService {
  constructor() {
    this.ttsSupported = 'speechSynthesis' in window;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.sttSupported = Boolean(SpeechRecognition);

    this.recognition = null;
    this.isListening = false;
    this.ttsEnabled = true;
    this.koreanVoice = null;
    this.lastSpokenText = '';

    // 콜백 함수들
    this.onResultCallback = null;
    this.onStatusChangeCallback = null;
    this.onCommandCallback = null;

    this._initTTS();
    this._initSTT(SpeechRecognition);
  }

  // --- TTS 초기화 ---
  _initTTS() {
    if (!this.ttsSupported) return;

    const findVoice = () => {
      const voices = window.speechSynthesis.getVoices();
      // 한국어 음성 찾기 (ko-KR, ko)
      this.koreanVoice = voices.find(v => v.lang.startsWith('ko') || v.lang === 'ko-KR') || null;
    };

    findVoice();
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = findVoice;
    }
  }

  // --- STT 초기화 ---
  _initSTT(SpeechRecognition) {
    if (!this.sttSupported) return;

    this.recognition = new SpeechRecognition();
    this.recognition.lang = 'ko-KR';
    this.recognition.continuous = false;
    this.recognition.interimResults = true;
    this.recognition.maxAlternatives = 3;

    this.recognition.onstart = () => {
      this.isListening = true;
      if (window.soundFeedback) window.soundFeedback.micStart();
      if (this.onStatusChangeCallback) {
        this.onStatusChangeCallback({ listening: true, text: '듣고 있습니다... 말씀해 주세요.' });
      }
    };

    this.recognition.onresult = (event) => {
      let interim = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interim += event.results[i][0].transcript;
        }
      }

      const current = finalTranscript || interim;
      if (this.onStatusChangeCallback) {
        this.onStatusChangeCallback({ listening: true, text: `인식 중: "${current}"` });
      }

      if (finalTranscript) {
        this._handleRecognizedText(finalTranscript.trim());
      }
    };

    this.recognition.onerror = (event) => {
      this.isListening = false;
      if (window.soundFeedback) window.soundFeedback.error();
      let errorMsg = '음성을 인식하지 못했습니다.';
      if (event.error === 'not-allowed') {
        errorMsg = '마이크 권한이 허용되지 않았습니다.';
      } else if (event.error === 'no-speech') {
        errorMsg = '말씀이 감지되지 않았습니다.';
      }
      if (this.onStatusChangeCallback) {
        this.onStatusChangeCallback({ listening: false, text: errorMsg });
      }
    };

    this.recognition.onend = () => {
      if (this.isListening) {
        this.isListening = false;
        if (window.soundFeedback) window.soundFeedback.micStop();
      }
      if (this.onStatusChangeCallback) {
        this.onStatusChangeCallback({ listening: false, text: '마이크 대기 중' });
      }
    };
  }

  // --- 음성 인식 토글 ---
  toggleListening() {
    if (!this.sttSupported) {
      this.speak('이 브라우저는 음성 인식을 지원하지 않습니다. 크롬 브라우저를 권장합니다.');
      return;
    }

    if (this.isListening) {
      this.stopListening();
    } else {
      this.startListening();
    }
  }

  startListening() {
    if (!this.sttSupported || this.isListening) return;
    // 발화 중인 TTS 멈춤 (자기 음성 재인식 방지)
    this.stopSpeaking();
    try {
      this.recognition.start();
    } catch (e) {
      console.warn('STT start error:', e);
    }
  }

  stopListening() {
    if (!this.sttSupported || !this.isListening) return;
    try {
      this.recognition.stop();
    } catch (e) {
      console.warn('STT stop error:', e);
    }
    this.isListening = false;
  }

  // --- 음성 안내 (TTS) 출력 ---
  speak(text, { priority = 'normal', onEnd = null } = {}) {
    if (!this.ttsSupported || !this.ttsEnabled || !text) return;

    this.lastSpokenText = text;

    // 만약 우선순위가 높거나 현재 말하고 있다면 취소하고 새로 발화
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'ko-KR';
    if (this.koreanVoice) {
      utterance.voice = this.koreanVoice;
    }
    // 시각장애인 고객이 듣기 편안한 속도와 톤
    utterance.rate = 1.05;
    utterance.pitch = 1.0;

    if (onEnd) {
      utterance.onend = onEnd;
    }

    window.speechSynthesis.speak(utterance);
  }

  stopSpeaking() {
    if (this.ttsSupported) {
      window.speechSynthesis.cancel();
    }
  }

  repeatLast() {
    if (this.lastSpokenText) {
      this.speak(this.lastSpokenText);
    } else {
      this.speak('다시 들을 안내 내용이 없습니다.');
    }
  }

  setTtsEnabled(enabled) {
    this.ttsEnabled = enabled;
    if (!enabled) {
      this.stopSpeaking();
    } else {
      this.speak('음성 안내가 켜졌습니다.');
    }
  }

  // --- 한국어 자연어 명령 파서 ---
  _handleRecognizedText(text) {
    const cleaned = text.replace(/[.,?!]/g, '').trim();
    console.log('음성 인식 텍스트:', cleaned);

    if (this.onStatusChangeCallback) {
      this.onStatusChangeCallback({ listening: false, text: `인식 완료: "${cleaned}"` });
    }

    const command = this._parseKoreanCommand(cleaned);
    if (this.onCommandCallback) {
      this.onCommandCallback(command, cleaned);
    }
  }

  _parseKoreanCommand(text) {
    const lower = text.toLowerCase();
    const cleaned = text.replace(/[.,?!]/g, '').trim();

    // 0. 매장 연결 긍정 답변 ("응", "네", "어", "그래", "좋아", "연결해줘" 등)
    const affirmativeRegex = /^(응|네|어|그래|좋아|연결|연결해|연결할래|연결해줘|예|오냐|콜|맞아|응응|웅|ㅇㅇ|옙|넵)$/;
    if (affirmativeRegex.test(cleaned) || cleaned.includes('응 연결') || cleaned.includes('네 연결') || cleaned.includes('연결해줘') || cleaned.includes('연결할래') || cleaned.includes('주문할래')) {
      return { action: 'CONFIRM_CONNECT' };
    }

    // 0-1. 매장 연결 부정 답변 ("아니", "아니오", "싫어", "취소", "나중에" 등)
    const negativeRegex = /^(아니|아니오|싫어|취소|나중에|하지마|안해|닫기|놉|노|아뇨)$/;
    if (negativeRegex.test(cleaned) || cleaned.includes('연결 안') || cleaned.includes('나중에 할래') || cleaned.includes('괜찮아')) {
      return { action: 'REJECT_CONNECT' };
    }

    // 1. 직원 호출 / 도움 요청
    if (lower.includes('직원') || lower.includes('도와') || lower.includes('도움') || lower.includes('호출') || lower.includes('사람')) {
      return { action: 'CALL_HELP' };
    }

    // 2. 키오스크 연결
    if (lower.includes('연결') || lower.includes('시작') || lower.includes('접속') || lower.includes('키오스크')) {
      return { action: 'CONNECT_KIOSK' };
    }

    // 3. 다시 듣기
    if (lower.includes('다시') || lower.includes('뭐라고') || lower.includes('반복')) {
      return { action: 'REPEAT' };
    }

    // 4. 고대비 모드
    if (lower.includes('고대비') || lower.includes('대비') || lower.includes('검정색') || lower.includes('노란색')) {
      return { action: 'TOGGLE_HIGH_CONTRAST' };
    }

    // 5. 글자 크기
    if (lower.includes('글자') && (lower.includes('크게') || lower.includes('키워'))) {
      return { action: 'INCREASE_FONT' };
    }
    if (lower.includes('글자') && (lower.includes('작게') || lower.includes('보통'))) {
      return { action: 'RESET_FONT' };
    }

    // 6. 장바구니 담기 ("담아줘", "담기", "장바구니에 담아", "담을래", "넣어줘")
    if (lower.includes('담아') || lower.includes('담기') || lower.includes('담을래') || lower.includes('넣어줘') || lower.includes('카트에') || lower.includes('이대로 담')) {
      const opt = this._extractOptionsOnly(lower);
      const q = this._extractQtyOnly(lower);
      return { action: 'ADD_TO_CART', options: opt, qty: q, raw: text };
    }

    // 6-1. 장바구니 확인
    if ((lower.includes('장바구니') || lower.includes('카트') || lower.includes('담은')) && (lower.includes('보여') || lower.includes('확인') || lower.includes('얼마') || lower.includes('목록') || lower.includes('열어'))) {
      return { action: 'VIEW_CART' };
    }

    // 7. 주문하기 / 결제하기
    if (lower.includes('주문') || lower.includes('결제') || lower.includes('계산') || lower.includes('구매')) {
      let method = null;
      if (lower.includes('카드') || lower.includes('키오스크')) method = 'kiosk';
      if (lower.includes('카운터') || lower.includes('직원') || lower.includes('직접')) method = 'counter';
      return { action: 'SUBMIT_ORDER', paymentMethod: method, raw: text };
    }

    // 7-1. 결제 수단 선택
    if (lower.includes('카드') || lower.includes('카드로')) {
      return { action: 'SELECT_PAYMENT', method: 'kiosk' };
    }
    if (lower.includes('카운터') || lower.includes('현금')) {
      return { action: 'SELECT_PAYMENT', method: 'counter' };
    }

    // 8. 취소 / 뒤로가기 / 닫기
    if (lower.includes('취소') || lower.includes('뒤로') || lower.includes('돌아가') || lower.includes('닫기') || lower.includes('닫아')) {
      return { action: 'CANCEL_OR_BACK' };
    }

    // 9. 메뉴 읽어줘
    if (lower.includes('메뉴') && (lower.includes('읽어') || lower.includes('알려') || lower.includes('뭐 있어') || lower.includes('목록'))) {
      return { action: 'READ_MENU' };
    }

    // 10. 실내 길안내
    if (lower.includes('길안내') || lower.includes('길 안내') || lower.includes('실내') || lower.includes('위치') || lower.includes('어디')) {
      return { action: 'OPEN_INDOOR_GUIDE' };
    }

    // 11. 매장 변경 / 매장 선택
    if (lower.includes('매장') && (lower.includes('변경') || lower.includes('선택') || lower.includes('다른'))) {
      return { action: 'OPEN_STORE_SELECT' };
    }

    // 12. 키오스크 연결 종료 / 해제
    if (lower.includes('연결 해제') || lower.includes('연결 종료') || lower.includes('연결 끊') || lower.includes('접속 종료')) {
      return { action: 'END_SESSION' };
    }

    // 13. 옵션 선택 및 수량 조절 단독 명령 (옵션 모달 오픈 중 발화 시)
    const standaloneOptions = this._extractOptionsOnly(lower);
    const parsedQty = this._extractQtyOnly(lower);
    const hasQtyAdj = lower.includes('늘려') || lower.includes('줄여') || lower.includes('하나 더') || lower.includes('한 개 더') || lower.includes('한 잔 더') || lower.includes('더 줘') || lower.includes('빼줘') || lower.includes('수량');
    
    if (Object.keys(standaloneOptions).length > 0 || parsedQty !== null || hasQtyAdj) {
      let qtyDelta = 0;
      if (lower.includes('늘려') || lower.includes('하나 더') || lower.includes('한 개 더') || lower.includes('한 잔 더') || lower.includes('더 줘') || lower.includes('추가')) {
        qtyDelta = 1;
      } else if (lower.includes('줄여') || lower.includes('하나 빼') || lower.includes('한 개 빼') || lower.includes('한 잔 빼') || lower.includes('빼줘')) {
        qtyDelta = -1;
      }
      return {
        action: 'SELECT_OPTION',
        options: standaloneOptions,
        qty: parsedQty,
        qtyDelta: qtyDelta,
        raw: text
      };
    }

    // 14. 특정 메뉴 주문 또는 탐색 (메뉴명 + 옵션 + 수량 파싱)
    const menuResult = this._extractMenuAndOptions(lower);
    if (menuResult.menuId) {
      return {
        action: 'ORDER_ITEM',
        menuId: menuResult.menuId,
        menuName: menuResult.menuName,
        options: menuResult.options,
        qty: menuResult.qty
      };
    }

    // 알 수 없는 명령
    return { action: 'UNKNOWN', raw: text };
  }

  // 단독 옵션 추출 (모달 내부에서 옵션만 말했을 때)
  _extractOptionsOnly(text) {
    const options = {};

    // 온도 파싱
    if (text.includes('따뜻') || text.includes('뜨거') || text.includes('핫') || text.includes('hot')) {
      options.temp = 'hot';
    } else if (text.includes('아이스') || text.includes('차갑') || text.includes('시원') || text.includes('ice') || text.includes('얼음')) {
      options.temp = 'ice';
    }

    // 크기 파싱
    if (text.includes('라지') || text.includes('큰') || text.includes('사이즈 업') || text.includes('large')) {
      options.size = 'large';
    } else if (text.includes('레귤러') || text.includes('보통') || text.includes('기본') || text.includes('작은') || text.includes('regular')) {
      options.size = 'regular';
    }

    // 추가 옵션 (샷, 디카페인)
    const extra = [];
    if (text.includes('샷추가') || text.includes('샷 추가') || text.includes('샷 넣어') || text.includes('샷 하나')) {
      extra.push('shot');
    }
    if (text.includes('디카페인') || text.includes('디카')) {
      extra.push('decaf');
    }
    if (extra.length > 0) {
      options.extra = extra;
    }

    // 우유 옵션
    if (text.includes('오트') || text.includes('귀리')) {
      options.milk = 'oat';
    } else if (text.includes('일반') && text.includes('우유')) {
      options.milk = 'regular';
    }

    // 휘핑크림
    if (text.includes('휘핑 빼') || text.includes('휘핑크림 빼') || text.includes('크림 빼')) {
      options.whip = 'without';
    } else if (text.includes('휘핑') || text.includes('휘핑크림')) {
      options.whip = 'with';
    }

    // 데우기
    if (text.includes('데워') || text.includes('데우')) {
      options.warm = 'yes';
    }

    return options;
  }

  // 단독 수량 추출
  _extractQtyOnly(text) {
    if (text.includes('1개') || text.includes('1잔') || text.includes('한 개') || text.includes('한 잔') || text.includes('하나만') || text.includes('한개')) {
      return 1;
    }
    if (text.includes('2개') || text.includes('2잔') || text.includes('두 개') || text.includes('두 잔') || text.includes('둘') || text.includes('두개')) {
      return 2;
    }
    if (text.includes('3개') || text.includes('3잔') || text.includes('세 개') || text.includes('세 잔') || text.includes('셋') || text.includes('세개')) {
      return 3;
    }
    if (text.includes('4개') || text.includes('4잔') || text.includes('네 개') || text.includes('네 잔') || text.includes('넷') || text.includes('네개')) {
      return 4;
    }
    if (text.includes('5개') || text.includes('5잔') || text.includes('다섯')) {
      return 5;
    }
    return null;
  }

  _extractMenuAndOptions(text) {
    // 지원 메뉴 매핑
    const menuMap = [
      { id: 'americano', names: ['아메리카노', '아메', '아메리카', '커피'] },
      { id: 'cafe-latte', names: ['카페라떼', '라떼', '카페 라떼'] },
      { id: 'vanilla-latte', names: ['바닐라라떼', '바닐라 라떼', '바닐라'] },
      { id: 'grapefruit-ade', names: ['자몽에이드', '자몽 에이드', '자몽'] },
      { id: 'croissant', names: ['크루아상', '크로와상', '크로아상', '빵'] },
      { id: 'cheesecake', names: ['치즈케이크', '치즈 케이크', '케이크'] },
      { id: 'lemon-tea', names: ['레몬티', '레몬차', '레몬 티'] },
      { id: 'cookie', names: ['쿠키', '초코쿠키', '초코 쿠키'] }
    ];

    let foundMenu = null;
    for (const item of menuMap) {
      if (item.names.some(name => text.includes(name))) {
        foundMenu = item;
        break;
      }
    }

    if (!foundMenu) {
      return { menuId: null };
    }

    const options = this._extractOptionsOnly(text);
    const qty = this._extractQtyOnly(text) || 1;

    return {
      menuId: foundMenu.id,
      menuName: foundMenu.names[0],
      options,
      qty
    };
  }
}

window.speechService = new SpeechService();
