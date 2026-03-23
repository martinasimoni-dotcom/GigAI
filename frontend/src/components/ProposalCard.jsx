import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import {
  CheckCircle, XCircle, Loader2, ChevronRight,
  X, AlertTriangle, Lightbulb, Clock, Euro, CalendarDays,
} from 'lucide-react'
import ConfidenceBadge from './ConfidenceBadge'
import MaterialComparison from './MaterialComparison'
import CostBreakdown from './CostBreakdown'

// ── Collapsed card row ─────────────────────────────────────────────────────────
export default function ProposalCard({ proposal, onApprove, onReject, isApproving, isRejecting }) {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!open) return
    const handler = (e) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open])

  const pd             = proposal.proposal_data || {}
  const recommendation = pd.recommendation || 'review'
  const timeAgo        = getTimeAgo(proposal.created_at)
  const cost           = proposal.cost || 0
  const timeline       = pd.timeline_weeks || proposal.timeline_weeks

  return (
    <>
      <article
        className="proposal-card bg-white rounded-xl border border-gray-100 shadow-sm px-4 py-3 flex items-center gap-3 cursor-pointer animate-slide-up"
        onClick={() => setOpen(true)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setOpen(true) }}
        aria-label={`Open proposal: ${proposal.title}`}
      >
        {/* Left: title + meta */}
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-gray-900 truncate leading-snug">
            {proposal.title}
          </h3>
          <div className="flex items-center gap-3 mt-0.5 flex-wrap">
            {cost > 0 && (
              <span className="flex items-center gap-0.5 text-xs text-gray-500">
                <Euro className="w-3 h-3" />
                {Number(cost).toLocaleString('en-EU')}
              </span>
            )}
            {timeline > 0 && (
              <span className="flex items-center gap-0.5 text-xs text-gray-500">
                <CalendarDays className="w-3 h-3" />
                {timeline} wks
              </span>
            )}
            {timeAgo && (
              <span className="flex items-center gap-0.5 text-xs text-gray-400">
                <Clock className="w-3 h-3" />
                {timeAgo}
              </span>
            )}
          </div>
        </div>

        {/* Right: badges + chevron */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <ConfidenceBadge confidence={proposal.confidence} />
          <RecommendationPill recommendation={recommendation} />
          <ChevronRight className="w-4 h-4 text-gray-300" />
        </div>
      </article>

      {/* Modal portal */}
      {open && createPortal(
        <ProposalModal
          proposal={proposal}
          onClose={() => setOpen(false)}
          onApprove={onApprove}
          onReject={onReject}
          isApproving={isApproving}
          isRejecting={isRejecting}
        />,
        document.body
      )}
    </>
  )
}

// ── Modal ──────────────────────────────────────────────────────────────────────
function ProposalModal({ proposal, onClose, onApprove, onReject, isApproving, isRejecting }) {
  const [showRejectInput, setShowRejectInput] = useState(false)
  const [rejectReason, setRejectReason]       = useState('')

  const pd           = proposal.proposal_data || {}
  const risks        = pd.risks || []
  const justification = pd.justification || proposal.summary || ''
  const nextSteps    = pd.next_steps || proposal.next_steps || []
  const directAnswer = pd.direct_answer || proposal.direct_answer || ''
  const recommendation = pd.recommendation || 'review'
  const isAnyLoading = isApproving || isRejecting

  function handleReject() {
    if (!showRejectInput) { setShowRejectInput(true); return }
    onReject(rejectReason)
    setShowRejectInput(false)
    setRejectReason('')
    onClose()
  }

  function handleApprove() {
    onApprove()
    onClose()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in"
      style={{ backgroundColor: 'rgba(0,0,0,0.4)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col animate-scale-in">

        {/* Header */}
        <div className="flex items-start justify-between gap-3 px-6 pt-5 pb-4 border-b border-gray-100 flex-shrink-0">
          <div className="flex-1 min-w-0">
            <h2 className="text-base font-bold text-gray-900 leading-snug">{proposal.title}</h2>
            {directAnswer && (
              <p className="mt-1 text-sm font-semibold text-brand-600">◆ {directAnswer}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors flex-shrink-0"
            aria-label="Close"
            style={{ minHeight: 'unset', minWidth: 'unset' }}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">

          <MaterialComparison proposalData={pd} extracted={proposal.extracted} />

          <CostBreakdown proposalData={pd} totalCost={proposal.cost} />

          {justification && (
            <div>
              <SectionLabel icon={<Lightbulb className="w-3.5 h-3.5" />} label="Justification" />
              <p className="mt-1.5 text-sm text-gray-600 leading-relaxed">{justification}</p>
            </div>
          )}

          {risks.length > 0 && (
            <div>
              <SectionLabel icon={<AlertTriangle className="w-3.5 h-3.5" />} label="Risks" />
              <ul className="mt-1.5 space-y-1">
                {risks.map((r, i) => (
                  <li key={i} className="flex gap-2 text-sm text-gray-600">
                    <span className="text-warning-500 font-bold flex-shrink-0 mt-px">•</span>
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {nextSteps.length > 0 && (
            <div>
              <SectionLabel label="Next Steps" />
              <ol className="mt-1.5 space-y-1 list-decimal list-inside">
                {nextSteps.map((s, i) => (
                  <li key={i} className="text-sm text-gray-600">{s}</li>
                ))}
              </ol>
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="px-6 pb-5 pt-4 border-t border-gray-100 flex-shrink-0 space-y-2.5">

          {showRejectInput && (
            <div className="flex gap-2 animate-slide-down">
              <input
                type="text"
                placeholder="Reason for rejection (optional)"
                value={rejectReason}
                onChange={e => setRejectReason(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleReject()}
                className="flex-1 border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-danger-500/30 focus:border-danger-400 transition-all"
                autoFocus
              />
              <button
                onClick={() => { setShowRejectInput(false); setRejectReason('') }}
                className="text-xs text-gray-400 hover:text-gray-600 px-2 transition-colors"
                style={{ minHeight: 'unset', minWidth: 'unset' }}
              >
                Cancel
              </button>
            </div>
          )}

          <div className="flex items-center gap-2">
            <div className="flex-1">
              <RecommendationPill recommendation={recommendation} />
            </div>
            <button
              onClick={handleReject}
              disabled={isAnyLoading}
              className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl border border-danger-200 text-danger-600 bg-danger-50 hover:bg-danger-100 text-sm font-semibold disabled:opacity-40 transition-colors"
            >
              {isRejecting
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : <XCircle className="w-4 h-4" />
              }
              {showRejectInput ? 'Confirm' : 'Reject'}
            </button>
            <button
              onClick={handleApprove}
              disabled={isAnyLoading}
              className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-brand-600 text-white hover:bg-brand-700 text-sm font-semibold disabled:opacity-40 transition-colors shadow-sm"
            >
              {isApproving
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : <CheckCircle className="w-4 h-4" />
              }
              Accept
            </button>
          </div>

        </div>
      </div>
    </div>
  )
}

// ── Shared sub-components ──────────────────────────────────────────────────────
function SectionLabel({ icon, label }) {
  return (
    <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-400 uppercase tracking-wider">
      {icon}
      {label}
    </div>
  )
}

function RecommendationPill({ recommendation }) {
  const map = {
    approve:                 { label: 'Approve'  },
    approve_with_conditions: { label: 'Approve*' },
    review_required:         { label: 'Review'   },
    review:                  { label: 'Review'   },
    reject:                  { label: 'Reject'   },
  }
  const label = map[recommendation]?.label ?? 'Review'
  return (
    <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
      AI: {label}
    </span>
  )
}

function getTimeAgo(dateStr) {
  if (!dateStr) return ''
  const diff  = Date.now() - new Date(dateStr).getTime()
  const mins  = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days  = Math.floor(diff / 86400000)
  if (mins  <  1) return 'just now'
  if (mins  < 60) return `${mins}m ago`
  if (hours < 24) return `${hours}h ago`
  return `${days}d ago`
}
