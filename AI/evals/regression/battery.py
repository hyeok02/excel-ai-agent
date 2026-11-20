"""Run the Q&A regression battery through the real service, recording or replaying model calls.

    python -m evals.regression.battery record --data DIR --tape tape.json --out answers.jsonl
    python -m evals.regression.battery replay --data DIR --tape tape.json --out answers.jsonl

``record`` calls the model (set OPENAI_INTENT_MODEL / OPENAI_QA_MODEL to a cheaper model to spend
less) and stores every response on the tape; ``replay`` answers every model call from the tape,
so a code change can be checked against the recorded run without any API cost.
"""
import argparse
import asyncio
import json
import logging
import os
import sys
import tempfile
import time
import warnings
from pathlib import Path

from evals.regression.llm_tape import Tape, install

QUESTIONS = Path(__file__).with_name("questions.tsv")


def questions(path=QUESTIONS, only=None):
    rows = [line.rstrip("\n").split("\t", 1) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")]
    return [(name, question) for name, question in rows if not only or name in only]


async def run(items, data, out, limit=None, tape=None, deadline=None, append=False):
    from app.agent import create_default_tool_registry
    from app.agent.query import WorkbookQuestionService
    from app.agent.query.conversation_resolver import LangChainQuestionContextResolver
    from app.agent.query.generator import LangChainQuestionAnswerGenerator
    from app.agent.query.intent_classifier import LangChainQuestionIntentClassifier
    from app.agent.query.question_index import build_question_data_index
    from app.services.workbook_parser import parse_workbook

    classifier = LangChainQuestionIntentClassifier.from_environment()
    generator = LangChainQuestionAnswerGenerator.from_environment()
    resolver = LangChainQuestionContextResolver.from_environment()
    parsed, begun = {}, time.time()
    done = set()
    if append and Path(out).exists():  # a run split into parts goes on where the last part stopped
        done = {(row["file"], row["question"]) for row in map(json.loads, Path(out).read_text(encoding="utf-8").splitlines())}
    with open(out, "a" if append else "w", encoding="utf-8") as stream:
        for name, question in items[:limit]:
            if (name, question) in done:
                continue
            if deadline and time.time() - begun > deadline:
                break
            if name not in parsed:
                folders = [Path(item) for item in str(data).split(os.pathsep) if item] + [Path(__file__).with_name("data")]
                content = next(folder / name for folder in folders if (folder / name).exists()).read_bytes()
                summary = parse_workbook(name, content)
                parsed[name] = (summary, build_question_data_index(name, content, summary))
            summary, index = parsed[name]
            _fresh_labels()
            service = WorkbookQuestionService(generator, create_default_tool_registry(), classifier=classifier,
                                              context_resolver=resolver)
            started, missed = time.time(), len(tape.misses) if tape is not None else 0
            try:
                answer = await service.answer(question, summary, index)
                result = {"status": str(getattr(answer.status, "value", answer.status)), "tools": answer.selected_tools,
                          "answer": answer.answer}
            except Exception as error:  # a failure is a result to compare, not a reason to stop
                result = {"status": "error", "tools": [], "answer": repr(error)[:300]}
            stream.write(json.dumps({"file": name, "question": question, "secs": round(time.time() - started, 1),
                                     **result, "tape_misses": len(tape.misses) - missed if tape is not None else 0},
                                    ensure_ascii=False) + "\n")
            stream.flush()
            if tape is not None:
                tape.save()  # each answered question's model calls are kept even if the run is stopped


def _fresh_labels():
    """Each question starts with no label readings, as in a new process: a question's model calls
    then never depend on which questions ran before it, or on where a run was split into parts."""
    from app.services.insights.display import label_translator
    for kept in (label_translator._READINGS, label_translator._COUNTERS, label_translator._PREPARED):
        kept.clear()
    os.environ["LABEL_READINGS_DIR"] = tempfile.mkdtemp(prefix="battery-labels-")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["record", "replay"])
    parser.add_argument("--data", default="", help="folders holding the battery's workbooks (os.pathsep-separated)")
    parser.add_argument("--tape", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--questions", default=str(QUESTIONS))
    parser.add_argument("--only", nargs="*", help="workbook names to run")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--append", action="store_true", help="skip questions already in --out and add the rest")
    parser.add_argument("--deadline", type=float, help="start no new question after this many seconds")
    args = parser.parse_args(argv)
    if os.environ.get("PYTHONHASHSEED") != "0" and argv is None:
        # Set order follows the hash seed, and some prompts list sets: a fixed seed makes a
        # recorded run and its replay send the same requests.
        os.execve(sys.executable, [sys.executable, "-m", "evals.regression.battery", *sys.argv[1:]],
                  {**os.environ, "PYTHONHASHSEED": "0"})
    warnings.filterwarnings("ignore")
    logging.disable(logging.CRITICAL)
    if args.mode == "replay":
        os.environ.setdefault("OPENAI_API_KEY", "replay-only")
    tape = Tape(args.tape, args.mode)
    undo = install(tape)
    try:
        asyncio.run(run(questions(Path(args.questions), args.only), args.data, args.out, args.limit, tape,
                        args.deadline, args.append))
    finally:
        undo()
        tape.save()
    print(json.dumps({"mode": args.mode, "hits": tape.hits, "recorded": tape.recorded, "misses": len(tape.misses)}))
    if tape.misses:
        print("not recorded:", *(json.dumps(item, ensure_ascii=False) for item in tape.misses[:10]), sep="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
