export function Sidebar({ activeTab, onTabChange }) {
  const tabs = [
    { id: 'inbox',     label: 'Inbox',     icon: '✉' },
    { id: 'proposals', label: 'Proposals', icon: '◈' },
    { id: 'projects',  label: 'Projects',  icon: '▦' },
    { id: 'employees', label: 'Team',      icon: '◉' },
    { id: 'schedule',  label: 'Schedule',  icon: '▸' },
  ]

  return (
    <nav className="sidebar">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          className={`sidebar-tab ${activeTab === tab.id ? 'active' : ''}`}
          onClick={() => onTabChange(tab.id)}
        >
          <span className="sidebar-icon">{tab.icon}</span>
          <span className="sidebar-label">{tab.label}</span>
        </button>
      ))}
    </nav>
  )
}
