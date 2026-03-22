export default function ConfidenceBadge({ confidence }) {
  const pct = Math.round((confidence || 0) * 100)

  let bg, text, label
  if (pct >= 80) {
    bg = 'bg-success-100 text-success-600'
    label = 'High'
  } else if (pct >= 60) {
    bg = 'bg-warning-100 text-warning-600'
    label = 'Medium'
  } else {
    bg = 'bg-danger-100 text-danger-600'
    label = 'Low'
  }

  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${bg}`}>
      <span className="text-sm font-bold">{pct}%</span>
      <span className="opacity-75">{label}</span>
    </span>
  )
}
