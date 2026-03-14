export function AuditLog({ decisions }) {
  const sorted = [...decisions].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))

  if (sorted.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="text-base font-semibold text-gray-900 mb-2">Decision History</h2>
        <p className="text-sm text-gray-500">No decisions yet.</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h2 className="text-base font-semibold text-gray-900 mb-3">Decision History</h2>
      <ul className="space-y-3">
        {sorted.map((d, i) => (
          <li key={i} className="border-b pb-2 last:border-b-0">
            <div className="flex items-start justify-between gap-2 flex-wrap">
              <span className="text-sm font-medium text-gray-900 flex-1">{d.title}</span>
              <span className={`text-xs px-2 py-0.5 rounded font-medium flex-shrink-0 ${d.decision === 'accept' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                {d.decision === 'accept' ? 'Accepted' : 'Rejected'}
              </span>
            </div>
            <div className="flex items-center gap-3 mt-0.5">
              <span className="text-xs text-gray-500">{d.confidence_score}%</span>
              <span className="text-xs text-gray-400">{new Date(d.timestamp).toLocaleString()}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
