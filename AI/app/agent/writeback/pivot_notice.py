"""Pivot tables keep their own cached totals; an edit reaches them only on refresh."""
import posixpath
import re
from io import BytesIO
from zipfile import BadZipFile, ZipFile

SHEET = re.compile(r'<sheet\b[^>]*\bname="([^"]+)"[^>]*\br:id="([^"]+)"')
RELATION = re.compile(r'<Relationship\b[^>]*\bId="([^"]+)"[^>]*\bTarget="([^"]+)"')


def pivot_sheets(content: bytes) -> list[str]:
    try:
        with ZipFile(BytesIO(content)) as package:
            names = set(package.namelist())
            workbook = package.read("xl/workbook.xml").decode("utf-8", "replace")
            links = dict(RELATION.findall(package.read("xl/_rels/workbook.xml.rels").decode("utf-8", "replace")))
            found = []
            for name, relation in SHEET.findall(workbook):
                link = links.get(relation, "")
                # An absolute target starts at the package root, a relative one next to workbook.xml.
                target = posixpath.normpath(link.lstrip("/") if link.startswith("/") else posixpath.join("xl", link))
                rels = posixpath.join(posixpath.dirname(target), "_rels", posixpath.basename(target) + ".rels")
                if rels in names and "relationships/pivotTable" in package.read(rels).decode("utf-8", "replace"):
                    found.append(name.replace("&amp;", "&"))
            return found
    except (BadZipFile, KeyError, ValueError):
        return []


def with_pivot_notice(proposal, content: bytes):
    sheets = pivot_sheets(content) if proposal.changes else []
    if not sheets:
        return proposal
    if refreshes_on_open(content):
        notice = (f"피벗 표({', '.join(sheets)})는 저장된 집계를 따로 들고 있습니다. 이 파일은 Excel에서 열 때 "
                  "피벗을 자동으로 새로 고치도록 설정되어 있어 바뀐 값이 반영됩니다. "
                  "Excel이 아닌 프로그램에서는 직접 새로 고쳐야 할 수 있습니다.")
    else:
        notice = (f"피벗 표({', '.join(sheets)})는 저장된 집계를 따로 들고 있어, 받은 파일을 Excel에서 열고 "
                  "‘데이터 → 모두 새로 고침’을 해야 바뀐 값이 반영됩니다.")
    return proposal.model_copy(update={"limitations": [*proposal.limitations, notice]})


def refreshes_on_open(content: bytes) -> bool:
    """Every pivot cache in the package is set to refresh when Excel opens the file."""
    try:
        with ZipFile(BytesIO(content)) as package:
            caches = [name for name in package.namelist()
                      if re.fullmatch(r"xl/pivotCache/pivotCacheDefinition\d+\.xml", name)]
            return bool(caches) and all(
                re.search(rb'<(?:\w+:)?pivotCacheDefinition\b[^>]*\brefreshOnLoad="(?:1|true)"', package.read(name))
                for name in caches)
    except (BadZipFile, KeyError, ValueError):
        return False
