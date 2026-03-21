/**
 * StakeholderList
 * Shows the affected stakeholders from the proposal alert.
 */
export function StakeholderList({ stakeholders }) {
  if (!stakeholders || stakeholders.length === 0) return null

  const ROLE_ICONS = {
    'Project Manager':      '◈',
    'Lead Architect':       '⬡',
    'Structural Engineer':  '▲',
    'Procurement Officer':  '◷',
    'Owner Representative': '●',
    'Site Superintendent':  '■',
  }

  return (
    <div className="stakeholder-wrap">
      <div className="stakeholder-title">Affected Stakeholders</div>
      <div className="stakeholder-list">
        {stakeholders.map((name, i) => (
          <span key={i} className="stakeholder-chip">
            <span className="stakeholder-icon">{ROLE_ICONS[name] ?? '○'}</span>
            {name}
          </span>
        ))}
      </div>
    </div>
  )
}
