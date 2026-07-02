import type { HealthStatus, RiskLevel, Trend } from '@/types/common'
import type { TimelineItem } from '@/components/shared'

export interface DashboardStats {
  openPRsAtRisk: number
  openPRsAtRiskTrend: Trend
  containersHealthy: number
  containersTotal: number
  openIncidents: number
  openIncidentsTrend: Trend
  engineeringHealthScore: number
  engineeringHealthTrend: Trend
  infraCostMonthly: number
  infraCostTrend: Trend
  deploymentConfidencePercent: number
  deploymentConfidenceTrend: Trend
}

export interface DevelopmentSnapshot {
  headline: string
  detail: string
  risk: RiskLevel
}

export interface ProductionSnapshot {
  headline: string
  detail: string
  health: HealthStatus
}

export interface ExecutiveSnapshot {
  headline: string
  detail: string
  trend: Trend
}

export interface DashboardSummary {
  stats: DashboardStats
  developmentSnapshot: DevelopmentSnapshot
  productionSnapshot: ProductionSnapshot
  executiveSnapshot: ExecutiveSnapshot
  healthTrend: { label: string; value: number }[]
  recentActivity: TimelineItem[]
}
