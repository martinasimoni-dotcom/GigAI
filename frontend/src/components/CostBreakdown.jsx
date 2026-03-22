import { useState } from 'react'
import { ChevronDown, ChevronUp, TrendingUp, TrendingDown, Minus } from 'lucide-react'

export default function CostBreakdown({ proposalData, totalCost }) {
  const [open, setOpen] = useState(false)
  const ca = proposalData?.cost_analysis || {}

  const oldUnit   = ca.old_unit_cost_eur
  const newUnit   = ca.new_unit_cost_eur
  const qty       = ca.quantity
  const delta     = ca.total_delta_eur ?? totalCost ?? 0
  const breakdown = ca.breakdown || []

  const absDelta  = Math.abs(delta)
  const isIncrease = delta > 0
  const isNeutral  = delta === 0

  const oldTotal = oldUnit && qty ? oldUnit * qty : null
  const newTotal = newUnit && qty ? newUnit * qty : null

  if (!delta && !oldTotal && !newTotal && breakdown.length === 0) return null

  return (
    <div className="rounded-xl border border-gray-100 overflow-hidden">
      {/* Summary row */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50">
        <span className="text-sm font-medium text-gray-600">Cost Impact</span>
        <div className="flex items-center gap-2">
          {oldTotal && (
            <span className="text-sm text-gray-400 line-through">€{fmt(oldTotal)}</span>
          )}
          {oldTotal && newTotal && (
            <span className="text-gray-300">→</span>
          )}
          {newTotal && (
            <span className="text-sm font-bold text-gray-900">€{fmt(newTotal)}</span>
          )}
          <DeltaBadge delta={delta} />
        </div>
      </div>

      {/* Per-unit row */}
      {oldUnit && newUnit && (
        <div className="flex gap-4 px-4 py-2.5 border-t border-gray-100 bg-white">
          <UnitCost label="Current" value={oldUnit} old />
          <UnitCost label="Proposed" value={newUnit} />
          {qty && (
            <div className="ml-auto text-xs text-gray-400 self-center">
              × {qty} units
            </div>
          )}
        </div>
      )}

      {/* Breakdown toggle */}
      {breakdown.length > 0 && (
        <>
          <button
            onClick={() => setOpen(!open)}
            className="w-full flex items-center justify-between px-4 py-2 text-xs font-medium text-gray-500 hover:text-gray-700 border-t border-gray-100 bg-white transition-colors"
          >
            <span>Line items ({breakdown.length})</span>
            {open ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>

          {open && (
            <div className="border-t border-gray-100 animate-slide-down">
              {breakdown.map((b, i) => (
                <div
                  key={i}
                  className="flex justify-between items-center px-4 py-2 text-xs bg-white border-t border-gray-50 first:border-0"
                >
                  <span className="text-gray-600">{b.item}</span>
                  <span className="font-medium text-gray-900">€{fmt(b.cost_eur || 0)}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

function DeltaBadge({ delta }) {
  const abs = Math.abs(delta)
  if (!abs) return null

  if (delta > 0)
    return (
      <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-xs font-semibold bg-warning-100 text-warning-600">
        <TrendingUp className="w-3 h-3" />+€{fmt(abs)}
      </span>
    )
  return (
    <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-xs font-semibold bg-success-100 text-success-600">
      <TrendingDown className="w-3 h-3" />−€{fmt(abs)}
    </span>
  )
}

function UnitCost({ label, value, old: isOld }) {
  return (
    <div>
      <p className={`text-[10px] font-semibold uppercase tracking-wider mb-0.5 ${isOld ? 'text-gray-400' : 'text-brand-500'}`}>{label}</p>
      <p className={`text-sm font-semibold ${isOld ? 'text-gray-400 line-through' : 'text-gray-900'}`}>€{fmt(value)}/u</p>
    </div>
  )
}

function fmt(n) {
  return Number(n).toLocaleString('en-EU')
}
