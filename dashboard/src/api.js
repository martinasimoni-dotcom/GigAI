const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ---------------------------------------------------------------------------
// Proposals
// ---------------------------------------------------------------------------

export async function fetchProposals() {
  try {
    const res = await fetch(`${BASE}/api/proposals`)
    if (!res.ok) return []
    const data = await res.json()
    return Array.isArray(data) ? data : (data.proposals ?? [])
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

// ---------------------------------------------------------------------------
// Audit & Health
// ---------------------------------------------------------------------------

export async function fetchAuditLog(params = {}) {
  const qs = new URLSearchParams(params).toString()
  try {
    const res = await fetch(`${BASE}/api/audit-log${qs ? '?' + qs : ''}`)
    if (!res.ok) return { runs: [] }
    return res.json()
  } catch {
    return { runs: [] }
  }
}

export async function fetchHealth() {
  try {
    const res = await fetch(`${BASE}/api/health`)
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// SSE
// ---------------------------------------------------------------------------

export function subscribeToEvents(onProposal) {
  const es = new EventSource(`${BASE}/api/events`)
  es.addEventListener('proposal', (event) => {
    try { onProposal(JSON.parse(event.data)) } catch {}
  })
  es.onmessage = (event) => {
    try { onProposal(JSON.parse(event.data)) } catch {}
  }
  return es
}

// ---------------------------------------------------------------------------
// Projects
// ---------------------------------------------------------------------------

export async function fetchProjects(params = {}) {
  const qs = new URLSearchParams(params).toString()
  try {
    const res = await fetch(`${BASE}/api/projects${qs ? '?' + qs : ''}`)
    if (!res.ok) return { projects: [], total: 0 }
    return res.json()
  } catch {
    return { projects: [], total: 0 }
  }
}

export async function fetchProjectStats() {
  try {
    const res = await fetch(`${BASE}/api/projects/stats`)
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export async function fetchProject(projectId) {
  try {
    const res = await fetch(`${BASE}/api/projects/${projectId}`)
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// Employees
// ---------------------------------------------------------------------------

export async function fetchEmployees(params = {}) {
  const qs = new URLSearchParams(params).toString()
  try {
    const res = await fetch(`${BASE}/api/employees${qs ? '?' + qs : ''}`)
    if (!res.ok) return { employees: [], total: 0 }
    return res.json()
  } catch {
    return { employees: [], total: 0 }
  }
}

export async function fetchEmployeeStats() {
  try {
    const res = await fetch(`${BASE}/api/employees/stats`)
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export async function fetchEmployee(employeeId) {
  try {
    const res = await fetch(`${BASE}/api/employees/${employeeId}`)
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// Schedule
// ---------------------------------------------------------------------------

export async function fetchSchedule(projectId, params = {}) {
  const qs = new URLSearchParams(params).toString()
  try {
    const res = await fetch(`${BASE}/api/schedule/${projectId}${qs ? '?' + qs : ''}`)
    if (!res.ok) return { tasks: [] }
    return res.json()
  } catch {
    return { tasks: [] }
  }
}

export async function fetchScheduleAnalysis(projectId) {
  try {
    const res = await fetch(`${BASE}/api/schedule/${projectId}/analysis`)
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// RFIs
// ---------------------------------------------------------------------------

export async function fetchRFIs(params = {}) {
  const qs = new URLSearchParams(params).toString()
  try {
    const res = await fetch(`${BASE}/api/rfis${qs ? '?' + qs : ''}`)
    if (!res.ok) return { rfis: [], total: 0 }
    return res.json()
  } catch {
    return { rfis: [], total: 0 }
  }
}

export async function fetchRFIStats() {
  try {
    const res = await fetch(`${BASE}/api/rfis/stats`)
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export async function draftRFI(rfiId) {
  const res = await fetch(`${BASE}/api/rfis/${rfiId}/draft`, { method: 'POST' })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function editRFI(rfiId, editedText) {
  const res = await fetch(`${BASE}/api/rfis/${rfiId}/edit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ edited_text: editedText }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function sendRFI(rfiId) {
  const res = await fetch(`${BASE}/api/rfis/${rfiId}/send`, { method: 'POST' })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function closeRFI(rfiId) {
  const res = await fetch(`${BASE}/api/rfis/${rfiId}/close`, { method: 'POST' })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

// ---------------------------------------------------------------------------
// Inbox
// ---------------------------------------------------------------------------

export async function fetchInbox(params = {}) {
  const qs = new URLSearchParams(params).toString()
  try {
    const res = await fetch(`${BASE}/api/inbox${qs ? '?' + qs : ''}`)
    if (!res.ok) return { items: [], total: 0 }
    return res.json()
  } catch {
    return { items: [], total: 0 }
  }
}

export async function fetchInboxStats() {
  try {
    const res = await fetch(`${BASE}/api/inbox/stats`)
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export async function markInboxRead(itemId) {
  try {
    const res = await fetch(`${BASE}/api/inbox/${itemId}/read`, { method: 'POST' })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// Learning
// ---------------------------------------------------------------------------

export async function fetchLearningStats() {
  try {
    const res = await fetch(`${BASE}/api/learning/stats`)
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}
