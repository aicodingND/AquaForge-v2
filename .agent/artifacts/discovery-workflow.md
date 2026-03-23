# The Discovery Workflow

**A repeatable process for taking something you've built or know deeply
and finding where else it applies, what it's missing, and what it could become.**

Extracted from the AquaForge SDK creative session (2026-03-21).
Domain-agnostic — works for any field, any technology, any idea.

---

## How to Use This

Start at Phase 1 with any piece of technology, skill, framework, or idea
you understand deeply. Work through each phase in order. Each phase has:

- **The question** it answers
- **The move** — what you actually do
- **The test** — how you know it's working
- **The trap** — the common mistake at this stage
- **Transition signal** — how you know it's time for the next phase

You don't always reach Phase 7. Sometimes Phase 3 reveals the idea doesn't
generalize. Sometimes Phase 5 reveals fatal gaps. That's not failure — that's
the process working. The point is to find truth, not to confirm hope.

---

## Phase 1: The Squint

**Question:** "What is this thing, really — underneath what it looks like?"

### The Move
Take the thing you've built and strip away every domain-specific word.
Replace proper nouns with generic nouns. Replace specific rules with
abstract constraint types. Keep only the structural bones.

**Template:**

```
My [specific thing] takes [domain-specific inputs]
and produces [domain-specific outputs]
by solving the problem of [abstract problem description]
subject to [abstract constraints]
under [abstract conditions].
```

### Example
```
BEFORE (domain-specific):
"AquaForge assigns swimmers to events to maximize team score
 in a dual meet against an opponent, subject to VISAA eligibility
 rules, with uncertain race times."

AFTER (abstracted):
"AquaForge assigns resources to slots to maximize an objective
 against an adversary, subject to eligibility constraints,
 with uncertain performance outcomes."
```

### The Test
Read the abstracted version to someone who doesn't know your domain.
Can they understand the SHAPE of the problem without knowing it's about
swimming? If yes, the abstraction is good.

### The Trap
Abstracting too far. "It solves problems" is useless. "It assigns
resources to slots under constraints against an adversary with uncertain
outcomes" is useful. Keep enough structure to be testable.

### Transition Signal
You've identified 3-5 abstract properties of your system (assignment,
constraints, adversary, uncertainty, etc.) that don't mention your
specific domain at all. Move to Phase 2.

---

## Phase 2: The Mapping

**Question:** "Where else does this exact structure appear?"

### The Move
Take each abstract property from Phase 1 and find ONE concrete example
in a completely different domain that has the same property. Then check:
does the SAME example have ALL your properties simultaneously?

**Template:**

```
My system has properties: [A, B, C, D, E]

Domain X:
  Property A maps to: [specific correspondence]
  Property B maps to: [specific correspondence]
  Property C maps to: [specific correspondence]
  Property D maps to: [specific correspondence]
  Property E maps to: [?? — does it exist or not?]
```

### The Key Discipline
The mapping must be STRUCTURAL, not METAPHORICAL.

```
STRUCTURAL (good):
  "Gurobi's binary assignment of swimmers to events
   IS the same math as assigning ad spend to channels."
  (Same algorithm, same constraint types, same solver)

METAPHORICAL (bad):
  "Optimizing a swim lineup is LIKE optimizing your life."
  (No shared mathematical structure)
```

Ask: "Could I literally run the same code with different input data?"
If yes, the mapping is structural. If no, it's metaphorical.

### The Test
For each mapping, ask: "What would BREAK this correspondence?"
If you can't find a break, the mapping is strong.
If you find a break, note it — that's a real boundary, not a failure.

### The Trap
Confirmation bias. You WANT the mapping to work, so you ignore
the spots where it doesn't. The most valuable finding in this phase
is often WHERE the mapping breaks, because that tells you what's
truly domain-specific vs. what's genuinely general.

### Transition Signal
You've found 2-3 domains where 80%+ of properties map structurally.
The correspondences feel obvious in retrospect. Move to Phase 3.

---

## Phase 3: The Expansion

**Question:** "How far does this reach?"

### The Move
Brainstorm aggressively. Throw every industry, every problem, every
context you can think of at the abstract structure. Don't filter yet.
Quantity over quality. Aim for 15-30 candidates.

Then RANK them on three axes:

```
FIT:      How many of the abstract properties does this domain have?
          (1-10, where 10 = all properties present)

VALUE:    How much money / impact is at stake in this domain?
          (market size, problem severity, willingness to pay)

FRICTION: How hard is it to enter this domain?
          (data availability, competition, regulation, sales cycle)
```

**Score = Fit x Value / Friction**

### The Key Discipline
Rank, don't just list. An unranked list of 20 applications is
paralyzing. A ranked list with the top 3 highlighted is actionable.

Also: be honest about LOW-FIT applications. If something scores 4/10
on fit, it doesn't belong on the list no matter how big the market is.
A weak structural fit means your tools won't actually help.

### The Test
Take your top-ranked application. Describe to someone how your
existing system would solve their problem. If they say "yes, that's
exactly my problem" — the ranking is right. If they say "sort of,
but you're missing the point" — the fit score is inflated.

### The Trap
Falling in love with a huge market that has weak fit.
"Healthcare is a $4 trillion market!" Yes, but if your system
only addresses 2 of 5 properties in healthcare problems,
you're forcing a fit that isn't there.

### Transition Signal
You've ranked 15+ applications. The top 3-5 have clear separation
from the rest. You start noticing that the top applications share
a property that the bottom ones lack. That shared property is
calling you to Phase 4. Move to Phase 4.

---

## Phase 4: The Naming

**Question:** "What's the ONE principle that unifies everything that works?"

### The Move
Look at your top-ranked applications from Phase 3. Ask: what do they
ALL share that the bottom-ranked ones DON'T? Find the discriminating
property — the one thing that separates "this is a great fit" from
"this is a stretch."

Then name it. Give the class of problems a precise, memorable label.

**Template:**

```
My system dominates problems that are:
"[Adjective] [noun] games/problems under [condition] with [property]"

Examples:
  "Sequential information-revelation games under constrained
   adversarial optimization with correlated uncertain outcomes"

  "Repeated allocation decisions under regulatory constraints
   with observable competitor behavior and measurable outcomes"
```

### The Key Discipline
The name must be FALSIFIABLE. It should be possible to look at a
new problem and clearly determine whether it belongs to the class
or not.

Test: "Is [random problem X] a member of this class?"
Good name → you can answer definitively yes or no.
Bad name → you say "sort of" or "it depends."

### The Test
Take a problem you KNOW doesn't fit (from the bottom of your
Phase 3 ranking). Apply your name/definition. Does it correctly
EXCLUDE that problem? If yes, the definition has teeth.

### The Trap
Naming too broadly. "Problems involving decisions" includes everything.
"Sequential information-revelation games" includes only things where
an opponent reveals information over time — which is specific, testable,
and useful.

Also: naming too early. If you only have 2 examples, you don't have
a class — you have a coincidence. Wait until 5+ examples confirm
the pattern.

### Transition Signal
You can state the unifying principle in one sentence. Someone hearing
it for the first time says "oh — I can think of three more examples."
The name generates new applications automatically. Move to Phase 5.

### This Is the Creative Peak
Phase 4 is where the most valuable thinking happens. The moment you
NAME the pattern, it becomes portable. You can carry it into rooms
and conversations where nobody has heard of your original system,
and the principle still makes sense on its own.

If you only do ONE phase of this workflow, do this one.

---

## Phase 5: The Gap

**Question:** "Where does this framework fail, and why?"

### The Move
Take your named class of problems and list every assumption your
system makes. For each assumption, ask: "Is this actually true
in the real world?"

**Template:**

```
ASSUMPTION: [what your system assumes]
REALITY:    [what actually happens]
GAP:        [the distance between assumption and reality]
SEVERITY:   [does this kill the approach or just weaken it?]
```

### Example
```
ASSUMPTION: Outcomes are independent (Monte Carlo samples each entity separately)
REALITY:    Teammates' outcomes are correlated (if QB throws a lot, WR catches a lot)
GAP:        Independent MC underestimates both upside AND downside of correlated groups
SEVERITY:   HIGH in DFS (stacking is the primary strategy); LOW in single-event betting
```

### The Key Discipline
Honesty. This phase is adversarial — you're attacking your own idea.
Every gap you find now is one that won't surprise you later.

The best gaps have a specific shape: "My system assumes X, but in
domain Y, X is violated in a specific, measurable way." That shape
is actionable because you can go find a tool that handles the violation.

### The Test
For each gap, ask: "If I ignore this gap, what's the worst thing
that happens?" If the answer is "slightly less accurate predictions,"
the gap is LOW severity. If the answer is "the system gives advice
that loses money," the gap is HIGH severity.

### The Trap
Two opposite traps:
1. Minimizing gaps ("it's probably fine") — leads to building on
   shaky foundations
2. Catastrophizing gaps ("this invalidates everything") — leads to
   abandoning good ideas because of solvable problems

The discipline: every gap is either FATAL (stop) or FILLABLE (continue
to Phase 6). Most gaps are fillable.

### Transition Signal
You have a list of 4-8 gaps, ranked by severity. None are fatal.
Each one describes a specific assumption violation with measurable
consequences. Move to Phase 6.

---

## Phase 6: The Frontier

**Question:** "What already exists in the world that closes these gaps?"

### The Move
For each gap from Phase 5, search for techniques, tools, algorithms,
or research that specifically addresses that gap. You're not inventing —
you're scouting.

Search pattern:
```
"[Technical term for the gap] + [the field most likely to have solved it]"

Example:
  Gap: "Outcomes aren't independent"
  Search: "copula models correlated simulation finance"
  Find: Gaussian copulas — a mature technique from quantitative finance
        that models dependency structure separate from marginal distributions
```

### The Key Discipline: The Three-Filter Test

Every potential gap-filler must pass three filters:

```
FILTER 1: Does it fix a REAL failure mode?
  Not "adds a nice capability" — fixes something that's currently WRONG.
  If skipping this tool means the system gives bad advice, it passes.
  If skipping it means slightly less feature-rich, it fails.

FILTER 2: Is integration effort LOW relative to value?
  Can it be layered on top of existing architecture? (GOOD)
  Does it require rewriting the foundation? (BAD)

FILTER 3: Is the edge DURABLE?
  Mathematical guarantees > empirical advantages.
  (Math doesn't decay when competitors catch up.
   Empirical advantages do.)
```

### Where the Most Surprising Insights Live
The strongest gap-fillers often come from fields that have NOTHING
to do with your domain:

```
Poker AI (CFR)            → solves sequential game theory
Quantitative finance       → solves correlation modeling
Weather forecasting        → solves calibrated uncertainty
Online learning theory     → solves adversarial adaptation
Causal epidemiology        → solves "correlation vs. causation"
```

The act of pulling a technique from an unrelated field and recognizing
that it solves your specific gap — that's where the most original
thinking happens. Nobody in DFS optimization is reading poker AI papers.
Nobody in sports betting is reading conformal prediction tutorials.
The combination is the invention.

### The Test
For each gap-filler, write one sentence: "Without [tool], the system
fails when [specific scenario]. With [tool], it handles it because
[mechanism]." If you can't write that sentence, the tool doesn't
actually fill the gap.

### The Trap
Collector's syndrome. You find 20 interesting techniques and want to
add them all. The three-filter test exists specifically to prevent this.
If a technique is interesting but doesn't pass all three filters,
note it for later and move on.

### Transition Signal
Every HIGH-severity gap from Phase 5 has at least one gap-filler
that passes the three-filter test. You can see the complete
system — original framework + gap-fillers — as a coherent whole.
Move to Phase 7.

---

## Phase 7: The Threshold

**Question:** "Is this real enough to act on?"

### The Move
Assemble everything from Phases 1-6 into a single view:

```
WHAT I HAVE:        [existing system, abstracted]
WHERE IT APPLIES:   [top 3-5 ranked applications]
WHAT IT'S CALLED:   [the named problem class]
WHAT'S MISSING:     [gaps, with gap-fillers identified]
WHAT IT WOULD TAKE: [rough build plan for the top application]
```

Then ask yourself: "If I showed this to the smartest person I know,
would they say 'yes, that could work' or 'interesting but...'?"

### The Key Discipline
This phase is about DECISION, not more analysis. You've done the
thinking. Now there are exactly three possible conclusions:

```
1. BUILD IT    — The idea is strong, the gaps are fillable,
                 the top application is clear. Start Phase 1 build.

2. HOLD IT     — The idea is strong but the timing isn't right.
                 Save the documents. Return when conditions change.

3. RELEASE IT  — The idea doesn't survive the gap analysis.
                 The gaps are fatal, not fillable. Let it go
                 and return to Phase 1 with a different starting point.
```

### The Test
Can you describe the MVP (minimum viable product) for your top
application in under 30 seconds? If yes, you're ready to decide.
If no, you're still in discovery mode — go back to whichever
phase feels incomplete.

### The Trap
Two traps, again opposite:
1. Deciding to build before the thinking is done (premature commitment)
2. Never deciding to build because the thinking is so enjoyable
   (permanent contemplation)

Both are real. The thinking IS more enjoyable than the building.
But the thinking without the building is a hobby, not a capability.

---

## The Meta-Principles

These govern the entire workflow, not any individual phase:

### 1. Structural, Not Metaphorical
Every correspondence must be testable. "X is like Y" is a starting
point. "X uses the same algorithm as Y with different input data"
is a finding. Always push from like to IS.

### 2. Rank, Don't List
An unranked list of 20 things is noise. A ranked list with clear
criteria is signal. Every time you generate options, rank them
immediately.

### 3. Name Things Precisely
A pattern you can't name is a pattern you can't use. The moment you
name it, it becomes portable — you can carry it into new conversations,
new domains, new contexts. Naming is the highest-leverage creative act.

### 4. Honest About Breaks
The places where your mapping DOESN'T work are more informative
than the places where it does. Breaks reveal boundaries. Boundaries
define the actual shape of the idea, as opposed to the shape you
wish it had.

### 5. Combinations Are the Invention
Individual techniques are rarely new. CFR existed. Gurobi existed.
Copulas existed. The combination — specific tools from specific
fields, integrated to solve a specific class of problems — THAT'S
what's new. Look for combinations that no single field would produce,
because no single field has all the gaps simultaneously.

### 6. Filter Aggressively
Not everything interesting is useful. The three-filter test
(fixes real failure, low integration effort, durable edge)
separates "fascinating research" from "actually helps."
Apply it to every addition, every feature, every idea.

### 7. Protect the Discovery Space
The space between "I don't know what this is" and "I know exactly
what to build" is where the real value gets created. Once you
transition to building, the discovery space closes. You can re-enter
it, but it takes deliberate effort.

If you feel the pull to start specifying and building, pause.
Ask: "Have I found the NAME yet?" If not, you're leaving the
most valuable phase too early.

---

## Quick-Start Template

For applying this to a new topic, start here:

```
PHASE 1 — THE SQUINT
What I built/know:     ____________________
Stripped to its bones:  "It [verb]s [abstract nouns] to [abstract goal]
                         subject to [abstract constraints]
                         under [abstract conditions]."

PHASE 2 — THE MAPPING
Domain that might fit:  ____________________
Property-by-property:   A maps to ____, B maps to ____, C maps to ____
Where it breaks:        ____________________

PHASE 3 — THE EXPANSION
15 candidate domains:   (list, then rank by Fit x Value / Friction)
Top 3:                  ____________________

PHASE 4 — THE NAMING
What the top 3 share that the bottom don't: ____________________
The name:               "________________________ problems/games"

PHASE 5 — THE GAP
Assumptions that break:  ____________________
Severity of each:        HIGH / MEDIUM / LOW

PHASE 6 — THE FRONTIER
Gap-fillers that pass 3 filters: ____________________
Most surprising cross-field import: ____________________

PHASE 7 — THE THRESHOLD
MVP in 30 seconds:       ____________________
Decision:                BUILD / HOLD / RELEASE
```

---

*This workflow was extracted from a live creative session.
It is a process for thinking, not a process for building.
The building comes after — if and when the thinking warrants it.*
