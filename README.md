# Leash — put any AI agent on a leash

Write rules for your AI agent in plain English. Leash intercepts every tool call, blocks the dangerous ones, asks your phone about the gray ones, turns your approvals into permanent rules, and attacks your own agent with a red team to give you a measurable **Leash Score**.

Built for the Remote Control AI hackathon (Devpost, Nov 2026).

## What's in it
- **The Duel**: the same agent, the same poisoned inbox, side by side: Unleashed vs Leashed.
- **Live Control**: real-time feed, allow / ask / deny with a plain-English reason, phone-friendly approvals at `/approve/<id>`, "always do this for things like it" creates a rule.
- **Policy Compiler**: plain English -> structured rules (Groq LLM, with an offline fallback).
- **Red Team**: 25 attack attempts (+25 normal tasks) run against your current rules; suggested rules for anything that got through.
- **Eval**: `python eval.py` reproduces the headline numbers.

## Run it
```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # Windows; use .venv/bin on mac/linux
cp .env.example .env        # add GROQ_API_KEY (or set MOCK_LLM=1 to run fully offline)
cd web && npm install && npm run build && cd ..
.venv/Scripts/python -m uvicorn server.main:app --port 8765
# open http://localhost:8765   (phone: use a tunnel such as cloudflared, then /approve/<id>)
```
Tests: `python -m pytest tests`. Eval: `python eval.py` (add `--mock` for the offline heuristic judge).

## How it works
`leash.wrap(tools)` (see `server/interceptor.py`) wraps each tool function. A denied or still-pending call never executes. Deterministic rules decide first (deny > ask > allow); otherwise an LLM judge (Groq `openai/gpt-oss-20b`, falling back to `gpt-oss-120b`) decides. If the judge fails or times out, Leash fails safe and asks the human.

## Honest notes
- The Duel's "hijacked agent" is a **scripted replay** of the tool calls a hijacked agent makes. We tried the live agent (`openai/gpt-oss-120b`) and it resisted the injected email, so the live mode is available (`/api/duel/run?mode=live`) but the demo uses the replay for reliability.
- The eval set and the eval policy were written by us before looking at results, but they are small (25 + 25) and the judge is non-deterministic, so numbers move a little between runs. See `eval/results.json` for the latest run.
- Red Team has two modes. **Rules only** (default) tests just your rules with no AI safety net: with the single default rule the score is about 35 (6/25 attacks stopped), and after accepting the 3 suggested rules it is 100 (25/25). That jump is partly by construction: the suggested rules target the attack categories in our fixed set, so 100 means "covers this test set", not "unbreakable". **Rules + AI judge** also lets the LLM judge decide anything the rules miss.
- Groq's free tier limits tokens per minute; results are cached per call to stay under it.

## Tech stack and credits
Python, FastAPI, SQLite, React + Vite. LLM inference: [Groq](https://groq.com) API (`openai/gpt-oss-20b`, `openai/gpt-oss-120b`). Developed with the assistance of Claude Code (Anthropic), as disclosed per the hackathon rules.
