import { useQuery } from '@tanstack/react-query'
import { fetchExecIntelligenceSummary } from '../api/exec-intelligence.api'

export function useExecIntelligenceSummary() {
  return useQuery({
    queryKey: ['executive-intelligence', 'summary'],
    queryFn: fetchExecIntelligenceSummary,
  })
}
