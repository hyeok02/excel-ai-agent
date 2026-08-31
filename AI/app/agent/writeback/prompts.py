import json

SYSTEM_PROMPT = """당신은 Excel 변경 제안 Agent입니다.
사용자 지시와 제공된 원본 셀 목록만 사용하여 변경 후보를 만드세요.
반드시 존재하는 일반 값 셀만 선택하고, 수식 셀이나 빈 셀은 선택하지 마세요.
새 값에 Excel 수식, 명령, 매크로를 만들지 마세요.
사용자가 명시하지 않은 값은 추측하지 마세요.
셀 주소는 A1 형식으로 정확히 쓰고 변경 이유를 한국어로 설명하세요.
안전하게 특정할 수 없다면 changes를 비우고 한계를 설명하세요."""


def build_writeback_prompt(
    instruction: str, filename: str, context: dict[str, object]
) -> str:
    payload = json.dumps(context, ensure_ascii=False, default=str)
    return (
        f"파일명: {filename}\n사용자 변경 지시: {instruction}\n"
        f"변경 가능한 원본 셀 후보(JSON):\n{payload}"
    )
