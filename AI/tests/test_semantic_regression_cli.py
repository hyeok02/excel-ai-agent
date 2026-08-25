import json
from pathlib import Path

from tests.run_semantic_regression import main
from tests.support.semantic_regression import load_semantic_fixture_cases

FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "semantic"


def test_cli_compares_actual_json_directory(tmp_path: Path, capsys: object) -> None:
    cases = load_semantic_fixture_cases(FIXTURE_DIRECTORY)
    for case in cases:
        payload = json.loads(case.expectation_path.read_text(encoding="utf-8"))
        actual_path = tmp_path / f"{case.workbook_path.stem}.actual.json"
        actual_path.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
    exit_code = main(["--actual-dir", str(tmp_path)])
    assert exit_code == 0
    assert "회귀 테스트 통과: 3개" in capsys.readouterr().out


def test_cli_returns_failure_when_actual_json_is_missing(
    tmp_path: Path,
    capsys: object,
) -> None:
    exit_code = main(["--actual-dir", str(tmp_path)])
    output = capsys.readouterr().out
    assert exit_code == 1
    assert "통과 0개 / 실패 3개" in output
    assert "execution_error" in output
