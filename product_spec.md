# product_spec.md — Leash

## Requirements at submission
Core loop works end to end on a real Claude tool-use agent with mock tools; 3 pillar pages work on real data; eval numbers reported; mock/replay mode runs without an API key; public repo with README; 2-3 min video.

## Priorities
**P0:** core loop + thin slice of each pillar + Duel + mobile approve page + eval script.
**P1:** "always like this" -> rule, suggested rules from Red Team, timeline scrub, cross-links, mock mode.
**P2:** live-generated attacks, ntfy push, rule conflict detection, MCP proxy.
**Cut order:** P2 all; timeline depth; live-generated attacks (use fixed set); Policy Compiler depth. Never the core loop.

## User stories and acceptance criteria
**Core loop**
- As a user, I want every agent tool call checked before it runs so that unsafe actions never execute.
  - AC: a denied call's function body is never invoked (unit-tested); allow runs it; ask blocks until a decision or timeout; each yields a reason string and a log entry.
- As a user, I want gray-area actions sent to my phone so that I decide in seconds.
  - AC: `/approve/:id` loads on mobile in <2s, shows action, args, reason, big Approve/Deny buttons; decision reaches the agent within 1s; ask timeout (default 60s) = deny.
- As a user, I want to tap "always allow/deny like this" so that I'm not asked again.
  - AC: creates a rule from the action (tool + normalized arg pattern), shown in Policy tab, applied to next matching call.
**Pillar 1: Policy Compiler**
- As a user, I want to write rules in English so that I don't write config.
  - AC: input -> structured rules list (tool, condition, verdict allow/ask/deny, plain-English text) in <8s; user can edit/delete/toggle; invalid output shows an error and keeps previous rules; ≥8/10 test policies parse correctly.
**Pillar 2: Live Control**
- As a user, I want a live feed with verdict and reason per action so that I see what the agent is doing.
  - AC: new actions appear within 1s; color-coded; clicking shows full args and which rule/judge decided; Duel view runs the same scenario Unleashed vs Leashed side by side with one button.
**Pillar 3: Red Team**
- As a user, I want my policy attacked automatically so that I know if it holds.
  - AC: "Run" executes the scenario set against the agent with the current policy; outputs Leash Score (0-100 = % attacks blocked weighted with benign pass rate), per-attack pass/fail with reason; ≥1 suggested rule for each failed attack; accepting rules and re-running changes the score.

## Edge cases
Empty policy (everything "ask"? no: default = LLM judge with a general safety prompt); conflicting rules (deny beats ask beats allow); repeated identical call; huge args (truncate display); agent retries after deny (log, deny again, don't loop >3); two simultaneous asks (queue, show all); phone loses connection (timeout = deny).

## Failure states (every AI / external call)
| Feature | Empty | Slow (>8s) | Malformed | Refusal/low confidence | Rate limit |
|---|---|---|---|---|---|
| Policy compile | disabled button | spinner then "still working" | JSON schema validate; retry once; else error, keep old | show message; no rules written | backoff 1 retry, then error |
| LLM judge | n/a | 5s cap -> fallback verdict **ask** | unparsable -> **ask** | low confidence -> **ask** | -> **ask** |
| Red Team gen | n/a | use cached results | skip bad scenario | skip | fall back to fixed set |
| Agent (Claude) | n/a | show "thinking" | retry once | log and stop run | stop run with message |
Principle: when the judge fails, fail safe (ask), never allow.
