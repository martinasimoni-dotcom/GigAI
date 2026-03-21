import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { AuditLog } from '../components/AuditLog.jsx'

describe('AuditLog', () => {
  it('renders empty state when no decisions', () => {
    render(<AuditLog decisions={[]} />)
    // Text is split by <br/>, so match partial text
    expect(screen.getByText(/No decisions yet/)).toBeInTheDocument()
  })

  it('renders decision title, badge, confidence and timestamp', () => {
    const decisions = [
      { proposalId: 'p1', title: 'Window Change', decision: 'accept', confidence_score: 86, timestamp: '2026-03-13T10:00:00Z' },
    ]
    render(<AuditLog decisions={decisions} />)
    expect(screen.getByText('Window Change')).toBeInTheDocument()
    expect(screen.getByText('Accepted')).toBeInTheDocument()
    // Score and % are in the same span: "86%"
    expect(screen.getByText('86%')).toBeInTheDocument()
  })

  it('renders newest decision first', () => {
    const decisions = [
      { proposalId: 'p1', title: 'Older Change', decision: 'reject', confidence_score: 40, timestamp: '2026-03-12T08:00:00Z' },
      { proposalId: 'p2', title: 'Newer Change', decision: 'accept', confidence_score: 90, timestamp: '2026-03-13T12:00:00Z' },
    ]
    render(<AuditLog decisions={decisions} />)
    // audit-item divs are rendered in sorted order — get all item titles
    const titles = screen.getAllByText(/Change$/).map((el) => el.textContent)
    expect(titles[0]).toBe('Newer Change')
    expect(titles[1]).toBe('Older Change')
  })
})
