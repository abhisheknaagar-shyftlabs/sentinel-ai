import { httpClient } from '@/services/http-client'
import type { DashboardSummary } from '../types'

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  return httpClient.get<DashboardSummary>('/dashboard/summary')
}
