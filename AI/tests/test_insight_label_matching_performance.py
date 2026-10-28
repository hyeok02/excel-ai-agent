"""Label lookup stays exact without compiling every workbook label per field."""
import random
import re

import pytest

from app.services.insights.verification import relation_grounding as grounding
from app.services.insights.verification.relation_index import Observation


def previous_label_spans(text, labels):
    """The pre-optimization implementation, kept as an equivalence oracle."""
    spans = []
    for label in set(labels):
        if not label or not re.search(r"[A-Za-z가-힣]", label):
            continue
        pattern = r"\s*".join(re.escape(word) for word in str(label).split())
        for match in re.finditer(r"(?<![A-Za-z가-힣])" + pattern, text, re.I):
            spans.append((match.start(), match.end(), label))
    return [span for span in spans if not any(
        other != span and other[0] <= span[0] and other[1] >= span[1]
        and other[1] - other[0] > span[1] - span[0] for other in spans
    )]


@pytest.mark.parametrize(("text", "labels"), [
    ("All Institutions, AllInstitutions, ALL\t\nINSTITUTIONS", [
        "All Institutions", "Institutions", "All", " all  institutions ",
        "All\u2003Institutions", "All\u00a0Institutions",
    ]),
    ("매출 매출액 x매출 서울매출 1매출 (매출) 매 출", ["매출", "매 출", "서울매출", "출"]),
    ("İnvestor ıNVESTOR ſhares Key İ I ı K k K S ſ s", [
        "Investor", "Shares", "Key", "I", "K", "S", "İ A", "ı A",
    ]),
    ("ΣMetric σmetric ςMETRIC ẞShares ßshares éRate Érate", [
        "ΣMetric", "σmetric", "ςmetric", "ẞShares", "ßShares", "ÉRate",
    ]),
    ("A+B (A) C.D [Fund] $Net A\\B Unit-24.5 %Rate", [
        "A+B", "(A)", "C.D", "[Fund]", "$Net", "A\\B", "Unit-24.5", "%Rate",
    ]),
    ("xSales Salesman SALES_1 Sales/Sales αSales 1Sales ſSales", ["Sales", "Salesman"]),
    ("1 2026 株式 Σ !!!", ["", " ", "1", "2026", "株式", "Σ", "!!!"]),
    ("Foo Bar FooBar", ["Foo", "Bar", "Foo Bar", "FooBar", "FOOBAR", "foo bar"]),
])
def test_label_prefilter_preserves_spans_boundaries_spacing_and_overlap(text, labels):
    assert sorted(grounding.label_spans(text, labels)) == sorted(previous_label_spans(text, labels))


def test_label_prefilter_preserves_randomized_unicode_literal_matches():
    rng = random.Random(92871)
    alphabet = "AbcIKS가힣금액İıſKΣσςéÉßẞ中01()[]+.*\\_-/"
    labels = ["".join(rng.choices(alphabet, k=rng.randrange(1, 18)))
              for _ in range(350)]
    labels.extend([" ".join(rng.sample(labels, 2)) for _ in range(50)])
    text = "; ".join(rng.choice([label, label.lower(), label.upper()])
                     .replace(" ", rng.choice(["", "\t", "\u2003"])) for label in labels)
    assert sorted(grounding.label_spans(text, labels)) == sorted(previous_label_spans(text, labels))


def test_thousands_of_absent_labels_never_reach_regex_compilation(monkeypatch):
    labels = [f"Investor-{number:05d}-Holdings" for number in range(6000)]
    labels += ["All Institutions", "보유 주식 수"]
    pattern_calls = []
    original = grounding._label_pattern

    def counted(label):
        pattern_calls.append(label)
        return original(label)

    monkeypatch.setattr(grounding, "_label_pattern", counted)
    text = "All Institutions의 주요 수치는 보유 주식 수 5,000입니다."
    assert {span[2] for span in grounding.label_spans(text, labels)} == {
        "All Institutions", "보유 주식 수",
    }
    assert set(pattern_calls) == {"All Institutions", "보유 주식 수"}
    assert len(pattern_calls) == 2


def test_pure_label_caches_are_bounded_and_reuse_compilation():
    grounding._label_pattern.cache_clear()
    for _ in range(4):
        assert grounding.label_spans("Unique Investor", ["Unique Investor"])
    stats = grounding._label_pattern.cache_info()
    assert stats.misses == 1
    assert stats.hits == 3
    assert stats.maxsize == 8192
    assert grounding._label_anchor.cache_info().maxsize == 8192


@pytest.mark.parametrize("text", [
    "All Institutions의 보유 주식 수는 5,000입니다.", "보유 주식 수", "5,000입니다.",
    "원본에서 확인한 내용", "주요 지표", "매출의수치는 100입니다.",
])
def test_non_owner_fields_do_not_scan_any_observations(text):
    class UnreadObservations:
        def __iter__(self):
            raise AssertionError("A field without an owner suffix scanned the workbook")

    assert grounding.grounded_metric_owner(text, {"sheet!a1:b5"}, UnreadObservations())


def observations():
    return [
        Observation(("Volume",), (), "120", frozenset({"sheet!b2"})),
        Observation(("Units",), (), "4200", frozenset({"sheet!b3"})),
        Observation(("Price",), (), "7.75", frozenset({"sheet!b4"})),
    ]


@pytest.mark.parametrize(("text", "valid"), [
    ("Volume의 주요 수치는 Units 4,200, Price 7.75입니다.", False),
    ("Volume의\n주요\t지표는 Units 4,200입니다.", False),
    ("VOLUME의 항목은 Price 7.75입니다.", False),
    ("Volume의 내용은 120입니다.", True),
    ("Units의 주요 수치는 4,200입니다.", True),
    ("Unknown의 주요 수치는 Units 4,200입니다.", True),
    ("Volume의 주요 수치는 Volume 120입니다.", True),
])
def test_owner_guard_preserves_wrong_metric_rejection(text, valid):
    assert grounding.grounded_metric_owner(text, {"sheet!a1:b5"}, observations()) is valid


def test_owner_fields_reuse_exact_spans_instead_of_scanning_twice(monkeypatch):
    calls = []
    original = grounding.label_spans

    def counted(text, labels):
        calls.append(text)
        return original(text, labels)

    monkeypatch.setattr(grounding, "label_spans", counted)
    assert not grounding.grounded_metric_owner(
        "Volume의 주요 수치는 Units 4,200입니다.", {"sheet!a1:b5"}, observations(),
    )
    assert len(calls) == 1


def test_owner_numbers_inside_source_labels_are_still_ignored():
    source = [Observation(("Plan", "Fund 4200"), (), "120", frozenset({"sheet!b2"}))]
    assert grounding.grounded_metric_owner(
        "Plan의 주요 수치는 Fund 4200 120입니다.", {"sheet!a1:b5"}, source,
    )
