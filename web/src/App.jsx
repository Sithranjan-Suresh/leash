import { NavLink, Route, Routes } from 'react-router-dom'
import { LeashProvider, useLeash } from './api'
import Live from './pages/Live'
import Policy from './pages/Policy'
import RedTeam from './pages/RedTeam'
import Approve from './pages/Approve'

function Shell() {
  const { connected, approvals } = useLeash()
  const pending = Object.values(approvals).filter((a) => a.status === 'pending').length
  return (
    <div className="shell">
      <header className="top">
        <div className="brand">
          <span className="logo">⛓</span> Leash
          <span className={`dot ${connected ? 'on' : ''}`} title={connected ? 'live' : 'reconnecting'} />
        </div>
        <nav>
          <NavLink to="/" end>Live Control{pending > 0 && <b className="count">{pending}</b>}</NavLink>
          <NavLink to="/policy">Policy</NavLink>
          <NavLink to="/redteam">Red Team</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Live />} />
          <Route path="/policy" element={<Policy />} />
          <Route path="/redteam" element={<RedTeam />} />
          <Route path="*" element={<Live />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <LeashProvider>
      <Routes>
        <Route path="/approve/:id" element={<Approve />} />
        <Route path="/*" element={<Shell />} />
      </Routes>
    </LeashProvider>
  )
}
