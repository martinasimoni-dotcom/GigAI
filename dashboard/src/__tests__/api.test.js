import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fetchProposals, postDecision, subscribeToEvents } from '../api.js'

describe('fetchProposals', () => {
  it('calls GET /api/proposals and returns JSON array', async () => {
    const mockData = [{ id: 'p1', confidence_score: 86 }]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    }))
    const result = await fetchProposals()
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/api/proposals')
    expect(result).toEqual(mockData)
    vi.unstubAllGlobals()
  })
})

describe('postDecision', () => {
  it('POSTs accept decision with null reason', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'ok' }),
    }))
    await postDecision('prop-1', 'accept', null)
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/proposals/prop-1/decision',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ decision: 'accept', reason: null }),
      })
    )
    vi.unstubAllGlobals()
  })

  it('POSTs reject decision with reason string', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'ok' }),
    }))
    await postDecision('prop-2', 'reject', 'Wrong supplier')
    const body = JSON.parse(fetch.mock.calls[0][1].body)
    expect(body.decision).toBe('reject')
    expect(body.reason).toBe('Wrong supplier')
    vi.unstubAllGlobals()
  })
})

describe('subscribeToEvents', () => {
  it('creates EventSource on /api/events and calls callback with parsed data', () => {
    const listeners = {}
    const fakeES = {
      onmessage: null,
      onerror: null,
      close: vi.fn(),
      addEventListener: vi.fn((event, handler) => { listeners[event] = handler }),
    }
    vi.stubGlobal('EventSource', vi.fn(() => fakeES))
    const callback = vi.fn()
    const es = subscribeToEvents(callback)
    expect(EventSource).toHaveBeenCalledWith('http://localhost:8000/api/events')

    // Simulate typed 'proposal' SSE event
    listeners.proposal({ data: JSON.stringify({ id: 'p1' }) })
    expect(callback).toHaveBeenCalledWith({ id: 'p1' })

    // Also test generic onmessage fallback
    fakeES.onmessage({ data: JSON.stringify({ id: 'p2' }) })
    expect(callback).toHaveBeenCalledWith({ id: 'p2' })

    expect(es).toBe(fakeES)
    vi.unstubAllGlobals()
  })
})
