export function AuditLog({ decisions }) {
  const sorted = [...decisions].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))

  const totalSaved = decisions
    .filter((d) => d.decision === 'accept' && d.time_saved)
    .reduce((acc, d) => acc + d.time_saved, 0)

  return (
    <>
      <div className="audit-title-row">
        <span className="audit-heading">Decision History</span>
        {sorted.length > 0 && (
          <span className="audit-count">{sorted.length}</span>
        )}
      </div>

      {/* Total time saved summary */}
      {totalSaved > 0 && (
        <div className="audit-time-saved">
          <span className="audit-time-saved-num">{totalSaved}</span>
          <span className="audit-time-saved-label">minutes saved this session</span>
        </div>
      )}

      {sorted.length === 0 ? (
        <div className="audit-empty">
          <div className="audit-empty-icon">◷</div>
          <div className="audit-empty-text">
            No decisions yet.<br />
            Accepted and rejected proposals will appear here.
          </div>
        </div>
      ) : (
        <div className="audit-timeline">
          {sorted.map((d, i) => (
            <div key={i} className="audit-item">
              <div className={`audit-dot ${d.decision}`} />
              <div className="audit-content">
                <div className="audit-item-title">{d.title}</div>
                <div className="audit-meta-row">
                  <span className={`audit-badge ${d.decision}`}>
                    {d.decision === 'accept' ? 'Accepted' : 'Rejected'}
                  </span>
                  <span className="audit-score">{d.confidence_score}%</span>
                  {d.time_saved && (
                    <span className="audit-time-chip">⚡ {d.time_saved}m saved</span>
                  )}
                  <span className="audit-time">
                    {new Date(d.timestamp).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
                {d.pipeline_ms && (
                  <div className="audit-pipeline-ms">
                    Pipeline: {(d.pipeline_ms / 1000).toFixed(1)}s
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  )
}
