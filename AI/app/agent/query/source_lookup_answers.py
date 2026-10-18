"""Exact bounded address lookups use original bytes without a model call."""
from dataclasses import asdict
import math

from app.agent.query.excel_number_formats import display_value, parse_number_format
from app.agent.query.models import QuestionAnswer, QuestionAnswerEvidence, QuestionAnswerVerification
from app.agent.query.question_formula_answers import direct_formula_answer
from app.agent.query.source_lookup_reader import read_source_range
from app.agent.query.source_lookup_references import direct_references
from app.agent.query.workbook_source import source_for
from app.agent.query.workbook_source_models import SourceReadError

MAX_DIRECT_CELLS = 80
MAX_DIRECT_RANGES = 8


def source_lookup_answer(question, sources):
    index = sources.original_index
    if getattr(index, "source_provider", None) is None:
        return None
    source = source_for(index)
    if source is None:
        return _unavailable(question, "현재 원본 파일과 조회 경로가 일치하지 않습니다.")
    try:
        requested = direct_references(question, source)
        if not requested:
            return None
        if len(requested) > MAX_DIRECT_RANGES or sum(item.area for item in requested) > MAX_DIRECT_CELLS:
            return _unavailable(question, "직접 표시할 셀 범위가 큽니다. 최대 80개 셀 이내로 범위를 좁혀 주세요.")
        cells = {cell.reference: cell for item in requested
                 for cell in read_source_range(source, item, MAX_DIRECT_CELLS)}
    except SourceReadError:
        return _unavailable(question, "요청한 셀 범위를 원본에서 끝까지 확인하지 못했습니다. 허용된 시트와 범위를 확인해 주세요.")
    missing = [cell for cell in cells.values() if cell.formula and cell.value is None]
    if missing:
        if len(cells) == 1 and (recovered := direct_formula_answer(question, sources)) is not None:
            return recovered
        return _unavailable(question, "요청한 수식에 저장된 계산 결과가 없습니다. 값을 0으로 대신하지 않았습니다. "
                            "Excel에서 계산·저장한 파일이 필요합니다.", missing)
    if any(cell.value_type == "unsupported" or isinstance(cell.value, float) and not math.isfinite(cell.value)
           for cell in cells.values()):
        return _unavailable(question, "요청한 셀 값의 형식을 안전하게 표시할 수 없습니다.")
    shortened = any(isinstance(cell.value, str) and len(cell.value) > 500 for cell in cells.values())
    lines = [f"{cell.reference}: {_display(cell)}" for cell in cells.values()]
    return QuestionAnswer(
        question=question, answer="\n".join(lines), status="limited" if shortened else "answered", confidence=1,
        selected_tools=["read_original_cells"], evidence=[_evidence(cell) for cell in cells.values()],
        limitations=["긴 셀 문자열은 앞의 500자까지만 표시했습니다."] if shortened else [],
        verification=QuestionAnswerVerification(level="source_checked" if shortened else "request_checked", checks=[
            "explicit_source_scope", "complete_source_read", "source_values",
        ]),
    )


def _display(cell):
    value = cell.value
    if value is None:
        return "빈 셀"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return display_value(value, parse_number_format(cell.number_format))
    return str(value)[:500] + ("…" if len(str(value)) > 500 else "")


def _evidence(cell):
    fields = asdict(cell.evidence())
    if isinstance(cell.value, str) and len(cell.value) > 500:
        fields.update(value=cell.value[:500], description="원본 셀 문자열의 앞 500자만 표시한 근거입니다.")
    return QuestionAnswerEvidence(**fields, label="직접 조회한 원본 셀")


def _unavailable(question, reason, cells=()):
    return QuestionAnswer(
        question=question, answer=reason, status="insufficient_evidence", confidence=0,
        selected_tools=["read_original_cells"], evidence=[_evidence(cell) for cell in cells],
        limitations=["미조회·누락된 원본 값을 빈 셀이나 0으로 취급하지 않았습니다."],
    )
