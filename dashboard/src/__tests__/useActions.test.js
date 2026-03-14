import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useActions } from '../hooks/useActions.js'
import * as api from '../api.js'

describe('useActions', () => {
  const mockResult = {
    proposal_id: 'p1',
    results: [{ action_type: 'email', status: 'success', message: 'Email sent', error: null }],
    success_count: 1,
    failure_count: 0,
  }

  beforeEach(() => {
    vi.spyOn(api, 'postDecision').mockResolvedValue(mockResult)
  })

  it('submitDecision calls postDecision and stores result in decisionState', async () => {
    const { result } = renderHook(() => useActions())
    await act(() => result.current.submitDecision('p1', 'accept', null))
    const state = result.current.decisionState.get('p1')
    expect(state.decided).toBe(true)
    expect(state.decision).toBe('accept')
    expect(state.actionResults).toHaveLength(1)
    expect(state.actionResults[0].action_type).toBe('email')
  })

  it('stores error in decisionState on postDecision failure', async () => {
    vi.spyOn(api, 'postDecision').mockRejectedValue(new Error('Network error'))
    const { result } = renderHook(() => useActions())
    await act(() => result.current.submitDecision('p1', 'reject', 'bad'))
    const state = result.current.decisionState.get('p1')
    expect(state.error).toBe('Network error')
    expect(state.decided).toBeFalsy()
  })
})
