# Discovery Flow — Standalone Prompt

**Use:** Paste this into any AI conversation (Claude, GPT, etc.) to enter
the discovery flow mode. Replace the bracketed sections with your topic.

---

## The Prompt

```
I want to enter discovery mode. We're not building anything today.
We're not planning anything. We're EXPLORING.

Here's what I'm starting with:

[STARTING POINT: Describe what you know deeply — a technology you
built, a skill you have, a problem you're facing, a pattern you
noticed, or a feeling you can't articulate yet.]

I want to find where this applies beyond its obvious context.
The goal is NOT a solution, a plan, or a spec. The goal is:

1. EXPAND: Find 10-15 domains where this same structure appears,
   including surprising ones I'd never think of. Test each mapping
   structurally — "does the SAME logic apply with different inputs?"
   not just "is this vaguely similar?" Rank them by fit, value,
   and accessibility.

2. NAME: Find the ONE principle that unifies all the domains where
   it works. State it in one sentence. Test the name by checking
   that it correctly EXCLUDES the domains where it doesn't work.

3. BREAK: Show me where the pattern fails and why. Be honest.
   The breaks tell me the actual shape of the idea, not the
   shape I wish it had.

Rules for this conversation:
- Follow SURPRISE. When a mapping works that we didn't expect,
  go deeper there first.
- Every mapping must be STRUCTURAL, not metaphorical. "X uses
  the same algorithm as Y" is good. "X is like Y" is not enough.
- Don't filter ideas before testing them. Let the list grow to
  15+ before ranking.
- Don't name the pattern until 5+ examples confirm it.
- Don't suggest building or implementing anything. We're in
  the thinking space, not the building space.
- Give me insights and examples along the way. Show me WHY
  each connection matters, not just THAT it exists.

Let's start.
```

---

## Variant Prompts for Different Scenarios

### A: Technology Transfer
```
I built [specific technology] for [specific domain]. It works by
[brief description of how it works].

Enter discovery mode. Strip away the domain-specific parts and find
the abstract structure. Then expand: where else in the world does
this same structure appear? I want 15 candidate domains, ranked.
Then name the class of problems my technology solves. Then show me
where it breaks.
```

### B: Skill Transfer
```
I'm deeply skilled at [specific skill]. I've done it for [X years]
in [specific context].

Enter discovery mode. What is this skill REALLY about, underneath
the domain? What are the 3-5 core cognitive or physical moves?
Then expand: what other fields require these same core moves?
Name the abstract capability. Show me where the analogy breaks.
```

### C: Problem Reframing
```
I'm stuck on [specific problem]. I've tried [approaches that didn't
work]. I think the problem might be that I'm framing it wrong.

Enter discovery mode. Strip the problem to its abstract structure.
Find 5 other fields that faced structurally identical problems.
What did they do? Could any of their solutions work here?
Name what this problem actually IS, not what it looks like.
```

### D: "What's Next" Exploration
```
I'm at a crossroads. I'm drawn to [vague interest] but I don't
know what to do with it.

Enter discovery mode. Help me understand what I'm actually drawn
to — not the specific thing, but the abstract property it has.
Find 10 other paths that share this same property. Rank them.
Name what I'm actually looking for. Show me which paths are
accessible from where I am now.
```

### E: Business Model Discovery
```
I have [specific asset, capability, or position]. I know it's
valuable but I don't know how to monetize it.

Enter discovery mode. What does my asset ACTUALLY provide, abstracted?
Find 10 examples of companies that monetize the same abstract value.
What are their business models? Rank by fit to my situation.
Name the core value I'm sitting on. Show me the delivery mechanism
that matches it best.
```

### F: Research Direction
```
I noticed [something interesting]. It might be nothing, but it
feels like there's a pattern.

Enter discovery mode. What exactly did I notice? What's surprising
about it? Has anyone in any field noticed something structurally
similar? Expand to adjacent phenomena. Test whether they're truly
related or just similar-looking. If the pattern is real, name it.
If it isn't, tell me why the resemblance is misleading.
```

### G: Competitive Advantage Discovery
```
I have [specific combination of skills/knowledge/access]. Most
people have only one or two of these. Where does the COMBINATION
create an unfair advantage?

Enter discovery mode. What does each component provide independently?
Where do they MULTIPLY each other (not just add)? Find markets or
problems where nobody has this combination. Name the advantage.
Show me where it's strongest and where it doesn't matter.
```

---

## How to Know the Session Worked

**Good session indicators:**
- You have a NAME that feels right and survives testing
- You learned something you didn't know before you started
- At least one application surprised you ("I never would have
  thought of that, but it obviously fits")
- The name generates NEW examples automatically
- You feel energized, not drained

**"Come back later" indicators:**
- Lots of mappings but no name yet (need more examples)
- The name keeps shifting (not enough evidence to crystallize)
- Energy is dropping (try a different starting point)

**"This doesn't generalize" indicators:**
- Fewer than 3 domains pass 80% structural match
- Every mapping requires special pleading to work
- The abstraction gets vaguer as you add more examples
- (This is a VALID outcome. Not everything generalizes.
  Knowing that is valuable — it saves you from building
  something that doesn't transfer.)

---

*Standalone prompt template for entering discovery flow in any AI conversation.*
*Extracted from the AquaForge SDK creative session (2026-03-21).*
*Companion to: discovery-workflow.md and discovery-flow-state.md*
