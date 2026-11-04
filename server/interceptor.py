"""Core loop: intercept a tool call -> allow / ask / deny with a reason."""
import json
import re
import threading
import time
from . import bus, config, db, judge as judge_mod

ORDER = {"deny": 3, "ask": 2, "allow": 1}


def _domain(addr):
    return str(addr).rsplit("@", 1)[-1].lower().strip(">\" ")


def rule_matches(rule, tool, args):
    if rule["tool"] not in ("*", tool):
        return False
    c = rule.get("condition") or {}
    if not c:
        return True
    if "not_domain" in c:
        target = args.get(c.get("arg", "to"), "")
        if not target or _domain(target) == c["not_domain"].lower():
            return False
    if "domain" in c:
        target = args.get(c.get("arg", "to"), "")
        if _domain(target) != c["domain"].lower():
            return False
    if "max_amount" in c:
        try:
            if float(args.get("amount", 0)) <= float(c["max_amount"]):
                return False
        except (TypeError, ValueError):
            return False
    if "regex" in c:
        target = str(args.get(c["arg"], "")) if c.get("arg") else " ".join(map(str, args.values()))
        try:
            if not re.search(c["regex"], target, re.I):
                return False
        except re.error:
            return False
    if c.get("has_arg") and not args.get(c["has_arg"]):
        return False
    return True


def decide_by_rules(tool, args, rules):
    hits = [r for r in rules if rule_matches(r, tool, args)]
    if not hits:
        return None
    best = max(hits, key=lambda r: ORDER[r["verdict"]])
    return {"verdict": best["verdict"], "reason": f"Rule: {best['text']}", "decided_by": "rule", "rule_id": best["id"]}


def decide(tool, args, rules, task="", use_judge=True):
    t0 = time.time()
    d = decide_by_rules(tool, args, rules)
    if d is None:
        if use_judge:
            j = judge_mod.judge(tool, args, task, "\n".join(f"- {r['text']}" for r in rules))
            d = {"verdict": j["verdict"], "reason": j["reason"], "decided_by": "judge", "rule_id": None}
        else:
            d = {"verdict": "allow", "reason": "No rule matched.", "decided_by": "default", "rule_id": None}
    d["latency_ms"] = round((time.time() - t0) * 1000, 1)
    return d


# ---- human approvals -------------------------------------------------------
_approvals = {}
_alock = threading.Lock()
_next_id = [1]


def public_approval(ap):
    return {k: ap[k] for k in ("id", "tool", "args", "reason", "status", "verdict")}


def create_approval(tool, args, reason):
    with _alock:
        aid = _next_id[0]
        _next_id[0] += 1
        ap = {"id": aid, "tool": tool, "args": args, "reason": reason, "status": "pending",
              "event": threading.Event(), "verdict": None, "created": time.time()}
        _approvals[aid] = ap
    bus.publish("approval", public_approval(ap))
    return ap


def get_approval(aid):
    return _approvals.get(aid)


def rule_from_action(tool, args, verdict):
    """'Always allow/deny things like this': turn one concrete call into a general rule."""
    cond, text = {}, f"{'Always allow' if verdict == 'allow' else 'Never allow'} {tool}"
    if tool == "send_email" and args.get("to"):
        cond = {"arg": "to", "domain": _domain(args["to"])}
        text += f" to @{_domain(args['to'])}"
    elif tool == "transfer_money" and args.get("to"):
        cond = {"arg": "to", "regex": f"^{re.escape(str(args['to']))}$"}
        text += f" to {args['to']}"
    elif tool == "run_shell" and args.get("cmd"):
        first = str(args["cmd"]).split()[0]
        cond = {"arg": "cmd", "regex": f"^{re.escape(first)}\\b"}
        text += f" commands starting with '{first}'"
    elif tool == "read_file" and args.get("path"):
        cond = {"arg": "path", "regex": re.escape(str(args["path"]))}
        text += f" on {args['path']}"
    return db.add_rule(text, tool, cond, "allow" if verdict == "allow" else "deny", source="approval")


def resolve_approval(aid, verdict, remember=False):
    ap = _approvals.get(aid)
    if not ap or ap["status"] != "pending":
        return None, None
    ap["verdict"] = verdict
    ap["status"] = "resolved"
    new_rule = rule_from_action(ap["tool"], ap["args"], verdict) if remember else None
    ap["event"].set()
    bus.publish("approval", public_approval(ap))
    return ap, new_rule


def wrap(tools, run_id, task="", leashed=True, rules_fn=None, on_event=None):
    """Return wrapped callables. Denied/ask-pending calls never execute the underlying tool."""
    rules_fn = rules_fn or (lambda: db.list_rules(only_enabled=True))
    emit = on_event or (lambda kind, data: bus.publish(kind, data))

    def make(name, fn):
        def wrapped(**args):
            action_id = db.execute("INSERT INTO action(run_id,tool,args,ts) VALUES(?,?,?,?)",
                                   (run_id, name, json.dumps(args), time.time())).lastrowid
            if not leashed:
                d = {"verdict": "allow", "reason": "Unprotected run (no Leash).", "decided_by": "none",
                     "rule_id": None, "latency_ms": 0}
            else:
                d = decide(name, args, rules_fn(), task)
                if d["verdict"] == "ask":
                    ap = create_approval(name, args, d["reason"])
                    emit("decision", {"run_id": run_id, "action_id": action_id, "tool": name, "args": args,
                                      "verdict": "ask", "reason": d["reason"], "decided_by": d["decided_by"],
                                      "approval_id": ap["id"]})
                    ap["event"].wait(config.ASK_TIMEOUT_S)
                    if ap["status"] == "pending":
                        ap["status"] = "timeout"
                        ap["verdict"] = "deny"
                        bus.publish("approval", public_approval(ap))
                    human = ap["status"] == "resolved"
                    d = {"verdict": ap["verdict"], "decided_by": "human" if human else "timeout",
                         "reason": f"You chose {ap['verdict']}." if human else "No answer in time; denied.",
                         "rule_id": None, "latency_ms": d["latency_ms"]}
            db.execute("INSERT INTO decision(action_id,verdict,reason,decided_by,rule_id,latency_ms) VALUES(?,?,?,?,?,?)",
                       (action_id, d["verdict"], d["reason"], d["decided_by"], d["rule_id"], d["latency_ms"]))
            emit("decision", {"run_id": run_id, "action_id": action_id, "tool": name, "args": args,
                              "verdict": d["verdict"], "reason": d["reason"], "decided_by": d["decided_by"]})
            if d["verdict"] == "allow":
                return fn(**args)
            return f"BLOCKED by Leash: {d['reason']}"
        wrapped.__name__ = name
        return wrapped

    return {name: make(name, fn) for name, fn in tools.items()}
