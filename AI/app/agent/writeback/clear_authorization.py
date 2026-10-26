"""Deletion needs an affirmative operation, never text intended for the cell."""
import re

_QUOTED = re.compile(r"'[^'\n]*'|\"[^\"\n]*\"|`[^`\n]*`|‘[^’\n]*’|“[^”\n]*”")
_NEGATED = re.compile(
    r"\b(?:not|never|no|don['’]t|do\s+not)\b|"
    r"(?:비우|비워|지우|지워|삭제|제거)[^,.!?]{0,16}(?:지\s*마|지\s*않|면\s*안|금지)", re.I,
)
_REPLACEMENT = re.compile(
    r"(?:으로|로)\s*(?:수정|변경|바꿔|입력|설정)|"
    r"^\s*(?:to|with|as|into)\b|"
    r"\b(?:set|change|update|replace|fill|write|insert|put|assign)\b.*\b(?:to|with|as|into)\b", re.I,
)
_CLEAR = re.compile(
    r"\b(?:clear|delete|remove)\b|(?:비워|지워)(?:줘|주세요)?|(?:비우|지우)(?:고|기|세요|라)|"
    r"(?:삭제|제거)(?:해(?:줘|주세요)?|하(?:세요|기|라)|하고)|"
    r"(?:삭제|제거)\s*(?:부탁(?:해|합니다|드려요))?[.!?\s]*$", re.I,
)


def clear_is_authorized(instruction):
    # Quoted replacement values such as 'delete me' must stay literal text.
    prose = _QUOTED.sub(" ", str(instruction))
    if _NEGATED.search(prose) or _REPLACEMENT.search(prose):
        return False
    return bool(_CLEAR.search(prose))
