import { createContext, useContext, useEffect, useReducer } from 'react'

export async function api(path, opts = {}) {
  const r = await fetch('/api' + path, {
    method: opts.method || (opts.body ? 'POST' : 'GET'),
    headers: opts.body ? { 'Content-Type': 'application/json' } : undefined,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  })
  const data = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(data.detail || data.error || `Request failed (${r.status})`)
  return data
}

// ---- live event store fed by Server-Sent Events -------------------------------------------
const initial = {
  connected: false,
  duel: { status: 'idle', unleashed: [], leashed: [], result: null },
  approvals: {},
  redteam: { status: 'idle', done: 0, total: 0, score: null, previous: null },
  feed: [],
}

function reducer(s, a) {
  switch (a.type) {
    case 'connected':
      return { ...s, connected: a.value }
    case 'duel': {
      const d = a.data
      if (d.status === 'started') return { ...s, duel: { status: 'running', unleashed: [], leashed: [], result: null } }
      if (d.status === 'done') return { ...s, duel: { ...s.duel, status: 'done', result: d } }
      return s
    }
    case 'decision': {
      const d = a.data
      const row = { ...d, key: `${d.run_id}-${d.action_id}-${d.verdict}` }
      const feed = [row, ...s.feed.filter((r) => !(r.action_id === d.action_id && r.verdict === 'ask' && d.verdict !== 'ask'))].slice(0, 60)
      let duel = s.duel
      if (d.side === 'unleashed' || d.side === 'leashed') {
        const list = s.duel[d.side].filter((r) => !(r.action_id === d.action_id))
        duel = { ...s.duel, [d.side]: [...list, row] }
      }
      return { ...s, feed, duel }
    }
    case 'approval':
      return { ...s, approvals: { ...s.approvals, [a.data.id]: a.data } }
    case 'redteam': {
      const d = a.data
      if (d.status === 'started') return { ...s, redteam: { ...s.redteam, status: 'running', done: 0, total: d.total } }
      if (d.status === 'progress') return { ...s, redteam: { ...s.redteam, done: d.done, total: d.total } }
      if (d.status === 'done') return { ...s, redteam: { ...s.redteam, status: 'done', score: d.score, previous: d.previous_score } }
      return s
    }
    default:
      return s
  }
}

const Ctx = createContext(null)
export const useLeash = () => useContext(Ctx)

export function LeashProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initial)
  useEffect(() => {
    const es = new EventSource('/api/stream')
    es.onopen = () => dispatch({ type: 'connected', value: true })
    es.onerror = () => dispatch({ type: 'connected', value: false })
    for (const t of ['duel', 'decision', 'approval', 'redteam']) {
      es.addEventListener(t, (e) => dispatch({ type: t, data: JSON.parse(e.data) }))
    }
    return () => es.close()
  }, [])
  return <Ctx.Provider value={state}>{children}</Ctx.Provider>
}
