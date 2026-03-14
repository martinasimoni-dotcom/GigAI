import { useState } from 'react'
import { ConfidenceIndicator } from './ConfidenceIndicator.jsx'
import { ActionPreview } from './ActionPreview.jsx'
import { DecisionPanel } from './DecisionPanel.jsx'

const REC_COLORS = {
  Accept: 'bg-green-100 text-green-800',
  'Requires Review': 'bg-yellow-100 text-yellow-800',
  Reject: 'bg-red-100 text-red-800',
}

export function ProposalCard({ proposal, submitDecision, decisionStateEntry, onRemove, onDecided }) {
  const [showReject, setShowReject] = useState(false)
  const [rejectReason, setRejectReason] = useState('')

  const loading = decisionStateEntry?.loading
  const decided = decisionStateEntry?.decided
  const buttonsDisabled = loading || decided

  async function handleAccept() {
    await submitDecision(proposal.id, 'accept', null)
    onDecided({ proposalId: proposal.id, title: proposal.alert.title, decision: 'accept', confidence_score: proposal.confidence_score, timestamp: new Date().toISOString() })
  }

  async function handleRejectSubmit() {
    await submitDecision(proposal.id, 'reject', rejectReason)
    onDecided({ proposalId: proposal.id, title: proposal.alert.title, decision: 'reject', confidence_score: proposal.confidence_score, timestamp: new Date().toISOString() })
    onRemove(proposal.id)
  }

  return (
    <div className="bg-white rounded-lg shadow p-4 mb-4 w-full">
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <h2 className="text-base font-semibold text-gray-900 flex-1">{proposal.alert.title}</h2>
        <div className="flex items-center gap-2 flex-shrink-0">
          <ConfidenceIndicator score={proposal.confidence_score} />
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${REC_COLORS[proposal.recommendation] ?? 'bg-gray-100 text-gray-700'}`}>
            {proposal.recommendation}
          </span>
        </div>
      </div>
      <p className="mt-1 text-sm text-gray-600">{proposal.alert.summary}</p>
      <ActionPreview actions={proposal.actions} />

      {decided ? (
        <DecisionPanel actionResults={decisionStateEntry.actionResults} decision={decisionStateEntry.decision} />
      ) : (
        <div className="mt-3 flex flex-col gap-2">
          {!showReject && (
            <div className="flex gap-2">
              <button
                onClick={handleAccept}
                disabled={buttonsDisabled}
                className="flex-1 py-2 px-3 rounded bg-green-600 text-white text-sm font-medium disabled:opacity-50 hover:bg-green-700"
              >
                {loading ? '...' : 'Accept'}
              </button>
              <button
                onClick={() => setShowReject(true)}
                disabled={buttonsDisabled}
                className="flex-1 py-2 px-3 rounded bg-red-600 text-white text-sm font-medium disabled:opacity-50 hover:bg-red-700"
              >
                Reject
              </button>
            </div>
          )}
          {showReject && (
            <div className="flex flex-col gap-2">
              <textarea
                className="w-full border rounded p-2 text-sm"
                rows={3}
                placeholder="Reason for rejection..."
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
              />
              <div className="flex gap-2">
                <button
                  onClick={handleRejectSubmit}
                  disabled={loading}
                  className="flex-1 py-2 px-3 rounded bg-red-600 text-white text-sm font-medium disabled:opacity-50"
                >
                  {loading ? '...' : 'Submit Rejection'}
                </button>
                <button
                  onClick={() => setShowReject(false)}
                  className="py-2 px-3 rounded bg-gray-200 text-gray-700 text-sm"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
