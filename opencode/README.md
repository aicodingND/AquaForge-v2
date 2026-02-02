# OpenCode CLI

Enhanced CLI for accessing and exploring Antigravity projects from the terminal.

## Features

- 📁 **List projects** - View all available projects
- 📄 **List files** - Browse with extension/pattern filtering
- 🔍 **Search** - Grep-like search across project files
- 🌲 **Tree view** - Visual project structure
- 👁️ **View files** - Syntax-highlighted file viewing with line ranges
- ✏️ **Write files** - Create or update files
- 📊 **Git diff** - View uncommitted changes
- ⚙️ **Auto-detect** - Automatically detect current project

## Installation

### Quick Start (from opencode directory)

```bash
cd /path/to/opencode
python main.py --help
```

### Install as Package (recommended)

```bash
cd /path/to/opencode
pip install -e .
```

Then use from anywhere:

```bash
oc list-projects
oc search "def optimize" --project AquaForge_v1.0.0-next_2026-01-10
```

## Commands

| Command         | Description                        | Example                               |
| --------------- | ---------------------------------- | ------------------------------------- |
| `list-projects` | List all projects                  | `oc list-projects`                    |
| `list-files`    | List files with filtering          | `oc list-files -e py -d 2`            |
| `show-file`     | View file with syntax highlighting | `oc show-file . main.py -s 1 -e 50`   |
| `search`        | Search files (regex)               | `oc search "class.*Optimizer"`        |
| `tree`          | Display project tree               | `oc tree -d 3`                        |
| `write-file`    | Write to a file                    | `oc write-file . test.txt -c "Hello"` |
| `diff`          | Show git diff                      | `oc diff -f src/main.py`              |
| `info`          | Show current config                | `oc info`                             |
| `context`       | Generate AI-ready context          | `oc context -f "*.py" -o context.md`  |
| `todo`          | Scan for TODO/FIXME/HACK           | `oc todo --priority`                  |
| `recent`        | Show recently modified files       | `oc recent -d 7 -e py`                |

## Configuration

Create `config.yaml`:

```yaml
provider: antigravity
mode: filesystem
root: "/path/to/workspace"

# Optional: custom exclude patterns
excludes:
  - .git
  - node_modules
  - __pycache__
```

## Usage Examples

### Search for a function definition

```bash
oc search "def calculate_score" --files "*.py"
```

### View specific lines of a file

```bash
oc show-file AquaForge main.py --start 100 --end 150
```

### List only Python files

```bash
oc list-files --ext py --depth 2
```

### View project structure

```bash
oc tree --depth 4
```

### Generate AI-ready context

```bash
oc context -f "src/*.py" -o context.md  # Save to file
oc context -f "*.ts" --max-lines 200    # Limit output
```

### Scan for TODOs and FIXMEs

```bash
oc todo                    # All action items
oc todo --priority         # Only FIXME/BUG/XXX/HACK
oc todo -f "backend/*.py"  # Filter by path
```

### See recently modified files

```bash
oc recent -d 7 -e py       # Python files from last 7 days
oc recent --limit 10       # Top 10 most recent
```

## Integration with Antigravity

Use OpenCode as **supplementary support**:

| Scenario                | Use              |
| ----------------------- | ---------------- |
| Complex multi-file work | Antigravity      |
| Quick file lookup       | OpenCode CLI     |
| Second AI opinion       | OpenCode Desktop |
| Batch scripting         | OpenCode CLI     |
| Generate AI context     | `oc context`     |
| Find tech debt          | `oc todo`        |
