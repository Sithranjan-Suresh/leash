# build_plan.md — Leash (solo, ~24h treated build)

**Model change:** Groq (OpenAI-compatible API, https://api.groq.com/openai/v1) replaces Anthropic in the specs. Agent + compile + red team: `openai/gpt-oss-120b`; per-call judge: `openai/gpt-oss-20b`. Key lives in `.env` (gitignored), never committed. Credit Groq in README.

**Roles:** solo owner of all pillars. Checkpoints at H6 / H12 / H18 of a 24h clock (start = when this build began); full feedback H6-7.2; freeze H12; submit buffer 90 min.

**Git rules:** commit and push to `main` after every task (user instruction), small commits, tag `checkpoint-1`, `freeze`.

## Task list (ordered; done test)
1. [x] Repo, .gitignore, env, docs pushed
2. [x] Backend scaffold (FastAPI, SQLite schema, config) — `uvicorn` starts, /api/health ok
3. [x] Interceptor + deterministic rules + unit tests — denied call never executes
4. [x] LLM judge (Groq) with fail-safe ask + mock mode
5. [x] Mock tools + demo agent loop (Groq tool use) — runs inbox task end to end
6. [x] Eval set (25 attacks / 25 benign) + eval.py with baselines — first numbers
7. [x] API + SSE stream + approvals + Duel endpoint
8. [x] Policy Compiler endpoint (+ approval -> rule)
9. [x] Red Team endpoint (fixed set, score, suggested rules)
10. [ ] Frontend shell + design tokens
11. [ ] Live Control page (Duel, feed, timeline) + mobile /approve
12. [ ] Policy page, Red Team page
13. [ ] Mock/replay mode, README, polish, tunnel test
14. [ ] Video + submission

Cut order: timeline depth, live-generated attacks, policy depth. Never core loop.
