import { useQuery } from '@tanstack/react-query'
import { fetchDevIntelligenceSummary } from '../api/dev-intelligence.api'

export const DEV_INTELLIGENCE_SUMMARY_KEY = ['development-intelligence', 'summary']
const SUMMARY_KEY = DEV_INTELLIGENCE_SUMMARY_KEY

export function useDevIntelligenceSummary() {
  return useQuery({
    queryKey: SUMMARY_KEY,
    queryFn: fetchDevIntelligenceSummary,
  })
}
