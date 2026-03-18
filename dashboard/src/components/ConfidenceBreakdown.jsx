/**
 * ConfidenceBreakdown
 *
 * Shows the 4-factor confidence scoring breakdown from the presentation (slide 24):
 *   Data Clarity    30%
 *   Historical Match 25%
 *   Cost Acceptable  25%
 *   No Red Flags     20%
 */
export function ConfidenceBreakdown({ breakdown }) {
  if (!breakdown) return null

  const factors = [
    { key: 'data_clarity',     color: '#3b82f6' },
    { key: 'historical_match', color: '#8b5cf6' },
    { key: 'cost_acceptable',  color: '#10b981' },
    { key: 'no_red_flags',     color: '#f59e0b' },
  ]

  return (
    <div className="breakdown-wrap">
      <div className="breakdown-title">Confidence Breakdown</div>
      {factors.map(({ key, color }) => {
        const factor = breakdown[key]
        if (!factor) return null
        const pct = Math.min(100, (factor.value / factor.weight) * 100)
        return (
          <div key={key} className="breakdown-row">
            <div className="breakdown-label">
              <span>{factor.label}</span>
              <span className="breakdown-weight">{factor.weight}%</span>
            </div>
            <div className="breakdown-bar-track">
              <div
                className="breakdown-bar-fill"
                style={{ width: `${pct}%`, background: color }}
              />
            </div>
            <span className="breakdown-value" style={{ color }}>
              {factor.value.toFixed(1)}
            </span>
          </div>
        )
      })}
    </div>
  )
}
