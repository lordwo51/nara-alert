# -*- coding: utf-8 -*-
"""
중복 알림 방지용 저장소.
같은 공고/사전규격/발주계획을 실행할 때마다 다시 보내지 않도록,
한 번 알림을 보낸 항목의 고유 ID를 seen_items.json에 기록해둡니다.

간단한 로컬 파일 기반이라 여러 대의 서버에서 동시에 돌리는 상황은 고려하지 않았습니다.
(개인/소규모 용도 기준)
"""
import json
import os

from config import SEEN_STORE_PATH


def load_seen() -> set:
    if not os.path.exists(SEEN_STORE_PATH):
        return set()
    try:
        with open(SEEN_STORE_PATH, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_seen(seen_ids: set):
    # 파일이 무한정 커지지 않도록 최근 5000개만 유지
    trimmed = list(seen_ids)[-5000:]
    with open(SEEN_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(trimmed, f, ensure_ascii=False)
