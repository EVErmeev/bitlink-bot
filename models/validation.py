from dataclasses import dataclass, field
from enum import Enum


class ValidationStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


@dataclass
class ValidationIssue:
    code: str
    message: str
    severity: ValidationStatus
    location: str = ""
    suggestion: str = ""


@dataclass
class ValidationReport:
    passed: bool = True
    issues: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)

    def add_issue(self, code: str, message: str, severity: ValidationStatus = ValidationStatus.FAILED, location: str = "", suggestion: str = ""):
        issue = ValidationIssue(code=code, message=message, severity=severity, location=location, suggestion=suggestion)
        if severity == ValidationStatus.FAILED:
            self.passed = False
            self.issues.append(issue)
        elif severity == ValidationStatus.WARNING:
            self.warnings.append(issue)
        self.checks[code] = (severity == ValidationStatus.PASSED)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "issues": [
                {"code": i.code, "message": i.message, "severity": i.severity.value, "location": i.location, "suggestion": i.suggestion}
                for i in self.issues
            ],
            "warnings": [
                {"code": w.code, "message": w.message, "severity": w.severity.value, "location": w.location, "suggestion": w.suggestion}
                for w in self.warnings
            ],
            "checks": self.checks,
        }
