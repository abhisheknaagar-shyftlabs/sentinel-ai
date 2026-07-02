import type { ConnectionStatus } from '@/types/common'

export type IntegrationCategory = 'source-control' | 'containers' | 'metrics' | 'dashboards'

export interface Integration {
  id: string
  name: string
  description: string
  category: IntegrationCategory
  status: ConnectionStatus
  connectedAccount?: string
  lastSyncedAt?: string
  /** Only set right after a connect call that also requested a repo to track. */
  repositoryTracked?: string
  repositoryError?: string
}
