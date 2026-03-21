import { useState } from 'react'

const ACTION_META = {
  email:    { icon: '✉', label: 'Email',    cls: 'email'    },
  task:     { icon: '◈', label: 'Task',     cls: 'task'     },
  calendar: { icon: '◷', label: 'Calendar', cls: 'calendar' },
  drawing:  { icon: '⬡', label: 'Drawing',  cls: 'drawing'  },
}

function ActionChip({ action }) {
  const [expanded, setExpanded] = useState(false)
  const meta = ACTION_META[action.action_type] ?? { icon: '○', label: action.action_type, cls: 'task' }

  const recipient = action.recipient || action.assignee || null
  const priority = action.priority || null

  return (
    <button
      className={`action-chip ${expanded ? 'expanded' : ''}`}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="action-chip-header">
        <div className={`action-icon ${meta.cls}`}>{meta.icon}</div>
        <div className="action-info">
          <div className="action-type">
            {meta.label}
            {recipient && <span className="action-recipient"> — {recipient}</span>}
          </div>
          <div className={`action-desc ${expanded ? 'expanded' : ''}`}>
            {action.description || '—'}
          </div>
        </div>
        <div className={`action-expand-icon ${expanded ? 'expanded' : ''}`}>›</div>
      </div>
      {expanded && (
        <div className="action-details">
          {priority && (
            <span className={`action-priority ${priority}`}>{priority} priority</span>
          )}
          {recipient && (
            <div className="action-detail-row">
              <span className="action-detail-label">{action.assignee ? 'Assignee' : 'To'}:</span>
              <span className="action-detail-value">{recipient}</span>
            </div>
          )}
        </div>
      )}
    </button>
  )
}

export function ActionPreview({ actions }) {
  if (!actions || actions.length === 0) return null
  return (
    <div className="actions-row">
      {actions.map((action, i) => (
        <ActionChip key={i} action={action} />
      ))}
    </div>
  )
}
