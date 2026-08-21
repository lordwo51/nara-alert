# -*- coding: utf-8 -*-
"""
나라장터 오픈API 호출 모듈 (업무구분: 용역 전용)

사용하는 3개 API (모두 공공데이터포털 data.go.kr 에서 활용신청):
  1. 조달청_나라장터 입찰공고정보서비스   -> 입찰공고(용역) 목록 + e발주 첨부파일
  2. 조달청_나라장터 사전규격정보서비스   -> 사전규격(용역) 목록
  3. 조달청_나라장터 발주계획현황서비스   -> 발주계획(용역) 목록

주의: data.go.kr은 운영기관 사정으로 오퍼레이션명이 바뀔 수 있습니다.
      만약 아래 요청이 계속 실패한다면, 해당 서비스의 "Swagger UI" 페이지에서
      정확한 오퍼레이션명을 다시 확인해 아래 *_OP 상수만 수정하면 됩니다.
"""
import time
import requests
from datetime import datetime, timedelta

from config import NARA_SERVICE_KEY, LOOKBACK_DAYS, ROWS_PER_PAGE, MAX_PAGES

BID_BASE = "http://apis.data.go.kr/1230000/ad/BidPublicInfoService"
BID_OP = "getBidPblancListInfoServcPPSSrch"           # 입찰공고(용역) 목록
EORDER_OP = "getBidPblancListInfoEorderAtchFileInfo"  # e발주 첨부파일(제안요청서 등)

PRESPEC_BASE = "http://apis.data.go.kr/1230000/ao/HrcspSsstndrdInfoService"
PRESPEC_OP = "getPublicPrcureThngInfoServcPPSSrch"    # 사전규격(용역) 목록

ORDERPLAN_BASE = "http://apis.data.go.kr/1230000/ao/OrderPlanSttusService"
ORDERPLAN_OP = "getOrderPlanSttusListServc"           # 발주계획(용역) 목록


def _date_range(days=None):
    days = days or LOOKBACK_DAYS
    end = datetime.now()
    start = end - timedelta(days=days)
    return start.strftime("%Y%m%d0000"), end.strftime("%Y%m%d2359")


def _get_items(url, params):
    """공통 응답 파싱: items가 dict/list/빈 문자열 등 제각각으로 오는 것을 모두 흡수."""
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[API 오류] {url} 요청 실패: {e}")
        return []

    header = data.get("response", {}).get("header", {})
    if header.get("resultCode") != "00":
        print(f"[API 응답 오류] {url}: {header.get('resultCode')} {header.get('resultMsg')}")
        return []

    body = data.get("response", {}).get("body", {})
    items = body.get("items")
    if not items or isinstance(items, str):
        return []
    if isinstance(items, dict):
        raw = items.get("item", [])
        return [raw] if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
    if isinstance(items, list):
        return items
    return []


def _paged_fetch(base_url, operation, extra_params):
    """여러 페이지를 순회하며 모든 결과를 모읍니다 (최대 MAX_PAGES 페이지까지)."""
    all_items = []
    url = f"{base_url}/{operation}"
    for page in range(1, MAX_PAGES + 1):
        params = {
            "ServiceKey": NARA_SERVICE_KEY,
            "type": "json",
            "numOfRows": ROWS_PER_PAGE,
            "pageNo": page,
            **extra_params,
        }
        items = _get_items(url, params)
        all_items.extend(items)
        if len(items) < ROWS_PER_PAGE:
            break
        time.sleep(0.2)  # API 과호출 방지
    return all_items


def fetch_bid_notices():
    """최근 N일 이내 등록된 용역 입찰공고 목록"""
    start, end = _date_range()
    return _paged_fetch(BID_BASE, BID_OP, {
        "inqryDiv": "1",
        "inqryBgnDt": start,
        "inqryEndDt": end,
    })


def fetch_eorder_attachments(bid_ntce_no):
    """공고번호로 e발주 첨부파일(제안요청서 등) 조회. 없으면 빈 리스트."""
    url = f"{BID_BASE}/{EORDER_OP}"
    params = {
        "ServiceKey": NARA_SERVICE_KEY,
        "type": "json",
        "inqryDiv": "2",
        "bidNtceNo": bid_ntce_no,
        "numOfRows": 10,
        "pageNo": 1,
    }
    return _get_items(url, params)


def fetch_pre_specs():
    """최근 N일 이내 등록된 용역 사전규격 목록"""
    start, end = _date_range()
    return _paged_fetch(PRESPEC_BASE, PRESPEC_OP, {
        "inqryDiv": "1",
        "inqryBgnDt": start,
        "inqryEndDt": end,
    })


def fetch_order_plans():
    """최근 N일 이내 등록된 용역 발주계획 목록"""
    start, end = _date_range()
    return _paged_fetch(ORDERPLAN_BASE, ORDERPLAN_OP, {
        "inqryDiv": "1",
        "inqryBgnDt": start,
        "inqryEndDt": end,
    })
