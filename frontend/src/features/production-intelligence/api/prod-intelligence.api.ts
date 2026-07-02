import { httpClient } from '@/services/http-client'
import type { ProdIntelligenceSummary } from '../types'

export async function fetchProdIntelligenceSummary(): Promise<ProdIntelligenceSummary> {
  return httpClient.get<ProdIntelligenceSummary>('/production-intelligence/summary')
}
