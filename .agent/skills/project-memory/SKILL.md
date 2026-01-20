---
name: Project Memory
description: Manages persistent memory across sessions - decisions, bugs, architecture
triggers:
  - remember this
  - what did we decide about
  - project history
  - past decisions
---

# Project Memory Skill 🧠

Use this skill to store and retrieve persistent knowledge across sessions.

---

## Memory Types

### 1. Decisions
Key decisions made during development that should persist.

**Storage**: `.agent/KNOWLEDGE_BASE.md` → Business Rules & Decisions section

**Format**:
```markdown
| Decision           | Date   | Rationale |
| ------------------ | ------ | --------- |
| [What was decided] | [Date] | [Why]     |
```

### 2. Bugs & Fixes
Historical bugs and their solutions for future reference.

**Storage**: `.agent/REFERENCE.md` → Historical Bug Fixes section

**Format**:
```markdown
### Bug: [Name]
**Date:** [Date]
**Symptoms:** [What happened]
**Cause:** [Root cause]
**Fix:** [Solution]
```

### 3. Session Notes
Active notes from current session.

**Storage**: `.agent/context/session_notes.md`

**Update during session**:
- Work completed
- Key decisions made
- Blockers encountered
- Next steps

### 4. Architecture Decisions
Significant architecture choices.

**Storage**: `.agent/REFERENCE.md` → Architecture Decisions Record section

**Format**: ADR format (ADR-### title)

---

## Memory Operations

### Remember (Store)

When user says "remember this" or similar:

1. **Identify memory type** (decision, bug, architecture, note)
2. **Format properly** using templates above
3. **Store in correct file**
4. **Confirm storage**

**Example**:
```
User: "Remember that we should use SST not Seton for team codes"

Action:
1. Type: Decision
2. Add to KNOWLEDGE_BASE.md Business Rules table
3. Confirm: "Stored: Use 'SST' team code, not 'Seton'"
```

### Recall (Retrieve)

When user asks about past decisions:

1. **Search relevant files**:
   - KNOWLEDGE_BASE.md for domain facts
   - REFERENCE.md for historical context
   - session_notes.md for recent work
   
2. **Present findings** with source

**Example**:
```
User: "What did we decide about relay scoring?"

Action:
1. Search KNOWLEDGE_BASE.md for "relay"
2. Find: "400 FR counts as individual slot at VCAC"
3. Return with context and source
```

### Update

When information changes:

1. **Find existing entry**
2. **Update content**
3. **Add changelog entry if significant**

---

## File Locations

| Memory Type   | File                     | Section                       |
| ------------- | ------------------------ | ----------------------------- |
| Domain Facts  | KNOWLEDGE_BASE.md        | Domain: Competitive Swimming  |
| Decisions     | KNOWLEDGE_BASE.md        | Business Rules & Decisions    |
| Bugs          | REFERENCE.md             | Historical Bug Fixes          |
| Architecture  | REFERENCE.md             | Architecture Decisions Record |
| Session Notes | context/session_notes.md | Active Notes                  |
| Changelog     | REFERENCE.md             | Changelog                     |

---

## Integration

This skill integrates with:
- `/aquaforge-start` - Loads memory at session start
- Session end - Prompts to save important learnings

---

## Best Practices

1. **Be specific** - Include dates, contexts, rationale
2. **Be concise** - Key information only
3. **Link sources** - Reference files/functions when relevant
4. **Update regularly** - Archive old notes, keep active ones current
5. **Use structured formats** - Tables and templates for searchability

---

_Skill: project-memory | Version: 1.0 | Pattern: Antigravity Awesome Skills_
