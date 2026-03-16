import { useProposals } from '../hooks/useProposals.js'
import { useActions } from '../hooks/useActions.js'
import { ProposalCard } from './ProposalCard.jsx'

export function ProposalFeed({ onDecided }) {
  const { proposals, setProposals } = useProposals()
  const { submitDecision, decisionState } = useActions()

  function handleRemove(id) {
    setProposals((prev) => prev.filter((p) => p.id !== id))
  }

  return (
    <>
      <div className="section-header">
        <span className="section-title">Active Proposals</span>
        {proposals.length > 0 && (
          <span className="section-count">{proposals.length}</span>
        )}
      </div>

      {proposals.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">◈</div>
          <div className="empty-title">No active proposals</div>
          <div className="empty-sub">
            Waiting for AI analysis to generate proposals.<br />
            They will appear here in real-time.
          </div>
          <div className="scanning">
            <span /><span /><span />
          </div>
        </div>
      ) : (
        proposals.map((proposal) => (
          <ProposalCard
            key={proposal.id}
            proposal={proposal}
            submitDecision={submitDecision}
            decisionStateEntry={decisionState.get(proposal.id)}
            onRemove={handleRemove}
            onDecided={onDecided}
          />
        ))
      )}
    </>
  )
}
