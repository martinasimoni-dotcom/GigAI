export function AuditLog({ decisions }) {
  const sorted = [...decisions].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))

  return (
    <>
      <div className="audit-title-row">
        <span className="audit-heading">Decision History</span>
        {sorted.length > 0 && (
          <span className="audit-count">{sorted.length}</span>
        )}
      </div>

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
                  <span className="audit-time">
                    {new Date(d.timestamp).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  )
}
