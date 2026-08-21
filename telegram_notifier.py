# -*- coding: utf-8 -*-
"""텔레그램으로 메시지를 보내는 모듈"""
import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS
import field_extractor as fx
import templates


def send_message(text: str) -> bool:
    """
    등록된 모든 chat_id(개인 + 그룹 등)에 같은 메시지를 보냅니다.
    TELEGRAM_CHAT_ID에 콤마(,)로 여러 개를 넣어두면 전부에게 발송됩니다.
    하나 이상 성공하면 True를 반환합니다 (다음 실행에서 이 알림을 다시 안 보내도록).
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        print("[텔레그램 설정 누락] TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID를 .env에 설정하세요.")
        print("--- 아래 내용을 대신 콘솔에 출력합니다 ---")
        print(text)
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    any_success = False
    for chat_id in TELEGRAM_CHAT_IDS:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        try:
            resp = requests.post(url, data=payload, timeout=15)
            resp.raise_for_status()
            any_success = True
        except Exception as e:
            print(f"[텔레그램 전송 실패] chat_id={chat_id}: {e}")
            print(text)
    return any_success


def format_alert(item: dict) -> str:
    """
    filters.classify()가 반환한 dict를 사용자가 지정한 4가지 양식 중
    (source, law_type) 조합에 맞는 것으로 렌더링합니다.
      - 입찰공고 + 건진법 -> 본공고(CM) 양식
      - 입찰공고 + 주택법 -> 본공고(주택법) 양식
      - 사전규격           -> 사전규격 양식
      - 발주계획           -> 발주계획 양식
    """
    source = item["source"]
    law_type = item["law_type"]
    raw_text = item.get("raw_text", "")

    common_args = (
        item["name"],
        item["notice_date"],
        item["agency"],
        item["demand_agency"],
        item["amount"],
        raw_text,
    )

    if source == "입찰공고" and law_type == "gunjin":
        fields = fx.build_fields_bid_cm(*common_args)
        return templates.render_bid_cm(fields)
    if source == "입찰공고" and law_type == "housing":
        fields = fx.build_fields_bid_housing(*common_args)
        return templates.render_bid_housing(fields)
    if source == "사전규격":
        fields = fx.build_fields_pre_spec(*common_args)
        return templates.render_pre_spec(fields)
    if source == "발주계획":
        fields = fx.build_fields_order_plan(*common_args)
        return templates.render_order_plan(fields)

    # 예상치 못한 조합에 대한 안전장치 (정상 흐름에서는 발생하지 않아야 함)
    return f"[{source}] {item['name']}\n(양식 매칭 실패 - 원본 정보)\n{item}"
