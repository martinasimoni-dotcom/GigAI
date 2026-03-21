import { useState, useEffect } from 'react'
import { fetchEmployees, fetchEmployeeStats } from '../api.js'

const PROFESSIONS = ['all', 'Project Manager', 'Architect', 'Structural Engineer', 'Site Superintendent', 'Estimator', 'Procurement Officer']
const DEPARTMENTS = ['all', 'Project Management', 'Engineering', 'Field Operations', 'Design', 'Procurement', 'Preconstruction']
const AVAILABILITY = ['all', 'available', 'assigned']

export function EmployeeLibrary() {
  const [employees, setEmployees] = useState([])
  const [stats, setStats] = useState(null)
  const [profession, setProfession] = useState('all')
  const [department, setDepartment] = useState('all')
  const [availability, setAvailability] = useState('all')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadEmployees()
    fetchEmployeeStats().then(setStats)
  }, [profession, department, availability, search])

  async function loadEmployees() {
    setLoading(true)
    const params = {}
    if (profession !== 'all') params.profession = profession
    if (department !== 'all') params.department = department
    if (availability !== 'all') params.availability = availability
    if (search) params.search = search
    const data = await fetchEmployees(params)
    setEmployees(data.employees ?? [])
    setLoading(false)
  }

  return (
    <div className="library-page">
      {/* Stats Row */}
      {stats && (
        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-card-value">{stats.total_employees}</div>
            <div className="stat-card-label">Total Team</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-value green">{stats.available}</div>
            <div className="stat-card-label">Available</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-value accent">{stats.assigned}</div>
            <div className="stat-card-label">Assigned</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-value">{stats.avg_experience}y</div>
            <div className="stat-card-label">Avg Experience</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-value">{Object.keys(stats.departments).length}</div>
            <div className="stat-card-label">Departments</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="filter-bar">
        <input
          className="filter-search"
          type="text"
          placeholder="Search by name, role, specialization..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="filter-pills">
          {PROFESSIONS.map((p) => (
            <button
              key={p}
              className={`filter-pill ${profession === p ? 'active' : ''}`}
              onClick={() => setProfession(p)}
            >
              {p === 'all' ? 'All Roles' : p}
            </button>
          ))}
        </div>
        <div className="filter-pills">
          {DEPARTMENTS.map((d) => (
            <button
              key={d}
              className={`filter-pill ${department === d ? 'active' : ''}`}
              onClick={() => setDepartment(d)}
            >
              {d === 'all' ? 'All Depts' : d}
            </button>
          ))}
        </div>
        <div className="filter-pills">
          {AVAILABILITY.map((a) => (
            <button
              key={a}
              className={`filter-pill ${availability === a ? 'active' : ''}`}
              onClick={() => setAvailability(a)}
            >
              {a === 'all' ? 'All' : a}
            </button>
          ))}
        </div>
      </div>

      {/* Results Count */}
      <div className="section-header">
        <span className="section-title">Team Members</span>
        <span className="section-count">{employees.length}</span>
      </div>

      {/* Employee Grid */}
      {loading ? (
        <div className="empty-state">
          <div className="spinner" style={{ width: 24, height: 24 }} />
        </div>
      ) : employees.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">◉</div>
          <div className="empty-title">No team members found</div>
          <div className="empty-sub">Try adjusting your filters</div>
        </div>
      ) : (
        <div className="employee-grid">
          {employees.map((e) => (
            <EmployeeCard key={e.employee_id} employee={e} />
          ))}
        </div>
      )}
    </div>
  )
}

function EmployeeCard({ employee: e }) {
  const isAvailable = e.availability === 'available'

  return (
    <div className="employee-card">
      <div className="employee-card-header">
        <div className="employee-avatar">
          {e.name.split(' ').map(n => n[0]).join('')}
        </div>
        <div style={{ flex: 1 }}>
          <div className="employee-name">{e.name}</div>
          <div className="employee-title">{e.title}</div>
        </div>
        <span
          className="tag-pill"
          style={{
            background: isAvailable ? 'var(--green-soft)' : 'var(--accent-soft)',
            color: isAvailable ? 'var(--green)' : 'var(--accent)',
          }}
        >
          {e.availability}
        </span>
      </div>

      <div className="employee-bio">{e.bio}</div>

      <div className="employee-meta">
        <div className="meta-item">
          <span className="meta-label">Department</span>
          <span className="meta-value">{e.department}</span>
        </div>
        <div className="meta-item">
          <span className="meta-label">Experience</span>
          <span className="meta-value">{e.years_experience} years</span>
        </div>
        <div className="meta-item">
          <span className="meta-label">Location</span>
          <span className="meta-value">{e.location}</span>
        </div>
        <div className="meta-item">
          <span className="meta-label">Rate</span>
          <span className="meta-value">${e.hourly_rate}/hr</span>
        </div>
      </div>

      {/* Certifications */}
      <div className="cert-row">
        {e.certifications.map((c) => (
          <span key={c} className="cert-tag">{c}</span>
        ))}
      </div>

      {/* Specializations */}
      <div className="spec-row">
        {e.specializations.map((s) => (
          <span key={s} className="spec-tag">{s}</span>
        ))}
      </div>

      <div className="employee-card-footer">
        <span className="footer-email">{e.email}</span>
        {e.current_projects.length > 0 && (
          <span className="footer-projects">{e.current_projects.length} project{e.current_projects.length !== 1 ? 's' : ''}</span>
        )}
      </div>
    </div>
  )
}
