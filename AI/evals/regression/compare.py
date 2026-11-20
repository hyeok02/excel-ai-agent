"""Compare two battery runs: which questions got worse, better, or only reworded.

    python -m evals.regression.compare before.jsonl after.jsonl
Exit status 1 when any question that answered before no longer does.
"""
import json
import sys

_ANSWERED = {"answered", "limited"}


def load(path):
    rows = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
    return {(row["file"], row["question"]): row for row in rows}


def _asks(row):
    return "지정해 주세요" in row["answer"]


def kind(row):
    if row["status"] in _ANSWERED and not _asks(row):
        return "answer"
    return "ask" if _asks(row) else "none"


def compare(before, after):
    worse, better, changed, missing = [], [], [], []
    rank = {"none": 0, "ask": 1, "answer": 2}
    for key, old in before.items():
        new = after.get(key)
        if new is None:
            missing.append(key)
        elif rank[kind(new)] < rank[kind(old)]:
            worse.append((key, old, new))
        elif rank[kind(new)] > rank[kind(old)]:
            better.append((key, old, new))
        elif new["answer"] != old["answer"]:
            changed.append((key, old, new))
    return worse, better, changed, missing


def main(argv=None):
    before_path, after_path = (argv or sys.argv[1:])[:2]
    worse, better, changed, missing = compare(load(before_path), load(after_path))
    for title, items in (("WORSE", worse), ("BETTER", better), ("CHANGED", changed)):
        print(f"== {title}: {len(items)}")
        for (name, question), old, new in items:
            print(f"- [{name}] {question}\n    before ({old['status']}): {old['answer'][:160]!r}\n"
                  f"    after  ({new['status']}): {new['answer'][:160]!r}")
    if missing:
        print(f"== MISSING: {len(missing)}")
    return 1 if worse or missing else 0


if __name__ == "__main__":
    sys.exit(main())
