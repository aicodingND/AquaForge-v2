"""OpenCode CLI: minimal explorer for Antigravity projects"""
import typer
from opencode.providers import AntigravityProvider
import yaml
from pathlib import Path

app = typer.Typer()

def load_config(path: str = "config.yaml"):
    p = Path(path)
    if not p.exists():
        raise typer.ClickException(f"Config file not found: {path}. Create {path} or run from a repo containing it.")
    with p.open("r") as f:
        return yaml.safe_load(f)

def build_provider_from_config(cfg: dict) -> AntigravityProvider:
    prov = cfg.get("provider")
    if prov != "antigravity":
        raise typer.ClickException("Only provider 'antigravity' is supported in this starter.")
    mode = cfg.get("mode", "filesystem")
    if mode == "filesystem":
        root = cfg.get("root")
        if not root:
            raise typer.ClickException("Missing 'root' in config for filesystem mode.")
        return AntigravityProvider(root=str(root))
    else:
        base_url = cfg.get("base_url")
        token = cfg.get("token")
        if not base_url:
            raise typer.ClickException("Missing 'base_url' in config for http mode.")
        return AntigravityProvider(base_url=base_url, token=token)

@app.command()
def list_projects(cfg_path: str = "config.yaml"):
    """List available Antigravity projects."""
    cfg = load_config(cfg_path)
    provider = build_provider_from_config(cfg)
    projects = provider.list_projects()
    for p in projects:
        typer.echo(p)

@app.command()
def list_files(project: str, cfg_path: str = "config.yaml"):
    """List files in a given project."""
    cfg = load_config(cfg_path)
    provider = build_provider_from_config(cfg)
    files = provider.list_project_files(project)
    for f in files:
        typer.echo(f)

@app.command()
def show_file(project: str, path: str, cfg_path: str = "config.yaml"):
    """Show the contents of a file in a project."""
    cfg = load_config(cfg_path)
    provider = build_provider_from_config(cfg)
    content = provider.read_file(project, path)
    typer.echo(content)

if __name__ == "__main__":
    app()
