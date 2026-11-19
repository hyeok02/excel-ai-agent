"""Names written as "A와 B" ("잉글랜드와 웨일스"): one source label, not two."""
import re

JOINED = re.compile(r"[가-힣](?:와|과) \S")


def joined_names(words, question):
    """The words, and each "A와 B" run of the question ("잉글랜드와 웨일스"), which may name one label."""
    runs = re.findall(r"[가-힣]{2,}(?:와|과) [가-힣]{2,}", question)
    return list(dict.fromkeys([*words, *(re.sub(r"(?:은|는|이|가|을|를|의)$", "", run) for run in runs)]))
