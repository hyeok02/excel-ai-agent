"""Read-only formula derivations; an uncached result is never an original value."""
from dataclasses import dataclass
from time import monotonic


@dataclass(frozen=True)
class FormulaLimits:
    max_cells: int = 4096
    max_range_cells: int = 1024
    max_depth: int = 32
    max_tokens: int = 512
    max_formula_length: int = 4096
    max_result_characters: int = 4096
    max_formulas: int = 256
    timeout_seconds: float = 1.0


@dataclass(frozen=True)
class FormulaResolution:
    reference: str
    formula: str | None
    status: str
    value: str | int | float | bool | None = None
    inputs: tuple[str, ...] = ()
    reason: str | None = None
    missing_references: tuple[str, ...] = ()
    message: str = ""


class FormulaUnavailable(Exception):
    def __init__(self, reason: str, references: tuple[str, ...] = ()):
        self.reason = reason
        self.references = references
        super().__init__(reason)


@dataclass
class FormulaBudget:
    limits: FormulaLimits
    started: float
    cells: int = 0

    def check(self, depth: int = 0, cells: int = 0) -> None:
        self.cells += cells
        if (depth > self.limits.max_depth or self.cells > self.limits.max_cells
                or monotonic() - self.started > self.limits.timeout_seconds):
            raise FormulaUnavailable("resource_limit")


def failure_message(reason: str, references: tuple[str, ...]) -> str:
    detail = ", ".join(references[:8])
    messages = {
        "external_data": "외부 파일/추가 기능 데이터의 저장된 계산 결과가 없습니다. 원본 Excel에서 해당 연결을 새로 고친 뒤 계산하고 저장해 다시 업로드해 주세요.",
        "missing_reference": "참조 원본이 현재 워크북에 없습니다. 참조 시트나 원본 데이터가 포함된 파일을 업로드해 주세요.",
        "unsupported_reference": "이 수식의 이름/구조적/동적 참조는 안전 계산 범위 밖입니다. Excel에서 계산하고 저장해 다시 업로드해 주세요.",
        "unsupported_function": "이 수식의 함수는 안전 계산 범위 밖입니다. Excel에서 계산하고 저장해 다시 업로드해 주세요.",
        "source_error": "참조 셀에 Excel 오류가 있어 값을 복원할 수 없습니다. 원본 오류를 수정하고 다시 계산해 주세요.",
        "calculation_error": "수식 계산 중 오류가 발생했습니다. 원본 수식과 입력값을 확인해 주세요.",
        "cycle": "수식에 순환 참조가 있어 값을 복원할 수 없습니다.",
        "resource_limit": "수식/참조 범위가 안전 계산 한도를 넘었습니다. Excel에서 계산하고 저장해 다시 업로드해 주세요.",
        "index_truncated": "참조 시트의 조회 범위가 잘려 있어 전체 입력값을 확인할 수 없습니다.",
    }
    return messages.get(reason, "수식을 안전하게 계산할 수 없습니다. Excel에서 계산하고 저장해 다시 업로드해 주세요.") + (f" 대상: {detail}" if detail else "")
