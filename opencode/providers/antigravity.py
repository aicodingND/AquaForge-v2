"""Antigravity provider: filesystem or HTTP-based access to Google IDE projects."""
from pathlib import Path
from typing import List

try:
    import requests  # type: ignore
except Exception:
    requests = None  # type: ignore


class AntigravityProvider:
    def __init__(self, root: str = None, base_url: str = None, token: str = None):
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

    # Internal HTTP helper
    def _http(self, path: str, method: str = "GET", data=None):
        if requests is None:
            raise RuntimeError("Requests library is not available.")
        url = f"{self.base_url}/{path.lstrip('/') }"
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        resp = requests.request(method, url, headers=headers, json=data)
        resp.raise_for_status()
        return resp.json()

    def list_projects(self) -> List[str]:
        if self.mode == "filesystem":
            if not self.root.exists():
                return []
            return [p.name for p in self.root.iterdir() if p.is_dir()]
        else:
            return self._http("projects")

    def list_project_files(self, project: str) -> List[str]:
        if self.mode == "filesystem":
            proj_path = self.root / project
            if not proj_path.exists():
                return []
            return [str(p.relative_to(self.root)) for p in proj_path.rglob("*") if p.is_file()]
        else:
            return self._http(f"projects/{project}/files")

    def read_file(self, project: str, path: str) -> str:
        if self.mode == "filesystem":
            file_path = self.root / project / path
            if not file_path.exists():
                raise FileNotFoundError(str(file_path))
            return file_path.read_text(encoding="utf-8")
        else:
            data = self._http(f"projects/{project}/files/{path}", method="GET")
            # If API returns raw content, adjust as needed; assume text here.
            return data
