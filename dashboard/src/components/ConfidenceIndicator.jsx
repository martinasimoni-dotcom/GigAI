export function ConfidenceIndicator({ score }) {
  const radius = 24
  const stroke = 3
  const circumference = 2 * Math.PI * radius
  const dashoffset = circumference - (score / 100) * circumference

  const color =
    score >= 75 ? 'var(--green)' :
    score >= 45 ? 'var(--orange)' :
    'var(--red)'

  return (
    <div className="confidence-gauge" aria-label={`Confidence: ${score}%`}>
      <svg width="64" height="64" viewBox="0 0 64 64">
        {/* Background track */}
        <circle
          cx="32" cy="32" r={radius}
          className="conf-track"
          strokeWidth={stroke}
        />
        {/* Filled arc */}
        <circle
          cx="32" cy="32" r={radius}
          className="conf-fill"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={dashoffset}
        />
      </svg>
      <div className="conf-value">
        <span className="conf-number" style={{ color }}>{score}</span>
        <span className="conf-pct">%</span>
      </div>
    </div>
  )
}
