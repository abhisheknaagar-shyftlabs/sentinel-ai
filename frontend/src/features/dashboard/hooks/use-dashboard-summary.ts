import { useQuery } from '@tanstack/react-query'
import { fetchDashboardSummary } from '../api/dashboard.api'

export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: fetchDashboardSummary,
  })
}
