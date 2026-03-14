import { useState } from 'react'
import { ProposalFeed } from './components/ProposalFeed.jsx'
import { AuditLog } from './components/AuditLog.jsx'

export default function App() {
  const [decisions, setDecisions] = useState([])

  function handleDecided(decisionRecord) {
    setDecisions((prev) => [decisionRecord, ...prev])
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-sm px-4 py-3">
        <h1 className="text-lg font-bold text-gray-900">GigAI — Proposal Dashboard</h1>
      </header>
      <main className="max-w-5xl mx-auto px-4 py-6">
        <div className="flex flex-col sm:flex-row gap-6">
          <section className="flex-1 min-w-0">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Active Proposals</h2>
            <ProposalFeed onDecided={handleDecided} />
          </section>
          <aside className="w-full sm:w-80 flex-shrink-0">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Audit Log</h2>
            <AuditLog decisions={decisions} />
          </aside>
        </div>
      </main>
    </div>
  )
}
