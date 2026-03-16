const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function fetchProposals() {
  try {
    const res = await fetch(`${BASE}/api/proposals`)
    if (!res.ok) return []
    return res.json()
  } catch {
    return []
  }
}

export async function postDecision(proposalId, decision, reason) {
  const res = await fetch(`${BASE}/api/proposals/${proposalId}/decision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, reason }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export function subscribeToEvents(onProposal) {
  const es = new EventSource(`${BASE}/api/events`)
  es.onmessage = (event) => {
    try { onProposal(JSON.parse(event.data)) } catch {}
  }
  return es
}
