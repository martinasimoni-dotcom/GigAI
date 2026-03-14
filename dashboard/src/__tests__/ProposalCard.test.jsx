import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ProposalCard } from '../components/ProposalCard.jsx'

const mockProposal = {
  id: 'p1',
  alert: { title: 'Aluminum to Wood Window Substitution', summary: '12 units, 3rd floor' },
  actions: [
    { action_type: 'email', description: 'Email Jane at Premium Wood Co.' },
    { action_type: 'task', description: 'Procurement task for Mike' },
  ],
  confidence_score: 86,
  recommendation: 'Accept',
  created_at: '2026-03-13T10:00:00Z',
}

describe('ProposalCard', () => {
  it('renders alert title and confidence score', () => {
    render(<ProposalCard proposal={mockProposal} submitDecision={vi.fn()} decisionStateEntry={undefined} onRemove={vi.fn()} onDecided={vi.fn()} />)
    expect(screen.getByText('Aluminum to Wood Window Substitution')).toBeInTheDocument()
    expect(screen.getByText('86%')).toBeInTheDocument()
  })

  it('renders recommendation badge', () => {
    render(<ProposalCard proposal={mockProposal} submitDecision={vi.fn()} decisionStateEntry={undefined} onRemove={vi.fn()} onDecided={vi.fn()} />)
    // Badge is a span; Accept button also exists — use getAllByText and check at least one is a span
    const matches = screen.getAllByText('Accept')
    expect(matches.some((el) => el.tagName === 'SPAN')).toBe(true)
  })

  it('Accept button calls submitDecision with accept decision', async () => {
    const submitDecision = vi.fn().mockResolvedValue(undefined)
    render(<ProposalCard proposal={mockProposal} submitDecision={submitDecision} decisionStateEntry={undefined} onRemove={vi.fn()} onDecided={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /accept/i }))
    expect(submitDecision).toHaveBeenCalledWith('p1', 'accept', null)
  })

  it('Reject button shows reason textarea', () => {
    render(<ProposalCard proposal={mockProposal} submitDecision={vi.fn()} decisionStateEntry={undefined} onRemove={vi.fn()} onDecided={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /reject/i }))
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('shows action results after decided state', () => {
    const decidedState = {
      decided: true,
      decision: 'accept',
      actionResults: [
        { action_type: 'email', status: 'success', message: 'Email sent', error: null },
      ],
    }
    render(<ProposalCard proposal={mockProposal} submitDecision={vi.fn()} decisionStateEntry={decidedState} onRemove={vi.fn()} onDecided={vi.fn()} />)
    expect(screen.getByText(/Email sent/)).toBeInTheDocument()
  })
})
