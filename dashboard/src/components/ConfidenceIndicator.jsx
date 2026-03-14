export function ConfidenceIndicator({ score }) {
  const colorClass =
    score >= 80 ? 'bg-green-500' : score >= 50 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-white text-sm font-semibold ${colorClass}`}
      aria-label={`Confidence: ${score}%`}
    >
      {score}%
    </span>
  )
}
