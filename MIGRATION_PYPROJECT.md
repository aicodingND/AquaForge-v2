# Migration Guide: requirements.txt → pyproject.toml

## What Changed

We've consolidated three separate requirements files into a single `pyproject.toml` with optional dependency groups:

- `requirements.txt` → `[project.dependencies]` (base)
- `requirements-dev.txt` → `[project.optional-dependencies.dev]`
- `requirements-prod.txt` → `[project.optional-dependencies.prod]`

## Migration Steps

### 1. Update your local environment

```bash
# From project root
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10

# Uninstall old deps (optional, for clean slate)
pip freeze | grep -v "^-e" | xargs pip uninstall -y

# Install new deps
pip install -e .              # Base dependencies
pip install -e ".[dev]"       # Add dev dependencies
pip install -e ".[prod]"      # Add production dependencies (optional for local)
```

### 2. Update CI/CD

The GitHub Actions workflow has been updated to continue using the old requirements files during the transition. No changes needed immediately.

### 3. Update Docker

**Dockerfile** currently uses `requirements.txt`. Update the pip install line:

```dockerfile
# Old
RUN pip install --no-cache-dir -r requirements.txt

# New
RUN pip install --no-cache-dir -e .
```

For production builds:
```dockerfile
RUN pip install --no-cache-dir -e ".[prod]"
```

### 4. Update documentation

Update any README or setup docs that reference `requirements*.txt`:

```bash
# Old
pip install -r requirements.txt -r requirements-dev.txt

# New
pip install -e ".[dev]"
```

## Benefits

- **Single source of truth** - No more syncing 3 files
- **Standard format** - PEP 621 compliant
- **Better tooling** - pip, poetry, pdm all support pyproject.toml
- **Cleaner installs** - `pip install .[dev]` instead of `-r requirements.txt -r requirements-dev.txt`
- **Tool configs included** - ruff, pytest, mypy configs now in one file

## Rollback

If you need to roll back, the original files are still in the repo (not deleted). Just:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

## Notes

- The old `requirements*.txt` files are **not deleted** yet. Remove them once you've verified pyproject.toml works.
- pytest.ini config has been migrated to `[tool.pytest.ini_options]` in pyproject.toml. You can delete pytest.ini if desired.
- Black config has been migrated to `[tool.ruff.format]`. Remove any `.black` config if present.
