import { useProposals } from '../hooks/useProposals.js'
import { useActions } from '../hooks/useActions.js'
import { ProposalCard } from './ProposalCard.jsx'

export function ProposalFeed({ onDecided }) {
  const { proposals, setProposals } = useProposals()
  const { submitDecision, decisionState } = useActions()

  function handleRemove(id) {
    setProposals((prev) => prev.filter((p) => p.id !== id))
  }

  if (proposals.length === 0) {
    return <p className="text-gray-500 text-sm mt-4">No active proposals.</p>
  }

  return (
    <div>
      {proposals.map((proposal) => (
        <ProposalCard
          key={proposal.id}
          proposal={proposal}
          submitDecision={submitDecision}
          decisionStateEntry={decisionState.get(proposal.id)}
          onRemove={handleRemove}
          onDecided={onDecided}
        />
      ))}
    </div>
  )
}
