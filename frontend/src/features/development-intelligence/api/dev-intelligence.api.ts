import { ApiError, httpClient } from '@/services/http-client'
import type { Branch, BranchComparison, DevIntelligenceSummary } from '../types'

export async function fetchDevIntelligenceSummary(): Promise<DevIntelligenceSummary> {
  return httpClient.get<DevIntelligenceSummary>('/development-intelligence/summary')
}

export async function fetchBranches(): Promise<Branch[]> {
  return httpClient.get<Branch[]>('/development-intelligence/branches')
}

interface CompareJobStart {
  jobId: string
  status: string
}

interface CompareJobStatus {
  jobId: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  result: BranchComparison | null
  error: string | null
}

const POLL_INTERVAL_MS = 2000
// ~260s - comfortably covers the backend's own worst-case retry budget
// (LLM_REQUEST_TIMEOUT x LLM_MAX_RETRIES, see CLAUDE.md) so this doesn't
// give up on a job that's still genuinely running.
const MAX_POLL_ATTEMPTS = 130

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/** The real comparison is a real AI call that can take anywhere from a few
 * seconds to a few minutes. Rather than holding one HTTP request open for
 * that whole time - which most production load balancers/reverse proxies
 * will kill well before it finishes, regardless of the backend's own
 * timeout settings - this starts a background job and polls for the
 * result. The external contract is unchanged from the old synchronous
 * version: callers still just get back a Promise<BranchComparison>, so
 * useBranchComparison/BranchComparisonPanel need no changes at all. */
export async function compareBranches(base: string, head: string): Promise<BranchComparison> {
  const { jobId } = await httpClient.post<CompareJobStart>(
    `/development-intelligence/compare/jobs?base=${encodeURIComponent(base)}&head=${encodeURIComponent(head)}`,
  )

  for (let attempt = 0; attempt < MAX_POLL_ATTEMPTS; attempt++) {
    await sleep(POLL_INTERVAL_MS)
    const job = await httpClient.get<CompareJobStatus>(
      `/development-intelligence/compare/jobs/${jobId}`,
    )
    if (job.status === 'completed' && job.result) return job.result
    if (job.status === 'failed') throw new ApiError(job.error ?? 'Comparison failed', 500)
  }

  throw new ApiError('Comparison timed out waiting for a result', 504)
}
