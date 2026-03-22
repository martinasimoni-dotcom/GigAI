import { ArrowRight, Package } from 'lucide-react'

export default function MaterialComparison({ proposalData, extracted }) {
  const mc = proposalData?.material_change || {}
  const from = mc.from || extracted?.material_from || ''
  const to   = mc.to   || extracted?.material_to   || ''
  const qty  = mc.quantity || extracted?.quantity || 0
  const unit = mc.unit || 'units'
  const areas = mc.affected_areas || extracted?.location || ''
  const elementIds = extracted?.element_ids || []

  if (!from && !to) return null

  return (
    <div className="space-y-2">
      {/* From → To */}
      <div className="flex items-stretch gap-2">
        <MaterialBox label="Current" value={from} variant="old" />
        <div className="flex items-center justify-center px-1">
          <div className="flex flex-col items-center gap-0.5">
            <ArrowRight className="w-4 h-4 text-gray-400" />
          </div>
        </div>
        <MaterialBox label="Proposed" value={to} variant="new" />
      </div>

      {/* Tags */}
      {(qty > 0 || areas || elementIds.length > 0) && (
        <div className="flex flex-wrap gap-1.5">
          {qty > 0 && (
            <Tag icon={<Package className="w-3 h-3" />}>
              {qty} {unit}
            </Tag>
          )}
          {areas && <Tag>{areas}</Tag>}
          {elementIds.slice(0, 4).map((id, i) => (
            <Tag key={i} mono>{id}</Tag>
          ))}
          {elementIds.length > 4 && (
            <Tag>+{elementIds.length - 4} more</Tag>
          )}
        </div>
      )}
    </div>
  )
}

function MaterialBox({ label, value, variant }) {
  const isNew = variant === 'new'
  return (
    <div className={`flex-1 rounded-xl px-3 py-2.5 ${isNew ? 'bg-brand-50 border border-brand-100' : 'bg-gray-50 border border-gray-100'}`}>
      <p className={`text-[10px] font-semibold uppercase tracking-wider mb-0.5 ${isNew ? 'text-brand-500' : 'text-gray-400'}`}>
        {label}
      </p>
      <p className={`text-sm font-semibold leading-snug ${isNew ? 'text-brand-700' : 'text-gray-500 line-through decoration-gray-400'}`}>
        {value || '—'}
      </p>
    </div>
  )
}

function Tag({ children, icon, mono }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 text-gray-600 rounded-md text-xs ${mono ? 'font-mono' : 'font-medium'}`}>
      {icon}
      {children}
    </span>
  )
}
