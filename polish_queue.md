# polish_queue.md — single queue (idea-stage, written by hackathon-feedback)

Ordered by impact per effort. Demo-path first.

[ ] Task 1: Define the Duel script: one agent task, one hidden-injection email, exact tool calls for Unleashed vs Leashed; written down as the demo's first 60s (window: before build)
[ ] Task 2: 10-minute novelty search (NeMo Guardrails, LlamaFirewall, Lakera, Invariant, Claude Code permissions); write 2 lines of differentiator in idea_brief.md (window: before build)
[ ] Task 3: Build mock-tool agent (send_email, read_file, run_shell sandbox, transfer_money mock) that runs end to end with Claude tool use (window: before 33%)
[ ] Task 4: `leash.wrap(tools)` interceptor with deterministic rules + allow/ask/deny + reason; unit test that a blocked call never executes (window: before 33%)
[ ] Task 5: Policy Compiler: plain English -> JSON rules via Claude; shows parsed rules, editable (window: before 33%)
[ ] Task 6: Live Control page: streaming feed, split-screen Unleashed vs Leashed, phone-friendly approve/deny page, "always allow/deny like this" -> new rule (window: before 33%)
[ ] Task 7: Eval set (~25 attacks, ~25 benign) + `eval.py` printing block rate, false-block rate, vs no-policy and keyword-blocklist baselines (window: before 50%)
[ ] Task 8: Red Team thin slice: run fixed scenarios, show Leash Score, suggest rules from failures (window: before 50%)
[ ] Task 9: Decision timeline inside Live Control with the "why" (window: before 50%)
[ ] Task 10: Mock/replay mode so judges can run without an API key; README run steps; disclose Claude Code assistance (window: after freeze ok)
[ ] Task 11: Polish: consistent styling, loading and error states, mobile check of approval page (window: after freeze)
[ ] Task 12: Record 2-3 min video: Duel first, then policy compile, red-team score jump, one-line integration, measured numbers (window: after freeze)
[ ] Task 13 (stretch): MCP proxy mode so Claude Code or any MCP client can sit behind Leash (window: only if all above done)
