const BASE_URL = 'http://localhost:8000'

/**
 * Fetch all proposals from the backend.
 * @returns {Promise<Array>} Array of proposal_response objects
 */
export async function fetchProposals() {
  const response = await fetch(`${BASE_URL}/api/proposals`)
  return response.json()
}

/**
 * Submit an accept or reject decision for a proposal.
 * @param {string} proposalId
 * @param {'accept'|'reject'} decision
 * @param {string|null} reason  Required for reject, null for accept
 * @returns {Promise<object>} Execution result from backend
 */
export async function postDecision(proposalId, decision, reason) {
  const response = await fetch(
    `${BASE_URL}/api/proposals/${proposalId}/decision`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision, reason }),
    }
  )
  return response.json()
}

/**
 * Subscribe to real-time proposal events via SSE.
 * @param {function} onProposal  Called with parsed proposal_response on each event
 * @returns {EventSource}  Caller must call .close() to unsubscribe
 */
export function subscribeToEvents(onProposal) {
  const es = new EventSource(`${BASE_URL}/api/events`)
  es.onmessage = (event) => {
    onProposal(JSON.parse(event.data))
  }
  return es
}
