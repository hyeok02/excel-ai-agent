"""A model may select source labels, never decide their semantic equivalence."""
from pydantic import BaseModel, ConfigDict, Field


class HeaderRelationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    table_id: str
    column_ids: list[str] = Field(min_length=1, max_length=2)
    mentions: list[str] = Field(min_length=2, max_length=2)


HEADER_RELATION_PROMPT = """
kind=field_relation은 두 명칭이 같은 항목인지, 별개의 항목인지, 무슨 차이인지
묻는 설명 질문입니다. 실제 데이터 값/건수/금액의 비교는 comparison이며
field_relation으로 바꾸지 마세요. 이 경우 header_relation=null입니다.
field_relation에서는 header_relation에 원본 table_id, 관련 column_ids 1~2개,
사용자 질문에도 원본 헤더에도 실제 등장하는 두 이름 mentions를 적으세요.
쉼표 등으로 함께 적힌 하나의 헤더도 선택할 수 있습니다. mentions는 서로
겹치지 않는 두 이름이며, 질문에 없는 이름/번역/추측을 추가하지 마세요.
코드가 헤더의 원본 셀과 위치를 검증해 함께/따로 적혔는지만 설명합니다.
같은 열에 적혔다고 실제 업무·회사·개념이 같거나 다르다고 판단하지 마세요.
원본 헤더에 연결할 수 없거나 두 이름이 모호하면 header_relation=null입니다.
field_relation일 때 tabular_query와 relational_query는 모두 null입니다.
다른 kind에서는 header_relation=null입니다.
"""
