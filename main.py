# -*- coding: utf-8 -*-
"""
나라장터 용역 (입찰공고 + 사전규격 + 발주계획) 텔레그램 알림 - 메인 실행 파일

실행:
    python main.py

cron / GitHub Actions 등으로 주기적으로 이 스크립트를 실행하면 됩니다.
(README.md 참고)
"""
import sys

import api_client
from filters import (
    classify,
    best_amount,
    first_nonempty,
    get_bid_attachments,
    get_prespec_attachments,
)
from telegram_notifier import send_message, format_alert
from seen_store import load_seen, save_seen
from scheduler import should_run_now

# 주택법/건진법 둘 다 첨부파일(제안요청서 등) 본문이 필요하므로,
# 첨부파일이 없는 공고는 e발주 탭도 확인합니다 (두 법 키워드 모두 대상).
ALL_LAW_KEYWORDS = ["주택법", "감리", "감리자", "주택", "건설사업관리", "CM", "건설기술용역"]


def process_bid_notices(seen: set) -> list:
    alerts = []
    items = api_client.fetch_bid_notices()
    print(f"[입찰공고] {len(items)}건 조회됨")

    for item in items:
        bid_no = item.get("bidNtceNo", "")
        bid_ord = item.get("bidNtceOrd", "00")  # 차수: 정정공고는 같은 공고번호 + 차수만 증가
        # 공고번호+차수를 합쳐서 판정 -> 최초공고와 정정공고를 서로 다른 알림으로 취급
        uid = f"bid:{bid_no}:{bid_ord}"
        if not bid_no or uid in seen:
            continue

        name = item.get("bidNtceNm", "")
        notice_agency = item.get("ntceInsttNm", "정보없음")   # 공고기관 (예: 조달청)
        demand_agency = item.get("dminsttNm", "정보없음")     # 수요기관 (예: 한국토지주택공사)
        amount = best_amount(item, ["bdgtAmt", "presmptPrce", "bssamt"])
        notice_date = item.get("bidNtceDt") or item.get("bidNtceBgnDt", "")
        url = item.get("bidNtceDtlUrl", "")
        is_correction = str(bid_ord) not in ("0", "00", "", "None")

        attachments = get_bid_attachments(item, [])
        if not attachments and any(k in name for k in ALL_LAW_KEYWORDS):
            eorder_files = api_client.fetch_eorder_attachments(bid_no)
            eorder_pairs = [
                (f.get("eorderAtchFileUrl", ""), f.get("eorderAtchFileNm", ""))
                for f in eorder_files
                if f.get("eorderAtchFileUrl")
            ]
            attachments = get_bid_attachments(item, eorder_pairs)

        result = classify(name, notice_agency, demand_agency, amount, attachments, notice_date, url, "입찰공고")
        if result:
            if is_correction:
                result["source"] = f"{result['source']} · 정정공고({bid_ord}차)"
            alerts.append((uid, result))

    return alerts


def process_pre_specs(seen: set) -> list:
    alerts = []
    items = api_client.fetch_pre_specs()
    print(f"[사전규격] {len(items)}건 조회됨")

    for item in items:
        spec_no = item.get("bfSpecRgstNo", "")
        uid = f"prespec:{spec_no}"
        if not spec_no or uid in seen:
            continue

        name = item.get("prdctClsfcNoNm", "")
        notice_agency = item.get("orderInsttNm", "정보없음")
        demand_agency = item.get("dmndInsttNm") or item.get("orderInsttNm", "정보없음")
        amount = best_amount(item, ["asignBdgtAmt", "bdgtAmt"])
        notice_date = item.get("rgstDt") or item.get("opninRgstClseDt", "")
        attachments = get_prespec_attachments(item)

        result = classify(name, notice_agency, demand_agency, amount, attachments, notice_date, "", "사전규격")
        if result:
            alerts.append((uid, result))

    return alerts


def process_order_plans(seen: set) -> list:
    """
    발주계획현황서비스는 응답 필드명이 문서화가 부족해 후보 필드명을 여러 개 시도합니다.
    실제 승인 후 첫 실행에서 콘솔에 raw item을 한 번 출력해보고,
    아래 candidate 리스트를 실제 필드명에 맞게 다듬어주시면 정확도가 올라갑니다.
    """
    alerts = []
    items = api_client.fetch_order_plans()
    print(f"[발주계획] {len(items)}건 조회됨")

    for idx, item in enumerate(items):
        name = first_nonempty(item, ["prdctClsfcNoNm", "orderPlanNm", "bizNm", "cntrctNm", "orderNm"], default="")
        if not name:
            continue

        raw_id = first_nonempty(
            item, ["orderPlanUntyNo", "orderNo", "untyNo", "orderPlanNo"], default=""
        )
        uid = f"orderplan:{raw_id or (name + str(idx))}"
        if uid in seen:
            continue

        notice_agency = first_nonempty(item, ["orderInsttNm", "ordInsttNm"], default="정보없음")
        demand_agency = first_nonempty(item, ["dminsttNm", "orderInsttNm"], default="정보없음")
        amount = best_amount(item, ["asignBdgtAmt", "orderPrearngeAmt", "bdgtAmt", "orderPrceAmt"])
        notice_date = first_nonempty(item, ["rgstDt", "orderPrearngeDate"], default="")

        # 발주계획 단계에는 보통 첨부파일이 없어, 있는 경우가 드뭅니다 -> 빈 리스트로 처리
        # (=주택법 건은 자동으로 금액기준 대체 로직이 적용됩니다)
        result = classify(name, notice_agency, demand_agency, amount, [], notice_date, "", "발주계획")
        if result:
            alerts.append((uid, result))

    return alerts


def main():
    run_ok, reason = should_run_now()
    print(f"[스케줄 체크] {reason}")
    if not run_ok:
        return  # 이번 10분 틱은 스킵 (API 호출 없음)

    seen = load_seen()
    all_alerts = []

    all_alerts += process_bid_notices(seen)
    all_alerts += process_pre_specs(seen)
    all_alerts += process_order_plans(seen)

    if not all_alerts:
        print("알림 대상 없음.")
        save_seen(seen)  # 알림이 없어도 파일은 항상 만들어둠 (다음 git add 실패 방지)
        return

    print(f"총 {len(all_alerts)}건 알림 발송 시작")
    for uid, result in all_alerts:
        message = format_alert(result)
        sent = send_message(message)
        if sent:
            seen.add(uid)

    save_seen(seen)
    print("완료.")


if __name__ == "__main__":
    sys.exit(main())
