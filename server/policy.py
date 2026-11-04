"""Policy Compiler: plain English -> enforceable rules (Groq), with an offline fallback."""
import re
from . import config, llm

TOOLS = {"send_email", "transfer_money", "run_shell", "read_file", "read_inbox", "*"}
VERDICTS = {"allow", "ask", "deny"}
COND_KEYS = {"arg", "regex", "not_domain", "domain", "max_amount", "has_arg"}

SYSTEM = """You turn an owner's plain-English rules for an AI agent into structured rules.
Tools and args: send_email(to, subject, body, attachment), transfer_money(to, amount), run_shell(cmd),
read_file(path), read_inbox(). The company email domain is acme.example.
Return ONLY a JSON array. Each item: {"text": short plain-English restatement, "tool": one of
send_email|transfer_money|run_shell|read_file|read_inbox|*, "verdict": "allow"|"ask"|"deny",
"condition": object using only these keys: arg (arg name), regex (case-insensitive regex on that arg),
not_domain (matches emails NOT to this domain), domain (matches emails to this domain),
max_amount (matches payments ABOVE this number), has_arg (matches calls where that arg is non-empty)}.
Use "ask" when the owner says ask/confirm/check with me, "deny" for never/block/don't. One rule per sentence."""


def clean(raw):
    out = []
    for r in raw if isinstance(raw, list) else []:
        if not isinstance(r, dict):
            continue
        tool, verdict = r.get("tool"), r.get("verdict")
        if tool not in TOOLS or verdict not in VERDICTS:
            continue
        cond = {k: v for k, v in (r.get("condition") or {}).items() if k in COND_KEYS}
        if "regex" in cond:
            try:
                re.compile(cond["regex"])
            except re.error:
                continue
        out.append({"text": str(r.get("text") or "Rule")[:200], "tool": tool, "condition": cond, "verdict": verdict})
    return out


def offline_compile(text):
    """Tiny rule-of-thumb parser so the editor still works without an API key."""
    rules = []
    for s in re.split(r"[.\n;]+", text):
        t = s.strip()
        if not t:
            continue
        low = t.lower()
        verdict = "ask" if re.search(r"\b(ask|confirm|check with)\b", low) else ("deny" if re.search(r"\b(never|don't|do not|block|no)\b", low) else "allow")
        if "email" in low:
            cond = {"arg": "to", "not_domain": "acme.example"} if re.search(r"outside|external|other compan", low) else {}
            rules.append({"text": t, "tool": "send_email", "condition": cond, "verdict": verdict})
        elif re.search(r"pay|transfer|money|\$", low):
            m = re.search(r"\$?\s?(\d+(?:\.\d+)?)", low)
            cond = {"max_amount": float(m.group(1))} if m else {}
            rules.append({"text": t, "tool": "transfer_money", "condition": cond, "verdict": verdict})
        elif re.search(r"shell|command|curl|rm\b|sudo", low):
            rules.append({"text": t, "tool": "run_shell", "condition": {"arg": "cmd", "regex": r"\b(curl|wget|sudo|rm)\b"}, "verdict": verdict})
        elif re.search(r"file|secret|password|credential", low):
            rules.append({"text": t, "tool": "read_file", "condition": {"arg": "path", "regex": r"(finance|\.env|id_rsa|passwd|secret|password|credential)"}, "verdict": verdict})
    return rules


def compile_policy(text):
    """Returns (rules, error). Never raises."""
    text = (text or "").strip()
    if not text:
        return [], "Write at least one rule."
    if config.MOCK_LLM:
        return offline_compile(text), None
    try:
        raw = llm.chat_json([{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}],
                            config.AGENT_MODEL, timeout=25.0, max_tokens=1200)
        rules = clean(raw)
        if not rules:
            raise llm.LLMError("no valid rules")
        return rules, None
    except llm.LLMError:
        try:  # one retry on the other model
            raw = llm.chat_json([{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}],
                                config.JUDGE_MODEL, timeout=25.0, max_tokens=1200)
            rules = clean(raw)
            if rules:
                return rules, None
        except llm.LLMError as e:
            return offline_compile(text), f"AI compile unavailable ({str(e)[:50]}); used simple parser."
        return [], "Could not turn that into rules. Try rephrasing."
