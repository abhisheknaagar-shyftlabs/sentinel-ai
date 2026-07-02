import { httpClient } from '@/services/http-client'
import type { ExecIntelligenceSummary } from '../types'

export async function fetchExecIntelligenceSummary(): Promise<ExecIntelligenceSummary> {
  return httpClient.get<ExecIntelligenceSummary>('/executive-intelligence/summary')
}
