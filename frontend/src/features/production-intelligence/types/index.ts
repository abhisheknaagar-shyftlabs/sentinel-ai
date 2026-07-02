import type { HealthStatus, IncidentSeverity, IncidentStatus, Trend } from '@/types/common'

export type LogLevel = 'info' | 'warn' | 'error' | 'debug'

export interface Container {
  id: string
  name: string
  status: HealthStatus
  cpuPercent: number
  memoryPercent: number
  uptime: string
  restarts: number
}

export interface LogEntry {
  id: string
  timestamp: string
  level: LogLevel
  service: string
  message: string
}

export interface Incident {
  id: string
  title: string
  service: string
  severity: IncidentSeverity
  status: IncidentStatus
  rootCause?: string
  autoRecovered: boolean
  startedAt: string
}

export interface ProdIntelligenceStats {
  containersHealthy: number
  containersTotal: number
  openIncidents: number
  openIncidentsTrend: Trend
  autoRecoveriesToday: number
  avgRecoveryTimeMinutes: number
  avgRecoveryTrend: Trend
}

export interface ProdIntelligenceSummary {
  stats: ProdIntelligenceStats
  containers: Container[]
  logs: LogEntry[]
  incidents: Incident[]
}
