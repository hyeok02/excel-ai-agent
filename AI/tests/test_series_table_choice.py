"""One series stated by several tables: a question word may name the table, else the report's order."""
from types import SimpleNamespace

from app.agent.query.references import normalize_reference
from app.agent.query.series_table_choice import table_choice
from tests.test_named_series_answers import Names

TITLES = {"1.2": "Table 1.2: emissions of all greenhouse gases", "1.4": "Table 1.4: emissions of methane (CH4)"}
CELLS = {normalize_reference(f"'{sheet}'!A1"): SimpleNamespace(sheet_name=sheet, value=title)
         for sheet, title in TITLES.items()}
ITEMS = [SimpleNamespace(fact=f"fact {sheet}", evidence=[f"'{sheet}'!A1", f"'{sheet}'!B9"]) for sheet in TITLES]
LABELS = [f"{sheet} — {title}" for sheet, title in TITLES.items()]


def test_without_a_word_naming_a_table_the_reports_first_table_is_used_and_named():
    item, label, others = table_choice(["전력 부문", "배출량"], "전력 부문", ITEMS, CELLS, Names({}))
    assert (item.fact, label, others) == ("fact 1.2", LABELS[0], [LABELS[1]])


def test_a_word_naming_one_table_picks_it():
    names = Names({"메탄": LABELS[1], "배출량": LABELS[0]})
    item, label, _ = table_choice(["전력 부문", "메탄", "배출량"], "전력 부문", ITEMS, CELLS, names)
    assert (item.fact, label) == ("fact 1.4", LABELS[1])


def test_tables_that_cannot_be_told_apart_leave_no_answer():
    untitled = [SimpleNamespace(fact=f"fact {n}", evidence=["'1.2'!B9"]) for n in (1, 2)]
    assert table_choice(["배출량"], "전력", untitled, CELLS, Names({})) is None
    same = [ITEMS[0], SimpleNamespace(fact="other", evidence=["'1.2'!A1"])]
    assert table_choice(["배출량"], "전력", same, CELLS, Names({})) is None
