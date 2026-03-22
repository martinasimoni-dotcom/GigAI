import { useState } from 'react'
import {
  FileText, Mail, CheckCircle, XCircle, Loader2,
  ChevronDown, ChevronUp, AlertTriangle, Lightbulb,
  Clock, MailCheck,
} from 'lucide-react'
import ConfidenceBadge from './ConfidenceBadge'
import MaterialComparison from './MaterialComparison'
import CostBreakdown from './CostBreakdown'

export default function ProposalCard({
  proposal,
  onCreateRfi,
  onSendEmail,
  onApprove,
  onReject,
  isCreatingRfi,
  isSendingEmail,
  isApproving,
  isRejecting,
}) {
  const [showRisks, setShowRisks] = useState(false)
  const [showRejectInput, setShowRejectInput] = useState(false)
  const [rejectReason, setRejectReason] = useState('')

  const pd = proposal.proposal_data || {}
  const risks       = pd.risks || []
  const justification = pd.justification || proposal.summary || ''
  const recommendation = pd.recommendation || 'review'

  const isAnyLoading = isCreatingRfi || isSendingEmail || isApproving || isRejecting

  const timeAgo = getTimeAgo(proposal.created_at)

  function handleRejectClick() {
    if (!showRejectInput) { setShowRejectInput(true); return }
    onReject(rejectReason)
    setShowRejectInput(false)
    setRejectReason('')
  }

  return (
    <article className="proposal-card bg-white rounded-2xl shadow-card overflow-hidden animate-slide-up">

      {/* ── Card header ───────────────────────────────────────────────────── */}
      <div className="px-5 pt-4 pb-3 border-b border-gray-50">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-bold text-gray-900 leading-snug">{proposal.title}</h3>
            <div className="flex items-center gap-2 mt-1">
              {proposal.source_rfi_id && (
                <span className="text-xs text-gray-400 font-mono bg-gray-50 px-1.5 py-0.5 rounded">
                  RFI {proposal.source_rfi_id.slice(0, 8)}…
                </span>
              )}
              {timeAgo && (
                <span className="flex items-center gap-1 text-xs text-gray-400">
                  <Clock className="w-3 h-3" />
                  {timeAgo}
                </span>
              )}
            </div>
          </div>
          <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
            <ConfidenceBadge confidence={proposal.confidence} />
            <RecommendationPill recommendation={recommendation} />
          </div>
        </div>
      </div>

      {/* ── Card body ─────────────────────────────────────────────────────── */}
      <div className="px-5 py-4 space-y-4">

        {/* Material comparison */}
        <MaterialComparison
          proposalData={pd}
          extracted={proposal.extracted}
        />

        {/* Cost breakdown */}
        <CostBreakdown
          proposalData={pd}
          totalCost={proposal.cost}
        />

        {/* AI Analysis */}
        {justification && (
          <div className="flex gap-2.5 bg-brand-50 rounded-xl p-3">
            <Lightbulb className="w-4 h-4 text-brand-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-brand-700 leading-relaxed">{justification}</p>
          </div>
        )}

        {/* Risks (collapsible) */}
        {risks.length > 0 && (
          <div className="rounded-xl border border-warning-100 overflow-hidden">
            <button
              onClick={() => setShowRisks(!showRisks)}
              className="w-full flex items-center justify-between px-3 py-2.5 bg-warning-50 text-warning-600 text-xs font-semibold"
            >
              <span className="flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" />
                {risks.length} risk{risks.length > 1 ? 's' : ''} identified
              </span>
              {showRisks ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
            {showRisks && (
              <ul className="px-3 py-2.5 space-y-1 bg-white animate-slide-down">
                {risks.map((r, i) => (
                  <li key={i} className="flex gap-2 text-xs text-gray-600">
                    <span className="text-warning-500 font-bold flex-shrink-0">•</span>
                    {r}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* Assignee + email status */}
        {proposal.assigned_user_email && (
          <div className="flex items-center gap-1.5">
            {proposal.email_sent
              ? <MailCheck className="w-3.5 h-3.5 text-success-500 flex-shrink-0" />
              : <Mail className="w-3.5 h-3.5 text-gray-300 flex-shrink-0" />
            }
            <p className={`text-xs ${proposal.email_sent ? 'text-success-600' : 'text-gray-400'}`}>
              {proposal.email_sent ? 'Email sent to ' : 'Assigned to '}
              <span className="font-medium">{proposal.assigned_user_email}</span>
            </p>
          </div>
        )}
      </div>

      {/* ── Action buttons ────────────────────────────────────────────────── */}
      <div className="px-5 pb-5 space-y-2.5">

        {/* Row 1 */}
        <div className="grid grid-cols-2 gap-2">
          <ActionButton
            icon={FileText}
            label="Create RFI"
            isLoading={isCreatingRfi}
            disabled={isAnyLoading}
            onClick={onCreateRfi}
            variant="outline-brand"
            tooltip="Create new RFI in ACC with proposal details"
          />
          <ActionButton
            icon={proposal.email_sent ? MailCheck : Mail}
            label={proposal.email_sent ? 'Resend Email' : 'Send Email'}
            isLoading={isSendingEmail}
            disabled={isAnyLoading || !proposal.assigned_user_email}
            onClick={onSendEmail}
            variant={proposal.email_sent ? 'outline-success' : 'outline-gray'}
            tooltip={proposal.assigned_user_email ? (proposal.email_sent ? 'Resend proposal email' : 'Email assigned user') : 'No assignee email on this RFI'}
          />
        </div>

        {/* Reject reason input */}
        {showRejectInput && (
          <div className="space-y-2 animate-slide-down">
            <input
              type="text"
              placeholder="Reason for rejection (optional)"
              value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleRejectClick()}
              className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-danger-500/30 focus:border-danger-400 transition-all"
              autoFocus
            />
            <button
              onClick={() => { setShowRejectInput(false); setRejectReason('') }}
              className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
              style={{ minHeight: 'unset', minWidth: 'unset' }}
            >
              Cancel
            </button>
          </div>
        )}

        {/* Row 2: Reject + Accept */}
        <div className="grid grid-cols-5 gap-2">
          <div className="col-span-2">
            <ActionButton
              icon={XCircle}
              label={showRejectInput ? 'Confirm' : 'Reject'}
              isLoading={isRejecting}
              disabled={isAnyLoading}
              onClick={handleRejectClick}
              variant="outline-danger"
              full
            />
          </div>
          <div className="col-span-3">
            <ActionButton
              icon={CheckCircle}
              label="Accept"
              isLoading={isApproving}
              disabled={isAnyLoading}
              onClick={onApprove}
              variant="solid-success"
              full
            />
          </div>
        </div>

      </div>
    </article>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function ActionButton({ icon: Icon, label, isLoading, disabled, onClick, variant, tooltip, full }) {
  const base = `btn-press flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-40 disabled:pointer-events-none ${full ? 'w-full' : 'w-full'}`

  const variants = {
    'outline-brand':   'border border-brand-200 text-brand-600 bg-brand-50 hover:bg-brand-100 hover:border-brand-300 focus:ring-brand-300',
    'outline-gray':    'border border-gray-200  text-gray-600  bg-gray-50  hover:bg-gray-100  focus:ring-gray-300',
    'outline-success': 'border border-success-200 text-success-600 bg-success-50 hover:bg-success-100 hover:border-success-300 focus:ring-success-300',
    'outline-danger':  'border border-danger-200 text-danger-600 bg-danger-50 hover:bg-danger-100 hover:border-danger-300 focus:ring-danger-300',
    'solid-success':   'bg-success-500 text-white hover:bg-success-600 active:bg-success-700 shadow-sm focus:ring-success-300',
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled || isLoading}
      title={tooltip}
      aria-label={tooltip || label}
      className={`${base} ${variants[variant]}`}
    >
      {isLoading
        ? <Loader2 className="w-4 h-4 animate-spin" />
        : <Icon className="w-4 h-4 flex-shrink-0" />
      }
      <span>{label}</span>
    </button>
  )
}

function RecommendationPill({ recommendation }) {
  const map = {
    approve: { label: 'Approve',  cls: 'bg-success-100 text-success-700' },
    review:  { label: 'Review',   cls: 'bg-warning-100 text-warning-700' },
    reject:  { label: 'Reject',   cls: 'bg-danger-100  text-danger-700'  },
  }
  const { label, cls } = map[recommendation] ?? map.review
  return (
    <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${cls}`}>
      AI: {label}
    </span>
  )
}

function getTimeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins  = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days  = Math.floor(diff / 86400000)
  if (mins < 1)  return 'just now'
  if (mins < 60) return `${mins}m ago`
  if (hours < 24) return `${hours}h ago`
  return `${days}d ago`
}
