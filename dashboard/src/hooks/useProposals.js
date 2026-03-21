import { useState, useEffect } from 'react'
import { fetchProposals, subscribeToEvents } from '../api.js'

export function useProposals() {
  const [proposals, setProposals] = useState([])

  useEffect(() => {
    fetchProposals().then(setProposals)

    const es = subscribeToEvents((newProposal) => {
      setProposals((prev) => [newProposal, ...prev])
    })

    return () => es.close()
  }, [])

  return { proposals, setProposals }
}
