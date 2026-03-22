import { Clock, CheckCircle, XCircle } from 'lucide-react'

const STATS = [
  {
    key: 'pending',
    label: 'Pending',
    icon: Clock,
    bg:   'bg-brand-50',
    ring: 'ring-brand-100',
    icon_bg: 'bg-brand-100',
    icon_color: 'text-brand-500',
    value_color: 'text-brand-600',
  },
  {
    key: 'approved',
    label: 'Approved',
    icon: CheckCircle,
    bg:   'bg-success-50',
    ring: 'ring-success-100',
    icon_bg: 'bg-success-100',
    icon_color: 'text-success-500',
    value_color: 'text-success-600',
  },
  {
    key: 'rejected',
    label: 'Rejected',
    icon: XCircle,
    bg:   'bg-gray-50',
    ring: 'ring-gray-100',
    icon_bg: 'bg-gray-100',
    icon_color: 'text-gray-400',
    value_color: 'text-gray-500',
  },
]

export default function StatsOverview({ stats, pendingCount }) {
  return (
    <div className="grid grid-cols-3 gap-3">
      {STATS.map(({ key, label, icon: Icon, bg, ring, icon_bg, icon_color, value_color }) => {
        const value = stats?.[key] ?? (key === 'pending' ? pendingCount : '—')
        return (
          <div
            key={key}
            className={`${bg} ring-1 ${ring} rounded-2xl p-3 flex flex-col gap-2 animate-scale-in`}
          >
            <div className={`w-8 h-8 ${icon_bg} rounded-xl flex items-center justify-center`}>
              <Icon className={`w-4 h-4 ${icon_color}`} />
            </div>
            <div>
              <p className={`text-2xl font-bold tracking-tight ${value_color}`}>{value}</p>
              <p className="text-xs text-gray-500 font-medium">{label}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
