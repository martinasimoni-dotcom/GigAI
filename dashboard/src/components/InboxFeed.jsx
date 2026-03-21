import { useState, useEffect } from 'react'
import { fetchInbox, fetchInboxStats, markInboxRead, archiveInboxItem } from '../api.js'

const COMM_TYPES = ['all', 'escalation', 'action-item', 'decision', 'question', 'FYI']
const SOURCES = ['all', 'gmail', 'fireflies', 'acc', 'internal']

const TYPE_ICON = {
  'escalation': '!',
  'action-item': '→',
  'decision': '✓',
  'question': '?',
  'FYI': 'i',
}
const TYPE_COLOR = {
  'escalation': 'var(--red)',
  'action-item': 'var(--accent)',
  'decision': 'var(--green)',
  'question': 'var(--orange)',
  'FYI': 'var(--text-tertiary)',
}
const SOURCE_ICON = {
  gmail: '✉',
  fireflies: '🎙',
  acc: '▦',
  internal: '◈',
}
const URGENCY_LABEL = { 1: 'Info', 2: 'Low', 3: 'Normal', 4: 'High', 5: 'Critical' }
const URGENCY_COLOR = {
  1: 'var(--text-tertiary)',
  2: 'var(--text-secondary)',
  3: 'var(--accent)',
  4: 'var(--orange)',
  5: 'var(--red)',
}

export function InboxFeed() {
  const [items, setItems] = useState([])
  const [stats, setStats] = useState(null)
  const [commType, setCommType] = useState('all')
  const [source, setSource] = useState('all')
  const [search, setSearch] = useState('')
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [expandedId, setExpandedId] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadInbox()
    fetchInboxStats().then(setStats)
  }, [commType, source, search, unreadOnly])

  async function loadInbox() {
    setLoading(true)
    const params = {}
    if (commType !== 'all') params.comm_type = commType
    if (source !== 'all') params.source = source  // Note: source filtering not in API yet, but ready
    if (search) params.search = search
    if (unreadOnly) params.unread_only = 'true'
    const data = await fetchInbox(params)
    setItems(data.items ?? [])
    setLoading(false)
  }

  async function handleMarkRead(itemId) {
    await markInboxRead(itemId)
    setItems(prev => prev.map(i =>
      i.item_id === itemId ? { ...i, is_read: true } : i
    ))
  }

  async function handleArchive(itemId) {
    await archiveInboxItem(itemId)
    setItems(prev => prev.filter(i => i.item_id !== itemId))
    fetchInboxStats().then(setStats)
  }

  function toggleExpand(itemId) {
    setExpandedId(prev => prev === itemId ? null : itemId)
  }

  return (
    <div className="library-page">
      {/* Stats Row */}
      {stats && (
        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-card-value">{stats.total}</div>
            <div className="stat-card-label">Total</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-value" style={{ color: 'var(--accent)' }}>{stats.unread}</div>
            <div className="stat-card-label">Unread</div>
          </div>
          {Object.entries(stats.by_type || {}).sort((a, b) => b[1] - a[1]).slice(0, 4).map(([type, count]) => (
            <div key={type} className="stat-card">
              <div className="stat-card-value" style={{ color: TYPE_COLOR[type] || 'var(--text-primary)' }}>{count}</div>
              <div className="stat-card-label" style={{ textTransform: 'capitalize' }}>{type.replace('-', ' ')}</div>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="filter-bar">
        <input
          className="filter-search"
          type="text"
          placeholder="Search inbox..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="filter-pills">
          {COMM_TYPES.map((t) => (
            <button
              key={t}
              className={`filter-pill ${commType === t ? 'active' : ''}`}
              onClick={() => setCommType(t)}
            >
              {t === 'all' ? 'All Types' : t.replace('-', ' ')}
            </button>
          ))}
        </div>
        <div className="filter-pills">
          {SOURCES.map((s) => (
            <button
              key={s}
              className={`filter-pill ${source === s ? 'active' : ''}`}
              onClick={() => setSource(s)}
            >
              {s === 'all' ? 'All Sources' : s}
            </button>
          ))}
          <button
            className={`filter-pill ${unreadOnly ? 'active' : ''}`}
            onClick={() => setUnreadOnly(!unreadOnly)}
          >
            Unread only
          </button>
        </div>
      </div>

      {/* Results */}
      <div className="section-header">
        <span className="section-title">Inbox</span>
        <span className="section-count">{items.length}</span>
      </div>

      {loading ? (
        <div className="empty-state">
          <div className="spinner" style={{ width: 24, height: 24 }} />
        </div>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">✉</div>
          <div className="empty-title">Inbox empty</div>
          <div className="empty-sub">No communications match your filters</div>
        </div>
      ) : (
        <div className="inbox-list">
          {items.map((item) => (
            <InboxItemCard
              key={item.item_id}
              item={item}
              expanded={expandedId === item.item_id}
              onToggle={() => toggleExpand(item.item_id)}
              onMarkRead={() => handleMarkRead(item.item_id)}
              onArchive={() => handleArchive(item.item_id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function InboxItemCard({ item, expanded, onToggle, onMarkRead, onArchive }) {
  const typeColor = TYPE_COLOR[item.comm_type] || 'var(--text-tertiary)'
  const urgColor = URGENCY_COLOR[item.urgency] || 'var(--text-tertiary)'
  const timeAgo = getTimeAgo(item.received_at)

  return (
    <div
      className={`inbox-card ${item.is_read ? 'read' : 'unread'} ${expanded ? 'expanded' : ''}`}
      onClick={onToggle}
    >
      <div className="inbox-card-stripe" style={{ background: typeColor }} />
      <div className="inbox-card-body">
        {/* Header Row */}
        <div className="inbox-card-header">
          <div className="inbox-type-icon" style={{ background: `${typeColor}18`, color: typeColor }}>
            {TYPE_ICON[item.comm_type] || '•'}
          </div>
          <div className="inbox-card-main">
            <div className="inbox-card-title-row">
              <span className={`inbox-card-summary ${!item.is_read ? 'bold' : ''}`}>
                {item.summary}
              </span>
              <span className="inbox-card-time">{timeAgo}</span>
            </div>
            <div className="inbox-card-meta">
              <span className="inbox-source-chip">
                {SOURCE_ICON[item.source] || '•'} {item.source}
              </span>
              <span className="tag-pill" style={{ background: `${typeColor}18`, color: typeColor }}>
                {item.comm_type}
              </span>
              <span className="tag-pill" style={{ background: `${urgColor}18`, color: urgColor }}>
                {URGENCY_LABEL[item.urgency]}
              </span>
              {item.project_name && (
                <span className="inbox-project-chip">{item.project_name}</span>
              )}
              <span className="inbox-sender">{item.sender}</span>
            </div>
          </div>
        </div>

        {/* Expanded Details */}
        {expanded && (
          <div className="inbox-expanded">
            {item.subject && (
              <div className="inbox-subject">Subject: {item.subject}</div>
            )}
            <div className="inbox-raw-text">{item.raw_text}</div>

            {/* Action Items */}
            {item.action_items?.length > 0 && (
              <div className="inbox-actions-section">
                <div className="inbox-actions-title">Action Items ({item.action_items.length})</div>
                {item.action_items.map((ai, idx) => (
                  <div key={idx} className="inbox-action-row">
                    <span className="inbox-action-assignee">{ai.assignee}</span>
                    <span className="inbox-action-desc">{ai.description}</span>
                    <span className="tag-pill" style={{
                      background: ai.priority === 'high' ? 'var(--red-soft)' : ai.priority === 'medium' ? 'var(--orange-soft)' : 'var(--green-soft)',
                      color: ai.priority === 'high' ? 'var(--red)' : ai.priority === 'medium' ? 'var(--orange)' : 'var(--green)',
                    }}>
                      {ai.priority}
                    </span>
                    {ai.deadline && (
                      <span className="inbox-action-deadline">{ai.deadline.split('T')[0]}</span>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Footer */}
            <div className="inbox-card-footer">
              {item.source_url && (
                <a
                  href={item.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inbox-source-link"
                  onClick={(e) => e.stopPropagation()}
                >
                  View original →
                </a>
              )}
              {!item.is_read && (
                <button
                  className="inbox-mark-read-btn"
                  onClick={(e) => { e.stopPropagation(); onMarkRead() }}
                >
                  Mark as read
                </button>
              )}
              <button
                className="inbox-mark-read-btn"
                onClick={(e) => { e.stopPropagation(); onArchive() }}
                style={{ color: 'var(--text-tertiary)' }}
              >
                Dismiss
              </button>
            </div>
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
