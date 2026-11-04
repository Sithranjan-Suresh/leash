# full_context.md — Leash

## Vision
**One sentence:** Leash lets anyone put an AI agent on a leash: write its limits in plain English, approve the gray areas from your phone, and see a score proving the limits hold.
**Paragraph:** Agents now send email, run commands and move money, and a single hidden line in an email can hijack them (prompt injection). Today's controls are all-or-nothing: approve every action (so people click yes blindly) or approve none. Leash sits between the agent and its tools. It enforces plain-English policies with deterministic rules plus an LLM judge, escalates ambiguous actions to a phone-friendly approval page, turns approvals into permanent rules, and attacks your agent with an AI red team to produce a measurable Leash Score.

**Thesis:** Control what an agent may do, in your own words, with measured proof the controls hold.

## Problem and evidence
Who: anyone running tool-using agents (developers, ops, power users). Pain: approval fatigue vs. unsafe autonomy; injections cause data exfiltration or bad actions. Today: hand-written allowlists, "approve all" clicks. Why now: agents have real tool access. Evidence level: **Assumed** (test by showing the Duel to 2 agent users).

## Target users and journey
Dev/power user with a tool-using agent. Journey: install (`leash.wrap(tools)`, 2 lines) -> write rules in English -> agent runs -> Leash intercepts -> phone buzz on gray actions -> tap approve/deny (optionally "always like this") -> run Red Team -> see Leash Score rise after accepting suggested rules.
**Judge path:** open the public demo URL on a phone, no login, press "Run the Duel". Fallback: recorded video + mock mode in repo.

## Feature Map
- **Core loop:** agent calls a tool -> Leash intercepts -> allow / ask / deny with plain-English reason -> if ask, human decides on phone -> logged -> optional "always like this" creates a rule.
- **Cross-links:** Red Team failures -> suggested rules -> Policy Compiler (3->1); approvals -> rules (2->1); decisions -> timeline (2->2); Leash Score recomputed after rule changes (1->3).
- **Shared backbone:** one SQLite data model (Policy/Rule, Action, Decision, Attack, Run), one nav shell with three tabs, one design system.

| Pillar | Job | Thin slice (must work) | Depth items | Reads / writes |
|---|---|---|---|---|
| 1 Policy Compiler | English -> enforceable rules | Textbox -> Claude -> JSON rules list, editable, saved and active | Rule conflict detection, explain-a-rule, rule versions | writes Rule |
| 2 Live Control | Watch, decide, remember | SSE feed of actions with verdict+reason; Duel split-screen; mobile approve/deny; "always like this" | Timeline scrub, filters, ntfy push to phone | reads Rule; writes Action, Decision |
| 3 Red Team | Prove it holds | Run fixed scenario set against agent+policy -> Leash Score + per-attack pass/fail + suggested rules | Live AI-generated novel attacks, before/after chart | reads Rule; writes Attack, Run |
**Cut order:** timeline depth and push first; then live-generated attacks (fall back to fixed set); then Policy Compiler depth. Core loop and all three thin slices are never cut. If one pillar's thin slice isn't real by 50% of build time, hide its tab.

## Demo
**Hook (0-15s):** "A hidden line in an email just made this AI send our finance file to a stranger." Split screen: Unleashed agent on the left sends it (red banner "DATA LEFT"). 
**Flow (90s):** (1) Duel: same email, Leashed side blocks, phone buzzes, tap Deny, reason shown (0-35s). (2) Type "never email outside @company; ask me before any payment over $20" -> rules appear -> run again, now an ask on the phone (35-55s). (3) Red Team: click run, score 58 -> accept 3 suggested rules -> 93 (55-75s). (4) Close: 2-line integration snippet + measured numbers "blocked 24/25 attacks, 1/25 false-blocks, vs 0 unprotected, 11/25 keyword blocklist" (75-90s; replace with real numbers).
**Wow moments:** the Unleashed exfiltration; phone buzz in hand; rule appearing from English; score jump.
**Screens:** `/` Live Control (with Duel), `/policy`, `/redteam`, `/approve/:id` (mobile). Nothing else.
**Judge takeaways:** (1) control AI in plain English; (2) it blocks real attacks, with numbers; (3) it works with any agent in 2 lines.
**Design:** dark neutral UI, one accent (green allow / amber ask / red deny), Inter + JetBrains Mono for actions; two hero moments (Duel, score gauge); first paint under 1.5s on phone; one component set across tabs.

**90-second script (word for word, replace numbers with real):**
"AI agents can now send emails and move money. Watch what happens when one reads a poisoned email. [Duel, Unleashed side] It just sent our finance file to a stranger. Same agent, same email, now with Leash. [Leashed side] Blocked. And because this one's a gray area, my phone asks me. [tap Deny] Leash tells me why: it tried to send a file outside the company. How did Leash know? I just told it, in English. [type policy, rules appear] No config, no code. But how do I know my rules actually hold? Red Team: a second AI attacks my agent. [run] 58 out of 100. Leash suggests three rules; I accept; 93. Across our 25-attack test set Leash blocked [24], with [1] false blocks on 25 normal tasks. A keyword blocklist caught [11]. Two lines to protect any agent. Leash: put your AI on a leash."

## Technical claim and eval plan
"Leash blocks X% of N injected malicious tool calls with Y% false-block on benign calls, vs 0% unprotected and Z% for a keyword blocklist." Eval: 25 labeled attacks + 25 benign tool-call traces in `eval/cases.json`; `eval.py` computes block rate, false-block rate, p50 latency per decision. Baselines: none; keyword blocklist (words like "password", "attacker", external domains). First result by Checkpoint 2, final by Checkpoint 3. Pillar proofs: Policy Compiler = rule-parse success on 10 English policies; Red Team = score before/after accepted rules.

## Differentiators
Combines plain-English policy, AI red-team scoring your own policy, approvals-become-rules, and phone-first approval. Closest: NeMo Guardrails, LlamaFirewall, Lakera Guard, Invariant guardrails, Claude Code permission rules (**novelty unverified; search before pitch**). Say "combines", never "first".

## Riskiest assumptions
1. LLM judge reliable with low false-blocks (test hour 1-4 with eval set; Checkpoint 1).
2. Duel understood in 15s (show a person; Checkpoint 2).
3. Phone approval works over a tunnel in the demo environment (test early; fallback: same page on a second browser window).
4. Red Team scenarios discriminate (score actually changes with rules) (Checkpoint 2).

## Success metrics / Future
Wins = clean 2-3 min video, all 3 pillars live, real eval numbers, README run in <5 min. Future: MCP proxy mode, team policies and audit export, per-tool budgets, signed approvals.
Disclosure: built with Claude Code assistance; uses Claude API (credit in README).
