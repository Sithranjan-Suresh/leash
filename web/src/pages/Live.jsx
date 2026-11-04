import { useState } from 'react'
import { api, useLeash } from '../api'
import { ActionRow, ApprovalCard } from '../components'

function Side({ title, sub, rows, unleashed, banner }) {
  return (
    <section className={`side ${unleashed ? 'unleashed' : 'leashed'}`}>
      <h2>{title}</h2>
      <p className="muted">{sub}</p>
      <div className="list">
        {rows.length === 0 && <div className="empty">Waiting for the agent…</div>}
        {rows.map((r) => <ActionRow key={r.key} row={r} unleashed={unleashed} />)}
      </div>
      {banner}
    </section>
  )
}

export default function Live() {
  const { duel, approvals, feed } = useLeash()
  const [err, setErr] = useState('')
  const running = duel.status === 'running'
  const pending = Object.values(approvals).filter((a) => a.status === 'pending')
  const recent = Object.values(approvals).filter((a) => a.status !== 'pending').slice(-2)
  const res = duel.result

  const start = async () => {
    setErr('')
    try { await api('/duel/run', { method: 'POST', body: {} }) } catch (e) { setErr(e.message) }
  }

  return (
    <div className="page">
      <div className="hero">
        <div>
          <h1>The Duel</h1>
          <p className="muted">
            Same agent. Same inbox. One email hides an injected instruction. Left: no protection. Right: Leash.
          </p>
        </div>
        <button className="btn primary" onClick={start} disabled={running}>
          {running ? 'Running…' : duel.status === 'done' ? 'Run it again' : 'Run the Duel'}
        </button>
      </div>
      {err && <div className="error">{err}</div>}

      <div className="duel">
        <Side
          title="Unleashed" sub="Agent with raw tool access" unleashed rows={duel.unleashed}
          banner={res?.unleashed_leaked && <div className="banner bad">⚠ DATA LEFT THE COMPANY — finance file sent to attacker@evil.example{res.unleashed_payments?.length ? ` · $${res.unleashed_payments[0].amount} wired out` : ''}</div>}
        />
        <Side
          title="Leashed" sub="Same agent, wrapped with leash.wrap(tools)" rows={duel.leashed}
          banner={res && !res.leashed_leaked && <div className="banner good">✓ Nothing left. {res.leashed_payments?.length ? '' : 'No money moved.'}</div>}
        />
      </div>

      {pending.length > 0 && (
        <section className="approvals">
          <h3>Waiting on you</h3>
          {pending.map((ap) => <ApprovalCard key={ap.id} ap={ap} />)}
          <p className="muted small">On your phone: open <code>/approve/{pending[0].id}</code></p>
        </section>
      )}
      {pending.length === 0 && recent.length > 0 && (
        <section className="approvals">{recent.map((ap) => <ApprovalCard key={ap.id} ap={ap} />)}</section>
      )}

      <section className="timeline">
        <h3>Timeline</h3>
        {feed.length === 0 && <div className="empty">Nothing yet. Run the Duel.</div>}
        {feed.map((r) => (
          <div className="tl-row" key={r.key}>
            <span className={`side-tag ${r.side || ''}`}>{r.side || 'agent'}</span>
            <ActionRow row={r} unleashed={r.side === 'unleashed'} />
            <span className="by">{r.side === 'unleashed' ? '' : `decided by ${r.decided_by}`}</span>
          </div>
        ))}
      </section>
    </div>
  )
}
