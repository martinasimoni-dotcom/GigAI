import { useState } from 'react'
import { postDecision } from '../api.js'

export function useActions() {
  const [decisionState, setDecisionState] = useState(new Map())

  async function submitDecision(proposalId, decision, reason) {
    setDecisionState((prev) => new Map(prev).set(proposalId, { loading: true }))
    try {
      const result = await postDecision(proposalId, decision, reason)
      setDecisionState((prev) =>
        new Map(prev).set(proposalId, {
          loading: false,
          decided: true,
          decision,
          actionResults: result.results,
        })
      )
    } catch (err) {
      setDecisionState((prev) =>
        new Map(prev).set(proposalId, {
          loading: false,
          error: err.message,
        })
      )
    }
  }

  return { submitDecision, decisionState }
}
