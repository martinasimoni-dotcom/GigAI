import { useState, useEffect } from 'react'
import { Sidebar } from './components/Sidebar.jsx'
import { ProposalFeed } from './components/ProposalFeed.jsx'
import { AuditLog } from './components/AuditLog.jsx'
import { ProjectLibrary } from './components/ProjectLibrary.jsx'
import { EmployeeLibrary } from './components/EmployeeLibrary.jsx'
import { ScheduleView } from './components/ScheduleView.jsx'
import { InboxFeed } from './components/InboxFeed.jsx'

export default function App() {
  const [activeTab, setActiveTab] = useState('inbox')
  const [decisions, setDecisions] = useState([])
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  function handleDecided(record) {
    setDecisions((prev) => [record, ...prev])
  }

  const accepted = decisions.filter((d) => d.decision === 'accept').length
  const rejected = decisions.filter((d) => d.decision === 'reject').length

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Topbar */}
      <header className="topbar">
        <div className="logo-wrap">
          <div className="logo">
            <span className="logo-gig">GIG</span>
            <span className="logo-ai">AI</span>
          </div>
          <div className="logo-sub">Construction Intelligence Platform</div>
        </div>

        <div className="topbar-stats">
          <div className="stat-pill">
            <div className="stat-item">
              <span className="stat-value accept">{accepted}</span>
              <span className="stat-label">Accepted</span>
            </div>
            <div className="stat-divider" />
            <div className="stat-item">
              <span className="stat-value reject">{rejected}</span>
              <span className="stat-label">Rejected</span>
            </div>
            <div className="stat-divider" />
            <div className="stat-item">
              <span className="stat-value">{accepted + rejected}</span>
              <span className="stat-label">Total</span>
            </div>
          </div>
        </div>

        <div className="topbar-right">
          <div className="live-badge">
            <span className="live-dot" />
            <span className="live-text">LIVE</span>
          </div>
          <div className="clock">
            {time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </div>
        </div>
      </header>

      {/* Main Layout with Sidebar */}
      <div className="app-body">
        <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

        <div className="main-content">
          {activeTab === 'inbox' && (
            <main className="page-panel">
              <InboxFeed />
            </main>
          )}

          {activeTab === 'proposals' && (
            <div className="layout">
              <main className="feed-panel">
                <ProposalFeed onDecided={handleDecided} />
              </main>
              <aside className="audit-panel">
                <AuditLog decisions={decisions} />
              </aside>
            </div>
          )}

          {activeTab === 'projects' && (
            <main className="page-panel">
              <ProjectLibrary />
            </main>
          )}

          {activeTab === 'employees' && (
            <main className="page-panel">
              <EmployeeLibrary />
            </main>
          )}

          {activeTab === 'schedule' && (
            <main className="page-panel">
              <ScheduleView />
            </main>
          )}
        </div>
      </div>
    </div>
  )
}
