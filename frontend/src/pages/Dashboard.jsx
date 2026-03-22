import { useState, useEffect, useRef, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, RefreshCw, ChevronDown, Zap, Loader2 } from 'lucide-react'
import axios from 'axios'

import StatsOverview    from '../components/StatsOverview'
import ProposalCard     from '../components/ProposalCard'
import EmptyState       from '../components/EmptyState'
import ToastContainer   from '../components/Toast'

const api = axios.create({ baseURL: 'http://localhost:8000/api' })

let toastCounter = 0

// ── Main Dashboard ────────────────────────────────────────────────────────────
export default function Dashboard() {
  const queryClient = useQueryClient()
  const [wsStatus, setWsStatus] = useState('connecting')
  const [toasts, setToasts] = useState([])
  const wsRef = useRef(null)

  const addToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = ++toastCounter
    setToasts(prev => [...prev, { id, message, type, duration }])
  }, [])

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  // WebSocket for real-time updates
  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket('ws://localhost:8000/ws')
      wsRef.current = ws
      ws.onopen  = () => setWsStatus('live')
      ws.onclose = () => { setWsStatus('reconnecting'); setTimeout(connect, 3000) }
      ws.onerror = () => setWsStatus('offline')
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'new_proposal') {
            queryClient.invalidateQueries(['proposals'])
            queryClient.invalidateQueries(['stats'])
            addToast(`New proposal: ${msg.proposal.title}`, 'info', 5000)
          }
        } catch {}
      }
    }
    connect()
    return () => wsRef.current?.close()
  }, [queryClient, addToast])

  // Queries
  const { data: proposals, isLoading, error, refetch } = useQuery({
    queryKey: ['proposals'],
    queryFn: () => api.get('/proposals?status=pending').then(r => r.data),
    refetchInterval: 20000,
  })

  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: () => api.get('/stats').then(r => r.data),
    refetchInterval: 30000,
  })

  // Mutations
  const createRfiMutation = useMutation({
    mutationFn: (id) => api.post(`/proposals/${id}/create-rfi`),
    onSuccess: (data) => {
      addToast(`RFI created in ACC: ${data.data?.rfi_id?.slice(0, 8) ?? 'done'}`, 'success')
    },
    onError: (err) => addToast(err.response?.data?.detail || 'Failed to create RFI', 'error'),
  })

  const sendEmailMutation = useMutation({
    mutationFn: (id) => api.post(`/proposals/${id}/send-email`),
    onSuccess: (data) => addToast(`Email resent to ${data.data?.to || 'assignee'}`, 'success'),
    onError: (err) => addToast(err.response?.data?.detail || 'Failed to send email', 'error'),
  })

  const approveMutation = useMutation({
    mutationFn: (id) => api.post(`/proposals/${id}/approve`),
    onSuccess: () => {
      queryClient.invalidateQueries(['proposals'])
      queryClient.invalidateQueries(['stats'])
      addToast('Proposal accepted — RFI created & email sent', 'success')
    },
    onError: (err) => addToast(err.response?.data?.detail || 'Approval failed', 'error'),
  })

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }) => api.post(`/proposals/${id}/reject`, { reason }),
    onSuccess: () => {
      queryClient.invalidateQueries(['proposals'])
      queryClient.invalidateQueries(['stats'])
      addToast('Proposal rejected', 'info')
    },
    onError: (err) => addToast(err.response?.data?.detail || 'Rejection failed', 'error'),
  })

  const [rfiInput, setRfiInput] = useState('')

  const processRfiMutation = useMutation({
    mutationFn: (rfi_id) => api.post('/process-rfi', { rfi_id }),
    onSuccess: (data) => {
      addToast(`Pipeline started for RFI "${data.data?.title || rfiInput}"`, 'success', 6000)
      setRfiInput('')
      setTimeout(() => {
        queryClient.invalidateQueries(['proposals'])
        queryClient.invalidateQueries(['stats'])
      }, 3000)
    },
    onError: (err) => addToast(err.response?.data?.detail || 'Failed to process RFI', 'error'),
  })

  const pending = proposals || []

  return (
    <div className="min-h-screen bg-[#F0F4FF]">

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">

          {/* Logo */}
          <div className="flex items-center gap-2.5 flex-shrink-0">
            <div className="w-8 h-8 bg-gradient-to-br from-brand-500 to-brand-700 rounded-xl flex items-center justify-center shadow-sm">
              <span className="text-white font-bold text-sm tracking-tight">Gi</span>
            </div>
            <span className="font-bold text-gray-900 text-base tracking-tight">GigAI</span>
          </div>

          {/* Project selector */}
          <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-gray-50 transition-colors group" style={{ minHeight: 'unset', minWidth: 'unset' }}>
            <span className="text-sm font-medium text-gray-700">Sea house</span>
            <ChevronDown className="w-3.5 h-3.5 text-gray-400 group-hover:text-gray-600 transition-colors" />
          </button>

          {/* Right side: connection status */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <WsStatusBadge status={wsStatus} />
            <button
              onClick={() => { refetch(); queryClient.invalidateQueries(['stats']) }}
              className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-50 transition-colors"
              aria-label="Refresh"
              style={{ minHeight: 'unset', minWidth: 'unset' }}
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </header>

      {/* ── Content ─────────────────────────────────────────────────────── */}
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-6 space-y-6">

        {/* Stats */}
        <StatsOverview stats={stats} pendingCount={pending.length} />

        {/* Error */}
        {error && (
          <div className="bg-white rounded-2xl p-4 flex gap-3 items-start shadow-card border border-danger-100 animate-scale-in">
            <div className="w-8 h-8 bg-danger-100 rounded-lg flex items-center justify-center flex-shrink-0">
              <AlertCircle className="w-4 h-4 text-danger-500" />
            </div>
            <div>
              <p className="font-semibold text-gray-900 text-sm">Backend not reachable</p>
              <p className="text-xs text-gray-500 mt-0.5">
                Run: <code className="bg-gray-100 px-1.5 py-0.5 rounded text-gray-700">cd backend && python main.py</code>
              </p>
            </div>
          </div>
        )}

        {/* Manual RFI trigger */}
        <div className="bg-white rounded-2xl shadow-card border border-brand-100 p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-7 h-7 bg-brand-50 rounded-lg flex items-center justify-center flex-shrink-0">
              <Zap className="w-3.5 h-3.5 text-brand-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">Process RFI</p>
              <p className="text-xs text-gray-400">Paste an ACC RFI ID to generate a proposal instantly</p>
            </div>
          </div>
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              if (rfiInput.trim()) processRfiMutation.mutate(rfiInput.trim())
            }}
          >
            <input
              type="text"
              value={rfiInput}
              onChange={(e) => setRfiInput(e.target.value)}
              placeholder="e.g. a1b2c3d4-e5f6-…"
              className="flex-1 text-sm px-3 py-2 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-300 bg-gray-50"
              disabled={processRfiMutation.isPending}
            />
            <button
              type="submit"
              disabled={!rfiInput.trim() || processRfiMutation.isPending}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {processRfiMutation.isPending
                ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Processing…</>
                : <><Zap className="w-3.5 h-3.5" /> Generate</>
              }
            </button>
          </form>
        </div>

        {/* Proposal grid */}
        {isLoading ? (
          <SkeletonGrid />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {pending.length === 0
              ? <EmptyState />
              : pending.map(proposal => (
                  <ProposalCard
                    key={proposal.id}
                    proposal={proposal}
                    onCreateRfi={() => createRfiMutation.mutate(proposal.id)}
                    onSendEmail={() => sendEmailMutation.mutate(proposal.id)}
                    onApprove={() => approveMutation.mutate(proposal.id)}
                    onReject={(reason) => rejectMutation.mutate({ id: proposal.id, reason })}
                    isCreatingRfi={createRfiMutation.isPending && createRfiMutation.variables === proposal.id}
                    isSendingEmail={sendEmailMutation.isPending && sendEmailMutation.variables === proposal.id}
                    isApproving={approveMutation.isPending && approveMutation.variables === proposal.id}
                    isRejecting={rejectMutation.isPending && rejectMutation.variables?.id === proposal.id}
                  />
                ))
            }
          </div>
        )}
      </main>

      {/* Toast notifications */}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function WsStatusBadge({ status }) {
  const map = {
    live:         { dot: 'live-dot',                              label: 'Live',         text: 'text-success-600' },
    connecting:   { dot: 'w-2 h-2 rounded-full bg-warning-500 animate-pulse', label: 'Connecting',   text: 'text-warning-600' },
    reconnecting: { dot: 'w-2 h-2 rounded-full bg-warning-500 animate-pulse', label: 'Reconnecting', text: 'text-warning-600' },
    offline:      { dot: 'w-2 h-2 rounded-full bg-danger-400',   label: 'Offline',      text: 'text-danger-500' },
  }
  const { dot, label, text } = map[status] ?? map.connecting

  return (
    <div className="flex items-center gap-1.5">
      <span className={dot} />
      <span className={`text-xs font-medium ${text}`}>{label}</span>
    </div>
  )
}

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      {[0, 1].map(i => (
        <div key={i} className="bg-white rounded-2xl shadow-card p-5 space-y-4 animate-fade-in">
          <div className="flex justify-between">
            <div className="space-y-2 flex-1">
              <div className="skeleton h-4 w-3/4" />
              <div className="skeleton h-3 w-1/3" />
            </div>
            <div className="skeleton h-6 w-16 rounded-full" />
          </div>
          <div className="flex gap-2">
            <div className="skeleton h-14 flex-1 rounded-xl" />
            <div className="w-8 flex items-center justify-center">
              <div className="skeleton h-3 w-3 rounded-full" />
            </div>
            <div className="skeleton h-14 flex-1 rounded-xl" />
          </div>
          <div className="skeleton h-16 rounded-xl" />
          <div className="grid grid-cols-2 gap-2">
            <div className="skeleton h-10 rounded-xl" />
            <div className="skeleton h-10 rounded-xl" />
          </div>
          <div className="grid grid-cols-5 gap-2">
            <div className="skeleton h-10 rounded-xl col-span-2" />
            <div className="skeleton h-10 rounded-xl col-span-3" />
          </div>
        </div>
      ))}
    </div>
  )
}
