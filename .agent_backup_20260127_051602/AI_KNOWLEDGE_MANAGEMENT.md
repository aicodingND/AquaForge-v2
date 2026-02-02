# Best Practices: AI Knowledge Management for Development

## How to Maintain a Persistent "Source of Truth" for Antigravity Sessions

**Created**: 2026-01-15

---

## 🎯 The Problem

When working with AI coding assistants (like Antigravity/Claude), the AI starts each session without memory of previous sessions. This document outlines best practices for maintaining persistent knowledge that the AI can reference.

---

## 📊 Options Comparison

| Approach                | Pros                                                  | Cons                          | Best For                           |
| ----------------------- | ----------------------------------------------------- | ----------------------------- | ---------------------------------- |
| **Markdown in Repo**    | Version controlled, AI reads directly, human-readable | Manual updates needed         | ⭐ Technical rules, architecture   |
| **NotebookLM**          | AI-powered summaries, multi-source ingestion          | External to repo, query-based | Research, documentation synthesis  |
| **JSON/YAML Files**     | Machine-readable, structured                          | Less human-friendly           | ⭐ Configuration, structured rules |
| **README Files**        | Ubiquitous, expected location                         | Gets cluttered                | ⭐ Quick onboarding                |
| **`.agent/` Directory** | Dedicated AI context, clean separation                | Non-standard                  | ⭐ AI-specific context             |
| **Notion/Confluence**   | Rich formatting, collaboration                        | External, requires API        | Team knowledge bases               |

---

## ⭐ Recommended Approach: Hybrid `.agent/` System

### Why This Works Best

1. **I Can Read It**: Files in the repo are directly accessible during coding sessions
2. **Version Controlled**: Changes are tracked with your code
3. **Human-Readable**: Markdown is easy for you to maintain
4. **Predictable Location**: I know to look in `.agent/` for context
5. **Structured Yet Flexible**: Mix of prose and structured data

### Recommended Structure

```
.agent/
├── KNOWLEDGE_BASE.md       # ⭐ Primary source of truth
│                           #    Domain knowledge, rules, decisions
│
├── workflows/              # Reusable command sequences
│   ├── ralph.md           # Ralph Wiggum iterative development
│   └── deploy.md          # Deployment workflow
│
├── context/                # Session-specific context (optional)
│   ├── championship.md    # Championship mode development context
│   └── current_sprint.md  # What we're working on now
│
├── rules/                  # Structured rules (optional)
│   ├── scoring.yaml       # Scoring rules in structured format
│   └── constraints.yaml   # Optimization constraints
│
└── prompts/                # Reusable prompt templates (optional)
    └── code_review.md
```

---

## 📝 Best Practices for KNOWLEDGE_BASE.md

### DO ✅

1. **Use Tables** - Easy for AI to parse structured information
2. **Include Sources** - Note where facts came from
3. **Date Updates** - Track when information was added
4. **Keep Current** - Remove outdated information
5. **Use Clear Headings** - Makes scanning efficient
6. **Include Examples** - Concrete examples clarify rules

### DON'T ❌

1. **Don't Duplicate** - If it's in code, reference the file instead
2. **Don't Over-Document** - Focus on what AI needs to know
3. **Don't Include Sensitive Data** - No API keys, passwords
4. **Don't Make It Too Long** - Split into multiple files if needed

---

## 🔄 When to Update KNOWLEDGE_BASE.md

### Update Immediately When:

- [ ] New domain rules are discovered (e.g., VISAA scoring)
- [ ] Architecture decisions are made
- [ ] You learn something the AI kept getting wrong
- [ ] External integrations are added

### Update Periodically:

- [ ] Prune outdated information
- [ ] Consolidate scattered notes
- [ ] Update dates and championships

---

## 🤖 How I (Antigravity) Use This

### At Session Start

When you ask me to work on AquaForge, I can:

1. Read `.agent/KNOWLEDGE_BASE.md` for domain context
2. Check `.agent/workflows/` for established patterns
3. Reference `docs/` for detailed documentation

### During Development

1. I apply rules from KNOWLEDGE_BASE.md to my suggestions
2. I reference constraints when optimizing
3. I avoid known gotchas documented in the file

### Updating

1. After research (like today's VISAA lookup), I update the knowledge base
2. You can ask me to add new facts anytime
3. I'll note what I learned for future sessions

---

## 🔧 Alternative: NotebookLM Integration

### When NotebookLM Makes Sense

1. **Research Phase**: Upload papers, PDFs, websites for synthesis
2. **Complex Documentation**: When you have many source documents
3. **Query-Based Access**: "What do we know about X?"

### Workflow

1. Create a NotebookLM notebook for AquaForge
2. Upload relevant documents (NFHS rulebook, VISAA docs)
3. Use NotebookLM to answer research questions
4. Export key findings to `.agent/KNOWLEDGE_BASE.md`

### Limitation

I (Antigravity) cannot directly access NotebookLM during coding sessions. You'd need to:

- Copy/paste relevant excerpts
- Or export summaries to markdown files

---

## 📋 Quick Start Checklist

### Initial Setup ✅

- [x] Create `.agent/KNOWLEDGE_BASE.md`
- [x] Add domain knowledge sections
- [x] Document key decisions
- [ ] Add structured rules files (optional)

### Per-Session

- [ ] Ask AI to read KNOWLEDGE_BASE.md if context seems missing
- [ ] Update file with new learnings after research
- [ ] Note any corrections needed

### Periodic Maintenance

- [ ] Review and prune quarterly
- [ ] Ensure dates are current
- [ ] Archive obsolete information

---

## 💡 Pro Tips

### 1. Use Frontmatter for Metadata (Optional)

```yaml
---
updated: 2026-01-15
version: 1.0
topics: [swimming, visaa, optimization]
---
```

### 2. Cross-Reference Files

```markdown
See also: [Championship Adaptation](../docs/VISAA_CHAMPIONSHIP_ADAPTATION.md)
```

### 3. Include "Ask Me About" Section

```markdown
## 🤖 If You're an AI, Ask About:

- VISAA championship scoring rules
- Why we use Nash Equilibrium
- Exhibition swimmer strategy
```

### 4. Version Important Changes

```markdown
## Changelog

| Date       | Change                         | Impact                    |
| ---------- | ------------------------------ | ------------------------- |
| 2026-01-15 | Added VISAA championship rules | New scoring module needed |
```

---

## 🏁 Summary

**For AquaForge, I recommend:**

1. **Primary**: `.agent/KNOWLEDGE_BASE.md` (created above)
2. **Workflows**: `.agent/workflows/` (already exists)
3. **Detailed Docs**: `docs/` (already exists)
4. **Handoff Context**: `docs/AI_HANDOFF_CONTEXT.md` (already exists)

**The combination gives you:**

- Quick reference for domain facts (KNOWLEDGE_BASE)
- Reusable command sequences (workflows)
- Deep documentation (docs)
- Session handoff notes (AI_HANDOFF_CONTEXT)

---

_This document itself is in `.agent/` for your reference!_
