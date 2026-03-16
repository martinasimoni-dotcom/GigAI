const ACTION_META = {
  email:    { icon: '✉', label: 'Email',    cls: 'email'    },
  task:     { icon: '◈', label: 'Task',     cls: 'task'     },
  calendar: { icon: '◷', label: 'Calendar', cls: 'calendar' },
  drawing:  { icon: '⬡', label: 'Drawing',  cls: 'drawing'  },
}

export function ActionPreview({ actions }) {
  if (!actions || actions.length === 0) return null
  return (
    <div className="actions-row">
      {actions.map((action, i) => {
        const meta = ACTION_META[action.action_type] ?? { icon: '○', label: action.action_type, cls: 'task' }
        return (
          <div key={i} className="action-chip">
            <div className={`action-icon ${meta.cls}`}>{meta.icon}</div>
            <div className="action-info">
              <div className="action-type">{meta.label}</div>
              <div className="action-desc" title={action.description}>
                {action.description || '—'}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
