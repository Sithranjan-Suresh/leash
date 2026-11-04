import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, useLeash } from '../api'
import { ApprovalCard } from '../components'

export default function Approve() {
  const { id } = useParams()
  const live = useLeash()
  const [ap, setAp] = useState(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    api(`/approvals/${id}`).then(setAp).catch((e) => setErr(e.message))
  }, [id])
  const current = live.approvals[id] || ap
  return (
    <div className="mobile">
      <div className="brand"><span className="logo">⛓</span> Leash</div>
      {err && <div className="error">{err}</div>}
      {!current && !err && <div className="empty">Loading…</div>}
      {current && <ApprovalCard ap={current} big />}
    </div>
  )
}
