"""How many cells a sheet's analysis sample may hold.

Questions keep the smaller sample: their calculations read the file through their own index, and a larger
sample only slows them (a 400 × 95 sheet took 4배 longer per question). Insights read whole tables from
the sample (a 1,451행 × 65열 list is 9만 셀), so a parse for insights runs inside wider_samples().
"""
from contextlib import contextmanager
from contextvars import ContextVar

_WIDER: ContextVar[int | None] = ContextVar("analysis_sample_cells", default=None)


@contextmanager
def wider_samples(enabled: bool = True):
    from app.services.workbook_details import analysis_samples
    token = _WIDER.set(analysis_samples.INSIGHT_SHEET_CELLS if enabled else None)
    try:
        yield
    finally:
        _WIDER.reset(token)


def sheet_cells() -> int:
    from app.services.workbook_details import analysis_samples
    return _WIDER.get() or analysis_samples.MAX_ANALYSIS_SHEET_CELLS


def region_cells() -> int:
    from app.services.workbook_details import analysis_samples
    return _WIDER.get() or analysis_samples.MAX_ANALYSIS_REGION_CELLS
