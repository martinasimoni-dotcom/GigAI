const ACTION_LABELS = {
  email: 'Email',
  task: 'Task',
  calendar: 'Calendar',
  drawing: 'Drawing',
}

export function ActionPreview({ actions }) {
  return (
    <ul className="mt-2 space-y-1">
      {actions.map((action, i) => (
        <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
          <span className="font-medium text-gray-900 min-w-[60px]">
            {ACTION_LABELS[action.action_type] ?? action.action_type}
          </span>
          <span>{action.description}</span>
        </li>
      ))}
    </ul>
  )
}
