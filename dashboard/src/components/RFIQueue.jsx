import { useState, useEffect } from 'react'
import { fetchRFIs, fetchRFIStats, sendRFI, closeRFI } from '../api.js'

const STATUSES = ['all', 'open', 'drafted', 'reviewed', 'sent', 'responded', 'closed']
const PRIORITIES = ['all', 'critical', 'high', 'medium', 'low']

const STATUS_COLOR = {
  open: 'var(--red)',
  drafted: 'var(--orange)',
  reviewed: 'var(--accent)',
  sent: 'var(--purple)',
  responded: 'var(--green)',
  closed: 'var(--text-tertiary)',
}
const PRIORITY_COLOR = {
  critical: 'var(--red)',
  high: 'var(--orange)',
  medium: 'var(--accent)',
  low: 'var(--text-tertiary)',
}

export function RFIQueue() {
  const [rfis, setRfis] = useState([])
  const [stats, setStats] = useState(null)
  const [status, setStatus] = useState('all')
  const [priority, setPriority] = useState('all')
  const [search, setSearch] = useState('')
  const [expandedId, setExpandedId] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadRFIs()
    fetchRFIStats().then(setStats)
  }, [status, priority, search])

  async function loadRFIs() {
    setLoading(true)
    const params = {}
    if (status !== 'all') params.status = status
    if (priority !== 'all') params.priority = priority
    if (search) params.search = search
    const data = await fetchRFIs(params)
    setRfis(data.rfis ?? [])
    setLoading(false)
  }

  async function handleSend(rfiId) {
    await sendRFI(rfiId)
    loadRFIs()
  }

  async function handleClose(rfiId) {
    await closeRFI(rfiId)
    loadRFIs()
  }

  return (
    <div className="library-page">
      {/* Stats */}
      {stats && (
        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-card-value">{stats.total}</div>
            <div className="stat-card-label">Total RFIs</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-value" style={{ color: 'var(--red)' }}>{stats.needs_attention}</div>
            <div className="stat-card-label">Needs Attention</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-value">{Math.round(stats.avg_age_hours)}h</div>
            <div className="stat-card-label">Avg Age</div>
          </div>
          {Object.entries(stats.by_status || {}).filter(([s]) => s !== 'closed').map(([s, c]) => (
            <div key={s} className="stat-card">
              <div className="stat-card-value" style={{ color: STATUS_COLOR[s] }}>{c}</div>
              <div className="stat-card-label" style={{ textTransform: 'capitalize' }}>{s}</div>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="filter-bar">
        <input
          className="filter-search"
          type="text"
          placeholder="Search RFIs..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="filter-pills">
          {STATUSES.map((s) => (
            <button
              key={s}
              className={`filter-pill ${status === s ? 'active' : ''}`}
              onClick={() => setStatus(s)}
            >
              {s === 'all' ? 'All Status' : s}
            </button>
          ))}
        </div>
        <div className="filter-pills">
          {PRIORITIES.map((p) => (
            <button
              key={p}
              className={`filter-pill ${priority === p ? 'active' : ''}`}
              onClick={() => setPriority(p)}
            >
              {p === 'all' ? 'All Priority' : p}
            </button>
          ))}
        </div>
      </div>

      <div className="section-header">
        <span className="section-title">RFI Queue</span>
        <span className="section-count">{rfis.length}</span>
      </div>

      {loading ? (
        <div className="empty-state">
          <div className="spinner" style={{ width: 24, height: 24 }} />
        </div>
      ) : rfis.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">?</div>
          <div className="empty-title">No RFIs found</div>
          <div className="empty-sub">RFIs are auto-detected from inbox communications</div>
        </div>
      ) : (
        <div className="rfi-list">
          {rfis.map((rfi) => (
            <RFICard
              key={rfi.rfi_id}
              rfi={rfi}
              expanded={expandedId === rfi.rfi_id}
              onToggle={() => setExpandedId(prev => prev === rfi.rfi_id ? null : rfi.rfi_id)}
              onSend={() => handleSend(rfi.rfi_id)}
              onClose={() => handleClose(rfi.rfi_id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function RFICard({ rfi, expanded, onToggle, onSend, onClose }) {
  const statusColor = STATUS_COLOR[rfi.status] || 'var(--text-tertiary)'
  const prioColor = PRIORITY_COLOR[rfi.priority] || 'var(--text-tertiary)'

  return (
    <div className={`rfi-card ${expanded ? 'expanded' : ''}`} onClick={onToggle}>
      <div className="rfi-card-stripe" style={{ background: statusColor }} />
      <div className="rfi-card-body">
        <div className="rfi-card-header">
          <div className="rfi-id-badge">{rfi.rfi_id}</div>
          <div className="rfi-card-main">
            <div className="rfi-card-title">{rfi.title}</div>
            <div className="rfi-card-meta">
              <span className="tag-pill" style={{ background: `${statusColor}18`, color: statusColor }}>
                {rfi.status}
              </span>
              <span className="tag-pill" style={{ background: `${prioColor}18`, color: prioColor }}>
                {rfi.priority}
              </span>
              <span className="rfi-category-chip">{rfi.category}</span>
              {rfi.project_name && <span className="inbox-project-chip">{rfi.project_name}</span>}
              <span className="inbox-sender">{rfi.age_hours}h old</span>
            </div>
          </div>
        </div>

        {expanded && (
          <div className="rfi-expanded">
            <div className="rfi-details-grid">
              <div className="meta-item">
                <span className="meta-label">Requester</span>
                <span className="meta-value">{rfi.requester}</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Assignee</span>
                <span className="meta-value">{rfi.assignee || 'Unassigned'}</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Created</span>
                <span className="meta-value">{new Date(rfi.created_at).toLocaleDateString()}</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Category</span>
                <span className="meta-value" style={{ textTransform: 'capitalize' }}>{rfi.category}</span>
              </div>
            </div>

            <div className="rfi-question-section">
              <div className="rfi-section-title">Question</div>
              <div className="rfi-question-text">{rfi.question}</div>
            </div>

            {rfi.response && (
              <div className="rfi-response-section">
                <div className="rfi-section-title">
                  {rfi.response.edited_by_pm ? 'Response (PM Edited)' : 'AI Draft Response'}
                  <span className="rfi-confidence">
                    {Math.round(rfi.response.confidence * 100)}% confidence
                  </span>
                </div>
                <div className="rfi-response-text">
                  {rfi.response.edited_by_pm ? rfi.response.pm_edits : rfi.response.draft_text}
                </div>
                {rfi.response.knowledge_sources?.length > 0 && (
                  <div className="rfi-sources">
                    <span className="meta-label">Sources:</span>
                    {rfi.response.knowledge_sources.map((s, i) => (
                      <span key={i} className="rfi-source-tag">{s}</span>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="rfi-card-actions" onClick={(e) => e.stopPropagation()}>
              {rfi.status === 'drafted' && (
                <button className="btn-accept" onClick={onSend} style={{ flex: 'none', padding: '8px 20px' }}>
                  Send Response
                </button>
              )}
              {rfi.status === 'reviewed' && (
                <button className="btn-accept" onClick={onSend} style={{ flex: 'none', padding: '8px 20px' }}>
                  Send Response
                </button>
              )}
              {rfi.status !== 'closed' && (
                <button className="btn-reject" onClick={onClose} style={{ flex: 'none', padding: '8px 20px' }}>
                  Close RFI
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
