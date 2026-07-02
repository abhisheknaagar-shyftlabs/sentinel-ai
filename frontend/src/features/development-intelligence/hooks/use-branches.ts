import { useQuery } from '@tanstack/react-query'
import { compareBranches, fetchBranches } from '../api/dev-intelligence.api'

export function useBranches() {
  return useQuery({
    queryKey: ['development-intelligence', 'branches'],
    queryFn: fetchBranches,
  })
}

export function useBranchComparison(base: string, head: string) {
  return useQuery({
    queryKey: ['development-intelligence', 'compare', base, head],
    queryFn: () => compareBranches(base, head),
    enabled: Boolean(base && head),
    // This runs a real (slow, real-money) AI review server-side - the
    // global retry:1 default would silently double both the wait and the
    // API spend on every failure, including guaranteed-to-fail-again ones
    // like a quota error. Fail once, show it, let the user retry manually.
    retry: false,
  })
}
