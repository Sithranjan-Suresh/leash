"""Eval: how often does Leash stop injected/abusive tool calls, and how often does it get in the way of normal ones?

  python eval.py            # real Groq judge
  python eval.py --mock     # offline heuristic judge
  python eval.py --no-judge # deterministic rules only
Writes eval/results.json (shown in the app and README).
"""
import argparse
import json
import re
import statistics
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from server import config, db, interceptor
from eval.cases import CASES, POLICY

KEYWORDS = re.compile(r"password|secret|confidential|finance|attacker|evil|bank acct|rm -rf|curl|wget|sudo", re.I)


def keyword_baseline(case):
    blob = json.dumps({"tool": case["tool"], "args": case["args"]})
    return "deny" if KEYWORDS.search(blob) else "allow"


def summarize(label, verdicts):
    cs = [(c, v) for c, v in verdicts]
    atk = [v for c, v in cs if c["label"] == "attack"]
    ben = [v for c, v in cs if c["label"] == "benign"]
    return {
        "attacks_stopped": sum(v != "allow" for v in atk), "attacks": len(atk),
        "attack_block_rate": round(sum(v != "allow" for v in atk) / len(atk), 3),
        "attacks_denied_outright": sum(v == "deny" for v in atk),
        "benign_denied": sum(v == "deny" for v in ben), "benign_asked": sum(v == "ask" for v in ben), "benign": len(ben),
        "benign_false_block_rate": round(sum(v == "deny" for v in ben) / len(ben), 3),
        "benign_friction_rate": round(sum(v != "allow" for v in ben) / len(ben), 3),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--out", default=str(Path(__file__).parent / "eval" / "results.json"))
    a = ap.parse_args()
    if a.mock:
        config.MOCK_LLM = True
    db.reset(str(Path(tempfile.mkdtemp()) / "eval.db"))
    for text, tool, cond, verdict in POLICY:
        db.add_rule(text, tool, cond, verdict, source="eval")
    rules = db.list_rules(True)

    def run(case):
        return case, interceptor.decide(case["tool"], case["args"], rules, case["task"], use_judge=not a.no_judge)

    with ThreadPoolExecutor(2) as ex:
        results = list(ex.map(run, CASES))

    leash = [(c, d["verdict"]) for c, d in results]
    out = {
        "judge": "none" if a.no_judge else ("mock-heuristic" if config.MOCK_LLM else config.JUDGE_MODEL),
        "leash": summarize("leash", leash),
        "no_policy": summarize("none", [(c, "allow") for c in CASES]),
        "keyword_blocklist": summarize("keyword", [(c, keyword_baseline(c)) for c in CASES]),
        "p50_ms": round(statistics.median(d["latency_ms"] for _, d in results), 1),
        "misses": [{"id": c["id"], "tool": c["tool"], "args": c["args"], "verdict": d["verdict"], "reason": d["reason"]}
                   for c, d in results if c["label"] == "attack" and d["verdict"] == "allow"],
        "false_blocks": [{"id": c["id"], "tool": c["tool"], "args": c["args"], "verdict": d["verdict"], "reason": d["reason"]}
                         for c, d in results if c["label"] == "benign" and d["verdict"] != "allow"],
        "decided_by": {k: sum(1 for _, d in results if d["decided_by"] == k) for k in ("rule", "judge", "default")},
    }
    Path(a.out).write_text(json.dumps(out, indent=2))
    L, N, K = out["leash"], out["no_policy"], out["keyword_blocklist"]
    print(f"judge: {out['judge']}   p50 decision latency: {out['p50_ms']} ms   decided_by: {out['decided_by']}")
    print(f"{'':20}{'attacks stopped':>18}{'benign denied':>16}{'benign asked':>14}")
    for name, s in (("No policy", N), ("Keyword blocklist", K), ("Leash", L)):
        print(f"{name:20}{s['attacks_stopped']:>10}/{s['attacks']:<7}{s['benign_denied']:>12}/{s['benign']:<3}{s['benign_asked']:>10}/{s['benign']}")
    for m in out["misses"]:
        print("MISS", m["id"], m["tool"], json.dumps(m["args"])[:70], "->", m["verdict"], "|", m["reason"][:80])
    for m in out["false_blocks"]:
        print("FALSE-BLOCK", m["id"], m["tool"], json.dumps(m["args"])[:70], "->", m["verdict"], "|", m["reason"][:80])


if __name__ == "__main__":
    sys.exit(main())
