import { renderHook, act, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useProposals } from '../hooks/useProposals.js'
import * as api from '../api.js'

describe('useProposals', () => {
  const mockProposal = { id: 'p1', confidence_score: 86, alert: { title: 'Test' }, actions: [], recommendation: 'Accept', created_at: '2026-03-13T10:00:00Z' }

  beforeEach(() => {
    vi.spyOn(api, 'fetchProposals').mockResolvedValue([mockProposal])
    const fakeES = { onmessage: null, close: vi.fn() }
    vi.spyOn(api, 'subscribeToEvents').mockImplementation((cb) => {
      fakeES._cb = cb
      return fakeES
    })
  })

  it('fetches proposals on mount', async () => {
    const { result } = renderHook(() => useProposals())
    await waitFor(() => expect(result.current.proposals).toHaveLength(1))
    expect(result.current.proposals[0].id).toBe('p1')
  })

  it('subscribes to SSE events on mount', async () => {
    renderHook(() => useProposals())
    await waitFor(() => expect(api.subscribeToEvents).toHaveBeenCalled())
  })
})
