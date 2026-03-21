import { useState, useEffect } from 'react'
import { fetchSchedule, fetchScheduleAnalysis, fetchProjects } from '../api.js'

export function ScheduleView() {
  const [tasks, setTasks] = useState([])
  const [analysis, setAnalysis] = useState(null)
  const [projects, setProjects] = useState([])
  const [projectId, setProjectId] = useState('PRJ-001')
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [noSchedule, setNoSchedule] = useState(false)

  // Load projects list on mount
  useEffect(() => {
    fetchProjects({ status: 'active', sort_by: 'name' }).then((data) => {
      setProjects(data.projects ?? [])
    })
  }, [])

  useEffect(() => {
    loadData()
  }, [projectId, filter])

  async function loadData() {
    setLoading(true)
    setNoSchedule(false)
    const params = {}
    if (filter === 'critical') params.critical_only = 'true'
    else if (filter !== 'all') params.status = filter

    const [schedData, analysisData] = await Promise.all([
      fetchSchedule(projectId, params),
      fetchScheduleAnalysis(projectId),
    ])

    if (!schedData.tasks || schedData.tasks.length === 0) {
      setNoSchedule(true)
      setTasks([])
      setAnalysis(null)
    } else {
      setTasks(schedData.tasks ?? [])
      setAnalysis(analysisData)
    }
    setLoading(false)
  }

  const health = analysis?.health_score
  const healthColor = {
    healthy: 'var(--green)',
    'at-risk': 'var(--orange)',
    concerning: 'var(--red)',
    critical: 'var(--red)',
  }[health?.label] || 'var(--text-tertiary)'

  return (
    <div className="library-page">
      {/* Project Selector */}
      <div className="filter-bar">
        <select
          className="filter-search"
          value={projectId}
          onChange={(e) => setProjectId(e.target.value)}
          style={{ maxWidth: 400, cursor: 'pointer' }}
        >
          {projects.map((p) => (
            <option key={p.project_id} value={p.project_id}>
              {p.name} — {p.city}
            </option>
          ))}
        </select>
      </div>

      {/* Health & Stats */}
      {analysis && (
        <div className="stats-row">
          <div className="stat-card" style={{ borderColor: healthColor }}>
            <div className="stat-card-value" style={{ color: healthColor }}>{health?.score}</div>
            <div className="stat-card-label">Health Score</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-value">{analysis.total_tasks}</div>
            <div className="stat-card-label">Total Tasks</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-value green">{analysis.completed}</div>
            <div className="stat-card-label">Completed</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-value accent">{analysis.in_progress}</div>
            <div className="stat-card-label">In Progress</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-value" style={{ color: 'var(--red)' }}>
              {analysis.urgent_tasks?.length ?? 0}
            </div>
            <div className="stat-card-label">Urgent</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-value" style={{ color: 'var(--orange)' }}>
              {analysis.conflicts?.length ?? 0}
            </div>
            <div className="stat-card-label">Conflicts</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="filter-bar">
        <div className="filter-pills">
          {['all', 'critical', 'in-progress', 'not-started', 'completed'].map((f) => (
            <button
              key={f}
              className={`filter-pill ${filter === f ? 'active' : ''}`}
              onClick={() => setFilter(f)}
            >
              {f === 'all' ? 'All Tasks' : f === 'critical' ? 'Critical Path' : f.replace('-', ' ')}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="empty-state">
          <div className="spinner" style={{ width: 24, height: 24 }} />
        </div>
      ) : noSchedule ? (
        <div className="empty-state">
          <div className="empty-icon">▸</div>
          <div className="empty-title">No schedule data for this project</div>
          <div className="empty-sub">
            Schedule data is available for projects with imported Primavera P6 schedules.
            Currently only Harbor View Tower (PRJ-001) has schedule data loaded.
          </div>
        </div>
      ) : (
        <div className="schedule-layout">
          {/* Predictions Panel */}
          {analysis?.predictions?.length > 0 && (
            <div className="schedule-panel">
              <div className="panel-title">Delay Predictions</div>
              {analysis.predictions.map((pred) => (
                <div key={pred.task_id} className="prediction-card">
                  <div className="prediction-header">
                    <span className="prediction-task">{pred.task_name}</span>
                    <span
                      className="tag-pill"
                      style={{
                        background: pred.impact === 'critical' ? 'var(--red-soft)' : 'var(--orange-soft)',
                        color: pred.impact === 'critical' ? 'var(--red)' : 'var(--orange)',
                      }}
                    >
                      +{pred.delay_days}d delay
                    </span>
                  </div>
                  <div className="prediction-progress">
                    <div className="progress-labels">
                      <span>Progress: {pred.current_progress}%</span>
                      <span className="meta-label">Expected: {pred.expected_progress}%</span>
                    </div>
                    <div className="progress-track">
                      <div className="progress-fill expected" style={{ width: `${pred.expected_progress}%` }} />
                      <div className="progress-fill actual" style={{ width: `${pred.current_progress}%` }} />
                    </div>
                  </div>
                  <div className="prediction-detail">
                    <span className="meta-label">Planned finish:</span> {pred.planned_finish}
                  </div>
                  <div className="prediction-detail">
                    <span className="meta-label">Predicted finish:</span>
                    <span style={{ color: 'var(--red)' }}> {pred.predicted_finish}</span>
                  </div>
                  <div className="prediction-rec">{pred.recommendation}</div>
                </div>
              ))}
            </div>
          )}

          {/* Conflicts Panel */}
          {analysis?.conflicts?.length > 0 && (
            <div className="schedule-panel">
              <div className="panel-title">Resource Conflicts</div>
              {analysis.conflicts.map((conf, i) => (
                <div key={i} className="conflict-card">
                  <div className="conflict-header">
                    <span className="conflict-resource">{conf.resource}</span>
                    <span
                      className="tag-pill"
                      style={{
                        background: conf.severity === 'high' ? 'var(--red-soft)' : 'var(--orange-soft)',
                        color: conf.severity === 'high' ? 'var(--red)' : 'var(--orange)',
                      }}
                    >
                      {conf.severity}
                    </span>
                  </div>
                  <div className="conflict-desc">{conf.description}</div>
                  <div className="conflict-tasks">
                    <div className="conflict-task">
                      <span className="meta-label">Task A:</span> {conf.task_a.name}
                      <span className="meta-label"> ({conf.task_a.start} to {conf.task_a.finish})</span>
                    </div>
                    <div className="conflict-task">
                      <span className="meta-label">Task B:</span> {conf.task_b.name}
                      <span className="meta-label"> ({conf.task_b.start} to {conf.task_b.finish})</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Urgent Tasks */}
          {analysis?.urgent_tasks?.length > 0 && (
            <div className="schedule-panel">
              <div className="panel-title">Urgent Tasks</div>
              {analysis.urgent_tasks.map((task) => (
                <div key={task.task_id} className="urgent-task-card">
                  <div className="urgent-task-header">
                    <span className="urgent-task-name">{task.name}</span>
                    <span className="urgency-score">{task.urgency_score}</span>
                  </div>
                  <div className="urgent-task-meta">
                    <span>{task.discipline}</span>
                    <span>{task.resource}</span>
                    <span>{task.start} — {task.finish}</span>
                  </div>
                  {task.critical && <span className="critical-badge">CRITICAL PATH</span>}
                </div>
              ))}
            </div>
          )}

          {/* Task List */}
          <div className="schedule-panel full-width">
            <div className="section-header">
              <span className="panel-title">Schedule</span>
              <span className="section-count">{tasks.length} tasks</span>
            </div>
            <div className="task-table">
              <div className="task-table-header">
                <span className="task-col-wbs">WBS</span>
                <span className="task-col-name">Task Name</span>
                <span className="task-col-dates">Start</span>
                <span className="task-col-dates">Finish</span>
                <span className="task-col-status">Status</span>
                <span className="task-col-progress">Progress</span>
                <span className="task-col-resource">Resource</span>
              </div>
              {tasks.map((t) => {
                const statusColor = {
                  completed: 'var(--green)',
                  'in-progress': 'var(--accent)',
                  'not-started': 'var(--text-tertiary)',
                }[t.status] || 'var(--text-tertiary)'

                return (
                  <div key={t.task_id} className={`task-row ${t.critical ? 'critical' : ''}`}>
                    <span className="task-col-wbs">{t.wbs}</span>
                    <span className="task-col-name">
                      {t.name}
                      {t.critical && <span className="critical-dot" />}
                    </span>
                    <span className="task-col-dates">{t.start}</span>
                    <span className="task-col-dates">{t.finish}</span>
                    <span className="task-col-status">
                      <span className="tag-pill" style={{ background: `${statusColor}18`, color: statusColor }}>
                        {t.status.replace('-', ' ')}
                      </span>
                    </span>
                    <span className="task-col-progress">
                      <div className="mini-progress-track">
                        <div
                          className="mini-progress-fill"
                          style={{
                            width: `${t.pct_complete}%`,
                            background: statusColor,
                          }}
                        />
                      </div>
                      <span className="mini-progress-text">{t.pct_complete}%</span>
                    </span>
                    <span className="task-col-resource">{t.resource}</span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
