# -*- coding: utf-8 -*-
"""
텔레그램 메시지 템플릿

아래 4개 함수는 사용자가 지정한 양식을 "띄어쓰기까지 그대로" 재현합니다.
필드 값이 확인되지 않으면 항상 "파악중"으로 채워지며(추측 금지),
메시지 안에 "파악중"이 하나라도 있으면 맨 마지막 줄에 경고 문구가 자동으로 붙습니다.

fields 딕셔너리의 각 값은 이미 "화면에 표시될 최종 문자열" 형태로
field_extractor.py에서 만들어져 넘어옵니다 (예: "1,500.0억(VAT포함)").
"""

CONFIRM_FOOTER = "\n\n* 확인이 필요합니다."


def _needs_confirmation(fields: dict) -> bool:
    return any(v == "파악중" for v in fields.values())


def _with_footer(text: str, fields: dict) -> str:
    if _needs_confirmation(fields):
        return text + CONFIRM_FOOTER
    return text


def render_bid_housing(f: dict) -> str:
    """[본공고] 주택법(공동주택 등) 대상 용역"""
    body = f"""[본공고] -{f['date']}-

1. {f['name']}

(1) 공고/수요기관 : {f['agency']}/{f['demand_agency']}
(2) 용역금액/기간 : {f['amount']}/{f['period']}
(3) 평가방법 : {f['eval_method']}
(4) 공동도급 : {f['joint_count']}개사 이내(최소{f['joint_pct']}%)
(5) 개 요 : {f['overview_name']}
  - 블 록 : {f['block']}
  - 연면적 : {f['area1']}㎡/{f['area2']}㎡
  - 규 모 : {f['scale']}
  - 공사비 : {f['const_cost']}
(6) 평가대상
  - 책임({f['chief_grade']})
  - 분야{f['field_count']}인 : {f['field_list']}
  - 기술지원{f['support_count']}인 : {f['support_list']}
(7) 정성평가 위원수({f['committee_total']}명)
  - {f['committee_breakdown']}
(8) 추진일정
- 소방PQ 및 협정서 : {f['sched_fire_pq']}
- 제안서 : {f['sched_proposal']}
- 입 찰 : {f['sched_bid']}
- 심 사 : {f['sched_review']}"""
    return _with_footer(body, f)


def render_bid_cm(f: dict) -> str:
    """[본공고] CM(건진법) 대상 용역"""
    body = f"""[본공고] -{f['date']}-

1. {f['name']}

(1) 공고/수요기관 : {f['agency']}/{f['demand_agency']}
(2) 용역금액/기간 : {f['amount']}/{f['period']}
(3) 평가방법 : {f['eval_method']}
(4) 공동도급 : {f['joint_count']}개사 이내(최소{f['joint_pct']}%)
(5) 분담비율 : {f['split_ratio']}
(6) 개 요 : {f['overview_name']}
- 연면적 : {f['area']}㎡
- 규 모 : {f['scale']}
- 공사비 : {f['const_cost']}
(7) 평가대상 (총{f['committee_total']}명)
 - 책임({f['chief_grade']})
  - 분야{f['field_count']}인 : {f['field_list']}
  - 기술지원{f['support_count']}인 : {f['support_list']}
(8) 추진일정
- 등록 및 PQ : {f['sched_register_pq']}
- 협정서 : {f['sched_agreement']}
- 제안서 : {f['sched_proposal']}
- 면 접 : {f['sched_interview']}
- 개 찰 : {f['sched_open']}"""
    return _with_footer(body, f)


def render_order_plan(f: dict) -> str:
    """[발주계획]"""
    body = f"""[발주계획] -{f['date']}-
* {f['name']}
(1) 공고/수요기관 : {f['agency']}/{f['demand_agency']}
(2) 용역금액 : {f['amount']}
(3) 평가방법 : {f['eval_method']}
(4) 발주시기 : {f['order_time']}
(5) 담      당 : {f['manager']}"""
    return _with_footer(body, f)


def render_pre_spec(f: dict) -> str:
    """[사전규격]"""
    body = f"""[사전규격] -{f['date']}-
* {f['name']}
(1) 공고/수요기관 : {f['agency']}/{f['demand_agency']}
(2) 용역금액/기간 : {f['amount']} / {f['period']}
(3) 평가방법 : {f['eval_method']}
(4) 개      요
  - 연면적 : {f['area']}㎡
  - 규   모 : {f['scale']}
  - 공사비 : {f['const_cost']}
(5)  평가대상 (총{f['committee_total']}명)
 - 책임({f['chief_grade']})
 - 분야{f['field_count']}인 : {f['field_list']}
 - 기술지원{f['support_count']}인 : {f['support_list']}
(6) 발주시기 : {f['order_time']}
(7) 담      당 : {f['manager']}"""
    return _with_footer(body, f)
