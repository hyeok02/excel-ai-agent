from pathlib import Path


MAX_SOURCE_LINES = 150
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOTS = (
    REPOSITORY_ROOT / "AI" / "app",
    REPOSITORY_ROOT / "AI" / "tests",
    REPOSITORY_ROOT / "BE" / "src" / "main",
    REPOSITORY_ROOT / "BE" / "src" / "test",
)


def test_python_and_java_files_stay_within_length_limit() -> None:
    oversized = []
    for root in SOURCE_ROOTS:
        for path in (*root.rglob("*.py"), *root.rglob("*.java")):
            line_count = len(path.read_text(encoding="utf-8").splitlines())
            if line_count > MAX_SOURCE_LINES:
                oversized.append(f"{path.relative_to(REPOSITORY_ROOT)}: {line_count} lines")

    assert not oversized, "150줄을 초과한 소스 파일:\n" + "\n".join(oversized)
