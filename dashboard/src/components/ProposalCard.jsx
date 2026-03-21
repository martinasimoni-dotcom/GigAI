import { useState } from 'react'
import { ConfidenceIndicator } from './ConfidenceIndicator.jsx'
import { ConfidenceBreakdown } from './ConfidenceBreakdown.jsx'
import { StakeholderList } from './StakeholderList.jsx'
import { DecisionPanel } from './DecisionPanel.jsx'

const REC_KEY = {
  'accept':          'accept',
  'Accept':          'accept',
  'review':          'review',
  'Requires Review': 'review',
  'reject':          'reject',
  'Reject':          'reject',
}

const ACTION_META = {
  email:    { icon: '✉', label: 'Email',    cls: 'email',    verb: 'Send email to' },
  task:     { icon: '◈', label: 'Task',     cls: 'task',     verb: 'Create task for' },
  calendar: { icon: '◷', label: 'Calendar', cls: 'calendar', verb: 'Schedule meeting with' },
  drawing:  { icon: '⬡', label: 'Drawing',  cls: 'drawing',  verb: 'Update drawing' },
}

export function ProposalCard({ proposal, submitDecision, decisionStateEntry, onRemove, onDecided }) {
  const [showReject, setShowReject]   = useState(false)
  const [showEdit, setShowEdit]       = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [editedActions, setEditedActions] = useState(null)
  const loading  = decisionStateEntry?.loading
  const decided  = decisionStateEntry?.decided
  const disabled = loading || decided

  const recKey     = REC_KEY[proposal.recommendation] ?? 'review'
  const stripeClass = decided ? 'decided' : recKey

  const timeSaved = proposal.time_saved_minutes ?? 45

  const actions = editedActions ?? proposal.actions ?? []

  function handleEditAction(idx, field, value) {
    const updated = [...actions]
    updated[idx] = { ...updated[idx], [field]: value }
    setEditedActions(updated)
  }

  function handleRemoveAction(idx) {
    const updated = actions.filter((_, i) => i !== idx)
    setEditedActions(updated)
  }

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

        {/* Actions — with clear descriptions of what happens */}
        {actions.length > 0 && (
          <div className="actions-section">
            <div className="actions-section-header">
              <span className="actions-section-title">
                Actions ({actions.length}) — what will happen when approved
              </span>
              {!decided && !showEdit && (
                <button
                  className="btn-edit-actions"
                  onClick={(e) => { e.stopPropagation(); setShowEdit(true); setEditedActions([...actions]) }}
                >
                  Edit actions
                </button>
              )}
              {showEdit && (
                <button
                  className="btn-edit-actions"
                  onClick={(e) => { e.stopPropagation(); setShowEdit(false) }}
                  style={{ color: 'var(--green)' }}
                >
                  Done editing
                </button>
              )}
            </div>
            <div className="actions-row">
              {actions.map((action, i) => {
                const meta = ACTION_META[action.action_type] ?? { icon: '○', label: action.action_type, cls: 'task', verb: 'Execute' }
                const recipient = action.recipient || action.assignee || ''
                const destination = action.project || action.drawing_number || action.calendar_id || ''

                return (
                  <div key={i} className="action-detail-card">
                    <div className="action-detail-card-header">
                      <div className={`action-icon ${meta.cls}`}>{meta.icon}</div>
                      <div className="action-detail-info">
                        <div className="action-detail-what">
                          {meta.verb} {recipient}
                        </div>
                        {showEdit ? (
                          <textarea
                            className="action-edit-textarea"
                            value={action.description || ''}
                            onChange={(e) => handleEditAction(i, 'description', e.target.value)}
                            rows={2}
                            onClick={(e) => e.stopPropagation()}
                          />
                        ) : (
                          <div className="action-detail-desc">
                            {action.description || action.subject || action.title || '—'}
                          </div>
                        )}
                        {destination && (
                          <div className="action-detail-dest">
                            Destination: {destination}
                          </div>
                        )}
                        {action.priority && (
                          <span className={`action-priority ${action.priority}`}>
                            {action.priority} priority
                          </span>
                        )}
                      </div>
                      {showEdit && (
                        <button
                          className="action-remove-btn"
                          onClick={(e) => { e.stopPropagation(); handleRemoveAction(i) }}
                          title="Remove action"
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Confidence breakdown */}
        <ConfidenceBreakdown
          breakdown={proposal.confidence_breakdown}
          rationale={proposal.alert?.confidence_rationale}
        />

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
          <DecisionPanel
            actionResults={decisionStateEntry.actionResults}
            decision={decisionStateEntry.decision}
          />
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
