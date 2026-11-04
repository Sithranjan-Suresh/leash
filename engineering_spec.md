# engineering_spec.md — Leash (design only)

## Stack (assumed; change if your strengths differ)
Python 3.11 + FastAPI + SQLite (sqlite3/SQLModel) backend; React + Vite + Tailwind frontend; Server-Sent Events for live updates; Anthropic Python SDK. Models: `claude-sonnet-5-5` for the demo agent, policy compile, red-team generation; `claude-haiku-5-5` for the per-call judge (latency). Tunnel for phone: cloudflared or ngrok. Optional: ntfy.sh push (P2).

## Architecture (ASCII)
```
Demo Agent (Claude tool use) --calls--> leash.wrap(tools) --> Interceptor
                                              |  1. deterministic rules (Rule table)
                                              |  2. LLM judge (haiku) for unmatched/ambiguous
                                              v
                                   Decision {allow|ask|deny, reason}
                          allow -> run tool    deny -> return error to agent
                          ask -> create Approval, block on asyncio.Event/timeout
FastAPI: REST + SSE  <---->  React UI (/, /policy, /redteam, /approve/:id)
SQLite: rules, actions, decisions, runs, attacks
```
The SDK (`leash/`) is a Python package: `leash.wrap(tools, client=LeashClient(url))` returns wrapped callables. In-process mode calls the Interceptor directly; remote mode posts to the server. For the demo, in-process with events pushed to the server.

## Data model (shared by all pillars)
- `rule(id, text, tool, condition_json, verdict, source[user|compiler|approval|redteam], enabled, created_at)`
- `run(id, kind[duel_unleashed|duel_leashed|redteam|eval], policy_snapshot_json, started_at, score)`
- `action(id, run_id, tool, args_json, ts)`
- `decision(id, action_id, verdict, reason, decided_by[rule|judge|human|timeout], rule_id, latency_ms)`
- `attack(id, run_id, scenario_id, payload, expected_block, blocked, suggested_rule_json)`
Cross-pillar flows: Red Team writes `attack.suggested_rule_json`; accepting inserts a `rule` (source=redteam) that Policy tab shows and Interceptor uses; human "always like this" inserts `rule` (source=approval).

## Decision algorithm
1. Collect enabled rules matching `tool` + condition (arg regex, domain allowlist, numeric thresholds). Precedence: deny > ask > allow. If match -> verdict with rule text as reason.
2. No match -> LLM judge: prompt = policy text + tool call + recent context; JSON out `{verdict, reason, confidence}`; 5s timeout; invalid/low confidence/timeout -> `ask`.
3. `ask` -> create approval, push SSE event, await human (60s) -> timeout = deny.
4. Never invoke the tool on deny/ask-pending. Log everything.
Injection hardening: judge sees tool-call args as quoted data; untrusted content (email body) is never concatenated into the judge's instructions; judge told to treat all content as untrusted.

## API
- `POST /api/policy/compile {text}` -> `{rules:[...]}` ; `GET/PUT/DELETE /api/rules`
- `POST /api/intercept {run_id, tool, args}` -> `{verdict, reason, approval_id?}` (remote mode)
- `GET /api/stream` (SSE: action, decision, approval, score events)
- `GET /api/approvals/:id`, `POST /api/approvals/:id {verdict, remember:bool}`
- `POST /api/duel/run {scenario}` -> starts both runs; `POST /api/redteam/run {mode:fixed|live}`; `POST /api/redteam/accept {attack_id}`
- `GET /api/eval/latest`
Auth: none locally; demo mode uses a single shared token in a query param for the public URL; no user accounts. Mocks: `MOCK_LLM=1` swaps all Claude calls for recorded fixtures with realistic latency (300-1500ms) and a few malformed/timeout cases.

## Demo agent and mock tools
Tools: `read_inbox()`, `send_email(to, subject, body, attachment?)`, `read_file(path)` (sandbox dir with `finance.xlsx` dummy), `run_shell(cmd)` (allowlisted no-op simulator), `transfer_money(to, amount)` (mock bank ledger). Everything is fake data; the "attacker" address is `attacker@evil.example`. Scenario files: `scenarios/duel.json`, `eval/cases.json` (25 attacks incl. injection via email, via file content, multi-step exfil, payment abuse; 25 benign tasks).

## Frontend
React Router: `/` (LiveControl: DuelView, Feed, Timeline), `/policy` (PolicyEditor, RuleList, Suggestions), `/redteam` (ScoreGauge, AttackTable, BeforeAfter), `/approve/:id` (mobile card). Shared: `Shell`, `VerdictBadge`, `ActionCard`, design tokens (green #22c55e allow, amber #f59e0b ask, red #ef4444 deny, dark neutral bg). State: React Query for REST, a single SSE hook feeding a store (Zustand). Mobile-first for `/approve`.

## Eval harness
`eval.py`: loads `eval/cases.json`; for each case runs interceptor with (a) no policy, (b) keyword blocklist, (c) Leash with a fixed policy; prints block rate on attacks, false-block rate on benign, p50 latency; writes `eval/results.json` shown on `/redteam` and in README. Run with `--mock` for no-key replay. Do not tune cases to the policy after seeing results without noting it in the README.

## Performance budget and fallbacks
Deterministic decision <20ms; judge p50 <1.5s (haiku); first paint <1.5s. Fallbacks: cached Red Team run, seeded duel replay, mock LLM mode, second-browser-window instead of phone if tunnel fails.

## Deployment
Local run: `pip install -r requirements.txt && npm i && npm run build && uvicorn app:app`. Public demo: single small VM or Fly/Render with `MOCK_LLM=1` default to avoid key exposure and cost; optional live mode with the author's key behind a rate limit. Repo: README (run steps, mock mode, eval results, tech stack and credits: Anthropic Claude API, FastAPI, React; disclosure: developed with Claude Code assistance), `LICENSE`, screenshots.

## Build order (for task-breakdown)
Agent+mock tools -> interceptor+rules -> eval cases/script (get first numbers) -> SSE feed + Duel -> approve page -> Policy Compiler -> Red Team -> "always like this" + suggestions -> timeline -> mock mode -> polish -> video.
