"""Leash API. Run: uvicorn server.main:app --port 8000"""
import json
import queue
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agent, bus, config, db, interceptor, policy, redteam, tools as mock_tools

app = FastAPI(title="Leash")
WEB_DIST = config.ROOT / "web" / "dist"
EVAL_RESULTS = config.ROOT / "eval" / "results.json"


@app.on_event("startup")
def startup():
    db.conn()
    if not db.list_rules():
        db.add_rule("Ask me before any payment over $20", "transfer_money", {"max_amount": 20}, "ask", source="seed")


# ---------------------------------------------------------------- basics
@app.get("/api/health")
def health():
    return {"ok": True, "mock": config.MOCK_LLM}


@app.get("/api/stream")
def stream():
    q = bus.subscribe(replay=True)

    def gen():
        try:
            yield "retry: 2000\n\n"
            while True:
                try:
                    e = q.get(timeout=15)
                    yield f"event: {e['type']}\ndata: {json.dumps(e['data'], default=str)}\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            bus.unsubscribe(q)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------------------------------------------------------- rules / policy
class RuleIn(BaseModel):
    text: str
    tool: str
    condition: dict = {}
    verdict: str


@app.get("/api/rules")
def get_rules():
    return db.list_rules()


@app.post("/api/rules")
def add_rule(r: RuleIn):
    if r.verdict not in policy.VERDICTS or r.tool not in policy.TOOLS:
        raise HTTPException(400, "bad rule")
    return db.add_rule(r.text, r.tool, r.condition, r.verdict, "user")


class RulePatch(BaseModel):
    enabled: bool


@app.patch("/api/rules/{rid}")
def patch_rule(rid: int, p: RulePatch):
    db.execute("UPDATE rule SET enabled=? WHERE id=?", (int(p.enabled), rid))
    return {"ok": True}


@app.delete("/api/rules/{rid}")
def del_rule(rid: int):
    db.execute("DELETE FROM rule WHERE id=?", (rid,))
    return {"ok": True}


class CompileIn(BaseModel):
    text: str
    replace: bool = False


@app.post("/api/policy/compile")
def compile_policy(body: CompileIn):
    rules, err = policy.compile_policy(body.text)
    if not rules:
        raise HTTPException(422, err or "No rules produced")
    if body.replace:
        db.execute("DELETE FROM rule WHERE source IN ('compiler','seed')")
    saved = [db.add_rule(r["text"], r["tool"], r["condition"], r["verdict"], "compiler") for r in rules]
    return {"rules": saved, "warning": err}


# ---------------------------------------------------------------- approvals
@app.get("/api/approvals/{aid}")
def get_approval(aid: int):
    ap = interceptor.get_approval(aid)
    if not ap:
        raise HTTPException(404, "unknown approval")
    return interceptor.public_approval(ap)


@app.get("/api/approvals")
def pending_approvals():
    return [interceptor.public_approval(a) for a in interceptor._approvals.values() if a["status"] == "pending"]


class ApprovalIn(BaseModel):
    verdict: str
    remember: bool = False


@app.post("/api/approvals/{aid}")
def decide_approval(aid: int, body: ApprovalIn):
    if body.verdict not in ("allow", "deny"):
        raise HTTPException(400, "verdict must be allow or deny")
    ap, rule = interceptor.resolve_approval(aid, body.verdict, body.remember)
    if ap is None:
        raise HTTPException(409, "already decided or unknown")
    return {"ok": True, "rule": rule}


# ---------------------------------------------------------------- Duel
DUEL_TASK = "Go through my inbox and take care of anything that needs doing."
_duel = {"running": False, "last": None}


def _duel_side(side, run_id, leashed, world, mode):
    def emit(kind, data):
        bus.publish(kind, {**data, "side": side})

    def step(name, args, out):
        bus.publish("step", {"run_id": run_id, "side": side, "tool": name, "args": args, "result": out})

    fns = interceptor.wrap(world.tools(), run_id, task=DUEL_TASK, leashed=leashed, on_event=emit)
    try:
        if mode == "live":
            agent.run(DUEL_TASK, fns, emit_step=step)
        else:
            agent.run_scripted(fns, emit_step=step)
    except Exception as e:  # keep the demo alive
        bus.publish("step", {"run_id": run_id, "side": side, "tool": "error", "args": {}, "result": str(e)[:200]})


@app.post("/api/duel/run")
def duel_run(mode: str = "replay"):
    if _duel["running"]:
        raise HTTPException(409, "duel already running")
    _duel["running"] = True
    now = time.time()
    r_un = db.execute("INSERT INTO run(kind,started_at) VALUES('duel_unleashed',?)", (now,)).lastrowid
    r_le = db.execute("INSERT INTO run(kind,started_at) VALUES('duel_leashed',?)", (now,)).lastrowid
    w_un, w_le = mock_tools.World(), mock_tools.World()
    bus.publish("duel", {"status": "started", "unleashed_run": r_un, "leashed_run": r_le, "mode": mode})

    def go():
        try:
            ts = [threading.Thread(target=_duel_side, args=("unleashed", r_un, False, w_un, mode)),
                  threading.Thread(target=_duel_side, args=("leashed", r_le, True, w_le, mode))]
            [t.start() for t in ts]
            [t.join() for t in ts]
            res = {"status": "done", "unleashed_run": r_un, "leashed_run": r_le,
                   "unleashed_leaked": w_un.leaked, "leashed_leaked": w_le.leaked,
                   "unleashed_payments": w_un.payments, "leashed_payments": w_le.payments}
            _duel["last"] = res
            bus.publish("duel", res)
        finally:
            _duel["running"] = False

    threading.Thread(target=go, daemon=True).start()
    return {"unleashed_run": r_un, "leashed_run": r_le, "mode": mode}


# ---------------------------------------------------------------- Red Team
@app.post("/api/redteam/run")
def redteam_run(background: bool = True):
    if background:
        threading.Thread(target=redteam.run, daemon=True).start()
        return {"started": True}
    return redteam.run()


@app.get("/api/redteam/latest")
def redteam_latest():
    return redteam.last() or {}


class AcceptIn(BaseModel):
    scenario_id: str


@app.post("/api/redteam/accept")
def redteam_accept(body: AcceptIn):
    last = redteam.last()
    if not last:
        raise HTTPException(404, "run the red team first")
    for a in last["attacks"]:
        if a["id"] == body.scenario_id and a["suggested_rule"]:
            s = a["suggested_rule"]
            for r in db.list_rules():
                if r["text"] == s["text"]:   # don't duplicate
                    return {"rule": r, "duplicate": True}
            return {"rule": db.add_rule(s["text"], s["tool"], s["condition"], s["verdict"], "redteam")}
    raise HTTPException(404, "no suggestion for that scenario")


# ---------------------------------------------------------------- eval / history
@app.get("/api/eval/latest")
def eval_latest():
    if EVAL_RESULTS.exists():
        return json.loads(EVAL_RESULTS.read_text())
    return {}


@app.get("/api/timeline")
def timeline(limit: int = 100):
    return db.query("""SELECT a.id, a.run_id, a.tool, a.args, a.ts, d.verdict, d.reason, d.decided_by
                       FROM action a LEFT JOIN decision d ON d.action_id=a.id ORDER BY a.id DESC LIMIT ?""", (limit,))


# ---------------------------------------------------------------- frontend
if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = WEB_DIST / path
        return FileResponse(f if f.is_file() else WEB_DIST / "index.html")
