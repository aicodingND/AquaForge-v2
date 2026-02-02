"""Antigravity provider: filesystem or HTTP-based access to Google IDE projects."""

import fnmatch
import re
import subprocess
from pathlib import Path

try:
    import requests  # type: ignore
except Exception:
    requests = None  # type: ignore

# Default patterns to exclude from file listings
DEFAULT_EXCLUDES = [
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".DS_Store",
    "*.pyc",
    ".next",
    "dist",
    "build",
    ".turbo",
    "coverage",
]


class AntigravityProvider:
    def __init__(
        self,
        root: str = None,
        base_url: str = None,
        token: str = None,
        excludes: list[str] = None,
    ):
        self.excludes = excludes or DEFAULT_EXCLUDES

        if root:
            self.mode = "filesystem"
            self.root = Path(root)
        elif base_url:
            self.mode = "http"
            self.base_url = base_url.rstrip("/")
            self.token = token
        else:
            raise ValueError("Must provide either 'root' or 'base_url'.")

        if self.mode == "http" and requests is None:
            raise RuntimeError("HTTP mode requires 'requests' package to be installed.")

    def _should_exclude(self, path: Path) -> bool:
        """Check if path matches any exclude pattern."""
        path_str = str(path)
        for pattern in self.excludes:
            if fnmatch.fnmatch(path.name, pattern):
                return True
            if pattern in path_str.split("/"):
                return True
        return False

    # Internal HTTP helper
    def _http(self, path: str, method: str = "GET", data=None):
        if requests is None:
            raise RuntimeError("Requests library is not available.")
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        resp = requests.request(method, url, headers=headers, json=data)
        resp.raise_for_status()
        return resp.json()

    def list_projects(self) -> list[str]:
        """List all projects in the workspace."""
        if self.mode == "filesystem":
            if not self.root.exists():
                return []
            return [
                p.name for p in self.root.iterdir() if p.is_dir() and not self._should_exclude(p)
            ]
        else:
            return self._http("projects")

    def list_project_files(
        self,
        project: str,
        extension: str | None = None,
        pattern: str | None = None,
        max_depth: int | None = None,
    ) -> list[str]:
        """List files in a project with optional filtering."""
        if self.mode == "filesystem":
            proj_path = self.root / project
            if not proj_path.exists():
                return []

            files = []
            for p in proj_path.rglob("*"):
                if not p.is_file():
                    continue
                if self._should_exclude(p):
                    continue

                # Check depth
                if max_depth is not None:
                    rel_parts = p.relative_to(proj_path).parts
                    if len(rel_parts) > max_depth:
                        continue

                # Check extension filter
                if extension and not p.suffix.lstrip(".") == extension.lstrip("."):
                    continue

                # Check glob pattern
                rel_path = str(p.relative_to(proj_path))
                if pattern and not fnmatch.fnmatch(rel_path, pattern):
                    continue

                files.append(rel_path)

            return sorted(files)
        else:
            return self._http(f"projects/{project}/files")

    def read_file(
        self, project: str, path: str, start_line: int = None, end_line: int = None
    ) -> str:
        """Read file contents, optionally a specific line range."""
        if self.mode == "filesystem":
            file_path = self.root / project / path
            if not file_path.exists():
                raise FileNotFoundError(str(file_path))

            content = file_path.read_text(encoding="utf-8")

            if start_line is not None or end_line is not None:
                lines = content.splitlines(keepends=True)
                start = (start_line or 1) - 1
                end = end_line or len(lines)
                content = "".join(lines[start:end])

            return content
        else:
            data = self._http(f"projects/{project}/files/{path}", method="GET")
            return data

    def write_file(self, project: str, path: str, content: str) -> bool:
        """Write content to a file in the project."""
        if self.mode == "filesystem":
            file_path = self.root / project / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return True
        else:
            self._http(
                f"projects/{project}/files/{path}",
                method="PUT",
                data={"content": content},
            )
            return True

    def search_files(
        self, project: str, pattern: str, file_pattern: str | None = None
    ) -> dict[str, list[tuple[int, str]]]:
        """Search for pattern in project files (grep-like)."""
        if self.mode == "filesystem":
            proj_path = self.root / project
            if not proj_path.exists():
                return {}

            results: dict[str, list[tuple[int, str]]] = {}
            regex = re.compile(pattern, re.IGNORECASE)

            for file_path in proj_path.rglob("*"):
                if not file_path.is_file():
                    continue
                if self._should_exclude(file_path):
                    continue

                rel_path = str(file_path.relative_to(proj_path))

                # Check file pattern filter
                if file_pattern and not fnmatch.fnmatch(rel_path, file_pattern):
                    continue

                # Skip binary files
                try:
                    content = file_path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, PermissionError):
                    continue

                matches = []
                for line_no, line in enumerate(content.splitlines(), 1):
                    if regex.search(line):
                        matches.append((line_no, line.strip()))

                if matches:
                    results[rel_path] = matches

            return results
        else:
            return self._http(
                f"projects/{project}/search", method="POST", data={"pattern": pattern}
            )

    def get_file_tree(self, project: str, max_depth: int = 3) -> dict[str, any]:
        """Get project structure as a nested dictionary."""
        if self.mode == "filesystem":
            proj_path = self.root / project
            if not proj_path.exists():
                return {}

            def build_tree(path: Path, depth: int) -> dict | None:
                if depth > max_depth:
                    return None
                if self._should_exclude(path):
                    return None

                if path.is_file():
                    return {"type": "file", "size": path.stat().st_size}

                children = {}
                try:
                    for child in sorted(path.iterdir()):
                        if self._should_exclude(child):
                            continue
                        child_tree = build_tree(child, depth + 1)
                        if child_tree is not None:
                            children[child.name] = child_tree
                except PermissionError:
                    pass

                return {"type": "directory", "children": children}

            return build_tree(proj_path, 0) or {}
        else:
            return self._http(f"projects/{project}/tree")

    def get_git_diff(self, project: str, path: str | None = None) -> str:
        """Get git diff for a file or entire project."""
        if self.mode == "filesystem":
            proj_path = self.root / project
            if not proj_path.exists():
                return ""

            cmd = ["git", "diff"]
            if path:
                cmd.append(path)

            try:
                result = subprocess.run(
                    cmd, cwd=proj_path, capture_output=True, text=True, timeout=10
                )
                return result.stdout
            except (subprocess.TimeoutExpired, FileNotFoundError):
                return ""
        else:
            return self._http(f"projects/{project}/diff")

    def auto_detect_project(self) -> str | None:
        """Auto-detect project from current working directory."""
        if self.mode != "filesystem":
            return None

        cwd = Path.cwd()
        try:
            # Check if cwd is within any project
            for project in self.root.iterdir():
                if project.is_dir() and not self._should_exclude(project):
                    try:
                        cwd.relative_to(project)
                        return project.name
                    except ValueError:
                        continue

            # Check if cwd is the root itself
            if cwd == self.root or cwd.parent == self.root:
                # Return the first project or current dir name
                projects = self.list_projects()
                return projects[0] if projects else None
        except Exception:
            pass

        return None
