export function DecisionPanel({ actionResults, decision }) {
  const isAccepted = decision === 'accept'

  return (
    <div className="decision-result">
      <div className={`result-header ${isAccepted ? 'accepted' : 'rejected'}`}>
        {isAccepted ? (
          <>
            <span>●</span>
            EXECUTION STATUS
          </>
        ) : (
          <>
            <span>✕</span>
            PROPOSAL REJECTED
          </>
        )}
      </div>

      {actionResults && actionResults.length > 0 && (
        <div className="result-items">
          {actionResults.map((r, i) => (
            <div key={i} className="result-item">
              <span className={`result-dot ${r.status}`} />
              <span className="result-type">{r.action_type}</span>
              <span className="result-msg">{r.message}</span>
              {r.error && <span className="result-err">({r.error})</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
