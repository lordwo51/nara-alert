# -*- coding: utf-8 -*-
"""
필드 추출 모듈

첨부파일 텍스트(및 API 메타데이터)에서 템플릿에 들어갈 값을 뽑아냅니다.
원칙: 확실하지 않으면 절대 추측하지 않고 "파악중"을 반환합니다.

⚠ 참고: 여기 정규식들은 "일반적인 공고문 표현"을 기준으로 짠 것이라,
실제 공고문 표현이 조금만 달라도 못 찾을 수 있습니다. 실제로 며칠 사용해보시고
자주 "파악중"으로 나오는 항목이 있으면, 그 항목의 정규식 패턴만 다듬어서
정확도를 올리는 방식으로 튜닝해나가는 걸 권장합니다 (각 함수가 독립적이라
하나씩 고쳐도 다른 부분에 영향 없습니다).
"""
import re
from datetime import datetime

UNKNOWN = "파악중"


# ── 공통 유틸 ───────────────────────────────────────────────────

def format_date(value) -> str:
    """datetime 객체 또는 'YYYYMMDD...' 형태 문자열을 'YY.MM.DD'로 변환."""
    try:
        if isinstance(value, datetime):
            return value.strftime("%y.%m.%d")
        digits = re.sub(r"\D", "", str(value))
        if len(digits) >= 8:
            return f"{digits[2:4]}.{digits[4:6]}.{digits[6:8]}"
    except Exception:
        pass
    return UNKNOWN


def format_amount(won) -> str:
    """원 단위 금액을 'X.X억원(VAT포함)' 형태로 변환. (금액 자체가 이미 부가세 포함 기준이라고 가정)"""
    try:
        amount = float(won)
        return f"{amount / 1e8:.1f}억원(VAT포함)"
    except (TypeError, ValueError):
        return UNKNOWN


# ── 텍스트 기반 추출 함수들 ───────────────────────────────────────

def extract_period(text: str) -> str:
    m = re.search(r"(\d+)\s*개월", text or "")
    return f"{m.group(1)}개월" if m else UNKNOWN


def extract_eval_method(text: str) -> str:
    """
    - 면접 평가 점수(면접OO점)가 실제로 발견될 때만 면접 형식 적용:
      면접{점수}점(책임{점수}점, 분야별기술인{점수}점)
    - 그 외(TP/SOQ/종심제)는 방법명만, 여러 개면 '또는'으로 연결
    주의: 본문에 "면접" 이라는 글자가 있어도(예: 일정표의 "면접 일정") 점수 표기가
    없으면 평가방법이 아니라 다른 맥락으로 보고 무시합니다.
    """
    text = text or ""
    score_m = re.search(r"면접\s*(\d+)\s*점", text)
    if score_m:
        chief_m = re.search(r"책임\D{0,10}?(\d+)\s*점", text)
        field_m = re.search(r"분야별\s*기술인\D{0,10}?(\d+)\s*점", text)
        parts = []
        if chief_m:
            parts.append(f"책임{chief_m.group(1)}점")
        if field_m:
            parts.append(f"분야별기술인{field_m.group(1)}점")
        member_str = ", ".join(parts) if parts else UNKNOWN
        return f"면접{score_m.group(1)}점({member_str})"

    methods = []
    if "TP" in text:
        methods.append("TP")
    if "SOQ" in text:
        methods.append("SOQ")
    if re.search(r"종합심사낙찰|종심제|종심", text):
        methods.append("종심제")
    return " 또는 ".join(methods) if methods else UNKNOWN


def extract_joint(text: str):
    """공동도급 개사 수 / 최소 지분율(%) 반환"""
    text = text or ""
    count_m = re.search(r"공동(?:수급|도급)\D{0,10}?(\d+)\s*개\s*사", text)
    pct_m = re.search(r"최소\s*(\d+(?:\.\d+)?)\s*%", text)
    return (
        count_m.group(1) if count_m else UNKNOWN,
        pct_m.group(1) if pct_m else UNKNOWN,
    )


def extract_split_ratio(text: str) -> str:
    """CM 분담비율: 건설/전기/통신/소방 4개 분야가 전부 확인될 때만 값을 채움."""
    text = text or ""
    disciplines = ["건설", "전기", "통신", "소방"]
    parts = []
    for d in disciplines:
        m = re.search(rf"{d}\s*(\d+(?:\.\d+)?)\s*%", text)
        if not m:
            return UNKNOWN
        parts.append(f"소방{m.group(1)}%" if d == "소방" else f"{d} {m.group(1)}%")
    return ", ".join(parts)


def extract_area(text: str, dual: bool = False):
    text = text or ""
    if dual:
        m = re.search(r"연면적\D{0,15}?([\d,\.]+)\s*㎡\s*/\s*([\d,\.]+)\s*㎡", text)
        if m:
            return m.group(1), m.group(2)
        return UNKNOWN, UNKNOWN
    m = re.search(r"연면적\D{0,15}?([\d,\.]+)\s*㎡", text)
    return m.group(1) if m else UNKNOWN


def extract_scale(text: str) -> str:
    text = text or ""
    m = re.search(r"(지하\s*\d+\s*층\s*~\s*지상\s*\d+\s*층|B\d+\s*~\s*\d+\s*층\s*\d*개?동?)", text)
    return m.group(1) if m else UNKNOWN


def extract_const_cost(text: str) -> str:
    m = re.search(r"공사비\D{0,10}?([\d,\.]+)\s*억", text or "")
    return f"{m.group(1)}억원(VAT포함)" if m else UNKNOWN


def extract_overview_name(text: str) -> str:
    m = re.search(r"개\s*요\s*[:：]\s*([^\n]+)", text or "")
    return m.group(1).strip() if m else UNKNOWN


def extract_committee(text: str):
    """정성평가 위원수 - '시공:8명, 구조:1명' 같은 표현에서 분야별 인원과 총원을 추출."""
    matches = re.findall(r"(시공|구조|토목|기계|전기|통신|소방|건축)\s*[:：]?\s*(\d+)\s*명", text or "")
    if not matches:
        return UNKNOWN, UNKNOWN
    total = sum(int(n) for _, n in matches)
    breakdown = ", ".join(f"{d}:{n}명" for d, n in matches)
    return str(total), breakdown


def extract_grades(text: str):
    """
    책임/분야/기술지원 등급 추출.
    - 책임: '건축N급' 매칭 우선, 없으면 처음 발견된 등급
    - 기술지원: 텍스트에서 '기술지원' 단어 뒤 200자 이내에 나오는 등급들
    - 분야: 나머지(책임/기술지원에 안 걸린) 등급들
    """
    text = text or ""
    all_matches = re.findall(r"(건축|토목|기계|전기|통신|소방|구조)\s*([1-9])\s*급", text)
    dedup = []
    seen = set()
    for d, g in all_matches:
        key = f"{d}{g}급"
        if key not in seen:
            seen.add(key)
            dedup.append(key)

    if not dedup:
        return UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN

    chief = next((x for x in dedup if x.startswith("건축")), dedup[0])

    support_list = []
    idx = text.find("기술지원")
    if idx != -1:
        tail = text[idx: idx + 200]
        support_list = [f"{d}{g}급" for d, g in re.findall(r"(건축|토목|기계|전기|통신|소방|구조)\s*([1-9])\s*급", tail)]

    field_list = [x for x in dedup if x != chief and x not in support_list]

    field_count = str(len(field_list)) if field_list else UNKNOWN
    support_count = str(len(support_list)) if support_list else UNKNOWN
    field_list_str = ", ".join(field_list) if field_list else UNKNOWN
    support_list_str = ", ".join(support_list) if support_list else UNKNOWN
    return chief, field_count, field_list_str, support_count, support_list_str


def extract_schedule_date(text: str, label_keywords: list) -> str:
    """라벨 키워드 주변(뒤 50자 이내)에서 날짜 형식(YYYY.MM.DD 등)을 찾음."""
    text = text or ""
    for kw in label_keywords:
        idx = text.find(kw)
        if idx == -1:
            continue
        tail = text[idx: idx + 50]
        m = re.search(r"(\d{2,4}[.\-/]\d{1,2}[.\-/]\d{1,2})", tail)
        if m:
            return m.group(1)
    return UNKNOWN


def extract_manager(text: str, demand_agency: str) -> str:
    """담당 : 발주처명 / 담당자명(전화번호) 형식"""
    text = text or ""
    name_m = re.search(r"담당자?\s*[:：]?\s*([가-힣]{2,4})", text)
    phone_m = re.search(r"(0\d{1,2}-?\d{3,4}-?\d{4})", text)
    if name_m and phone_m:
        agency_disp = demand_agency or UNKNOWN
        return f"{agency_disp} / {name_m.group(1)}({phone_m.group(1)})"
    return UNKNOWN


# ── 템플릿별 조립 함수 ───────────────────────────────────────────

def build_fields_bid_housing(name, notice_date, agency, demand_agency, amount_won, raw_text):
    area1, area2 = extract_area(raw_text, dual=True)
    joint_count, joint_pct = extract_joint(raw_text)
    chief, field_count, field_list, support_count, support_list = extract_grades(raw_text)
    committee_total, committee_breakdown = extract_committee(raw_text)
    return {
        "date": format_date(notice_date),
        "name": name or UNKNOWN,
        "agency": agency or UNKNOWN,
        "demand_agency": demand_agency or UNKNOWN,
        "amount": format_amount(amount_won),
        "period": extract_period(raw_text),
        "eval_method": extract_eval_method(raw_text),
        "joint_count": joint_count,
        "joint_pct": joint_pct,
        "overview_name": extract_overview_name(raw_text),
        "block": UNKNOWN,  # 블록 표기는 문서마다 형식이 제각각이라 기본 파악중 (필요시 정규식 추가)
        "area1": area1,
        "area2": area2,
        "scale": extract_scale(raw_text),
        "const_cost": extract_const_cost(raw_text),
        "chief_grade": chief,
        "field_count": field_count,
        "field_list": field_list,
        "support_count": support_count,
        "support_list": support_list,
        "committee_total": committee_total,
        "committee_breakdown": committee_breakdown,
        "sched_fire_pq": extract_schedule_date(raw_text, ["소방PQ", "협정서"]),
        "sched_proposal": extract_schedule_date(raw_text, ["제안서"]),
        "sched_bid": extract_schedule_date(raw_text, ["입찰"]),
        "sched_review": extract_schedule_date(raw_text, ["심사"]),
    }


def build_fields_bid_cm(name, notice_date, agency, demand_agency, amount_won, raw_text):
    joint_count, joint_pct = extract_joint(raw_text)
    chief, field_count, field_list, support_count, support_list = extract_grades(raw_text)
    committee_total, _ = extract_committee(raw_text)
    return {
        "date": format_date(notice_date),
        "name": name or UNKNOWN,
        "agency": agency or UNKNOWN,
        "demand_agency": demand_agency or UNKNOWN,
        "amount": format_amount(amount_won),
        "period": extract_period(raw_text),
        "eval_method": extract_eval_method(raw_text),
        "joint_count": joint_count,
        "joint_pct": joint_pct,
        "split_ratio": extract_split_ratio(raw_text),
        "overview_name": extract_overview_name(raw_text),
        "area": extract_area(raw_text, dual=False),
        "scale": extract_scale(raw_text),
        "const_cost": extract_const_cost(raw_text),
        "chief_grade": chief,
        "field_count": field_count,
        "field_list": field_list,
        "support_count": support_count,
        "support_list": support_list,
        "committee_total": committee_total,
        "sched_register_pq": extract_schedule_date(raw_text, ["등록", "PQ"]),
        "sched_agreement": extract_schedule_date(raw_text, ["협정서"]),
        "sched_proposal": extract_schedule_date(raw_text, ["제안서"]),
        "sched_interview": extract_schedule_date(raw_text, ["면접"]),
        "sched_open": extract_schedule_date(raw_text, ["개찰"]),
    }


def build_fields_order_plan(name, notice_date, agency, demand_agency, amount_won, raw_text):
    return {
        "date": format_date(notice_date),
        "name": name or UNKNOWN,
        "agency": agency or UNKNOWN,
        "demand_agency": demand_agency or UNKNOWN,
        "amount": format_amount(amount_won),
        "eval_method": extract_eval_method(raw_text),
        "order_time": UNKNOWN,  # 발주시기는 항상 파악중 고정 (요청사항)
        "manager": extract_manager(raw_text, demand_agency),
    }


def build_fields_pre_spec(name, notice_date, agency, demand_agency, amount_won, raw_text):
    chief, field_count, field_list, support_count, support_list = extract_grades(raw_text)
    committee_total, _ = extract_committee(raw_text)
    return {
        "date": format_date(notice_date),
        "name": name or UNKNOWN,
        "agency": agency or UNKNOWN,
        "demand_agency": demand_agency or UNKNOWN,
        "amount": format_amount(amount_won),
        "period": extract_period(raw_text),
        "eval_method": extract_eval_method(raw_text),
        "area": extract_area(raw_text, dual=False),
        "scale": extract_scale(raw_text),
        "const_cost": extract_const_cost(raw_text),
        "committee_total": committee_total,
        "chief_grade": chief,
        "field_count": field_count,
        "field_list": field_list,
        "support_count": support_count,
        "support_list": support_list,
        "order_time": UNKNOWN,  # 발주시기는 항상 파악중 고정 (요청사항)
        "manager": extract_manager(raw_text, demand_agency),
    }
