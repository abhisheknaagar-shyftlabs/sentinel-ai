export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'

export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy' | 'unknown'

export type DeploymentConfidence = 'safe' | 'caution' | 'blocked'

export type IncidentSeverity = 'sev1' | 'sev2' | 'sev3' | 'sev4'

export type IncidentStatus = 'open' | 'investigating' | 'resolved' | 'monitoring'

export type TrendDirection = 'up' | 'down' | 'flat'

export type ConnectionStatus = 'connected' | 'disconnected' | 'error' | 'pending'

export interface TrendPoint {
  label: string
  value: number
}

export interface Trend {
  direction: TrendDirection
  changePercent: number
  isPositive: boolean
}
