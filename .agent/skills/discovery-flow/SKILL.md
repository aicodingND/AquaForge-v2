---
name: discovery-flow
description: Enter the discovery flow state — structured creative exploration where the GOAL is to find the pattern, name it, and see where it breaks. Not brainstorming, not building. The space in between where insights compound. Use when you want to explore ideas across domains, find hidden connections, or think through something deeply before committing to any plan.
allowed-tools: Read, Glob, Grep, WebSearch, WebFetch, Agent
---

# Discovery Flow

> **Purpose:** Set the stage for Phases 3-4 of the discovery process — the expansion
> and naming phases — as their own end goal. The output is a NAMED PATTERN with
> identified boundaries, not a plan, not a spec, not a task list.

---

## When to Invoke

| User Signal | This Skill Applies |
|---|---|
| "I want to explore..." | Yes |
| "What if [X] could also..." | Yes |
| "Help me think through..." | Yes |
| "Where else could this apply?" | Yes |
| "I have a hunch about..." | Yes |
| "Build me a..." | No — use brainstorming or plan-writing |
| "Fix this bug..." | No — use systematic-debugging |
| "Review this code..." | No — use code-reviewer |

---

## Operating Rules

### 1. NO BUILDING
Do not write code, create files, or produce specifications during discovery flow.
The only outputs are: insights, mappings, names, gaps, and questions.
If the conversation drifts toward "how would we implement this," gently redirect:
"That's a Phase 7 question — we're still in Phase 3/4. Let's keep expanding."

### 2. FOLLOW SURPRISE
When a mapping works that wasn't expected, go deeper there FIRST.
Expected confirmations are low-information. Unexpected fits are high-information.
Prioritize threads that produce the reaction: "Wait, that actually works?"

### 3. STRUCTURAL, NOT METAPHORICAL
Every correspondence must be testable. Push from "X is like Y" to
"X uses the same math/logic/structure as Y with different inputs."
If a mapping is only metaphorical, name it as such and move on.

### 4. ACCUMULATE BEFORE NAMING
Do not name the pattern until 5+ examples confirm it. Premature naming
freezes the exploration. Let the name emerge from sufficient evidence.

### 5. RANK, DON'T LIST
Every time a list of options/applications/examples exceeds 5 items,
rank them immediately. Unranked lists are noise.

### 6. BE HONEST ABOUT BREAKS
When a mapping DOESN'T work, that's MORE informative than when it does.
Breaks reveal boundaries. Boundaries define the actual shape.
Never paper over a break to preserve the narrative.

---

## The Session Arc

### Opening Move: The Squint

Start by abstracting whatever the user brings. Strip domain-specific
language. Find the structural bones.

```
PROMPT TO SELF:
"What is this thing, underneath what it looks like?
 What are its 3-5 abstract properties?
 If I removed every proper noun, what kind of problem remains?"
```

### Phase 2: First Contact

Find ONE domain that shares the abstract structure. Test the mapping
property by property. Note where it holds AND where it breaks.

```
PROMPT TO SELF:
"Does [Domain X] have ALL the same properties?
 Which properties map exactly?
 Which ones break, and what does the break tell us?"
```

### Phase 3: The Expansion (TARGET ZONE)

This is where discovery flow begins. Rapidly generate and test
applications across as many domains as possible.

```
TECHNIQUE: Spray and test.
  - Generate 10-20 candidate domains in 2 minutes
  - For each, quick-test: does it have the key properties?
  - Discard <50% fit immediately
  - Rank remainder by Fit x Value / Friction
  - Deep-dive the top 3-5

LOOK FOR:
  - The application that SURPRISES you (unexpected fit = high value)
  - The application that ALMOST works but breaks on one property
    (the break reveals something important about the pattern)
  - The cluster: 3+ applications that share a sub-property the
    others lack (this points toward the Phase 4 name)
```

### Phase 4: The Naming (PEAK)

This is the creative peak. Everything before this was observation.
This is creation. Find the sentence that captures the entire pattern.

```
PROMPT TO SELF:
"What do the TOP applications share that the BOTTOM ones lack?
 What single property discriminates between 'great fit' and 'stretch'?
 Can I state the unifying principle in ONE sentence?
 Does that sentence correctly EXCLUDE the things that don't fit?"

TEST THE NAME:
  - Take an application you KNOW doesn't fit.
  - Apply the name/definition. Does it correctly exclude it?
  - If yes → the name has teeth.
  - If no → the name is too broad. Tighten it.
```

### Phase 5: The Gap (Optional Continuation)

If the session has energy after naming, find where the pattern breaks.

```
PROMPT TO SELF:
"What assumptions does this pattern make?
 Which assumptions are violated in the real world?
 For each violation: is it FATAL or FILLABLE?"
```

### Closing: Capture

Before ending, capture:
1. The NAME (one sentence)
2. The TOP 3 applications (ranked)
3. The KEY INSIGHT (the thing that wasn't obvious before the session)
4. The BREAK POINTS (where the pattern fails and why)
5. The OPEN QUESTIONS (what would you explore next?)

---

## Facilitator Behavior

During discovery flow, the AI's role shifts from assistant to THINKING PARTNER:

| Normal Mode | Discovery Flow Mode |
|---|---|
| Answer questions | Ask questions back |
| Solve problems | Extend problems into new domains |
| Converge to solutions | Diverge to possibilities, then compress |
| Be concise | Take space for the insight to develop |
| Filter for relevance | Follow surprise, even if tangential |
| Track progress | Track ENERGY — where is the momentum? |

### Key Facilitation Moves

**"What if that's also true for..."** — Extend a working mapping to an adjacent domain.

**"That breaks because..."** — Stress-test a mapping with a specific counterexample.

**"The thing those three have in common is..."** — Attempt a premature name to see if it holds.

**"Wait — that means..."** — Follow a logical implication of a mapping to its conclusion.

**"Who else has this problem and doesn't know it?"** — Reframe an application in terms of who would pay.

**"What would need to be true for that to work?"** — Identify hidden assumptions.

---

## Scenario Templates

The discovery flow process works for ANY starting point. Here are
entry templates for completely different scenarios:

---

### Scenario A: Technology Transfer
*"I built X for domain Y. Where else does it apply?"*

```
THE SQUINT:
  My [technology] solves the problem of [abstract description].
  Its core properties are: ________________

THE MAPPING:
  Domain that might share this structure: ________________
  Property match:  A→___, B→___, C→___, D→___
  Where it breaks: ________________

THE EXPANSION:
  15 candidate domains: [brainstorm rapidly, rank by fit x value / friction]

THE NAME:
  "My technology dominates problems that are: ________________"
```

**Example:** "I built a real-time inventory optimizer for restaurants.
Where else does it apply?" → Squint: "It assigns limited perishable
resources to time-sensitive demand under uncertain consumption." →
Map to: hospital blood banks, live event catering, cloud server
autoscaling, airline seat pricing...

---

### Scenario B: Skill Transfer
*"I'm deeply skilled at X. What else could I do with this?"*

```
THE SQUINT:
  My skill is really about: ________________ (abstracted)
  The core cognitive/physical moves are: ________________

THE MAPPING:
  Another field that requires the same moves: ________________
  Where the analogy holds: ________________
  Where it breaks: ________________

THE EXPANSION:
  15 fields/roles that require these same core moves: [rank]

THE NAME:
  "My skill set is really about: ________________"
  "I thrive in situations that require: ________________"
```

**Example:** "I'm a trial lawyer. What other careers use the same
skills?" → Squint: "I construct arguments under adversarial
conditions, read opponents in real-time, and persuade a neutral
third party under time pressure." → Map to: sales negotiation,
political debate coaching, crisis PR, hostage negotiation,
competitive debate judging, startup pitching...

---

### Scenario C: Problem Reframing
*"I'm stuck on problem X. Is there another way to see it?"*

```
THE SQUINT:
  The problem feels like: ________________
  Stripped to its bones, it's really: ________________

THE MAPPING:
  Another field that solved a structurally similar problem: ________________
  Their solution was: ________________
  Could that approach apply here? ________________

THE EXPANSION:
  5 fields that faced this same structural problem: [list their solutions]

THE NAME:
  "This isn't really a [domain] problem. It's a [abstract class] problem.
   And [field X] already solved it."
```

**Example:** "My startup can't figure out pricing." → Squint: "We're
setting a price in a market where customers have asymmetric
information about product quality." → Map to: used car markets
(Akerlof's lemons problem), insurance underwriting, art auctions →
Name: "This is a signaling problem. The price isn't just a price —
it's a SIGNAL of quality. The solution is from information economics,
not from running A/B tests on price points."

---

### Scenario D: Business Model Discovery
*"I have [asset/capability]. How do I make money with it?"*

```
THE SQUINT:
  What my asset actually provides is: ________________ (abstracted)
  The value it creates is: ________________

THE MAPPING:
  Someone else who monetizes similar abstract value: ________________
  Their business model: ________________
  Would that model work here? ________________

THE EXPANSION:
  10 business models that monetize this type of value: [rank by fit]

THE NAME:
  "The core value is ________________.
   The best delivery mechanism is ________________."
```

**Example:** "I have 5 years of scraped real estate data. How do I
make money?" → Squint: "I have a proprietary historical dataset
with predictive power in an illiquid market." → Map to: Bloomberg
(financial data terminal), Zillow (real estate estimates), PitchBook
(VC deal data) → Name: "You're not selling data. You're selling
REDUCED UNCERTAINTY in high-stakes illiquid decisions. Charge
per-decision, not per-data-point."

---

### Scenario E: Life/Career Exploration
*"I feel drawn to X but I'm not sure why. Help me understand."*

```
THE SQUINT:
  What draws me is really: ________________ (abstracted from the specific thing)
  The feeling is: ________________

THE MAPPING:
  Other activities/fields that produce the same feeling: ________________
  What they all share: ________________

THE EXPANSION:
  10 paths that would give me this: [rank by accessibility + alignment]

THE NAME:
  "What I'm actually looking for is: ________________
   The specific instance I started with was just one expression of it."
```

**Example:** "I'm drawn to competitive swimming coaching but I'm
a software engineer." → Squint: "I want to optimize the performance
of a small team against competition, with feedback loops and
measurable outcomes." → Map to: engineering management, fantasy
sports, esports team management, personal training, startup founding →
Name: "You want COMPETITIVE OPTIMIZATION WITH A TEAM. Coaching is
one instance. Building a startup is another. They scratch the same
itch because they ARE the same activity at the structural level."

---

### Scenario F: Research Direction Finding
*"There's something interesting here but I can't articulate it."*

```
THE SQUINT:
  The thing I noticed: ________________
  What's surprising about it: ________________

THE MAPPING:
  Has anyone noticed something similar in a different context? ________________
  What did they do with it? ________________

THE EXPANSION:
  Adjacent phenomena that might be related: [list]
  Are they related, or just similar-looking? [test structurally]

THE NAME:
  "The phenomenon is: ________________
   The question worth investigating is: ________________"
```

---

### Scenario G: Creative Project Direction
*"I want to make something but I don't know what."*

```
THE SQUINT:
  The medium/tools I'm drawn to: ________________
  What excites me about them (abstracted): ________________

THE MAPPING:
  Works I admire that produce the same feeling: ________________
  What they share structurally: ________________

THE EXPANSION:
  10 possible projects: [rank by personal energy + feasibility]

THE NAME:
  "The thing I actually want to create is: ________________
   The specific medium matters less than: ________________"
```

---

## Anti-Patterns (What Discovery Flow Is NOT)

| Anti-Pattern | Why It Kills the State |
|---|---|
| Starting with "how do we build this?" | Skips directly to construction — no pattern to discover |
| Filtering ideas before testing them | Kills threads that lead to the key insight |
| Stopping at the first working mapping | One mapping is a coincidence, not a pattern |
| Naming too early (fewer than 5 examples) | Premature name freezes exploration |
| Treating every break as a failure | Breaks are information, not failures |
| Trying to produce a deliverable | The deliverable is the INSIGHT, not a document |
| Rushing through the ramp (first 30 min) | Discovery flow has increasing returns — the start is slow by nature |
| Switching to evaluation mode ("is this practical?") | Practicality is Phase 7. We're in Phase 3-4. |

---

## Session Endings

### Good Ending Indicators
- You have a NAME that feels right and survives stress-testing
- You have 3+ applications ranked with clear separation
- You discovered something you didn't know before the session started
- The name generates NEW examples automatically when you apply it

### "Come Back Later" Indicators
- You have lots of mappings but no name yet (need more examples)
- The name keeps changing (not enough evidence to crystallize)
- Energy is dropping (the ramp didn't reach acceleration)

### "This Doesn't Generalize" Indicators
- Fewer than 3 domains pass 80% property match
- Every mapping requires special exceptions to work
- The abstraction keeps getting vaguer to accommodate more examples
- (This is a VALID outcome — not everything generalizes. Knowing
  that saves you from building something that doesn't transfer.)
