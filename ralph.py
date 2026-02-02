# Ralph Wiggum Technique Implementation
# ======================================
#
# The "Ralph Wiggum" technique (named after The Simpsons character) is an
# AI-driven iterative development methodology that runs an AI coding agent
# in a continuous loop until a task is complete.
#
# Key Concepts:
# - Continuous iteration until success
# - Clear success criteria (tests pass, build succeeds, etc.)
# - Self-correction through feedback loops
# - Autonomous operation with guardrails
#
# This file provides scripts and workflows for implementing Ralph-style
# automated development for AquaForge.

"""
Ralph Wiggum Automated Development Script

This script implements the "Ralph loop" - running AI-assisted development
tasks iteratively until they succeed or hit a stop condition.

Usage:
    python ralph.py --task "implement feature X"
    python ralph.py --task "fix all tests" --max-iterations 10
    python ralph.py --task "refactor module Y" --stop-on-success
"""

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any


class RalphLoop:
    """
    The Ralph Wiggum iterative development loop.

    Runs a task repeatedly until:
    - Success criteria are met
    - Max iterations reached
    - Manual stop signal received
    """

    def __init__(
        self,
        task: str,
        max_iterations: int = 50,
        stop_on_success: bool = True,
        success_criteria: Callable[[], bool] | None = None,
        log_dir: Path = Path(".ralph"),
    ):
        self.task = task
        self.max_iterations = max_iterations
        self.stop_on_success = stop_on_success
        self.success_criteria = success_criteria or self._default_success_criteria
        self.log_dir = log_dir
        self.log_dir.mkdir(exist_ok=True)

        self.iteration = 0
        self.history: list[dict[str, Any]] = []
        self.start_time = None

    def _default_success_criteria(self) -> bool:
        """Default success: all tests pass."""
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def _check_build(self) -> bool:
        """Check if the application builds successfully."""
        result = subprocess.run(
            ["python", "-c", "from swim_ai_reflex.backend.api.main import api_app"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def _check_api_tests(self) -> bool:
        """Check if API tests pass."""
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_api.py", "-v"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def _log_iteration(self, success: bool, notes: str = ""):
        """Log iteration results."""
        entry = {
            "iteration": self.iteration,
            "timestamp": datetime.now().isoformat(),
            "task": self.task,
            "success": success,
            "notes": notes,
        }
        self.history.append(entry)

        # Write to log file
        log_file = self.log_dir / f"ralph_log_{datetime.now().strftime('%Y%m%d')}.json"
        with open(log_file, "w") as f:
            json.dump(self.history, f, indent=2)

    def run(self) -> bool:
        """
        Run the Ralph loop.

        Returns:
            True if task completed successfully, False otherwise
        """
        self.start_time = datetime.now()
        print("🔄 Starting Ralph Loop")
        print(f"   Task: {self.task}")
        print(f"   Max iterations: {self.max_iterations}")
        print(f"   Stop on success: {self.stop_on_success}")
        print("-" * 50)

        while self.iteration < self.max_iterations:
            self.iteration += 1
            print(f"\n📍 Iteration {self.iteration}/{self.max_iterations}")

            # Check success criteria
            try:
                success = self.success_criteria()

                if success and self.stop_on_success:
                    self._log_iteration(True, "Success criteria met!")
                    print(f"✅ Success! Task completed in {self.iteration} iterations")
                    return True

                self._log_iteration(success)

                if not success:
                    print("   ⏳ Not complete yet, continuing...")
                    # In a real implementation, this would trigger the AI agent
                    # to analyze the failure and attempt a fix
                    time.sleep(1)  # Prevent tight loop

            except KeyboardInterrupt:
                print("\n🛑 Manual stop signal received")
                self._log_iteration(False, "Manually stopped")
                return False
            except Exception as e:
                print(f"   ❌ Error: {e}")
                self._log_iteration(False, str(e))

        print(f"\n⚠️ Max iterations ({self.max_iterations}) reached")
        return False


def run_tests_loop() -> bool:
    """Run tests in a loop until they all pass."""
    ralph = RalphLoop(
        task="Make all tests pass",
        max_iterations=10,
        success_criteria=lambda: subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_api.py", "-v"],
            capture_output=True,
        ).returncode
        == 0,
    )
    return ralph.run()


def run_build_loop() -> bool:
    """Run build checks in a loop until successful."""
    ralph = RalphLoop(
        task="Fix build errors",
        max_iterations=20,
        success_criteria=lambda: subprocess.run(
            ["python", "-c", "from swim_ai_reflex.backend.api.main import api_app"],
            capture_output=True,
        ).returncode
        == 0,
    )
    return ralph.run()


# ============================================================
# CLAUDE CODE INTEGRATION
# ============================================================
#
# To use Ralph with Claude Code, add this to your .claude/settings.json:
#
# {
#   "hooks": {
#     "stop": {
#       "command": "python ralph.py --check-complete",
#       "prevents_stop": true
#     }
#   }
# }
#
# This intercepts Claude's "I'm done" signal and re-feeds the prompt
# if the success criteria aren't met.
# ============================================================


class ClaudeCodeRalph:
    """
    Integration for Claude Code's stop hook.

    When Claude Code tries to stop, this checks if the task is actually
    complete. If not, it returns a signal to continue.
    """

    STOP_CONDITIONS = {
        "tests_pass": lambda: subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_api.py",
                "tests/test_api_integration.py",
                "-v",
                "--timeout=30",
                "-m",
                "not slow",
            ],
            capture_output=True,
        ).returncode
        == 0,
        "build_succeeds": lambda: subprocess.run(
            [sys.executable, "-c", "import swim_ai_reflex"], capture_output=True
        ).returncode
        == 0,
        "no_lint_errors": lambda: subprocess.run(
            [sys.executable, "-m", "ruff", "check", "."], capture_output=True
        ).returncode
        == 0,
        "api_starts": lambda: subprocess.run(
            [
                sys.executable,
                "-c",
                "from swim_ai_reflex.backend.api.main import api_app",
            ],
            capture_output=True,
        ).returncode
        == 0,
    }

    @classmethod
    def check_complete(cls, conditions: list[str] = None) -> bool:
        """
        Check if all specified conditions are met.

        Args:
            conditions: List of condition names to check

        Returns:
            True if all conditions pass, False otherwise
        """
        if conditions is None:
            conditions = ["build_succeeds"]

        for condition in conditions:
            if condition in cls.STOP_CONDITIONS:
                if not cls.STOP_CONDITIONS[condition]():
                    print(f"❌ Condition '{condition}' not met - continuing...")
                    return False

        print("✅ All conditions met - stopping")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Ralph Wiggum Technique - Iterative AI Development"
    )

    parser.add_argument("--task", type=str, help="Description of the task to complete")

    parser.add_argument(
        "--max-iterations", type=int, default=50, help="Maximum number of iterations"
    )

    parser.add_argument(
        "--stop-on-success",
        action="store_true",
        default=True,
        help="Stop when success criteria are met",
    )

    parser.add_argument(
        "--check-complete",
        action="store_true",
        help="Check if task is complete (for Claude Code hook)",
    )

    parser.add_argument(
        "--conditions",
        nargs="+",
        default=["build_succeeds"],
        help="Conditions to check: tests_pass, build_succeeds, no_lint_errors, api_starts",
    )

    parser.add_argument(
        "--run-tests", action="store_true", help="Run the test-passing loop"
    )

    parser.add_argument(
        "--run-build", action="store_true", help="Run the build-fixing loop"
    )

    args = parser.parse_args()

    if args.check_complete:
        # Claude Code hook mode
        complete = ClaudeCodeRalph.check_complete(args.conditions)
        sys.exit(0 if complete else 1)

    elif args.run_tests:
        success = run_tests_loop()
        sys.exit(0 if success else 1)

    elif args.run_build:
        success = run_build_loop()
        sys.exit(0 if success else 1)

    elif args.task:
        ralph = RalphLoop(
            task=args.task,
            max_iterations=args.max_iterations,
            stop_on_success=args.stop_on_success,
        )
        success = ralph.run()
        sys.exit(0 if success else 1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
