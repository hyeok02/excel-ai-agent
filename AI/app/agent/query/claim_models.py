"""The model selects source bindings; it cannot author a verified value or predicate."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SourceClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["cell_value", "verified_fact", "unknown"]
    value_reference: str | None = Field(default=None, max_length=200)
    subject_reference: str | None = Field(default=None, max_length=200)
    property_reference: str | None = Field(default=None, max_length=200)
    period_reference: str | None = Field(default=None, max_length=200)
    fact: str | None = Field(default=None, max_length=2000)


CLAIM_INSTRUCTIONS = """
claims에 답변을 원자적 주장으로 나눠 넣으세요. 질문·대화·인사이트 제목은 사실 근거가 아닙니다.
cell_value: value_reference에 원본 값 셀 주소를 적으세요. 같은 행의 대상/기간 셀이
있으면 subject_reference/period_reference에, 실제 원본 열 머리글은 property_reference에
적으세요. 값이나 상태 해석은 쓰지 마세요. 서버가 해당 주소의 실제 값으로 답을 구성합니다.
서로 다른 행의 대상·기간, 다른 열의 머리글을 연결하지 마세요. 복잡한 배치는 셀 단독으로
인용하고 관계를 추측하지 마세요. 같은 열 이름에 있는 두 명칭이 같은 작업이라는 뜻은 아닙니다.
x/o/△/공백 등의 표시는 범례 없이 성공·실패·정상·불량·완료 등으로 해석하지 마세요.
verified_fact: 현재 Tool data.verified_insights의 질문에 맞는 fact 전체를 그대로 복사하세요.
그 fact의 모든 support_references(없으면 required_references)를 evidence에 포함하세요.
unknown: 의미·원인·관계 등을 원본에서 확인할 수 없을 때 사용하세요. 해당 해석을
사실로 쓰지 마세요. 확인 가능한 cell_value/verified_fact와 함께 내보내면 그 사실은 유지됩니다.
모든 참조는 현재 Tool evidence에 존재해야 하며 대화에만 나온 주소는 사용할 수 없습니다.
claims가 있으면 answer의 자유 서술은 표시하지 않고 서버에서 검증·재구성한 주장만 표시합니다.
claims를 생략해서 원본 검증을 우회하지 마세요. 확인 가능한 주장이 없으면 unknown만 반환하세요.
"""
