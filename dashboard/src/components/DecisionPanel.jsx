export function DecisionPanel({ actionResults, decision }) {
  const STATUS_ICON = { success: '✓', failed: '✗' }
  return (
    <div className="mt-3 border-t pt-3">
      <p className="text-sm font-semibold text-gray-700 mb-1">
        {decision === 'accept' ? 'Execution Status' : 'Rejected'}
      </p>
      {actionResults && (
        <ul className="space-y-1">
          {actionResults.map((r, i) => (
            <li key={i} className={`flex items-center gap-2 text-sm ${r.status === 'success' ? 'text-green-700' : 'text-red-700'}`}>
              <span>{STATUS_ICON[r.status]}</span>
              <span className="capitalize">{r.action_type}</span>
              <span className="text-gray-600">— {r.message}</span>
              {r.error && <span className="text-red-500">({r.error})</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
