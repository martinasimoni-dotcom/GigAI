import { useEffect, useState } from 'react'
import { CheckCircle, XCircle, Info, X } from 'lucide-react'

// ── Toast item ────────────────────────────────────────────────────────────────
function ToastItem({ toast, onRemove }) {
  const [leaving, setLeaving] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => {
      setLeaving(true)
      setTimeout(() => onRemove(toast.id), 250)
    }, toast.duration ?? 4000)
    return () => clearTimeout(t)
  }, [toast.id, toast.duration, onRemove])

  const styles = {
    success: { icon: CheckCircle, bg: 'bg-success-500', ring: '' },
    error:   { icon: XCircle,     bg: 'bg-danger-500',  ring: '' },
    info:    { icon: Info,         bg: 'bg-brand-500',   ring: '' },
  }
  const { icon: Icon, bg } = styles[toast.type] ?? styles.info

  return (
    <div
      className={`flex items-start gap-3 px-4 py-3 bg-white rounded-2xl shadow-toast border border-gray-100 min-w-[260px] max-w-xs ${leaving ? 'animate-toast-out' : 'animate-toast-in'}`}
    >
      <div className={`w-7 h-7 ${bg} rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5`}>
        <Icon className="w-3.5 h-3.5 text-white" />
      </div>
      <p className="text-sm font-medium text-gray-800 leading-snug flex-1 pt-0.5">{toast.message}</p>
      <button
        onClick={() => { setLeaving(true); setTimeout(() => onRemove(toast.id), 250) }}
        className="text-gray-400 hover:text-gray-600 transition-colors mt-0.5 flex-shrink-0"
        aria-label="Dismiss"
        style={{ minHeight: 'unset', minWidth: 'unset' }}
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}

// ── Toast container ───────────────────────────────────────────────────────────
export default function ToastContainer({ toasts, onRemove }) {
  return (
    <div
      className="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none"
      aria-live="polite"
    >
      {toasts.map(t => (
        <div key={t.id} className="pointer-events-auto">
          <ToastItem toast={t} onRemove={onRemove} />
        </div>
      ))}
    </div>
  )
}
