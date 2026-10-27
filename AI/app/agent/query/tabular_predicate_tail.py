"""Reject unparsed additional predicates after one recognized value."""
import re


def unsupported_tail(remainder, conjunctive=False):
    tail = remainder.strip()
    if not tail:
        return False
    if conjunctive:
        return True
    if re.search(r"['\"‘“]", tail):
        return True
    if re.search(r"\b(?:and|or|but|except|excluding|not|without)\b\s+\S|"
                 r"(?:이면서|이거나|또는|혹은|빼고|제외|아닌|포함)\s*\S", tail, re.I):
        return True
    # A separator can terminate a sentence or separate another literal. Only
    # an empty tail or an output request is harmless without another field.
    if tail[0] in ",;.!?":
        rest = tail.lstrip(",;.!? ").strip()
        return bool(rest) and not re.fullmatch(
            r"(?:rows?|records?|count|list|show|please|보여줘|알려줘|목록|건수|개수)[\s?!.]*", rest, re.I)
    return False
