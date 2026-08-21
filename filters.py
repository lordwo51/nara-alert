# -*- coding: utf-8 -*-
"""
핵심 필터링 로직

1) 공고명(사업명)에 건진법 키워드가 있으면 -> 금액 10억 이상일 때만 알림
2) 공고명(사업명)에 주택법 키워드가 있으면
   - 첨부파일에서 텍스트 추출 성공 -> "면접" 단어가 있을 때만 알림
   - 첨부파일이 없거나 텍스트 추출 실패 -> 금액 10억 이상일 때만 알림 (⚠ 표시)
"""
from config import (
    AMOUNT_THRESHOLD_WON,
    GUNJIN_KEYWORDS,
    HOUSING_KEYWORDS,
    INTERVIEW_KEYWORD,
)
from file_extractor import download_and_extract, contains_keyword


def to_amount(value) -> int:
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0


def best_amount(item: dict, keys: list) -> int:
    """여러 후보 필드명 중 가장 큰 금액을 반환 (필드명이 소스마다 달라서 후보를 여러 개 시도)."""
    return max((to_amount(item.get(k, 0)) for k in keys), default=0)


def first_nonempty(item: dict, keys: list, default="정보없음"):
    for k in keys:
        v = item.get(k)
        if v:
            return v
    return default


def matched_keywords(name: str, keywords: list) -> list:
    return [k for k in keywords if k in (name or "")]


def get_bid_attachments(item: dict, eorder_files: list) -> list:
    """입찰공고 항목의 첨부파일 (ntceSpecDocUrl1~10) + e발주 첨부파일을 합쳐서 반환.
    반환: [(url, filename), ...]
    """
    files = []
    for i in range(1, 11):
        url = item.get(f"ntceSpecDocUrl{i}", "")
        name = item.get(f"ntceSpecFileNm{i}", "")
        if url:
            files.append((url, name or f"첨부파일{i}"))
    for url, name in eorder_files:
        files.append((url, name))
    return files


def get_prespec_attachments(item: dict) -> list:
    files = []
    for i in range(1, 6):
        url = item.get(f"specDocFileUrl{i}", "")
        if url:
            files.append((url, f"규격문서{i}"))
    return files


def extract_combined_text(attachments: list) -> tuple:
    """
    첨부파일 목록을 다운로드해서 텍스트를 합칩니다.
    반환: (합쳐진 텍스트, 추출 성공 여부)
    첨부파일이 있어도 전부 추출 실패하면 성공 여부 False -> 호출부에서 "확인 불가"로 처리.
    """
    if not attachments:
        return "", False

    combined = []
    any_success = False
    for url, name in attachments:
        text = download_and_extract(url, name)
        if text.strip():
            any_success = True
            combined.append(text)
    return "\n".join(combined), any_success


def classify(name: str, agency: str, demand_agency: str, amount: int, attachments: list,
             notice_date, url: str, source_label: str):
    """
    공고 1건을 판별합니다.
    반환값: None (알림 대상 아님) 또는 알림용 dict
      - law_type: 'gunjin' | 'housing'  (메시지 템플릿 선택에 사용)
      - raw_text: 첨부파일에서 추출된 본문 텍스트 (템플릿 필드 추출에 재사용)
    """
    gunjin_hits = matched_keywords(name, GUNJIN_KEYWORDS)
    housing_hits = matched_keywords(name, HOUSING_KEYWORDS)

    if not gunjin_hits and not housing_hits:
        return None

    combined_text, extracted_ok = extract_combined_text(attachments)

    # ── 건진법 대상 ──────────────────────────────────────
    if gunjin_hits:
        if amount >= AMOUNT_THRESHOLD_WON:
            return {
                "law": "건진법(건설기술진흥법)",
                "law_type": "gunjin",
                "matched_keyword": ", ".join(gunjin_hits),
                "reason": f"금액 {amount:,}원 ≥ 10억원",
                "name": name,
                "agency": agency,
                "demand_agency": demand_agency,
                "amount": amount,
                "notice_date": notice_date,
                "url": url,
                "source": source_label,
                "raw_text": combined_text,
            }
        return None

    # ── 주택법 대상 ──────────────────────────────────────
    if housing_hits:
        if attachments and extracted_ok:
            if contains_keyword(combined_text, INTERVIEW_KEYWORD):
                return {
                    "law": "주택법",
                    "law_type": "housing",
                    "matched_keyword": ", ".join(housing_hits),
                    "reason": "첨부파일 본문에서 '면접' 확인",
                    "name": name,
                    "agency": agency,
                    "demand_agency": demand_agency,
                    "amount": amount,
                    "notice_date": notice_date,
                    "url": url,
                    "source": source_label,
                    "raw_text": combined_text,
                }
            return None  # 첨부파일은 있지만 '면접' 없음 -> 알림 안 함

        # 첨부파일이 없거나(=attachments 비어있음), 있어도 텍스트 추출을 전부 실패한 경우
        if amount >= AMOUNT_THRESHOLD_WON:
            note = "첨부파일 없음" if not attachments else "첨부파일 본문 확인 실패"
            return {
                "law": "주택법",
                "law_type": "housing",
                "matched_keyword": ", ".join(housing_hits),
                "reason": f"⚠ {note} → 금액기준 적용 ({amount:,}원 ≥ 10억원)",
                "name": name,
                "agency": agency,
                "demand_agency": demand_agency,
                "amount": amount,
                "notice_date": notice_date,
                "url": url,
                "source": source_label,
                "raw_text": combined_text,
            }
        return None

    return None
