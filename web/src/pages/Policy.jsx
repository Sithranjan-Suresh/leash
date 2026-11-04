import { useEffect, useState } from 'react'
import { api } from '../api'

const EXAMPLE = `Never send email to anyone outside acme.example.
Ask me before any payment over $20.
Ask me before reading passwords, keys or finance files.
Never run curl, wget, sudo or rm.`

const SRC = { user: 'you', compiler: 'from your words', approval: 'from an approval', redteam: 'red team fix', seed: 'default' }

export default function Policy() {
  const [text, setText] = useState(EXAMPLE)
  const [rules, setRules] = useState([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [note, setNote] = useState('')

  const load = () => api('/rules').then(setRules).catch((e) => setErr(e.message))
  useEffect(() => { load() }, [])

  const compile = async () => {
    setBusy(true); setErr(''); setNote('')
    try {
      const r = await api('/policy/compile', { body: { text, replace: true } })
      setNote(r.warning || `Created ${r.rules.length} rules.`)
      await load()
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  const toggle = async (r) => { await api(`/rules/${r.id}`, { method: 'PATCH', body: { enabled: !r.enabled } }); load() }
  const remove = async (r) => { await api(`/rules/${r.id}`, { method: 'DELETE' }); load() }

  return (
    <div className="page two">
      <section>
        <h1>Say it in English</h1>
        <p className="muted">Write what your agent may and may not do. Leash turns it into rules it enforces on every tool call.</p>
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={8} spellCheck={false} />
        <button className="btn primary" onClick={compile} disabled={busy || !text.trim()}>{busy ? 'Compiling…' : 'Compile to rules'}</button>
        {note && <div className="note">{note}</div>}
        {err && <div className="error">{err}</div>}
      </section>
      <section>
        <h2>Active rules <span className="muted">({rules.filter((r) => r.enabled).length})</span></h2>
        {rules.length === 0 && <div className="empty">No rules yet — the AI judge uses its own judgment.</div>}
        {rules.map((r) => (
          <div className={`rule ${r.enabled ? '' : 'off'}`} key={r.id}>
            <span className={`badge ${r.verdict}`}>{r.verdict === 'deny' ? 'NEVER' : r.verdict === 'ask' ? 'ASK' : 'ALLOW'}</span>
            <div className="rule-main">
              <div>{r.text}</div>
              <div className="muted small"><code>{r.tool}</code> · {SRC[r.source] || r.source}</div>
            </div>
            <button className="link" onClick={() => toggle(r)}>{r.enabled ? 'disable' : 'enable'}</button>
            <button className="link" onClick={() => remove(r)}>delete</button>
          </div>
        ))}
      </section>
    </div>
  )
}
