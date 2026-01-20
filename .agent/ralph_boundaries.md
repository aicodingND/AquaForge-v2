# Ralph Boundaries & Guardrails

## Hard Boundaries (Never Cross)

### 🚫 STOP Conditions

These conditions immediately halt the Ralph loop:

1. **Security Risk Detected**
   - Credentials exposed in code
   - SQL injection vulnerability introduced
   - Authentication bypass possible

2. **Data Loss Risk**
   - DELETE operations on production data
   - Irreversible file operations
   - Database truncation

3. **Infinite Loop Detected**
   - Same exact error 3+ consecutive times
   - No progress after 5 iterations
   - Resource exhaustion (memory/CPU)

4. **Scope Creep**
   - Task expanding beyond original definition
   - Touching files outside allowed scope
   - Introducing unrelated dependencies

### ⚠️ PAUSE Conditions

These require confirmation before continuing:

1. **Major Refactor Required**
   - >50% of a file needs rewriting
   - Architecture change needed
   - Breaking API changes

2. **External Dependencies**
   - New packages need installation
   - External API calls required
   - Database schema changes

3. **Uncertainty**
   - Multiple valid approaches exist
   - Requirements unclear
   - Trade-offs need human decision

## Soft Boundaries (Prefer Not To Cross)

1. **File Count**: Prefer <5 files per iteration
2. **Line Changes**: Prefer <100 lines per iteration
3. **Test Coverage**: Don't reduce coverage
4. **Performance**: Don't degrade by >10%

## Scope Limits Per Task Type

### API Development

```
Allowed:
  ✅ routers/*.py
  ✅ models.py
  ✅ deps.py
  ✅ tests/test_api.py

Not Allowed Without Permission:
  ⚠️ main.py (core app)
  ⚠️ config.py
  ⚠️ requirements.txt
  
Never:
  🚫 .env files
  🚫 secrets/*
  🚫 production configs
```

### Bug Fixes

```
Allowed:
  ✅ Files mentioned in error
  ✅ Direct dependencies of those files
  ✅ Related tests

Not Allowed:
  ⚠️ Unrelated files
  ⚠️ "While I'm here" changes
```

### Refactoring

```
Allowed:
  ✅ Specified module/package
  ✅ Tests for that module

Requires Checkpoint:
  ⚠️ Every 10 files changed
  ⚠️ Any interface changes
```

## Error Handling Protocol

### Error Seen Once

→ Analyze → Attempt fix → Continue

### Error Seen Twice  

→ Different approach → Log attempt → Continue

### Error Seen Three Times

→ **STOP** → Report to user → Request guidance

### Unknown Error Type

→ Log full traceback → Attempt safe rollback → Report

## Progress Checkpoints

Every 5 iterations:

1. Log current state
2. Summarize changes made
3. Report remaining issues
4. Confirm continuation

## Rollback Protocol

If iteration introduces regression:

1. Identify last known good state
2. Revert problematic changes
3. Log what was attempted
4. Try alternative approach

## Success Validation

Before declaring success:

1. ✅ Primary success criteria met
2. ✅ No new test failures
3. ✅ No new lint errors
4. ✅ Build still succeeds
5. ✅ No regressions in related functionality
