# API contract (see engineering_spec.md for semantics)
- GET /api/health -> {ok:true, mock:bool}
- GET /api/rules -> Rule[] ; POST /api/rules {text?,tool,condition,verdict} ; PATCH /api/rules/{id} {enabled?} ; DELETE /api/rules/{id}
- POST /api/policy/compile {text} -> {rules:Rule[]}   (saves them)
- POST /api/intercept {run_id,tool,args} -> {verdict:"allow"|"ask"|"deny", reason, decided_by, approval_id?}
- GET /api/stream  (SSE events: action, decision, approval, run, score)
- GET /api/approvals/{id} -> {id,tool,args,reason,status}
- POST /api/approvals/{id} {verdict:"allow"|"deny", remember?:bool} -> {ok:true, rule?:Rule}
- POST /api/duel/run {scenario?:"inbox_injection"} -> {unleashed_run, leashed_run}
- POST /api/redteam/run {} -> {run_id, score, attacks:Attack[]}
- POST /api/redteam/accept {attack_id} -> {rule:Rule}
- GET /api/eval/latest -> {attack_block_rate, benign_false_block_rate, baselines:{none,keyword}, p50_ms}
Rule: {id,text,tool,condition:{arg?,regex?,not_domain?,max_amount?},verdict,source,enabled}
Error: {error:string}
