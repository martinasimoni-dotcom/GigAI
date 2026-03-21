import { useState, useEffect } from 'react'
import { fetchProjects, fetchProjectStats } from '../api.js'

const CATEGORIES = ['all', 'residential', 'commercial', 'mixed-use', 'infrastructure', 'renovation', 'industrial']
const STATUSES = ['all', 'active', 'completed', 'on-hold', 'planning', 'pre-construction']
const PRIORITIES = ['all', 'critical', 'high', 'medium', 'low']

function formatBudget(n) {
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(1)}B`
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`
  return `$${n}`
}

export function ProjectLibrary() {
  const [projects, setProjects] = useState([])
  const [stats, setStats] = useState(null)
  const [category, setCategory] = useState('all')
  const [status, setStatus] = useState('all')
  const [priority, setPriority] = useState('all')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadProjects()
    fetchProjectStats().then(setStats)
  }, [category, status, priority, search])

  async function loadProjects() {
    setLoading(true)
    const params = {}
    if (category !== 'all') params.category = category
    if (status !== 'all') params.status = status
    if (priority !== 'all') params.priority = priority
    if (search) params.search = search
    const data = await fetchProjects(params)
    setProjects(data.projects ?? [])
    setLoading(false)
  }

  return (
    <div className="library-page">
      {/* Stats Row */}
      {stats && (
        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-card-value">{stats.total_projects}</div>
            <div className="stat-card-label">Total Projects</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-value accent">{stats.active}</div>
            <div className="stat-card-label">Active</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-value green">{stats.completed}</div>
            <div className="stat-card-label">Completed</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-value">{formatBudget(stats.total_budget)}</div>
            <div className="stat-card-label">Total Portfolio</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-value">{stats.total_team_size}</div>
            <div className="stat-card-label">Total Staff</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="filter-bar">
        <input
          className="filter-search"
          type="text"
          placeholder="Search projects..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="filter-pills">
          {CATEGORIES.map((c) => (
            <button
              key={c}
              className={`filter-pill ${category === c ? 'active' : ''}`}
              onClick={() => setCategory(c)}
            >
              {c === 'all' ? 'All Types' : c.replace('-', ' ')}
            </button>
          ))}
        </div>
        <div className="filter-pills">
          {STATUSES.map((s) => (
            <button
              key={s}
              className={`filter-pill ${status === s ? 'active' : ''}`}
              onClick={() => setStatus(s)}
            >
              {s === 'all' ? 'All Status' : s.replace('-', ' ')}
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

      {/* Results Count */}
      <div className="section-header">
        <span className="section-title">Projects</span>
        <span className="section-count">{projects.length}</span>
      </div>

      {/* Project Grid */}
      {loading ? (
        <div className="empty-state">
          <div className="spinner" style={{ width: 24, height: 24 }} />
        </div>
      ) : projects.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">▦</div>
          <div className="empty-title">No projects found</div>
          <div className="empty-sub">Try adjusting your filters</div>
        </div>
      ) : (
        <div className="project-grid">
          {projects.map((p) => (
            <ProjectCard key={p.project_id} project={p} />
          ))}
        </div>
      )}
    </div>
  )
}

function ProjectCard({ project: p }) {
  const statusColor = {
    active: 'var(--green)',
    completed: 'var(--accent)',
    'on-hold': 'var(--orange)',
    planning: 'var(--purple)',
    'pre-construction': 'var(--purple)',
  }[p.status] || 'var(--text-tertiary)'

  const priorityColor = {
    critical: 'var(--red)',
    high: 'var(--orange)',
    medium: 'var(--accent)',
    low: 'var(--text-tertiary)',
  }[p.priority] || 'var(--text-tertiary)'

  return (
    <div className="project-card">
      <div className="project-card-header">
        <div style={{ flex: 1 }}>
          <div className="project-card-name">{p.name}</div>
          <div className="project-card-client">{p.client}</div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <span className="tag-pill" style={{ background: `${statusColor}18`, color: statusColor }}>
            {p.status.replace('-', ' ')}
          </span>
          <span className="tag-pill" style={{ background: `${priorityColor}18`, color: priorityColor }}>
            {p.priority}
          </span>
        </div>
      </div>

      <div className="project-card-desc">{p.description}</div>

      <div className="project-card-meta">
        <div className="meta-item">
          <span className="meta-label">Location</span>
          <span className="meta-value">{p.city}, {p.region}</span>
        </div>
        <div className="meta-item">
          <span className="meta-label">Category</span>
          <span className="meta-value" style={{ textTransform: 'capitalize' }}>{p.category.replace('-', ' ')}</span>
        </div>
        <div className="meta-item">
          <span className="meta-label">Budget</span>
          <span className="meta-value">{formatBudget(p.budget)}</span>
        </div>
        <div className="meta-item">
          <span className="meta-label">Team</span>
          <span className="meta-value">{p.team_size} people</span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="progress-section">
        <div className="progress-header">
          <span className="meta-label">Completion</span>
          <span className="progress-pct">{p.completion_pct}%</span>
        </div>
        <div className="progress-track">
          <div
            className="progress-fill"
            style={{
              width: `${p.completion_pct}%`,
              background: p.completion_pct === 100 ? 'var(--green)' : 'var(--accent)',
            }}
          />
        </div>
        <div className="progress-budget">
          <span className="meta-label">Spent</span>
          <span className="meta-value">{formatBudget(p.spent)} / {formatBudget(p.budget)}</span>
        </div>
      </div>

      {/* Tags */}
      <div className="project-tags">
        {p.tags.map((t) => (
          <span key={t} className="project-tag">{t}</span>
        ))}
      </div>

      {/* PM & Super */}
      <div className="project-card-footer">
        <span className="footer-person">PM: {p.project_manager}</span>
        {p.superintendent !== 'TBD' && (
          <span className="footer-person">Super: {p.superintendent}</span>
        )}
      </div>
    </div>
  )
}
