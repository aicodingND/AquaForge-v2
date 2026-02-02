---
description: Use OpenCode CLI for quick file exploration and supplementary AI assistance
---

# OpenCode CLI Workflow

OpenCode is an enhanced CLI for accessing and exploring Antigravity projects from the terminal.

## Quick Setup

```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10/opencode
```

## Commands Reference

### 📁 List Projects

```bash
python main.py list-projects
```

### 📄 List Files (with filtering)

```bash
# All files
python main.py list-files AquaForge_v1.0.0-next_2026-01-10

# Only Python files
python main.py list-files AquaForge_v1.0.0-next_2026-01-10 --ext py

# With glob pattern
python main.py list-files AquaForge_v1.0.0-next_2026-01-10 --pattern "*.test.ts"

# Limit depth
python main.py list-files AquaForge_v1.0.0-next_2026-01-10 --depth 2
```

### 👁️ View File (with syntax highlighting)

```bash
# Full file
python main.py show-file AquaForge_v1.0.0-next_2026-01-10 README.md

# Specific line range
python main.py show-file AquaForge_v1.0.0-next_2026-01-10 main.py --start 50 --end 100
```

### 🔍 Search (grep-like)

```bash
# Basic search
python main.py search "def optimize" --project AquaForge_v1.0.0-next_2026-01-10

# Search only Python files
python main.py search "class.*Strategy" -p AquaForge_v1.0.0-next_2026-01-10 --files "*.py"

# Limit results
python main.py search "import" -p AquaForge_v1.0.0-next_2026-01-10 --max 20
```

### 🌲 Tree View

```bash
python main.py tree AquaForge_v1.0.0-next_2026-01-10 --depth 3
```

### ✏️ Write File

```bash
# Write inline content
python main.py write-file AquaForge_v1.0.0-next_2026-01-10 test.txt --content "Hello World"

# Write from another file
python main.py write-file AquaForge_v1.0.0-next_2026-01-10 config.json --from /path/to/source.json
```

### 📊 Git Diff

```bash
# All changes
python main.py diff AquaForge_v1.0.0-next_2026-01-10

# Specific file
python main.py diff AquaForge_v1.0.0-next_2026-01-10 --file src/main.py
```

### ⚙️ Info

```bash
python main.py info
```

## Shell Alias (Optional)

Add to `~/.zshrc`:

```bash
alias oc='cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10/opencode && python main.py'
```

Then use:

```bash
oc list-projects
oc search "SwimmerEntry" -p AquaForge_v1.0.0-next_2026-01-10
oc tree AquaForge_v1.0.0-next_2026-01-10
```

## Install as Package (Best)

```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10/opencode
pip install -e .
```

Then use globally:

```bash
oc list-projects
oc search "optimize" --project AquaForge_v1.0.0-next_2026-01-10
```

## Integration with Antigravity

| Task                         | Primary Tool | Supplementary        |
| ---------------------------- | ------------ | -------------------- |
| Complex multi-file edits     | Antigravity  | -                    |
| Quick code search            | Antigravity  | **OpenCode CLI**     |
| File exploration             | Antigravity  | OpenCode CLI/Desktop |
| Code review / second opinion | Antigravity  | OpenCode Desktop     |
| Batch file operations        | -            | **OpenCode CLI**     |
| Git diff preview             | -            | **OpenCode CLI**     |
| CI/CD checks                 | -            | OpenCode CLI         |

## When to Use OpenCode

### CLI (Terminal)

1. **Quick search** - Find function definitions, class usages
2. **File exploration** - Browse project structure
3. **Line range viewing** - Check specific sections of code
4. **Git diff** - Preview changes before commit
5. **Batch scripting** - Automate file operations

### Desktop App

1. **Side-by-side assistance** - Second AI perspective
2. **Isolated prototyping** - Test code snippets
3. **GUI preference** - Visual file browsing

## Best Practices

- **Don't duplicate work** - Antigravity is primary, OpenCode is support
- **Use search for discovery** - Find where things are defined/used
- **Use tree for orientation** - Understand project structure
- **Antigravity for state** - Keep all project memory here
