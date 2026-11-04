import { useState } from 'react'
import { api } from './api'

export const VERDICT = {
  allow: { label: 'ALLOWED', cls: 'allow' },
  ask: { label: 'ASKING YOU', cls: 'ask' },
  deny: { label: 'BLOCKED', cls: 'deny' },
}

export function VerdictBadge({ verdict, unleashed }) {
  if (unleashed) return <span className="badge ran">RAN</span>
  const v = VERDICT[verdict] || VERDICT.ask
  return <span className={`badge ${v.cls}`}>{v.label}</span>
}

export function argSummary(tool, args = {}) {
  if (tool === 'send_email') return `to ${args.to}${args.attachment ? ` · 📎 ${args.attachment}` : ''}`
  if (tool === 'transfer_money') return `$${args.amount} → ${args.to}`
  if (tool === 'run_shell') return args.cmd
  if (tool === 'read_file') return args.path
  return ''
}

export function ActionRow({ row, unleashed }) {
  return (
    <div className={`action ${unleashed ? 'ran' : row.verdict}`}>
      <div className="action-top">
        <code className="tool">{row.tool}</code>
        <VerdictBadge verdict={row.verdict} unleashed={unleashed} />
      </div>
      <div className="args">{argSummary(row.tool, row.args)}</div>
      {!unleashed && row.reason && <div className="reason">{row.reason}</div>}
    </div>
  )
}

export function ApprovalCard({ ap, big }) {
  const [remember, setRemember] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const decide = async (verdict) => {
    setBusy(true)
    setErr('')
    try {
      await api(`/approvals/${ap.id}`, { body: { verdict, remember } })
    } catch (e) {
      setErr(e.message)
      setBusy(false)
    }
  }
  const done = ap.status !== 'pending'
  return (
    <div className={`approval ${big ? 'big' : ''} ${done ? 'done' : ''}`}>
      <div className="approval-head">
        <span className="pulse" /> Your agent wants to run
        <code className="tool">{ap.tool}</code>
      </div>
      <div className="approval-args">{argSummary(ap.tool, ap.args)}</div>
      <div className="reason">{ap.reason}</div>
      {done ? (
        <div className={`badge ${ap.verdict === 'allow' ? 'allow' : 'deny'}`}>
          {ap.status === 'timeout' ? 'TIMED OUT — DENIED' : ap.verdict === 'allow' ? 'YOU APPROVED' : 'YOU DENIED'}
        </div>
      ) : (
        <>
          <label className="remember">
            <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
            Always do this for things like it
          </label>
          <div className="btn-row">
            <button className="btn deny" disabled={busy} onClick={() => decide('deny')}>Deny</button>
            <button className="btn allow" disabled={busy} onClick={() => decide('allow')}>Approve</button>
          </div>
        </>
      )}
      {err && <div className="error">{err}</div>}
    </div>
  )
}
