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
    notice = (f"피벗 표({', '.join(sheets)})는 저장된 집계를 따로 들고 있어, 받은 파일을 Excel에서 열고 "
              "‘데이터 → 모두 새로 고침’을 해야 바뀐 값이 반영됩니다.")
    return proposal.model_copy(update={"limitations": [*proposal.limitations, notice]})
