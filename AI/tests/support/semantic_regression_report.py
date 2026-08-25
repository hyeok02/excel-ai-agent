from dataclasses import dataclass


@dataclass(frozen=True)
class RegressionIssue:
    code: str
    location: str
    expected: str | None
    actual: str | None

    def describe(self) -> str:
        values = []
        if self.expected is not None:
            values.append(f"expected={self.expected}")
        if self.actual is not None:
            values.append(f"actual={self.actual}")
        suffix = f" ({', '.join(values)})" if values else ""
        return f"[{self.code}] {self.location}{suffix}"


@dataclass(frozen=True)
class FixtureRegressionResult:
    fixture: str
    issues: tuple[RegressionIssue, ...]

    @property
    def passed(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class SemanticRegressionReport:
    results: tuple[FixtureRegressionResult, ...]

    @property
    def passed(self) -> bool:
        return all(result.passed for result in self.results)

    @property
    def passed_count(self) -> int:
        return sum(result.passed for result in self.results)

    @property
    def failed_count(self) -> int:
        return len(self.results) - self.passed_count

    def failure_message(self) -> str:
        lines = [
            "Excel 의미 분석 회귀 테스트 실패",
            f"통과 {self.passed_count}개 / 실패 {self.failed_count}개",
        ]
        for result in self.results:
            if not result.passed:
                lines.append(f"- {result.fixture}")
                lines.extend(f"  - {issue.describe()}" for issue in result.issues)
        return "\n".join(lines)

    def assert_passed(self) -> None:
        if not self.passed:
            raise AssertionError(self.failure_message())
