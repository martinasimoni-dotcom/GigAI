export function ConfidenceIndicator({ score }) {
  const radius = 26
  const stroke = 3.5
  const circumference = 2 * Math.PI * radius
  const dashoffset = circumference - (score / 100) * circumference

  const color =
    score >= 75 ? 'var(--success)' :
    score >= 45 ? 'var(--warning)' :
    'var(--danger)'

  const glow =
    score >= 75 ? 'var(--success-glow)' :
    score >= 45 ? 'rgba(245,158,11,0.3)' :
    'var(--danger-glow)'

  return (
    <div className="confidence-gauge" aria-label={`Confidence: ${score}%`}>
      <svg width="68" height="68" viewBox="0 0 68 68">
        <defs>
          <filter id={`glow-${score}`} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        {/* Background track */}
        <circle
          cx="34" cy="34" r={radius}
          className="conf-track"
          strokeWidth={stroke}
        />
        {/* Filled arc */}
        <circle
          cx="34" cy="34" r={radius}
          className="conf-fill"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={dashoffset}
          filter={`url(#glow-${score})`}
          style={{ filter: `drop-shadow(0 0 4px ${glow})` }}
        />
      </svg>
      <div className="conf-value">
        <span className="conf-number" style={{ color }}>{score}</span>
        <span className="conf-pct">%</span>
      </div>
    </div>
  )
}
