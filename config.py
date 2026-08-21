# -*- coding: utf-8 -*-
"""
나라장터 용역 입찰 텔레그램 알림 - 설정 파일

실제 키 값은 이 파일에 직접 적지 말고, 같은 폴더에 ".env" 파일을 만들어
아래 형식으로 넣어주세요 (env.example 파일 참고):

    NARA_SERVICE_KEY=발급받은_인증키
    TELEGRAM_BOT_TOKEN=봇_토큰
    TELEGRAM_CHAT_ID=본인_chat_id

이 config.py는 그 값들을 읽어오기만 합니다.
"""
import os
from urllib.parse import unquote
from dotenv import load_dotenv

load_dotenv()

# ── 공공데이터포털 API 인증키 ──────────────────────────────────────
# data.go.kr에서 아래 3개 서비스를 각각 "활용신청" 하면 됩니다.
#   1) 조달청_나라장터 입찰공고정보서비스
#   2) 조달청_나라장터 사전규격정보서비스
#   3) 조달청_나라장터 발주계획현황서비스
# 세 서비스 모두 같은 인증키를 그대로 쓸 수 있습니다.
#
# data.go.kr은 "Encoding(URL인코딩된 형태, %2B 등 포함)"과
# "Decoding(원본 형태, + = 문자가 그대로 있음)" 두 버전을 제공하는데,
# requests 라이브러리가 요청 시 자동으로 한 번 더 인코딩하기 때문에
# Encoding 버전을 그대로 넣으면 이중 인코딩되어 오류가 날 수 있습니다.
# 아래에서 unquote()로 항상 "디코딩된 원본 형태"로 정규화하므로,
# 어떤 버전을 .env에 붙여넣으셔도 안전하게 동작합니다.
_raw_key = os.getenv("NARA_SERVICE_KEY", "")
NARA_SERVICE_KEY = unquote(_raw_key) if _raw_key else ""

# ── 텔레그램 ────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# 여러 명(또는 개인+그룹)에게 동시에 보내고 싶으면 콤마(,)로 구분해서 넣으세요.
# 예: TELEGRAM_CHAT_ID=7496191142,-1004319379374
_raw_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_CHAT_IDS = [cid.strip() for cid in _raw_chat_id.split(",") if cid.strip()]

# ── 조회 기간 ───────────────────────────────────────────────────
# 실행할 때마다 "최근 N일 이내 등록/공고된 건"을 조회합니다.
# 5분 등 짧은 간격으로 자주 돌린다면 1일이면 충분합니다 (놓친 건 없이도 중복방지가 걸러줌).
# 하루 1~2번만 돌린다면 2~3일로 넉넉히 잡아도 됩니다.
LOOKBACK_DAYS = 1

# 한 번 호출에 가져올 행 수 / 최대 페이지 수 (API 과호출 방지용 안전장치)
ROWS_PER_PAGE = 100
MAX_PAGES = 5

# ── 실행 스케줄 (scheduler.py에서 사용) ─────────────────────────
# cron 자체는 "10분마다 항상 실행"으로 단순하게 걸어두고,
# 아래 값을 기준으로 "지금이 실제로 API를 조회할 타이밍인지"를 코드가 판단합니다.
# (판단 기준은 항상 "오늘"의 요일 - 자정이 지나면 그날의 새 규칙이 바로 적용됩니다)
DAY_PERIOD_START_HOUR = 8    # 낮 시간대 시작 (08:00)
DAY_PERIOD_END_HOUR = 20     # 낮 시간대 종료 (20:00 부터는 밤 시간대)

WEEKEND_DAY_ANCHOR_HOURS = [8, 11, 14, 17]  # 주말 낮: 이 시각 정각에만 실행 (3시간 간격)
WEEKEND_NIGHT_RUN_HOUR = 23      # 주말 밤: 자정 직전 딱 한 번 실행할 시각
WEEKEND_NIGHT_RUN_MINUTE = 50    # 23:50 = cron이 10분마다 돌 때 자정 전 마지막 틱

# ── 금액 기준 ───────────────────────────────────────────────────
AMOUNT_THRESHOLD_WON = 1_000_000_000  # 10억원

# ── 건진법(건설기술진흥법) 대상 용역 판별 키워드 ───────────────────
# 공고명/사업명에 아래 키워드 중 하나라도 포함되면 "건진법 대상"으로 분류합니다.
GUNJIN_KEYWORDS = ["건설사업관리", "CM", "건설기술용역"]

# ── 주택법 대상 용역 판별 키워드 ─────────────────────────────────
HOUSING_KEYWORDS = ["주택법", "감리", "감리자", "주택"]

# ── 주택법 건에서 "면접 실시" 여부를 판단할 첨부파일 내 키워드 ───────
INTERVIEW_KEYWORD = "면접"

# ── 중복 알림 방지용 저장 파일 (이미 보낸 공고/사전규격/발주계획 ID 기록) ──
SEEN_STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen_items.json")

# 참고: 이 로직에 맞지 않는 회색지대(첨부파일이 있는데 다운로드/추출은 실패한 경우)는
# "확인 불가"로 보고 금액 기준으로 대체 알림을 보내되, 메시지에 "⚠ 본문 확인 실패"를 표시합니다.
