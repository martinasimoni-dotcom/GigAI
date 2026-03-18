import { useState } from 'react'
import { ConfidenceIndicator } from './ConfidenceIndicator.jsx'
import { ConfidenceBreakdown } from './ConfidenceBreakdown.jsx'
import { StakeholderList } from './StakeholderList.jsx'
import { ActionPreview } from './ActionPreview.jsx'
import { DecisionPanel } from './DecisionPanel.jsx'

const REC_KEY = {
  'accept':          'accept',
  'Accept':          'accept',
  'review':          'review',
  'Requires Review': 'review',
  'reject':          'reject',
  'Reject':          'reject',
}

export function ProposalCard({ proposal, submitDecision, decisionStateEntry, onRemove, onDecided }) {
  const [showReject, setShowReject]   = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const loading  = decisionStateEntry?.loading
  const decided  = decisionStateEntry?.decided
  const disabled = loading || decided

  const recKey     = REC_KEY[proposal.recommendation] ?? 'review'
  const stripeClass = decided ? 'decided' : recKey

  const timeSaved = proposal.time_saved_minutes ?? 45   // from backend (slide 33 baseline)

  async function handleAccept() {
    await submitDecision(proposal.id, 'accept', null)
    onDecided({
      proposalId:       proposal.id,
      title:            proposal.alert?.title ?? 'Untitled',
      decision:         'accept',
      confidence_score: proposal.confidence_score,
      timestamp:        new Date().toISOString(),
      time_saved:       timeSaved,
      pipeline_ms:      proposal.pipeline_ms,
    })
  }

  async function handleRejectSubmit() {
    await submitDecision(proposal.id, 'reject', rejectReason)
    onDecided({
      proposalId:       proposal.id,
      title:            proposal.alert?.title ?? 'Untitled',
      decision:         'reject',
      confidence_score: proposal.confidence_score,
      timestamp:        new Date().toISOString(),
    })
    onRemove(proposal.id)
  }

  return (
    <div className="proposal-card">
      <div className={`card-stripe ${stripeClass}`} />
      <div className="card-body">

        {/* Header */}
        <div className="card-header">
          <h2 className="card-title">{proposal.alert?.title ?? 'Untitled Proposal'}</h2>
          <div className="card-header-right">
            <ConfidenceIndicator score={proposal.confidence_score ?? 0} />
            <span className={`rec-badge ${recKey}`}>{proposal.recommendation}</span>
          </div>
        </div>

        {/* Summary */}
        <p className="card-summary">{proposal.alert?.summary ?? ''}</p>

        {/* Stakeholders */}
        <StakeholderList stakeholders={proposal.alert?.stakeholders} />

        {/* Actions */}
        <ActionPreview actions={proposal.actions ?? []} />

        {/* Confidence breakdown */}
        <ConfidenceBreakdown breakdown={proposal.confidence_breakdown} />

        {/* Triggered rules */}
        {proposal.triggered_rules?.length > 0 && (
          <div className="rules-row">
            {proposal.triggered_rules.map((r) => (
              <span key={r} className="rule-tag">{r}</span>
            ))}
          </div>
        )}

        {/* Decision area */}
        {decided ? (
          <>
            <DecisionPanel
              actionResults={decisionStateEntry.actionResults}
              decision={decisionStateEntry.decision}
            />
            {decisionStateEntry.decision === 'accept' && (
              <div className="time-saved-banner">
                <span className="time-saved-icon">⚡</span>
                <span>
                  <strong>{timeSaved} minutes saved</strong>
                  {' '}— GigAI handled what would have taken a PM manually.
                </span>
              </div>
            )}
          </>
        ) : (
          <>
            {!showReject ? (
              <div className="decision-row">
                <button className="btn-accept" onClick={handleAccept} disabled={disabled}>
                  {loading
                    ? <span className="spinner" style={{ color: 'var(--success)' }} />
                    : '✓'}
                  {!loading && 'Accept'}
                </button>
                <button className="btn-reject" onClick={() => setShowReject(true)} disabled={disabled}>
                  ✕ Reject
                </button>
              </div>
            ) : (
              <div className="reject-form">
                <div className="reject-label">Reason for rejection</div>
                <textarea
                  className="reject-textarea"
                  rows={3}
                  placeholder="Describe why this proposal is being rejected..."
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                />
                <div className="reject-actions">
                  <button
                    className="btn-submit-reject"
                    onClick={handleRejectSubmit}
                    disabled={loading}
                  >
                    {loading
                      ? <span className="spinner" style={{ color: 'var(--danger)' }} />
                      : 'Submit Rejection'}
                  </button>
                  <button className="btn-cancel" onClick={() => setShowReject(false)}>
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
