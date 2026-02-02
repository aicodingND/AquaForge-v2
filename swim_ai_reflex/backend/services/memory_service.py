"""
Self-Learning Memory Service

Provides persistent memory with Mem0 (optional) and file-based fallback.
Mem0 can be easily disabled by setting MEM0_ENABLED=false or removing API key.

Usage:
    memory = MemoryService()
    memory.log_mistake("router bug", "used wrong param name", "grep all usages")
    memory.log_pattern("fallback strategy", "primary with fallback", "when replacing algorithms")

    # Search (uses Mem0 if available, else file grep)
    results = memory.search("exhibition swimmer rules")
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


class MemoryService:
    """
    Hybrid memory service with Mem0 + file-based fallback.

    To disable Mem0:
        - Set MEM0_ENABLED=false in environment
        - Or remove MEM0_API_KEY
        - Falls back to file-based memory automatically
    """

    def __init__(
        self, project_root: str | None = None, user_id: str = "aquaforge-agent"
    ):
        self.project_root = Path(project_root or os.getcwd())
        self.memory_dir = self.project_root / ".agent" / "memory"
        self.user_id = user_id

        # Mem0 is optional - easy to disable
        self.mem0_enabled = self._init_mem0()

    def _init_mem0(self) -> bool:
        """Initialize Mem0 if available and enabled."""
        # Check kill switch
        if os.environ.get("MEM0_ENABLED", "true").lower() == "false":
            print("Mem0 disabled via MEM0_ENABLED=false")
            return False

        api_key = os.environ.get("MEM0_API_KEY")
        if not api_key:
            print("Mem0 not configured (no API key), using file-based memory")
            return False

        try:
            from mem0 import MemoryClient

            self.mem0_client = MemoryClient(api_key=api_key)
            print("Mem0 connected successfully")
            return True
        except ImportError:
            print("Mem0 not installed (pip install mem0ai), using file-based memory")
            return False
        except Exception as e:
            print(f"Mem0 init failed: {e}, using file-based memory")
            return False

    # -------------------------------------------------------------------------
    # Core Operations
    # -------------------------------------------------------------------------

    def log_mistake(
        self,
        summary: str,
        issue: str,
        fix: str,
        file: str = "",
        root_cause: str = "",
        prevention: str = "",
    ) -> None:
        """Log a mistake for future reference."""
        entry = {
            "type": "mistake",
            "date": datetime.now().isoformat()[:10],
            "summary": summary,
            "file": file,
            "issue": issue,
            "root_cause": root_cause,
            "fix": fix,
            "prevention": prevention,
        }

        # Always write to file (primary source of truth)
        self._append_to_file("MISTAKES.md", self._format_mistake(entry))

        # Optionally sync to Mem0
        if self.mem0_enabled:
            self._sync_to_mem0(entry)

    def log_pattern(
        self,
        name: str,
        what_worked: str,
        reuse_when: str,
        context: str = "",
        example: str = "",
    ) -> None:
        """Log a successful pattern for reuse."""
        entry = {
            "type": "pattern",
            "date": datetime.now().isoformat()[:10],
            "name": name,
            "context": context,
            "what_worked": what_worked,
            "reuse_when": reuse_when,
            "example": example,
        }

        self._append_to_file("PATTERNS.md", self._format_pattern(entry))

        if self.mem0_enabled:
            self._sync_to_mem0(entry)

    def log_learning(self, learning: str, category: str = "general") -> None:
        """Log a key learning from the session."""
        entry = {
            "type": "learning",
            "date": datetime.now().isoformat()[:10],
            "category": category,
            "content": learning,
        }

        self._append_to_file("LEARNINGS.md", f"\n- **{category}:** {learning}")

        if self.mem0_enabled:
            self._sync_to_mem0(entry)

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Search memories.

        Uses Mem0 semantic search if available, else greps files.
        """
        results = []

        # Try Mem0 first
        if self.mem0_enabled:
            try:
                mem0_results = self.mem0_client.search(
                    query, filters={"user_id": self.user_id}, limit=limit
                )
                results.extend(mem0_results.get("results", []))
            except Exception as e:
                print(f"Mem0 search failed: {e}, falling back to files")

        # Always include file-based results
        file_results = self._search_files(query)
        results.extend(file_results)

        return results[:limit]

    # -------------------------------------------------------------------------
    # File Operations
    # -------------------------------------------------------------------------

    def _append_to_file(self, filename: str, content: str) -> None:
        """Append content to a memory file."""
        filepath = self.memory_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "a") as f:
            f.write(content)

    def _format_mistake(self, entry: dict) -> str:
        """Format a mistake entry for markdown."""
        return f"""

## {entry["date"]} Error: {entry["summary"]}

**File:** `{entry.get("file", "N/A")}`
**Issue:** {entry["issue"]}
**Root Cause:** {entry.get("root_cause", "TBD")}
**Fix:** {entry["fix"]}
**Prevention:** {entry.get("prevention", "TBD")}
"""

    def _format_pattern(self, entry: dict) -> str:
        """Format a pattern entry for markdown."""
        example_block = ""
        if entry.get("example"):
            example_block = f"""
**Example:**
```python
{entry["example"]}
```"""

        return f"""

## {entry["date"]} Pattern: {entry["name"]}

**Context:** {entry.get("context", "General")}
**What Worked:** {entry["what_worked"]}
**Reuse When:** {entry["reuse_when"]}{example_block}
"""

    def _search_files(self, query: str) -> list[dict[str, Any]]:
        """Simple grep-based file search."""
        results = []
        query_lower = query.lower()

        for md_file in self.memory_dir.glob("*.md"):
            try:
                content = md_file.read_text()
                if query_lower in content.lower():
                    # Extract relevant section
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if query_lower in line.lower():
                            # Get context (3 lines before/after)
                            start = max(0, i - 3)
                            end = min(len(lines), i + 4)
                            snippet = "\n".join(lines[start:end])
                            results.append(
                                {
                                    "source": str(md_file),
                                    "memory": snippet,
                                    "score": 0.5,  # Basic match
                                }
                            )
                            break
            except Exception:
                pass

        return results

    # -------------------------------------------------------------------------
    # Mem0 Sync
    # -------------------------------------------------------------------------

    def _sync_to_mem0(self, entry: dict) -> None:
        """Sync an entry to Mem0 for semantic search."""
        if not self.mem0_enabled:
            return

        try:
            # Format as conversation for Mem0
            content = json.dumps(entry, indent=2)
            messages = [{"role": "assistant", "content": f"Learned: {content}"}]
            self.mem0_client.add(messages, user_id=self.user_id)
        except Exception as e:
            print(f"Mem0 sync failed (non-fatal): {e}")


# Convenience singleton
_memory_instance: MemoryService | None = None


def get_memory() -> MemoryService:
    """Get the global memory service instance."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = MemoryService()
    return _memory_instance


# Quick helpers
def log_mistake(summary: str, issue: str, fix: str, **kwargs) -> None:
    get_memory().log_mistake(summary, issue, fix, **kwargs)


def log_pattern(name: str, what_worked: str, reuse_when: str, **kwargs) -> None:
    get_memory().log_pattern(name, what_worked, reuse_when, **kwargs)


def search_memory(query: str) -> list[dict]:
    return get_memory().search(query)
