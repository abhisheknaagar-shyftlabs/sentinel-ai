import { useQuery } from '@tanstack/react-query'
import { fetchProdIntelligenceSummary } from '../api/prod-intelligence.api'

export function useProdIntelligenceSummary() {
  return useQuery({
    queryKey: ['production-intelligence', 'summary'],
    queryFn: fetchProdIntelligenceSummary,
  })
}
