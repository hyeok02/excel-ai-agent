import re

from app.services.semantic_models import SemanticRole

TITLE_KEYWORDS = ("현황", "보고서", "분석", "검토", "대시보드", "summary", "report")
UNIT_PATTERN = re.compile(r"(?:단위\s*[:：]|금액\s*단위|달성률\s*단위)", re.IGNORECASE)
WARNING_PATTERN = re.compile(r"(?:주의|경고|유의|변경\s*시|변경하면|주의사항)", re.IGNORECASE)
SOURCE_PATTERN = re.compile(r"(?:출처|기준일|작성일|source\s*:)", re.IGNORECASE)
NOTE_PATTERN = re.compile(r"(?:메모\s*[:：]|비고\s*[:：]|참고\s*[:：]|note\s*:)", re.IGNORECASE)
RULE_PATTERN = re.compile(r"(?:판단\s*기준|검토\s*기준|적용\s*기준|조건|임계|기준값)", re.IGNORECASE)
INSTRUCTION_PATTERN = re.compile(
    r"(?:사용\s*안내|사용법|수정하세요|확인하세요|변경하지\s*마세요)",
    re.IGNORECASE,
)
INPUT_PATTERN = re.compile(r"(?:사용자\s*입력|입력값|가정값|기초\s*데이터)", re.IGNORECASE)
CALCULATION_PATTERN = re.compile(r"(?:계산\s*결과|계산식|산출|중간\s*계산)", re.IGNORECASE)
OUTPUT_PATTERN = re.compile(r"(?:최종\s*결과|의사결정\s*요약|판정|결과\s*요약)", re.IGNORECASE)
TOTAL_PATTERN = re.compile(r"^(?:합계|총계|소계|누계|total)$", re.IGNORECASE)

ROLE_REASONS = {
    SemanticRole.TITLE: ("title_style", "상단 병합·강조 서식과 제목 문구를 탐지"),
    SemanticRole.DESCRIPTION: ("narrative_text", "계산값이 없는 문장형 설명 영역을 탐지"),
    SemanticRole.UNIT: ("unit_label", "단위 표기 문구를 탐지"),
    SemanticRole.HEADER: ("header_style_transition", "데이터 앞의 열 이름 행을 헤더로 분리"),
    SemanticRole.DATA: ("tabular_data", "헤더 아래 반복되는 데이터 행을 탐지"),
    SemanticRole.TOTAL: ("total_formula_pattern", "합계 문구와 집계 수식 행을 탐지"),
    SemanticRole.INPUT: ("input_heading", "입력·가정값 문구와 상수 값 영역을 탐지"),
    SemanticRole.CALCULATION: ("formula_distribution", "계산 문구와 수식 분포를 탐지"),
    SemanticRole.OUTPUT: ("output_heading", "판정·결과 문구와 결과 수식을 탐지"),
    SemanticRole.INSTRUCTION: ("instruction_text", "사용 방법과 작업 순서를 설명하는 문장을 탐지"),
    SemanticRole.WARNING: ("warning_text", "주의·경고 표현이 포함된 문장을 탐지"),
    SemanticRole.SOURCE_NOTE: ("source_note_text", "출처·기준일 문구를 탐지"),
    SemanticRole.NOTE: ("note_text", "메모·비고·참고 문구를 탐지"),
    SemanticRole.RULE_NOTE: ("rule_note_text", "판단·검토 기준을 설명하는 문장을 탐지"),
    SemanticRole.SYSTEM_CACHE: ("system_policy", "시스템 캐시 시트 정책을 적용"),
}

ROLE_CONFIDENCE = {
    SemanticRole.TITLE: 0.94,
    SemanticRole.UNIT: 0.97,
    SemanticRole.WARNING: 0.96,
    SemanticRole.SOURCE_NOTE: 0.96,
    SemanticRole.NOTE: 0.92,
    SemanticRole.RULE_NOTE: 0.9,
    SemanticRole.INSTRUCTION: 0.9,
    SemanticRole.HEADER: 0.88,
    SemanticRole.TOTAL: 0.94,
    SemanticRole.INPUT: 0.9,
    SemanticRole.CALCULATION: 0.92,
    SemanticRole.OUTPUT: 0.92,
    SemanticRole.DATA: 0.84,
    SemanticRole.SYSTEM_CACHE: 1.0,
}
