import { useState, useEffect, useRef, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle, Zap, Loader2,
  Clock, CheckCircle, XCircle,
  ChevronDown, Plus,
} from 'lucide-react'
import axios from 'axios'

import ProposalCard   from '../components/ProposalCard'
import EmptyState     from '../components/EmptyState'
import ToastContainer from '../components/Toast'
import LoadingOverlay from '../components/LoadingOverlay'

const api = axios.create({ baseURL: 'http://localhost:8000/api' })

let toastCounter = 0

// ── Main Dashboard ─────────────────────────────────────────────────────────────
export default function Dashboard() {
  const queryClient  = useQueryClient()
  const [toasts, setToasts]         = useState([])
  const [rfiInput, setRfiInput]     = useState('')
  const [dropdownOpen, setDropdown] = useState(false)
  const dropdownRef                 = useRef(null)
  const wsRef                       = useRef(null)

  const addToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = ++toastCounter
    setToasts(prev => [...prev, { id, message, type, duration }])
  }, [])

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  // Close dropdown on outside click or Escape
  useEffect(() => {
    if (!dropdownOpen) return
    function handleClick(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target))
        setDropdown(false)
    }
    function handleKey(e) { if (e.key === 'Escape') setDropdown(false) }
    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleKey)
    }
  }, [dropdownOpen])

  // WebSocket (silent)
  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket('ws://localhost:8000/ws')
      wsRef.current = ws
      ws.onclose = () => setTimeout(connect, 3000)
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
  const { data: proposals, isLoading, error } = useQuery({
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
    <div style={{ minHeight: '100vh', background: 'var(--gray-50)' }}>

      {/* ── Top bar ──────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 top-bar">
        <div style={{ maxWidth: '960px', margin: '0 auto', padding: '0 var(--space-lg)', height: '64px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>

          {/* Left: Logo · GigAI · divider · Row Houses dropdown */}
          <div className="top-bar__left">
            <img src="/logo.png" alt="GIGAI" className="top-bar__logo" />
            <span className="top-bar__brand">GigAI</span>
            <div className="top-bar__divider" />

            {/* Project dropdown */}
            <div style={{ position: 'relative' }} ref={dropdownRef}>
              <button
                className="top-bar__project-selector"
                onClick={() => setDropdown(o => !o)}
                aria-haspopup="true"
                aria-expanded={dropdownOpen}
              >
                <span className="top-bar__project-name">Row Houses</span>
                <ChevronDown className="top-bar__dropdown-icon" style={{ width: 'var(--icon-sm)', height: 'var(--icon-sm)', color: 'rgba(255,255,255,0.8)' }} />
              </button>

              {dropdownOpen && (
                <div className="project-dropdown" role="menu">
                  <button
                    className="dropdown-item"
                    role="menuitem"
                    onClick={() => setDropdown(false)}
                  >
                    <Plus style={{ width: 'var(--icon-md)', height: 'var(--icon-md)', color: 'var(--gray-600)' }} />
                    Aggiungi progetto
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Right: stats */}
          <div className="top-bar__stats">
            <StatItem icon={Clock}       value={pending.length}          />
            <StatItem icon={CheckCircle} value={stats?.approved ?? '—'}  />
            <StatItem icon={XCircle}     value={stats?.rejected ?? '—'}  />
          </div>

        </div>
      </header>

      {/* Loading overlay */}
      {processRfiMutation.isPending && <LoadingOverlay />}

      {/* ── Main content ─────────────────────────────────────────────────── */}
      <main style={{ maxWidth: '960px', margin: '0 auto', padding: 'var(--space-xl) var(--space-lg)', display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }}>

        {/* Error */}
        {error && (
          <div className="bg-white rounded-lg p-4 flex gap-3 items-start border border-red-100 animate-scale-in" style={{ boxShadow: 'var(--shadow-sm)' }}>
            <AlertCircle style={{ width: 16, height: 16, color: '#EF4444', flexShrink: 0, marginTop: 2 }} />
            <div>
              <p style={{ fontWeight: 600, fontSize: 'var(--text-sm)', color: 'var(--gray-900)', margin: 0 }}>Backend not reachable</p>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--gray-600)', marginTop: 4 }}>
                Run: <code style={{ background: 'var(--gray-100)', padding: '1px 6px', borderRadius: 4 }}>cd backend && python main.py</code>
              </p>
            </div>
          </div>
        )}

        {/* Process RFI card */}
        <div className="process-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', marginBottom: 'var(--space-sm)' }}>
            <Zap style={{ width: 'var(--icon-sm)', height: 'var(--icon-sm)', color: 'var(--blue-primary)', flexShrink: 0 }} />
            <div>
              <p className="process-card__title" style={{ margin: 0 }}>Process RFI</p>
              <p className="process-card__description" style={{ margin: 0 }}>Paste an ACC RFI ID to generate a proposal instantly</p>
            </div>
          </div>
          <form
            style={{ display: 'flex', gap: 'var(--space-sm)' }}
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
              className="process-card__input"
              style={{ flex: 1 }}
              disabled={processRfiMutation.isPending}
            />
            <button
              type="submit"
              disabled={!rfiInput.trim() || processRfiMutation.isPending}
              className="btn-primary"
              style={{ display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap', opacity: (!rfiInput.trim() || processRfiMutation.isPending) ? 0.4 : 1, cursor: (!rfiInput.trim() || processRfiMutation.isPending) ? 'not-allowed' : 'pointer' }}
            >
              {processRfiMutation.isPending
                ? <><Loader2 style={{ width: 14, height: 14, animation: 'spin 1s linear infinite' }} /> Processing…</>
                : <><Zap style={{ width: 14, height: 14 }} /> Generate</>
              }
            </button>
          </form>
        </div>

        {/* Proposal list */}
        {isLoading ? (
          <SkeletonList />
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: 'var(--space-sm)' }}>
            {pending.length === 0
              ? <EmptyState />
              : pending.map(proposal => (
                  <ProposalCard
                    key={proposal.id}
                    proposal={proposal}
                    onApprove={() => approveMutation.mutate(proposal.id)}
                    onReject={(reason) => rejectMutation.mutate({ id: proposal.id, reason })}
                    isApproving={approveMutation.isPending && approveMutation.variables === proposal.id}
                    isRejecting={rejectMutation.isPending && rejectMutation.variables?.id === proposal.id}
                  />
                ))
            }
          </div>
        )}

      </main>

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  )
}

// ── Stat item ──────────────────────────────────────────────────────────────────
function StatItem({ icon: Icon, value }) {
  return (
    <div className="stat-item">
      <Icon className="stat-item__icon" style={{ width: 'var(--icon-md)', height: 'var(--icon-md)' }} />
      <span>{value}</span>
    </div>
  )
}

// ── Skeleton ───────────────────────────────────────────────────────────────────
function SkeletonList() {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: 'var(--space-sm)' }}>
      {[0, 1, 2, 3].map(i => (
        <div key={i} className="animate-fade-in" style={{ background: 'var(--white)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--gray-200)', padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div className="skeleton" style={{ height: 14, width: '75%' }} />
            <div className="skeleton" style={{ height: 12, width: '40%' }} />
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
            <div className="skeleton" style={{ height: 24, width: 56, borderRadius: 9999 }} />
            <div className="skeleton" style={{ height: 20, width: 48, borderRadius: 9999 }} />
          </div>
        </div>
      ))}
    </div>
  )
}
