import { useState, useEffect } from 'react'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const SOURCE_ICON = { meeting: '🎙', email: '✉', proposal: '◈', acc: '▦', internal: '◉' }
const SOURCE_COLOR = {
  meeting: 'var(--accent)',
  email: 'var(--green)',
  proposal: 'var(--orange)',
  acc: 'var(--purple)',
  internal: 'var(--text-secondary)',
}

export function DecisionTracker() {
  const [decisions, setDecisions] = useState([])
  const [stats, setStats] = useState(null)
  const [search, setSearch] = useState('')
  const [source, setSource] = useState('all')
  const [tag, setTag] = useState('all')
  const [expandedId, setExpandedId] = useState(null)
  const [loading, setLoading] = useState(true)

  const sources = ['all', 'meeting', 'email', 'proposal', 'acc', 'internal']
  const tags = ['all', 'material', 'design', 'MEP', 'schedule', 'budget', 'safety', 'vendor', 'permit']

  useEffect(() => { loadDecisions(); loadStats() }, [search, source, tag])

  async function loadDecisions() {
    setLoading(true)
    const params = new URLSearchParams()
    if (search) params.set('search', search)
    if (source !== 'all') params.set('source', source)
    if (tag !== 'all') params.set('tag', tag)
    const qs = params.toString()
    try {
      const res = await fetch(`${BASE}/api/decisions${qs ? '?' + qs : ''}`)
      const data = await res.json()
      setDecisions(data.decisions ?? [])
    } catch { setDecisions([]) }
    setLoading(false)
  }

  async function loadStats() {
    try {
      const res = await fetch(`${BASE}/api/decisions/stats`)
      setStats(await res.json())
    } catch {}
  }

  return (
    <div className="library-page">
      {stats && (
        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-card-value">{stats.total}</div>
            <div className="stat-card-label">Total Decisions</div>
          </div>
          {Object.entries(stats.by_source || {}).map(([s, c]) => (
            <div key={s} className="stat-card">
              <div className="stat-card-value" style={{ color: SOURCE_COLOR[s] }}>{c}</div>
              <div className="stat-card-label" style={{ textTransform: 'capitalize' }}>{s}</div>
            </div>
          ))}
        </div>
      )}

      <div className="filter-bar">
        <input
          className="filter-search"
          type="text"
          placeholder="Search decisions by keyword, person, topic..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="filter-pills">
          {sources.map((s) => (
            <button key={s} className={`filter-pill ${source === s ? 'active' : ''}`} onClick={() => setSource(s)}>
              {s === 'all' ? 'All Sources' : s}
            </button>
          ))}
        </div>
        <div className="filter-pills">
          {tags.map((t) => (
            <button key={t} className={`filter-pill ${tag === t ? 'active' : ''}`} onClick={() => setTag(t)}>
              {t === 'all' ? 'All Topics' : t}
            </button>
          ))}
        </div>
      </div>

      <div className="section-header">
        <span className="section-title">Decision Timeline</span>
        <span className="section-count">{decisions.length}</span>
      </div>

      {loading ? (
        <div className="empty-state"><div className="spinner" style={{ width: 24, height: 24 }} /></div>
      ) : decisions.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">✓</div>
          <div className="empty-title">No decisions found</div>
          <div className="empty-sub">Decisions are auto-captured from meetings, emails, and proposals</div>
        </div>
      ) : (
        <div className="decision-timeline-list">
          {decisions.map((d) => (
            <DecisionCard
              key={d.decision_id}
              decision={d}
              expanded={expandedId === d.decision_id}
              onToggle={() => setExpandedId(prev => prev === d.decision_id ? null : d.decision_id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function DecisionCard({ decision: d, expanded, onToggle }) {
  const srcColor = SOURCE_COLOR[d.source] || 'var(--text-tertiary)'
  const timeAgo = getTimeAgo(d.decided_at)

  return (
    <div className={`decision-card ${expanded ? 'expanded' : ''}`} onClick={onToggle}>
      <div className="decision-card-dot" style={{ background: srcColor }} />
      <div className="decision-card-body">
        <div className="decision-card-header">
          <div style={{ flex: 1 }}>
            <div className="decision-card-title">{d.title}</div>
            <div className="decision-card-meta">
              <span className="tag-pill" style={{ background: `${srcColor}18`, color: srcColor }}>
                {SOURCE_ICON[d.source] || '•'} {d.source}
              </span>
              <span className="inbox-sender">{d.decided_by}</span>
              {d.project_name && <span className="inbox-project-chip">{d.project_name}</span>}
              {d.tags.map((t) => (
                <span key={t} className="project-tag">{t}</span>
              ))}
              <span className="inbox-card-time">{timeAgo}</span>
            </div>
          </div>
        </div>

        {expanded && (
          <div className="decision-expanded">
            <div className="rfi-question-text">{d.description}</div>
            <div className="rfi-details-grid" style={{ marginTop: 12 }}>
              <div className="meta-item">
                <span className="meta-label">Decided By</span>
                <span className="meta-value">{d.decided_by}</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Source</span>
                <span className="meta-value" style={{ textTransform: 'capitalize' }}>{d.source}</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Date</span>
                <span className="meta-value">{new Date(d.decided_at).toLocaleDateString()}</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Project</span>
                <span className="meta-value">{d.project_name || 'Company-wide'}</span>
              </div>
            </div>
            {d.source_url && (
              <a href={d.source_url} target="_blank" rel="noopener noreferrer" className="inbox-source-link" onClick={(e) => e.stopPropagation()}>
                View original source →
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function getTimeAgo(isoDate) {
  const diff = Date.now() - new Date(isoDate).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}
