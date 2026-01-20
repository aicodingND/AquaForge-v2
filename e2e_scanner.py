#!/usr/bin/env python3
"""
E2E Fix Scanner - Automated issue detection for AquaForge.

This script runs all quality checks and generates a prioritized issue report.
Used by the /e2e-fix workflow.

Usage:
    python e2e_scanner.py [--fix] [--json] [--verbose]

Options:
    --fix       Auto-fix what can be fixed (ruff --fix)
    --json      Output in JSON format for programmatic use
    --verbose   Show detailed output
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Issue:
    """Represents a single issue found during scanning."""

    category: str  # type, lint, test, import, todo
    severity: str  # critical, high, medium, low
    file: str
    line: Optional[int]
    message: str
    fixable: bool = False


@dataclass
class ScanReport:
    """Complete scan report."""

    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    pyright_errors: int = 0
    pyright_warnings: int = 0
    ruff_errors: int = 0
    ruff_fixable: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    todos_found: int = 0
    import_ok: bool = True
    issues: list = field(default_factory=list)

    def is_clean(self) -> bool:
        """Check if the codebase is clean (no issues)."""
        return (
            self.pyright_errors == 0
            and self.ruff_errors == 0
            and self.tests_failed == 0
            and self.import_ok
        )

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "is_clean": self.is_clean(),
            "summary": {
                "pyright_errors": self.pyright_errors,
                "pyright_warnings": self.pyright_warnings,
                "ruff_errors": self.ruff_errors,
                "ruff_fixable": self.ruff_fixable,
                "tests_passed": self.tests_passed,
                "tests_failed": self.tests_failed,
                "tests_skipped": self.tests_skipped,
                "todos_found": self.todos_found,
                "import_ok": self.import_ok,
            },
            "issues": [
                {
                    "category": i.category,
                    "severity": i.severity,
                    "file": i.file,
                    "line": i.line,
                    "message": i.message,
                    "fixable": i.fixable,
                }
                for i in self.issues
            ],
        }


def run_command(cmd: list[str], cwd: Optional[Path] = None) -> tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def scan_pyright(report: ScanReport, verbose: bool = False) -> None:
    """Run pyright and collect type errors."""
    print("🔍 Running Pyright type check...")

    code, stdout, stderr = run_command(["pyright", "--outputjson"])

    try:
        data = json.loads(stdout)
        report.pyright_errors = data.get("summary", {}).get("errorCount", 0)
        report.pyright_warnings = data.get("summary", {}).get("warningCount", 0)

        for diag in data.get("generalDiagnostics", []):
            severity = "high" if diag.get("severity") == "error" else "medium"
            report.issues.append(
                Issue(
                    category="type",
                    severity=severity,
                    file=diag.get("file", ""),
                    line=diag.get("range", {}).get("start", {}).get("line"),
                    message=diag.get("message", ""),
                    fixable=False,
                )
            )

        if verbose:
            print(
                f"   Found {report.pyright_errors} errors, {report.pyright_warnings} warnings"
            )

    except json.JSONDecodeError:
        # Fallback: parse text output
        lines = (stdout + stderr).split("\n")
        for line in lines:
            if "error:" in line.lower():
                report.pyright_errors += 1


def scan_ruff(report: ScanReport, fix: bool = False, verbose: bool = False) -> None:
    """Run ruff and collect lint errors."""
    print("🔍 Running Ruff linting...")

    cmd = ["ruff", "check", ".", "--output-format=json"]
    if fix:
        cmd.append("--fix")

    code, stdout, stderr = run_command(cmd)

    try:
        issues = json.loads(stdout) if stdout.strip() else []
        report.ruff_errors = len(issues)
        report.ruff_fixable = sum(1 for i in issues if i.get("fix"))

        for issue in issues[:20]:  # Limit to first 20
            report.issues.append(
                Issue(
                    category="lint",
                    severity="medium",
                    file=issue.get("filename", ""),
                    line=issue.get("location", {}).get("row"),
                    message=f"{issue.get('code')}: {issue.get('message')}",
                    fixable=bool(issue.get("fix")),
                )
            )

        if verbose:
            print(
                f"   Found {report.ruff_errors} issues ({report.ruff_fixable} fixable)"
            )

    except json.JSONDecodeError:
        # Count errors from exit code
        if code != 0:
            report.ruff_errors = 1


def scan_tests(report: ScanReport, verbose: bool = False) -> None:
    """Run pytest and collect test results."""
    print("🔍 Running Pytest...")

    code, stdout, stderr = run_command(
        [
            "python",
            "-m",
            "pytest",
            "tests/",
            "-v",
            "--tb=no",
            "-q",
            "--collect-only",
            "-q",
        ]
    )

    # Count tests from collection
    len([line_item for line_item in stdout.split("\n") if "::" in line_item])

    # Actually run tests
    code, stdout, stderr = run_command(
        ["python", "-m", "pytest", "tests/", "-v", "--tb=short", "-q"]
    )

    # Parse results
    for line in (stdout + stderr).split("\n"):
        if "passed" in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if p == "passed" and i > 0:
                    try:
                        report.tests_passed = int(parts[i - 1])
                    except ValueError:
                        pass
        if "failed" in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if p == "failed" and i > 0:
                    try:
                        report.tests_failed = int(parts[i - 1])
                    except ValueError:
                        pass
        if "FAILED" in line and "::" in line:
            # Extract failed test info
            test_name = line.split("FAILED")[1].strip() if "FAILED" in line else line
            report.issues.append(
                Issue(
                    category="test",
                    severity="high",
                    file=test_name.split("::")[0] if "::" in test_name else "",
                    line=None,
                    message=f"Test failed: {test_name}",
                    fixable=False,
                )
            )

    if verbose:
        print(f"   Passed: {report.tests_passed}, Failed: {report.tests_failed}")


def scan_todos(report: ScanReport, verbose: bool = False) -> None:
    """Find TODO/FIXME comments."""
    print("🔍 Scanning for TODOs...")

    code, stdout, stderr = run_command(
        [
            "grep",
            "-rn",
            "-e",
            "TODO",
            "-e",
            "FIXME",
            "-e",
            "XXX",
            "-e",
            "HACK",
            "--include=*.py",
            "swim_ai_reflex/",
        ]
    )

    todos = [line_item for line_item in stdout.split("\n") if line_item.strip()]

    report.todos_found = len(todos)

    for todo in todos[:10]:  # Limit to first 10
        parts = todo.split(":", 2)
        if len(parts) >= 3:
            report.issues.append(
                Issue(
                    category="todo",
                    severity="low",
                    file=parts[0],
                    line=int(parts[1]) if parts[1].isdigit() else None,
                    message=parts[2].strip(),
                    fixable=False,
                )
            )

    if verbose:
        print(f"   Found {report.todos_found} TODOs/FIXMEs")


def scan_imports(report: ScanReport, verbose: bool = False) -> None:
    """Verify critical imports work."""
    print("🔍 Checking imports...")

    test_code = """
import sys
try:
    from swim_ai_reflex.backend.api.main import api_app, create_app
    from swim_ai_reflex.backend.services.optimization_service import OptimizationService
    print("OK")
except Exception as e:
    print(f"FAIL:{e}")
    sys.exit(1)
"""

    code, stdout, stderr = run_command(["python", "-c", test_code])

    if "OK" in stdout:
        report.import_ok = True
        if verbose:
            print("   ✅ All critical imports successful")
    else:
        report.import_ok = False
        report.issues.append(
            Issue(
                category="import",
                severity="critical",
                file="",
                line=None,
                message=f"Import failed: {stderr or stdout}",
                fixable=False,
            )
        )
        if verbose:
            print(f"   ❌ Import failed: {stderr or stdout}")


def print_report(report: ScanReport) -> None:
    """Print a formatted report to the console."""
    print("\n" + "=" * 60)
    print("📊 E2E SCAN REPORT")
    print("=" * 60)
    print(f"Timestamp: {report.timestamp}")
    print()

    # Summary table
    print("┌─────────────────┬──────────┬────────┐")
    print("│ Check           │ Status   │ Count  │")
    print("├─────────────────┼──────────┼────────┤")

    pyright_status = "✅ PASS" if report.pyright_errors == 0 else "❌ FAIL"
    print(f"│ Pyright         │ {pyright_status} │ {report.pyright_errors:>6} │")

    ruff_status = "✅ PASS" if report.ruff_errors == 0 else "❌ FAIL"
    print(f"│ Ruff            │ {ruff_status} │ {report.ruff_errors:>6} │")

    test_status = "✅ PASS" if report.tests_failed == 0 else "❌ FAIL"
    print(f"│ Tests           │ {test_status} │ {report.tests_failed:>6} │")

    import_status = "✅ PASS" if report.import_ok else "❌ FAIL"
    print(
        f"│ Imports         │ {import_status} │ {'OK' if report.import_ok else 'FAIL':>6} │"
    )

    print(f"│ TODOs           │ ⚠️  INFO │ {report.todos_found:>6} │")
    print("└─────────────────┴──────────┴────────┘")
    print()

    if report.is_clean():
        print("🎉 CODEBASE IS CLEAN - All checks passed!")
    else:
        print("❌ ISSUES FOUND - Fixes required")
        print()

        # Group issues by severity
        critical = [i for i in report.issues if i.severity == "critical"]
        high = [i for i in report.issues if i.severity == "high"]
        medium = [i for i in report.issues if i.severity == "medium"]

        if critical:
            print("🔴 CRITICAL ISSUES:")
            for issue in critical[:5]:
                print(f"   • [{issue.category}] {issue.file}:{issue.line or '?'}")
                print(f"     {issue.message[:80]}")
            print()

        if high:
            print("🟠 HIGH PRIORITY:")
            for issue in high[:5]:
                print(f"   • [{issue.category}] {issue.file}:{issue.line or '?'}")
                print(f"     {issue.message[:80]}")
            print()

        if medium:
            print(f"🟡 MEDIUM PRIORITY: {len(medium)} issues")
            print()

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="E2E Fix Scanner for AquaForge")
    parser.add_argument("--fix", action="store_true", help="Auto-fix lint issues")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    report = ScanReport()

    if not args.json:
        print("🚀 Starting E2E Scan...")
        print()

    # Run all scans
    scan_imports(report, args.verbose)
    scan_pyright(report, args.verbose)
    scan_ruff(report, fix=args.fix, verbose=args.verbose)
    scan_tests(report, args.verbose)
    scan_todos(report, args.verbose)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print_report(report)

    # Exit with appropriate code
    sys.exit(0 if report.is_clean() else 1)


if __name__ == "__main__":
    main()
