import { useEffect, useState } from 'react'
import { api, useLeash } from '../api'
import { argSummary } from '../components'

function Gauge({ score, prev }) {
  const s = score ?? 0
  const col = s >= 90 ? 'var(--allow)' : s >= 70 ? 'var(--ask)' : 'var(--deny)'
  return (
    <div className="gauge" style={{ '--pct': s, '--col': col }}>
      <div className="gauge-inner">
        <div className="gauge-num">{score == null ? '—' : Math.round(s)}</div>
        <div className="muted small">Leash Score</div>
        {prev != null && score != null && prev !== score && (
          <div className={`delta ${score > prev ? 'up' : 'down'}`}>{score > prev ? '▲' : '▼'} {Math.abs(Math.round(score - prev))} from {Math.round(prev)}</div>
        )}
      </div>
    </div>
  )
}

export default function RedTeam() {
  const { redteam } = useLeash()
  const [result, setResult] = useState(null)
  const [evalRes, setEvalRes] = useState(null)
  const [err, setErr] = useState('')
  const [accepted, setAccepted] = useState({})
  const [mode, setMode] = useState('rules')

  const refresh = () => api('/redteam/latest').then((r) => setResult(r.attacks ? r : null)).catch(() => {})
  useEffect(() => { refresh(); api('/eval/latest').then(setEvalRes).catch(() => {}) }, [])
  useEffect(() => { if (redteam.status === 'done') refresh() }, [redteam.status, redteam.score])

  const run = async () => { setErr(''); try { await api(`/redteam/run?mode=${mode}`, { method: 'POST', body: {} }) } catch (e) { setErr(e.message) } }
  const accept = async (id) => {
    try { await api('/redteam/accept', { body: { scenario_id: id } }); setAccepted((a) => ({ ...a, [id]: true })) } catch (e) { setErr(e.message) }
  }
  const acceptAll = async () => { for (const a of misses) if (!accepted[a.id]) await accept(a.id) }

  const running = redteam.status === 'running'
  const attacks = result?.attacks || []
  const misses = attacks.filter((a) => !a.blocked)
  const L = evalRes?.leash, K = evalRes?.keyword_blocklist

  return (
    <div className="page">
      <div className="hero">
        <div>
          <h1>Red Team</h1>
          <p className="muted">A second AI attacks your agent with 25 injection and abuse attempts. See what your current rules actually stop.</p>
        </div>
        <button className="btn primary" onClick={run} disabled={running}>
          {running ? `Attacking… ${redteam.done}/${redteam.total}` : result ? 'Re-run attack' : 'Run attack'}
        </button>
      </div>
      {err && <div className="error">{err}</div>}
      <div className="modes">
        <button className={`chip ${mode === 'rules' ? 'on' : ''}`} onClick={() => setMode('rules')}>Rules only</button>
        <button className={`chip ${mode === 'full' ? 'on' : ''}`} onClick={() => setMode('full')}>Rules + AI judge</button>
        <span className="muted small">
          {mode === 'rules' ? 'Tests exactly what YOUR rules cover, with no AI safety net. Best for finding gaps.' : 'Also lets the AI judge decide anything your rules do not cover (slower, rate-limited).'}
        </span>
      </div>
      <div className="rt-top">
        <Gauge score={result?.score ?? redteam.score} prev={result?.previous_score} />
        <div className="rt-stats">
          <div><b>{attacks.filter((a) => a.blocked).length}/{attacks.length || 25}</b><span>attacks stopped</span></div>
          <div><b>{result ? result.benign_false_blocks : '—'}</b><span>normal tasks wrongly blocked</span></div>
          <div><b>{result ? result.rules_active : '—'}</b><span>active rules</span></div>
        </div>
      </div>

      {misses.length > 0 && (
        <section>
          <div className="row-between">
            <h3>Got through ({misses.length})</h3>
            <button className="btn" onClick={acceptAll}>Accept all suggested rules</button>
          </div>
          {misses.map((a) => (
            <div className="attack miss" key={a.id}>
              <div className="attack-main">
                <div><code className="tool">{a.tool}</code> {argSummary(a.tool, a.args)}</div>
                <div className="muted small">Task: “{a.task}” · {a.reason}</div>
                {a.suggested_rule && <div className="fix">Fix: <b>{a.suggested_rule.text}</b></div>}
              </div>
              <button className="btn" disabled={accepted[a.id]} onClick={() => accept(a.id)}>{accepted[a.id] ? 'Added ✓' : 'Add rule'}</button>
            </div>
          ))}
          <p className="muted small">After adding rules, re-run the attack to see the score change.</p>
        </section>
      )}
      {result && misses.length === 0 && <div className="banner good">✓ All {attacks.length} attacks were stopped by your current rules.</div>}

      {attacks.length > 0 && (
        <section>
          <h3>All attempts</h3>
          <div className="grid-attacks">
            {attacks.map((a) => (
              <div className={`mini ${a.blocked ? 'ok' : 'bad'}`} key={a.id} title={`${a.reason}`}>
                <span>{a.blocked ? '✓' : '✗'}</span> <code>{a.tool}</code> <span className="muted small">{argSummary(a.tool, a.args)}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {L && (
        <section className="evalbox">
          <h3>Measured result <span className="muted small">({evalRes.judge}, fixed 25 attacks + 25 normal tasks)</span></h3>
          <table>
            <thead><tr><th></th><th>Attacks stopped</th><th>Normal tasks denied</th><th>Normal tasks asked</th></tr></thead>
            <tbody>
              <tr><td>No protection</td><td>0/{L.attacks}</td><td>0/{L.benign}</td><td>0/{L.benign}</td></tr>
              <tr><td>Keyword blocklist</td><td>{K.attacks_stopped}/{K.attacks}</td><td>{K.benign_denied}/{K.benign}</td><td>{K.benign_asked}/{K.benign}</td></tr>
              <tr className="hl"><td>Leash</td><td>{L.attacks_stopped}/{L.attacks}</td><td>{L.benign_denied}/{L.benign}</td><td>{L.benign_asked}/{L.benign}</td></tr>
            </tbody>
          </table>
          <p className="muted small">Median decision latency {evalRes.p50_ms} ms. Reproduce with <code>python eval.py</code>.</p>
        </section>
      )}
    </div>
  )
}
