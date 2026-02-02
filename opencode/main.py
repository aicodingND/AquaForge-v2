"""OpenCode CLI: Enhanced explorer for Antigravity projects.

Features:
- List projects and files with filtering
- Search across project files (grep-like)
- View files with syntax highlighting
- Tree view of project structure
- Write/edit files
- Git diff integration
- Auto-detect current project
"""

from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree

# Handle both standalone and package import
try:
    from opencode.providers.antigravity import AntigravityProvider
except ImportError:
    from providers.antigravity import AntigravityProvider

app = typer.Typer(
    name="opencode",
    help="OpenCode CLI - Access and explore Antigravity projects",
    add_completion=False,
)
console = Console()


def load_config(path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    p = Path(path)
    if not p.exists():
        # Try parent directories
        for parent in Path.cwd().parents:
            candidate = parent / "opencode" / "config.yaml"
            if candidate.exists():
                p = candidate
                break
        else:
            raise typer.ClickException(
                f"Config file not found: {path}. Create config.yaml in the opencode directory."
            )
    with p.open("r") as f:
        return yaml.safe_load(f)


def build_provider_from_config(cfg: dict) -> AntigravityProvider:
    """Build provider instance from configuration."""
    prov = cfg.get("provider")
    if prov != "antigravity":
        raise typer.ClickException("Only provider 'antigravity' is supported.")

    mode = cfg.get("mode", "filesystem")
    excludes = cfg.get("excludes")

    if mode == "filesystem":
        root = cfg.get("root")
        if not root:
            raise typer.ClickException("Missing 'root' in config for filesystem mode.")
        return AntigravityProvider(root=str(root), excludes=excludes)
    else:
        base_url = cfg.get("base_url")
        token = cfg.get("token")
        if not base_url:
            raise typer.ClickException("Missing 'base_url' in config for http mode.")
        return AntigravityProvider(base_url=base_url, token=token, excludes=excludes)


def get_project_or_auto(project: str | None, provider: AntigravityProvider) -> str:
    """Get project name or auto-detect from current directory."""
    if project:
        return project
    detected = provider.auto_detect_project()
    if detected:
        return detected
    raise typer.ClickException(
        "No project specified and could not auto-detect. Provide --project or run from within a project directory."
    )


# ============================================================================
# Commands
# ============================================================================


@app.command("list-projects")
def list_projects(
    cfg_path: str = typer.Option("config.yaml", help="Path to config file"),
):
    """List available Antigravity projects."""
    cfg = load_config(cfg_path)
    provider = build_provider_from_config(cfg)
    projects = provider.list_projects()

    if not projects:
        console.print("[yellow]No projects found.[/yellow]")
        return

    table = Table(title="📁 Projects", show_header=True, header_style="bold cyan")
    table.add_column("Project Name", style="green")

    for p in projects:
        table.add_row(p)

    console.print(table)


@app.command("list-files")
def list_files(
    project: str | None = typer.Argument(None, help="Project name (auto-detected if omitted)"),
    ext: str | None = typer.Option(
        None, "--ext", "-e", help="Filter by file extension (e.g., py, tsx)"
    ),
    pattern: str | None = typer.Option(
        None, "--pattern", "-p", help="Filter by glob pattern (e.g., *.test.ts)"
    ),
    depth: int | None = typer.Option(None, "--depth", "-d", help="Maximum directory depth"),
    cfg_path: str = typer.Option("config.yaml", help="Path to config file"),
):
    """List files in a project with optional filtering."""
    cfg = load_config(cfg_path)
    provider = build_provider_from_config(cfg)
    project = get_project_or_auto(project, provider)

    files = provider.list_project_files(project, extension=ext, pattern=pattern, max_depth=depth)

    if not files:
        console.print(f"[yellow]No files found in {project}.[/yellow]")
        return

    # Group by extension for summary
    ext_counts: dict = {}
    for f in files:
        file_ext = Path(f).suffix or "(no ext)"
        ext_counts[file_ext] = ext_counts.get(file_ext, 0) + 1

    console.print(f"\n[bold cyan]📄 Files in {project}[/bold cyan] ({len(files)} total)\n")

    for f in files[:100]:  # Limit output
        console.print(f"  {f}")

    if len(files) > 100:
        console.print(f"\n  [dim]... and {len(files) - 100} more files[/dim]")

    # Show extension summary
    console.print("\n[bold]Extension Summary:[/bold]")
    for ext_name, count in sorted(ext_counts.items(), key=lambda x: -x[1])[:10]:
        console.print(f"  {ext_name}: {count}")


@app.command("show-file")
def show_file(
    project: str | None = typer.Argument(None, help="Project name"),
    path: str = typer.Argument(..., help="Path to file within project"),
    start: int | None = typer.Option(None, "--start", "-s", help="Start line (1-indexed)"),
    end: int | None = typer.Option(None, "--end", "-e", help="End line (1-indexed)"),
    no_highlight: bool = typer.Option(False, "--no-highlight", help="Disable syntax highlighting"),
    cfg_path: str = typer.Option("config.yaml", help="Path to config file"),
):
    """Show the contents of a file with syntax highlighting."""
    cfg = load_config(cfg_path)
    provider = build_provider_from_config(cfg)
    project = get_project_or_auto(project, provider)

    try:
        content = provider.read_file(project, path, start_line=start, end_line=end)
    except FileNotFoundError:
        raise typer.ClickException(f"File not found: {project}/{path}")

    if no_highlight:
        console.print(content)
    else:
        # Determine language from extension
        ext = Path(path).suffix.lstrip(".") or "text"
        lang_map = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "tsx": "tsx",
            "jsx": "jsx",
            "yml": "yaml",
            "md": "markdown",
        }
        lang = lang_map.get(ext, ext)

        syntax = Syntax(
            content,
            lang,
            theme="monokai",
            line_numbers=True,
            start_line=start or 1,
        )
        console.print(Panel(syntax, title=f"📄 {path}", border_style="cyan"))


@app.command("search")
def search(
    pattern: str = typer.Argument(..., help="Search pattern (regex)"),
    project: str | None = typer.Option(None, "--project", "-p", help="Project name"),
    file_pattern: str | None = typer.Option(
        None, "--files", "-f", help="Filter files by glob pattern"
    ),
    max_results: int = typer.Option(50, "--max", "-m", help="Maximum results to show"),
    cfg_path: str = typer.Option("config.yaml", help="Path to config file"),
):
    """Search for pattern in project files (grep-like)."""
    cfg = load_config(cfg_path)
    provider = build_provider_from_config(cfg)
    project = get_project_or_auto(project, provider)

    console.print(
        f"\n[bold cyan]🔍 Searching for '[green]{pattern}[/green]' in {project}...[/bold cyan]\n"
    )

    results = provider.search_files(project, pattern, file_pattern=file_pattern)

    if not results:
        console.print("[yellow]No matches found.[/yellow]")
        return

    total_matches = sum(len(matches) for matches in results.values())
    shown = 0

    for file_path, matches in sorted(results.items()):
        console.print(f"[bold green]{file_path}[/bold green]")
        for line_no, line in matches:
            if shown >= max_results:
                break
            console.print(f"  [dim]{line_no:4d}:[/dim] {line[:120]}")
            shown += 1
        if shown >= max_results:
            break

    console.print(f"\n[dim]Found {total_matches} matches in {len(results)} files[/dim]")
    if shown < total_matches:
        console.print(f"[dim](Showing first {max_results} results, use --max to show more)[/dim]")


@app.command("tree")
def tree(
    project: str | None = typer.Argument(None, help="Project name"),
    depth: int = typer.Option(3, "--depth", "-d", help="Maximum depth"),
    cfg_path: str = typer.Option("config.yaml", help="Path to config file"),
):
    """Display project structure as a tree."""
    cfg = load_config(cfg_path)
    provider = build_provider_from_config(cfg)
    project = get_project_or_auto(project, provider)

    tree_data = provider.get_file_tree(project, max_depth=depth)

    if not tree_data:
        console.print(f"[yellow]No files found in {project}.[/yellow]")
        return

    def build_rich_tree(node: dict, tree: Tree):
        if node.get("type") == "directory":
            children = node.get("children", {})
            for name, child in sorted(children.items()):
                if child.get("type") == "directory":
                    subtree = tree.add(f"📁 [bold blue]{name}[/bold blue]")
                    build_rich_tree(child, subtree)
                else:
                    size = child.get("size", 0)
                    size_str = (
                        f"[dim]({size:,} bytes)[/dim]"
                        if size < 10000
                        else f"[dim]({size // 1024:,} KB)[/dim]"
                    )
                    tree.add(f"📄 {name} {size_str}")

    rich_tree = Tree(f"🗂️ [bold cyan]{project}[/bold cyan]")
    build_rich_tree(tree_data, rich_tree)
    console.print(rich_tree)


@app.command("write-file")
def write_file(
    project: str | None = typer.Argument(None, help="Project name"),
    path: str = typer.Argument(..., help="Path to file within project"),
    content: str | None = typer.Option(None, "--content", "-c", help="Content to write"),
    from_file: str | None = typer.Option(None, "--from", "-f", help="Read content from this file"),
    cfg_path: str = typer.Option("config.yaml", help="Path to config file"),
):
    """Write content to a file in the project."""
    cfg = load_config(cfg_path)
    provider = build_provider_from_config(cfg)
    project = get_project_or_auto(project, provider)

    if from_file:
        content = Path(from_file).read_text(encoding="utf-8")
    elif content is None:
        raise typer.ClickException("Must provide --content or --from-file")

    provider.write_file(project, path, content)
    console.print(f"[green]✓ Wrote to {project}/{path}[/green]")


@app.command("diff")
def diff(
    project: str | None = typer.Argument(None, help="Project name"),
    path: str | None = typer.Option(None, "--file", "-f", help="Specific file to diff"),
    cfg_path: str = typer.Option("config.yaml", help="Path to config file"),
):
    """Show git diff for project or specific file."""
    cfg = load_config(cfg_path)
    provider = build_provider_from_config(cfg)
    project = get_project_or_auto(project, provider)

    diff_output = provider.get_git_diff(project, path)

    if not diff_output:
        console.print("[yellow]No changes detected.[/yellow]")
        return

    syntax = Syntax(diff_output, "diff", theme="monokai", line_numbers=False)
    console.print(Panel(syntax, title="📊 Git Diff", border_style="yellow"))


@app.command("info")
def info(cfg_path: str = typer.Option("config.yaml", help="Path to config file")):
    """Show current configuration and auto-detected project."""
    cfg = load_config(cfg_path)
    provider = build_provider_from_config(cfg)

    table = Table(title="⚙️ OpenCode Configuration", show_header=False)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Provider", cfg.get("provider", "unknown"))
    table.add_row("Mode", cfg.get("mode", "filesystem"))
    table.add_row("Root", cfg.get("root", "N/A"))

    detected = provider.auto_detect_project()
    table.add_row("Auto-detected Project", detected or "[dim]None[/dim]")
    table.add_row("Current Directory", str(Path.cwd()))

    console.print(table)


# ============================================================================
# Phase 1 Enhancement Commands
# ============================================================================


@app.command("context")
def context(
    project: str | None = typer.Argument(None, help="Project name"),
    files: str = typer.Option("*.py", "--files", "-f", help="Glob pattern for files"),
    max_lines: int = typer.Option(500, "--max-lines", "-m", help="Max lines per file"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file"),
    cfg_path: str = typer.Option("config.yaml", help="Path to config file"),
):
    """Generate AI-ready context from files for copy-paste to AI tools."""
    import datetime

    cfg = load_config(cfg_path)
    provider = build_provider_from_config(cfg)
    project = get_project_or_auto(project, provider)

    matching_files = provider.list_project_files(project, pattern=files)

    if not matching_files:
        console.print(f"[yellow]No files matching '{files}' found.[/yellow]")
        return

    context_parts = [
        "# Code Context",
        f"# Generated: {datetime.datetime.now().isoformat()}",
        f"# Project: {project}",
        f"# Pattern: {files}",
        "",
    ]

    total_lines = 0
    files_included = 0

    for file_path in matching_files:
        try:
            content = provider.read_file(project, file_path)
            lines = content.splitlines()

            if len(lines) > max_lines:
                lines = lines[:max_lines]
                truncated = True
            else:
                truncated = False

            context_parts.append(f"## {file_path}")
            context_parts.append(f"```{Path(file_path).suffix.lstrip('.') or 'text'}")
            context_parts.extend(lines)
            context_parts.append("```")
            if truncated:
                context_parts.append(f"*[Truncated at {max_lines} lines]*")
            context_parts.append("")

            total_lines += len(lines)
            files_included += 1

        except Exception as e:
            context_parts.append(f"## {file_path}")
            context_parts.append(f"*Error reading file: {e}*")
            context_parts.append("")

    result = "\n".join(context_parts)

    if output:
        Path(output).write_text(result, encoding="utf-8")
        console.print(f"[green]✓ Context written to {output}[/green]")
    else:
        console.print(result)

    console.print(f"\n[dim]Included {files_included} files, {total_lines} lines total[/dim]")


@app.command("todo")
def todo(
    project: str | None = typer.Argument(None, help="Project name"),
    priority: bool = typer.Option(False, "--priority", "-p", help="Show only FIXME/XXX/HACK"),
    file_pattern: str | None = typer.Option(None, "--files", "-f", help="Filter files"),
    cfg_path: str = typer.Option("config.yaml", help="Path to config file"),
):
    """Scan for TODO, FIXME, HACK, and XXX comments in the codebase."""
    cfg = load_config(cfg_path)
    provider = build_provider_from_config(cfg)
    project = get_project_or_auto(project, provider)

    # Define search patterns
    if priority:
        patterns = ["FIXME", "XXX", "HACK", "BUG"]
        title = "🔥 Priority Action Items"
    else:
        patterns = ["TODO", "FIXME", "XXX", "HACK", "BUG", "NOTE", "OPTIMIZE"]
        title = "📋 Action Items"

    all_results: dict[str, list] = {}

    for pattern in patterns:
        results = provider.search_files(project, pattern, file_pattern=file_pattern)
        for file_path, matches in results.items():
            if file_path not in all_results:
                all_results[file_path] = []
            for line_no, line in matches:
                all_results[file_path].append((pattern, line_no, line))

    if not all_results:
        console.print("[green]✓ No action items found![/green]")
        return

    # Sort and display
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Type", style="yellow", width=8)
    table.add_column("File", style="green")
    table.add_column("Line", style="dim", width=6)
    table.add_column("Content", style="white", overflow="fold")

    total_count = 0
    for file_path in sorted(all_results.keys()):
        items = sorted(all_results[file_path], key=lambda x: x[1])
        for tag, line_no, content in items:
            # Color-code by severity
            if tag in ("FIXME", "BUG", "XXX"):
                tag_style = f"[bold red]{tag}[/bold red]"
            elif tag == "HACK":
                tag_style = f"[bold yellow]{tag}[/bold yellow]"
            else:
                tag_style = f"[cyan]{tag}[/cyan]"

            table.add_row(tag_style, file_path, str(line_no), content[:80])
            total_count += 1

    console.print(table)
    console.print(f"\n[dim]Found {total_count} items in {len(all_results)} files[/dim]")


@app.command("recent")
def recent(
    project: str | None = typer.Argument(None, help="Project name"),
    days: int = typer.Option(7, "--days", "-d", help="Show files modified in last N days"),
    ext: str | None = typer.Option(None, "--ext", "-e", help="Filter by extension"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max files to show"),
    cfg_path: str = typer.Option("config.yaml", help="Path to config file"),
):
    """Show recently modified files sorted by modification time."""
    import datetime

    cfg = load_config(cfg_path)
    provider = build_provider_from_config(cfg)
    project = get_project_or_auto(project, provider)

    if provider.mode != "filesystem":
        console.print("[yellow]Recent files only available in filesystem mode.[/yellow]")
        return

    proj_path = provider.root / project
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)

    recent_files = []
    for file_path in proj_path.rglob("*"):
        if not file_path.is_file():
            continue
        if provider._should_exclude(file_path):
            continue

        # Filter by extension
        if ext and file_path.suffix.lstrip(".") != ext.lstrip("."):
            continue

        try:
            mtime = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
            if mtime > cutoff:
                rel_path = file_path.relative_to(proj_path)
                recent_files.append((mtime, rel_path, file_path.stat().st_size))
        except (OSError, PermissionError):
            continue

    if not recent_files:
        console.print(f"[yellow]No files modified in the last {days} days.[/yellow]")
        return

    # Sort by modification time, newest first
    recent_files.sort(key=lambda x: x[0], reverse=True)
    recent_files = recent_files[:limit]

    table = Table(
        title=f"📅 Recently Modified (last {days} days)",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Modified", style="dim", width=16)
    table.add_column("File", style="green")
    table.add_column("Size", style="dim", justify="right", width=10)

    for mtime, rel_path, size in recent_files:
        time_str = mtime.strftime("%Y-%m-%d %H:%M")
        size_str = f"{size:,}" if size < 10000 else f"{size // 1024:,} KB"
        table.add_row(time_str, str(rel_path), size_str)

    console.print(table)
    console.print(f"\n[dim]Showing {len(recent_files)} of most recent files[/dim]")


if __name__ == "__main__":
    app()
