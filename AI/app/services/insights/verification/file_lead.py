"""A first sentence that says what the file is, when the usual one only strings column names together.

'이 파일은 국어와 영어 관련 내용을 정리한 자료입니다' becomes '이 파일은 ‘성적’ 시트에 학생 18명의 …':
the table's own title when it has one, else its sheet(s), what its rows are, how many, and what is recorded.
"""
import re

from app.services.insights.narratives.narrative_values import after_lead, subject_particle
from app.services.insights.verification.validation_index import extract_references

FIRST = re.compile(r"^\s*(이 파일(?:은|에는)\s.+?다\.(?:\s*\([^)]*\))?)", re.S)
_WEAK = re.compile(r"^이 파일은 (?:.+ 관련 내용을 정리한 자료입니다|.+ (?:등 주요 수치의 (?:기간별 )?)?변동을 다룹니다"
                   r"|(?:.+의 )?‘[^’]+’ 기록 [\d,]+건을 정리한 목록입니다)\.$")
_DATE = re.compile(r"^(\d{4})[.\-/](\d{1,2})(?:[.\-/]\d{1,2})?(?:$|[T\s])")
_PLACES = re.compile(r"지점|지역|매장|점포|도시|국가|시도|\b(?:region|store|branch|city|country|state)\b", re.I)
_PEOPLE = re.compile(r"이름|성명|직원|사원|학생|\b(?:name|employee|student)\b", re.I)
_TYPE = re.compile(r"구분|유형|종류|\b(?:type|kind)\b", re.I)
_MONTH = re.compile(r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?"
                    r"|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?", re.I)
_LARGE = re.compile(r"^‘(.+)’ 시트에는 [\d,]+행 ([\d,]+)열 규모의 표가 있습니다\.")
RECORDS = 20  # more rows than this are a record list, told by how many and over when


def described(report, context, force=False):
    """force: the summary compares sheets ('January' · 'March'), so a lead naming one of them is replaced."""
    found = FIRST.match(report.overview or "")
    if not found or not (force or _WEAK.match(" ".join(found[1].split()))) or any(
            item.title.endswith("서식 구성") for item in report.insights[:1]):
        return report  # a form is already told by its outline
    large = _LARGE.match(report.insights[0].fact) if report.insights else None  # read by its size alone
    lead = f"이 파일은 ‘{large[1]}’ 시트에 {large[2]}개 열의 기록을 담은 큰 표 자료입니다." if large else _lead(report, context)
    if lead:
        report.overview = after_lead(lead, report.overview[found.end():])
    return report


def _lead(report, context):
    from app.services.insights.narratives.item_tables import item_tables
    from app.services.insights.narratives.layout_tables import kept_rows, label, numbers, texts
    refs = [ref for item in report.insights[:1] for evidence in item.evidence for ref in extract_references(evidence)]
    refs.sort(key=lambda ref: 0)  # cited order: the first sheet first
    sheets = {str(sheet.get("name", "")): sheet for sheet in context.get("sheets", []) if isinstance(sheet, dict)}
    cited = next((" ".join(ref.split("!", 1)[0].strip("'").split()).casefold() for ref in refs), "")
    name = next((sheet for sheet in sheets if " ".join(sheet.split()).casefold() == cited), "")  # refs are casefolded
    if not name:
        return ""
    tables = [table for table in item_tables(sheets[name]) if table["rows"]]
    cells = {ref.split("!", 1)[1].split(":")[0].upper() for ref in refs if "!" in ref}
    tables.sort(key=lambda table: not any(cell["cell"] in cells for row in [*table["header"], *table["rows"]]
                                          for cell in row.values()))  # the table the insight cites, first
    if not tables:
        return ""
    table = tables[0]
    columns = sorted(set().union(*table["header"]))
    first = min(columns)
    rows = kept_rows(table, first) or table["rows"]
    key = next((p for p in columns if (names := texts(rows, p)) and len(set(names)) == len(names)), first)
    if not texts(rows, key):  # the names under no header, left of the first column: Mortgage/Rent, Gas, …
        key = max((p for p in set().union(*rows) if p < first and texts(rows, p)), default=key)
    from app.services.insights.narratives.item_periods import _period
    measures = [_period(table, p) for p in columns if p != key and numbers(rows, p)]
    beside = False
    for other in tables[1:]:  # tables side by side over the same items: 인원 | 매출
        other_key = min(other["header"][-1] | other["header"][0])
        if texts(kept_rows(other, other_key), other_key) == texts(rows, key):
            beside = True
            measures += [label(other, p) for p in sorted(other["header"][-1]) if p != other_key
                         and numbers(kept_rows(other, other_key), p)]
    several = len({ref.split("!", 1)[0] for ref in refs}) > 1  # '2023' and '2024': one sheet's title is not the file's
    if table["title"] and not beside and not several:
        return f"이 파일에는 {table['title']} 자료가 담겨 있습니다."
    if len(measures) < 2:  # 직원 명부: its columns say what is kept, not only the one number
        measures = [label(table, p) for p in columns if p != key]
    named = list(dict.fromkeys(sheet for ref in refs for sheet in sheets  # every period's sheet the summary cites
                               if " ".join(sheet.split()).casefold() == " ".join(ref.split("!", 1)[0].strip("'").split()).casefold()))
    group = named if len(named) > 1 else _same_layout(sheets, name, table, label)
    where = "·".join(f"‘{sheet.strip()}’" for sheet in group) + " 시트에"
    if len(group) > 1 and len(rows) > RECORDS:  # records kept one sheet per month: all of them are told
        rows = [row for sheet in group for other in item_tables(sheets[sheet])[:1] for row in other["rows"]]
    dated = all(_DATE.match(" ".join(str(row.get(key, {}).get("value") or "").split())) for row in rows)
    if (len(rows) > RECORDS or dated) and len(_periods(measures)) < 3:  # many rows, or one a day; not items by month
        kinds = next((sorted(set(values), key=values.index) for p in sorted(rows[0]) if p != key
                      and _TYPE.search(label(table, p)) and (values := texts(rows, p)) and len(set(values)) == 2),
                     [])  # 구분: 수입 · 지출
        kinds = f"{'·'.join(kinds)} " if kinds else ""
        return f"이 파일은 {where} {_span(table, rows)}{kinds}기록 {len(rows):,}건을 정리한 자료입니다."
    what = _listed(measures)
    if not what:
        return ""
    kind = label(table, key)
    kind = "" if not re.search(r"[A-Za-z가-힣]", kind) or kind.startswith("(") or kind.endswith(":") else kind
    start = min((p for p in columns if numbers(table["rows"], p)), default=key)  # the first column of values
    named = [row for row in table["rows"] if any(isinstance(cell.get("value"), str) and cell["value"].strip()
                                                 for p, cell in row.items() if p < start)]
    if len(rows) < 0.6 * len(named):  # 매출 · 비용 · 이익 heading the lines indented under them: every line counts
        rows, kind = named, ""
    if _PEOPLE.search(kind):
        items = f"{len(rows)}명의 "
    else:
        items = f"{kind} {len(rows)}{'곳' if _PLACES.search(kind) else '개'}의 " if kind else f"항목 {len(rows)}개의 "
    return f"이 파일은 {where} {items}{what}{_object(what)} 정리한 자료입니다."


def _same_layout(sheets, name, table, label):
    """The sheets that repeat this sheet's header, in workbook order ('2022년', '2023년')."""
    from app.services.insights.narratives.item_tables import item_tables
    shape = [label(table, p) for p in sorted(table["header"][-1])]
    same = [sheet for sheet, data in sheets.items()
            if any([label(other, p) for p in sorted(other["header"][-1])] == shape for other in item_tables(data))]
    return same if name in same and len(same) > 1 else [name]


def _span(table, rows):
    """'2024년 1월~6월 ' over a column of dates, else nothing."""
    for p in sorted(rows[0]):
        values = [" ".join(str(row.get(p, {}).get("value") or "").split()) for row in rows]
        months = [found for value in values if (found := _DATE.match(value))]
        if months and len(months) == len(values):
            (y1, m1), (y2, m2) = min((int(f[1]), int(f[2])) for f in months), max((int(f[1]), int(f[2])) for f in months)
            return f"{y1}년 {m1}월~{m2}월 " if y1 == y2 else f"{y1}년 {m1}월~{y2}년 {m2}월 "
    return ""


def _listed(measures):
    measures = list(dict.fromkeys(measure for measure in measures if re.search(r"[A-Za-z가-힣0-9]", measure or "")
                                  and not measure.endswith(":")))  # '$' and 'Income Statement:' are not columns
    periods = _periods(measures)
    if len(periods) >= 2:
        return f"{periods[0]}~{periods[-1]} 값"
    if len(measures) > 3:
        return ", ".join(measures[:3]) + " 등"
    if len(measures) == 3:
        return ", ".join(measures)
    if len(measures) == 2:
        from app.services.insights.narratives.narrative_values import joining_particle
        return f"{measures[0]}{joining_particle(measures[0])} {measures[1]}"
    return measures[0] if measures else ""


def _periods(measures):
    """The measures that are periods: FY2023, 3월, Q1, or a month's name (January … December, Jan … Dec)."""
    from app.services.insights.narratives.item_periods import PERIOD
    return [measure for measure in measures if PERIOD.match(measure or "") or _MONTH.fullmatch((measure or "").strip())]


def _object(word):
    return "을" if subject_particle(word) == "이" else "를"
