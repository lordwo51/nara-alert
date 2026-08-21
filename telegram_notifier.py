# -*- coding: utf-8 -*-
"""텔레그램으로 메시지를 보내는 모듈"""
import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import field_extractor as fx
import templates


def send_message(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[텔레그램 설정 누락] TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID를 .env에 설정하세요.")
        print("--- 아래 내용을 대신 콘솔에 출력합니다 ---")
        print(text)
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, data=payload, timeout=15)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[텔레그램 전송 실패] {e}")
        print(text)
        return False


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
